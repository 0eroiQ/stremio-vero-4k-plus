#!/usr/bin/env python3
"""Local Stremio-to-OSMC/Kodi settings bridge.

The HTTP service binds only to loopback. Settings are validated against a
small allowlist and stored atomically. Kodi values are queued while Kodi is
stopped and can be applied through its local JSON-RPC endpoint immediately
before playback starts.
"""

from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Callable
import urllib.error
import urllib.request


API_VERSION = 1
DEFAULT_BIND = "127.0.0.1"
DEFAULT_PORT = 47821
DEFAULT_STATE_PATH = Path("/var/lib/stremio-vero/settings.json")

DEFAULT_SETTINGS: dict[str, Any] = {
    "picture": {
        "adjustRefreshRate": "startStop",
        "hdrMode": "auto",
        "syncPlaybackToDisplay": False,
        "hardwareDecoding": True,
    },
    "audio": {
        "preferredLanguage": "original",
        "channels": "2.0",
        "passthrough": False,
        "ac3": True,
        "eac3": False,
        "dts": False,
        "truehd": False,
        "dtshd": False,
    },
    "subtitles": {
        "preferredLanguage": "original",
        "fontSize": 42,
        "textColor": "FFFFFFFF",
        "backgroundColor": "FF000000",
        "verticalMargin": 4.95,
    },
    "device": {
        "cecEnabled": True,
        "automaticUpdates": False,
    },
}


def _choice(*values: object) -> Callable[[Any], bool]:
    allowed = set(values)
    return lambda value: value in allowed


def _integer_between(low: int, high: int, step: int = 1) -> Callable[[Any], bool]:
    return lambda value: (
        isinstance(value, int)
        and not isinstance(value, bool)
        and low <= value <= high
        and (value - low) % step == 0
    )


def _number_between(low: float, high: float) -> Callable[[Any], bool]:
    return lambda value: (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and low <= float(value) <= high
    )


def _argb(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 8
        and all(character in "0123456789abcdefABCDEF" for character in value)
    )


FIELD_VALIDATORS: dict[str, Callable[[Any], bool]] = {
    "picture.adjustRefreshRate": _choice("off", "always", "startStop", "start"),
    "picture.hdrMode": _choice("passthrough", "hdrToSdr", "auto", "hdrToBt2020Sdr"),
    "picture.syncPlaybackToDisplay": lambda value: isinstance(value, bool),
    "picture.hardwareDecoding": lambda value: isinstance(value, bool),
    "audio.preferredLanguage": lambda value: isinstance(value, str) and 1 <= len(value) <= 64,
    "audio.channels": _choice("2.0", "2.1", "3.0", "3.1", "4.0", "4.1", "5.0", "5.1", "7.0", "7.1"),
    "audio.passthrough": lambda value: isinstance(value, bool),
    "audio.ac3": lambda value: isinstance(value, bool),
    "audio.eac3": lambda value: isinstance(value, bool),
    "audio.dts": lambda value: isinstance(value, bool),
    "audio.truehd": lambda value: isinstance(value, bool),
    "audio.dtshd": lambda value: isinstance(value, bool),
    "subtitles.preferredLanguage": lambda value: isinstance(value, str) and 1 <= len(value) <= 64,
    "subtitles.fontSize": _integer_between(12, 74, 2),
    "subtitles.textColor": _argb,
    "subtitles.backgroundColor": _argb,
    "subtitles.verticalMargin": _number_between(0.0, 50.0),
    "device.cecEnabled": lambda value: isinstance(value, bool),
    "device.automaticUpdates": lambda value: isinstance(value, bool),
}


REFRESH_RATE_VALUES = {"off": 0, "always": 1, "startStop": 2, "start": 3}
HDR_VALUES = {"passthrough": 0, "hdrToSdr": 1, "auto": 2, "hdrToBt2020Sdr": 3}
CHANNEL_VALUES = {
    "2.0": 1,
    "2.1": 2,
    "3.0": 3,
    "3.1": 4,
    "4.0": 5,
    "4.1": 6,
    "5.0": 7,
    "5.1": 8,
    "7.0": 9,
    "7.1": 10,
}

KODI_SETTINGS: dict[str, tuple[str, Callable[[Any], Any]]] = {
    "picture.adjustRefreshRate": ("videoplayer.adjustrefreshrate", REFRESH_RATE_VALUES.__getitem__),
    "picture.hdrMode": ("videoplayer.amlhdrmodes", HDR_VALUES.__getitem__),
    "picture.syncPlaybackToDisplay": ("videoplayer.usedisplayasclock", bool),
    "picture.hardwareDecoding": ("videoplayer.useamcodec", bool),
    "audio.preferredLanguage": ("locale.audiolanguage", str),
    "audio.channels": ("audiooutput.channels", CHANNEL_VALUES.__getitem__),
    "audio.passthrough": ("audiooutput.passthrough", bool),
    "audio.ac3": ("audiooutput.ac3passthrough", bool),
    "audio.eac3": ("audiooutput.eac3passthrough", bool),
    "audio.dts": ("audiooutput.dtspassthrough", bool),
    "audio.truehd": ("audiooutput.truehdpassthrough", bool),
    "audio.dtshd": ("audiooutput.dtshdpassthrough", bool),
    "subtitles.preferredLanguage": ("locale.subtitlelanguage", str),
    "subtitles.fontSize": ("subtitles.fontsize", int),
    "subtitles.textColor": ("subtitles.colorpick", str),
    "subtitles.backgroundColor": ("subtitles.bgcolorpick", str),
    "subtitles.verticalMargin": ("subtitles.marginvertical", float),
}


class SettingsError(ValueError):
    """A rejected settings update."""


def flatten(values: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in values.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            output.update(flatten(value, path))
        else:
            output[path] = value
    return output


def assign_path(values: dict[str, Any], path: str, value: Any) -> None:
    section, key = path.split(".", 1)
    values[section][key] = value


def get_path(values: dict[str, Any], path: str) -> Any:
    section, key = path.split(".", 1)
    return values[section][key]


def validate_patch(patch: Any) -> dict[str, Any]:
    if not isinstance(patch, dict) or not patch:
        raise SettingsError("values must be a non-empty object")
    flat = flatten(patch)
    for path, value in flat.items():
        validator = FIELD_VALIDATORS.get(path)
        if validator is None:
            raise SettingsError(f"unsupported setting: {path}")
        if not validator(value):
            raise SettingsError(f"invalid value for {path}: {value!r}")
    return flat


def normalize(values: dict[str, Any]) -> list[str]:
    adjustments: list[str] = []
    if values["audio"]["passthrough"] and values["picture"]["syncPlaybackToDisplay"]:
        values["picture"]["syncPlaybackToDisplay"] = False
        adjustments.append("picture.syncPlaybackToDisplay disabled because passthrough is enabled")
    return adjustments


class SettingsStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> dict[str, Any]:
        values = copy.deepcopy(DEFAULT_SETTINGS)
        if not self.path.exists():
            return values
        parsed = json.loads(self.path.read_text(encoding="utf-8"))
        flat = validate_patch(parsed)
        for path, value in flat.items():
            assign_path(values, path, value)
        normalize(values)
        return values

    def update(self, patch: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        flat = validate_patch(patch)
        values = self.load()
        for path, value in flat.items():
            assign_path(values, path, value)
        adjustments = normalize(values)
        self.save(values)
        return values, adjustments

    def save(self, values: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix="settings-", suffix=".json", dir=self.path.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(values, stream, indent=2, sort_keys=True)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, self.path)
        finally:
            temporary.unlink(missing_ok=True)


@dataclass
class KodiApplyResult:
    applied: list[str]
    unavailable: list[str]


class KodiClient:
    def __init__(self, url: str = "http://127.0.0.1:8080/jsonrpc", timeout: float = 2.0):
        self.url = url
        self.timeout = timeout
        self.request_id = 0

    def call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        self.request_id += 1
        body = json.dumps({
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {},
        }).encode("utf-8")
        request = urllib.request.Request(
            self.url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
        if "error" in result:
            raise RuntimeError(f"Kodi JSON-RPC {method} failed: {result['error']}")
        return result.get("result")

    def available_setting_ids(self) -> set[str]:
        result = self.call("Settings.GetSettings", {"level": "expert"})
        return {setting["id"] for setting in result.get("settings", [])}

    def apply(self, values: dict[str, Any]) -> KodiApplyResult:
        available = self.available_setting_ids()
        applied: list[str] = []
        unavailable: list[str] = []
        flat = flatten(values)
        for path, (setting_id, convert) in KODI_SETTINGS.items():
            if setting_id not in available:
                unavailable.append(setting_id)
                continue
            self.call(
                "Settings.SetSettingValue",
                {"setting": setting_id, "value": convert(flat[path])},
            )
            applied.append(setting_id)
        return KodiApplyResult(applied=applied, unavailable=unavailable)


class BridgeHandler(BaseHTTPRequestHandler):
    server_version = "StremioVeroSettings/0.1"
    store: SettingsStore

    def _origin(self) -> str | None:
        origin = self.headers.get("Origin")
        allowed = {
            "http://127.0.0.1:8080",
            "http://127.0.0.1:8765",
            "http://127.0.0.1:11470",
            "http://localhost:8080",
            "http://localhost:8765",
            "http://localhost:11470",
        }
        return origin if origin in allowed else None

    def _send(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        origin = self._origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        origin = self._origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "GET, PATCH, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Vary", "Origin")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/v1/health":
            self._send(HTTPStatus.OK, {"apiVersion": API_VERSION, "status": "ready"})
            return
        if self.path == "/v1/settings":
            self._send(HTTPStatus.OK, {
                "apiVersion": API_VERSION,
                "values": self.store.load(),
                "capabilities": {
                    "kodiSettings": True,
                    "network": False,
                    "bluetooth": False,
                    "cec": False,
                    "osmcUpdates": False,
                },
            })
            return
        self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_PATCH(self) -> None:  # noqa: N802
        if self.path != "/v1/settings":
            self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 2 or length > 64 * 1024:
                raise SettingsError("invalid request size")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if set(payload) != {"values"}:
                raise SettingsError("request must contain only values")
            values, adjustments = self.store.update(payload["values"])
        except (SettingsError, json.JSONDecodeError, UnicodeDecodeError) as error:
            self._send(HTTPStatus.BAD_REQUEST, {"error": str(error)})
            return
        self._send(HTTPStatus.OK, {
            "apiVersion": API_VERSION,
            "values": values,
            "adjustments": adjustments,
        })

    def log_message(self, format: str, *args: object) -> None:
        print(f"settings-bridge: {format % args}")


def serve(path: Path, bind: str, port: int) -> None:
    if bind not in {"127.0.0.1", "::1", "localhost"}:
        raise SystemExit("refusing non-loopback bind address")
    BridgeHandler.store = SettingsStore(path)
    server = ThreadingHTTPServer((bind, port), BridgeHandler)
    print(f"settings-bridge listening on http://{bind}:{port}")
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--bind", default=DEFAULT_BIND)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--apply-kodi", action="store_true")
    parser.add_argument("--kodi-url", default="http://127.0.0.1:8080/jsonrpc")
    args = parser.parse_args()

    if args.apply_kodi:
        try:
            result = KodiClient(args.kodi_url).apply(SettingsStore(args.state).load())
        except (OSError, urllib.error.URLError, RuntimeError) as error:
            raise SystemExit(f"Kodi settings unavailable: {error}") from error
        print(json.dumps({"applied": result.applied, "unavailable": result.unavailable}))
        return
    serve(args.state, args.bind, args.port)


if __name__ == "__main__":
    main()
