// Copyright (C) 2026 Stremio for Vero 4K+ contributors

import { useCallback, useEffect, useState } from 'react';

const SETTINGS_ENDPOINT = 'http://127.0.0.1:47821/v1/settings';

export type VeroSettings = {
    picture: {
        adjustRefreshRate: 'off' | 'always' | 'startStop' | 'start',
        hdrMode: 'passthrough' | 'hdrToSdr' | 'auto' | 'hdrToBt2020Sdr',
        syncPlaybackToDisplay: boolean,
        hardwareDecoding: boolean,
    },
    audio: {
        preferredLanguage: string,
        channels: '2.0' | '2.1' | '3.0' | '3.1' | '4.0' | '4.1' | '5.0' | '5.1' | '7.0' | '7.1',
        passthrough: boolean,
        ac3: boolean,
        eac3: boolean,
        dts: boolean,
        truehd: boolean,
        dtshd: boolean,
    },
    subtitles: {
        preferredLanguage: string,
        fontSize: number,
        textColor: string,
        backgroundColor: string,
        verticalMargin: number,
    },
    device: {
        cecEnabled: boolean,
        automaticUpdates: boolean,
    },
};

export type VeroSettingsPatch = {
    picture?: Partial<VeroSettings['picture']>,
    audio?: Partial<VeroSettings['audio']>,
    subtitles?: Partial<VeroSettings['subtitles']>,
    device?: Partial<VeroSettings['device']>,
};

export type VeroCapabilities = {
    kodiSettings: boolean,
    network: boolean,
    bluetooth: boolean,
    cec: boolean,
    osmcUpdates: boolean,
};

type SettingsResponse = {
    apiVersion: number,
    values: VeroSettings,
    capabilities?: VeroCapabilities,
    adjustments?: string[],
};

const useVeroSettings = () => {
    const [values, setValues] = useState<VeroSettings | null>(null);
    const [capabilities, setCapabilities] = useState<VeroCapabilities | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [busy, setBusy] = useState(false);

    const load = useCallback(async () => {
        try {
            const response = await fetch(SETTINGS_ENDPOINT);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const body = await response.json() as SettingsResponse;
            setValues(body.values);
            setCapabilities(body.capabilities ?? null);
            setError(null);
        } catch (reason) {
            setError(reason instanceof Error ? reason.message : 'Vero Settings unavailable');
        }
    }, []);

    const update = useCallback(async (patch: VeroSettingsPatch) => {
        setBusy(true);
        try {
            const response = await fetch(SETTINGS_ENDPOINT, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ values: patch }),
            });
            const body = await response.json() as SettingsResponse & { error?: string };
            if (!response.ok) throw new Error(body.error ?? `HTTP ${response.status}`);
            setValues(body.values);
            setError(null);
        } catch (reason) {
            setError(reason instanceof Error ? reason.message : 'Vero Settings unavailable');
        } finally {
            setBusy(false);
        }
    }, []);

    useEffect(() => {
        void load();
    }, [load]);

    return { values, capabilities, error, busy, update, reload: load };
};

export default useVeroSettings;
