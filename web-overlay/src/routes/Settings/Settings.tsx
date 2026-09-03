// Based on Stremio Web. Copyright (C) 2017-2023 Smart code 203358507

import React, { useCallback, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { usePlatform, useProfile, useStreamingServer, withCoreSuspender } from 'stremio/common';
import { MainNavBars } from 'stremio/components';
import { SECTIONS } from './constants';
import Menu from './Menu';
import General from './General';
import Interface from './Interface';
import Player from './Player';
import Streaming from './Streaming';
import Vero from './Vero';
import Shortcuts from './Shortcuts';
import Info from './Info';
import styles from './Settings.less';

const Settings = () => {
    const { t } = useTranslation();
    const profile = useProfile();
    const platform = usePlatform();
    const streamingServer = useStreamingServer();

    const [selectedSectionId, setSelectedSectionId] = useState(SECTIONS.GENERAL);

    const onMenuSelect = useCallback((event: React.MouseEvent<HTMLDivElement>) => {
        const sectionId = event.currentTarget.dataset.section;
        if (sectionId) setSelectedSectionId(sectionId);
    }, []);

    const activeSection = useMemo(() => {
        switch (selectedSectionId) {
            case SECTIONS.INTERFACE:
                return {
                    title: t('INTERFACE'),
                    description: 'Language and how Stremio looks on this TV.',
                    content: <Interface profile={profile} />,
                };
            case SECTIONS.PLAYER:
                return {
                    title: t('SETTINGS_NAV_PLAYER'),
                    description: 'Subtitles, audio, controls and autoplay.',
                    content: <Player profile={profile} />,
                };
            case SECTIONS.STREAMING:
                return {
                    title: t('SETTINGS_NAV_STREAMING'),
                    description: 'Streaming server, cache and connection options.',
                    content: <Streaming profile={profile} streamingServer={streamingServer} />,
                };
            case SECTIONS.VERO:
                return {
                    title: 'Vero 4K+ Device',
                    description: 'Picture, HDMI audio and Vero system services.',
                    content: <Vero />,
                };
            case SECTIONS.SHORTCUTS:
                return {
                    title: t('SETTINGS_NAV_SHORTCUTS'),
                    description: 'Remote and keyboard controls.',
                    content: !platform.isMobile ? <Shortcuts /> : null,
                };
            default:
                return {
                    title: t('SETTINGS_NAV_GENERAL'),
                    description: 'Your Stremio account and device information.',
                    content: <><General profile={profile} /><Info streamingServer={streamingServer} /></>,
                };
        }
    }, [platform.isMobile, profile, selectedSectionId, streamingServer, t]);

    return (
        <MainNavBars className={styles['settings-container']} route={'settings'}>
            <div className={`${styles['settings-content']} animation-fade-in`}>
                <Menu selected={selectedSectionId} streamingServer={streamingServer} onSelect={onMenuSelect} />

                <main className={styles['settings-stage']}>
                    <header className={styles['stage-header']}>
                        <div className={styles['stage-eyebrow']}>Stremio for Vero 4K+</div>
                        <h1 className={styles['stage-title']}>{activeSection.title}</h1>
                        <p className={styles['stage-description']}>{activeSection.description}</p>
                    </header>
                    <div key={selectedSectionId} className={`${styles['sections-container']} animation-fade-in`}>
                        {activeSection.content}
                    </div>
                </main>
            </div>
        </MainNavBars>
    );
};

const SettingsFallback = () => (
    <MainNavBars className={styles['settings-container']} route={'settings'} />
);

export default withCoreSuspender(Settings, SettingsFallback);
