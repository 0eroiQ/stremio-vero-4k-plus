// Based on Stremio Web. Copyright (C) 2017-2023 Smart code 203358507

import React, { useCallback, useMemo } from 'react';
import classNames from 'classnames';
import { useTranslation } from 'react-i18next';
import { usePlatform } from 'stremio/common';
import { Button } from 'stremio/components';
import Icon from '@stremio/stremio-icons/react';
import { SECTIONS } from '../constants';
import styles from './Menu.less';

type Props = {
    selected: string,
    streamingServer: StreamingServer,
    onSelect: (event: React.MouseEvent<HTMLDivElement>) => void,
};

const Menu = ({ selected, streamingServer, onSelect }: Props) => {
    const { t } = useTranslation();
    const { shell } = usePlatform();
    const platform = usePlatform();

    const settings = useMemo(() => (
        streamingServer?.settings?.type === 'Ready' ?
            streamingServer.settings.content as StreamingServerSettings : null
    ), [streamingServer?.settings]);

    const items = useMemo(() => ([
        { id: SECTIONS.GENERAL, label: t('SETTINGS_NAV_GENERAL'), icon: 'person' },
        { id: SECTIONS.INTERFACE, label: t('INTERFACE'), icon: 'language' },
        { id: SECTIONS.PLAYER, label: t('SETTINGS_NAV_PLAYER'), icon: 'play' },
        { id: SECTIONS.STREAMING, label: t('SETTINGS_NAV_STREAMING'), icon: 'network' },
        { id: SECTIONS.VERO, label: 'Vero 4K+ Device', icon: 'settings' },
        ...(!platform.isMobile ? [{ id: SECTIONS.SHORTCUTS, label: t('SETTINGS_NAV_SHORTCUTS'), icon: 'remote' }] : []),
    ]), [platform.isMobile, t]);

    const onKeyDown = useCallback((event: React.KeyboardEvent<HTMLDivElement>) => {
        if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
            const menu = event.currentTarget.parentElement;
            const buttons = Array.from(menu?.querySelectorAll<HTMLElement>('[data-tv-row="settings-menu"]') || []);
            const currentIndex = buttons.indexOf(event.currentTarget);
            const offset = event.key === 'ArrowDown' ? 1 : -1;
            const nextIndex = Math.min(Math.max(currentIndex + offset, 0), buttons.length - 1);
            if (currentIndex !== -1 && nextIndex !== currentIndex) {
                event.preventDefault();
                event.stopPropagation();
                buttons[nextIndex].focus();
            }
        } else if (event.key === 'ArrowRight') {
            const stage = event.currentTarget.closest('[class*="settings-content"]')?.querySelector<HTMLElement>('[class*="settings-stage"]');
            const firstControl = stage?.querySelector<HTMLElement>('[tabindex="0"], [tabindex="-1"], a[href]');
            if (firstControl) {
                event.preventDefault();
                event.stopPropagation();
                firstControl.focus();
            }
        }
    }, []);

    return (
        <div className={styles['menu']}>
            <div className={styles['heading']}>
                <span>Settings</span>
                <small>Choose a category</small>
            </div>

            <div className={styles['menu-items']}>
                {items.map((item, index) => (
                    <Button
                        key={item.id}
                        className={classNames(styles['button'], { [styles['selected']]: selected === item.id })}
                        title={item.label}
                        data-section={item.id}
                        data-tv-row={'settings-menu'}
                        data-tv-item={index}
                        onClick={onSelect}
                        onKeyDown={onKeyDown}
                    >
                        <Icon className={styles['icon']} name={item.icon} />
                        <span className={styles['label']}>{item.label}</span>
                        <Icon className={styles['chevron']} name={'caret-right'} />
                    </Button>
                ))}
            </div>

            <div className={styles['spacing']} />
            <div className={styles['device-footer']} title={`${t('SETTINGS_BUILD_VERSION')}: ${process.env.COMMIT_HASH}`}>
                <span>Stremio</span>
                <small>{process.env.VERSION} · Vero 4K+</small>
            </div>
            {
                settings?.serverVersion &&
                    <div className={styles['version-info-label']} title={settings.serverVersion}>{t('SETTINGS_SERVER_VERSION')}: {settings.serverVersion}</div>
            }
            {
                typeof shell.state.version === 'string' &&
                    <div className={styles['version-info-label']} title={shell.state.version}>
                        {t('SETTINGS_SHELL_VERSION')}: {shell.state.version}
                    </div>
            }
        </div>
    );
};

export default Menu;
