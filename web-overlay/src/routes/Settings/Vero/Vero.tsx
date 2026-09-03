// Copyright (C) 2026 Stremio for Vero 4K+ contributors

import React, { forwardRef } from 'react';
import { MultiselectMenu, Toggle } from 'stremio/components';
import { Category, Option, Section } from '../components';
import useVeroSettings, { VeroSettingsPatch } from './useVeroSettings';
import styles from './Vero.less';

type Choice = { value: string | number, label: string };

const refreshRateOptions: Choice[] = [
    { value: 'off', label: 'Off' },
    { value: 'startStop', label: 'On start / stop' },
    { value: 'start', label: 'On start' },
    { value: 'always', label: 'Always' },
];

const hdrOptions: Choice[] = [
    { value: 'auto', label: 'Automatic' },
    { value: 'passthrough', label: 'Pass through' },
    { value: 'hdrToSdr', label: 'Convert HDR to SDR' },
    { value: 'hdrToBt2020Sdr', label: 'Convert HDR to BT.2020 SDR' },
];

const channelOptions: Choice[] = ['2.0', '2.1', '3.0', '3.1', '4.0', '4.1', '5.0', '5.1', '7.0', '7.1']
    .map((value) => ({ value, label: value }));

const subtitleSizeOptions: Choice[] = Array.from({ length: 32 }, (_, index) => 12 + (index * 2))
    .map((value) => ({ value, label: `${value} px` }));

const Vero = forwardRef<HTMLDivElement>((_, ref) => {
    const { values, capabilities, error, busy, update } = useVeroSettings();
    const disabled = busy || values === null;
    const patch = (next: VeroSettingsPatch) => void update(next);

    return (
        <Section ref={ref} label={'Vero 4K+ Device'}>
            <div className={styles['status']}>
                <span className={error ? styles['offline'] : styles['online']} />
                {error ? `Vero Settings offline: ${error}` : 'Vero Settings connected'}
            </div>

            <Category icon={'glasses'} label={'Picture'}>
                <Option label={'Match display refresh rate'}>
                    <MultiselectMenu
                        className={'multiselect'}
                        disabled={disabled}
                        options={refreshRateOptions}
                        value={values?.picture.adjustRefreshRate}
                        onSelect={(value) => patch({ picture: { adjustRefreshRate: value } })}
                    />
                </Option>
                <Option label={'HDR mode'}>
                    <MultiselectMenu
                        className={'multiselect'}
                        disabled={disabled}
                        options={hdrOptions}
                        value={values?.picture.hdrMode}
                        onSelect={(value) => patch({ picture: { hdrMode: value } })}
                    />
                </Option>
                <Option label={'Hardware video decoding'}>
                    <Toggle
                        disabled={disabled}
                        checked={values?.picture.hardwareDecoding ?? false}
                        onClick={() => patch({ picture: { hardwareDecoding: !values?.picture.hardwareDecoding } })}
                    />
                </Option>
                <Option label={'Sync playback to display'}>
                    <Toggle
                        disabled={disabled || Boolean(values?.audio.passthrough)}
                        checked={values?.picture.syncPlaybackToDisplay ?? false}
                        onClick={() => patch({ picture: { syncPlaybackToDisplay: !values?.picture.syncPlaybackToDisplay } })}
                    />
                </Option>
            </Category>

            <Category icon={'volume-medium'} label={'HDMI audio'}>
                <Option label={'Speaker layout'}>
                    <MultiselectMenu
                        className={'multiselect'}
                        disabled={disabled}
                        options={channelOptions}
                        value={values?.audio.channels}
                        onSelect={(value) => patch({ audio: { channels: value } })}
                    />
                </Option>
                <Option label={'Audio passthrough'}>
                    <Toggle
                        disabled={disabled}
                        checked={values?.audio.passthrough ?? false}
                        onClick={() => patch({ audio: { passthrough: !values?.audio.passthrough } })}
                    />
                </Option>
                <Option label={'Dolby Digital (AC-3)'}>
                    <Toggle disabled={disabled} checked={values?.audio.ac3 ?? false} onClick={() => patch({ audio: { ac3: !values?.audio.ac3 } })} />
                </Option>
                <Option label={'Dolby Digital Plus (E-AC-3)'}>
                    <Toggle disabled={disabled} checked={values?.audio.eac3 ?? false} onClick={() => patch({ audio: { eac3: !values?.audio.eac3 } })} />
                </Option>
                <Option label={'DTS'}>
                    <Toggle disabled={disabled} checked={values?.audio.dts ?? false} onClick={() => patch({ audio: { dts: !values?.audio.dts } })} />
                </Option>
                <Option label={'Dolby TrueHD'}>
                    <Toggle disabled={disabled} checked={values?.audio.truehd ?? false} onClick={() => patch({ audio: { truehd: !values?.audio.truehd } })} />
                </Option>
                <Option label={'DTS-HD'}>
                    <Toggle disabled={disabled} checked={values?.audio.dtshd ?? false} onClick={() => patch({ audio: { dtshd: !values?.audio.dtshd } })} />
                </Option>
            </Category>

            <Category icon={'subtitles'} label={'Kodi subtitle renderer'}>
                <Option label={'Subtitle size'}>
                    <MultiselectMenu
                        className={'multiselect'}
                        disabled={disabled}
                        options={subtitleSizeOptions}
                        value={values?.subtitles.fontSize}
                        onSelect={(value) => patch({ subtitles: { fontSize: value } })}
                    />
                </Option>
            </Category>

            <Category icon={'remote'} label={'Vero services'}>
                <Option label={'HDMI-CEC'}>
                    <Toggle
                        disabled={disabled || !capabilities?.cec}
                        checked={values?.device.cecEnabled ?? false}
                        onClick={() => patch({ device: { cecEnabled: !values?.device.cecEnabled } })}
                    />
                </Option>
                <Option label={'Automatic OSMC updates'}>
                    <Toggle
                        disabled={disabled || !capabilities?.osmcUpdates}
                        checked={values?.device.automaticUpdates ?? false}
                        onClick={() => patch({ device: { automaticUpdates: !values?.device.automaticUpdates } })}
                    />
                </Option>
                <div className={styles['pending']}>
                    Network, Bluetooth, remote pairing and updates stay disabled until their OSMC adapters pass device tests.
                </div>
            </Category>
        </Section>
    );
});

Vero.displayName = 'Vero';

export default Vero;
