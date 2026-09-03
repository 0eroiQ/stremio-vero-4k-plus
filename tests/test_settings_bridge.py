from __future__ import annotations

import json
from http.server import ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.request

from runtime.settings_bridge.bridge import (
    DEFAULT_SETTINGS,
    BridgeHandler,
    KodiClient,
    SettingsError,
    SettingsStore,
    validate_patch,
)


class SettingsStoreTests(unittest.TestCase):
    def test_packaged_defaults_match_bridge_defaults(self) -> None:
        packaged = json.loads(
            (Path(__file__).resolve().parents[1] / "runtime" / "settings_bridge" / "default-settings.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(packaged, DEFAULT_SETTINGS)

    def test_missing_file_returns_safe_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory) / "settings.json")
            self.assertEqual(store.load(), DEFAULT_SETTINGS)

    def test_update_is_persisted_as_complete_document(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "settings.json"
            values, adjustments = SettingsStore(state).update({
                "picture": {"hdrMode": "passthrough"},
                "audio": {"channels": "5.1"},
            })
            self.assertEqual(adjustments, [])
            self.assertEqual(values["picture"]["hdrMode"], "passthrough")
            self.assertEqual(values["audio"]["channels"], "5.1")
            persisted = json.loads(state.read_text(encoding="utf-8"))
            self.assertEqual(persisted, values)
            self.assertEqual(state.stat().st_mode & 0o777, 0o600)

    def test_passthrough_disables_sync_to_display(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory) / "settings.json")
            values, adjustments = store.update({
                "picture": {"syncPlaybackToDisplay": True},
                "audio": {"passthrough": True},
            })
            self.assertFalse(values["picture"]["syncPlaybackToDisplay"])
            self.assertEqual(len(adjustments), 1)

    def test_unknown_and_invalid_values_are_rejected(self) -> None:
        with self.assertRaisesRegex(SettingsError, "unsupported setting"):
            validate_patch({"danger": {"eraseStorage": True}})
        with self.assertRaisesRegex(SettingsError, "invalid value"):
            validate_patch({"subtitles": {"fontSize": 13}})


class SettingsBridgeHttpTests(unittest.TestCase):
    def test_loopback_api_reads_and_updates_settings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            BridgeHandler.store = SettingsStore(Path(directory) / "settings.json")
            server = ThreadingHTTPServer(("127.0.0.1", 0), BridgeHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            endpoint = f"http://127.0.0.1:{server.server_port}/v1/settings"
            try:
                with urllib.request.urlopen(endpoint, timeout=2) as response:
                    current = json.loads(response.read())
                self.assertEqual(current["values"]["picture"]["hdrMode"], "auto")

                request = urllib.request.Request(
                    endpoint,
                    data=json.dumps({"values": {"audio": {"channels": "5.1"}}}).encode(),
                    headers={
                        "Content-Type": "application/json",
                        "Origin": "http://127.0.0.1:8765",
                    },
                    method="PATCH",
                )
                with urllib.request.urlopen(request, timeout=2) as response:
                    updated = json.loads(response.read())
                    allowed_origin = response.headers["Access-Control-Allow-Origin"]
                self.assertEqual(updated["values"]["audio"]["channels"], "5.1")
                self.assertEqual(allowed_origin, "http://127.0.0.1:8765")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


class FakeKodiClient(KodiClient):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, dict[str, object]]] = []

    def call(self, method: str, params: dict[str, object] | None = None) -> object:
        params = params or {}
        self.calls.append((method, params))
        if method == "Settings.GetSettings":
            return {
                "settings": [
                    {"id": "videoplayer.adjustrefreshrate"},
                    {"id": "videoplayer.amlhdrmodes"},
                    {"id": "audiooutput.channels"},
                    {"id": "audiooutput.passthrough"},
                ]
            }
        return "OK"


class KodiSettingsMappingTests(unittest.TestCase):
    def test_allowlisted_values_map_to_exact_osmc_kodi_ids(self) -> None:
        client = FakeKodiClient()
        values = json.loads(json.dumps(DEFAULT_SETTINGS))
        values["picture"]["adjustRefreshRate"] = "startStop"
        values["picture"]["hdrMode"] = "auto"
        values["audio"]["channels"] = "5.1"
        values["audio"]["passthrough"] = True

        result = client.apply(values)
        updates = {
            params["setting"]: params["value"]
            for method, params in client.calls
            if method == "Settings.SetSettingValue"
        }

        self.assertEqual(updates["videoplayer.adjustrefreshrate"], 2)
        self.assertEqual(updates["videoplayer.amlhdrmodes"], 2)
        self.assertEqual(updates["audiooutput.channels"], 8)
        self.assertIs(updates["audiooutput.passthrough"], True)
        self.assertEqual(set(result.applied), set(updates))
        self.assertIn("subtitles.fontsize", result.unavailable)


if __name__ == "__main__":
    unittest.main()
