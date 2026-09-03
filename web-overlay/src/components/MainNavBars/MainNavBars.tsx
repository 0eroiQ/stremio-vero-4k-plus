// Copyright (C) 2017-2023 Smart code 203358507
// Stremio for Vero 4K+ TV navigation overlay.

import React, { memo } from 'react';
import classnames from 'classnames';
import { VerticalNavBar } from 'stremio/components/NavBar';
import { useContentGamepadNavigation, useVerticalNavGamepadNavigation } from 'stremio/services/GamepadNavigation';
import styles from './MainNavBars.less';

const TABS = [
    { id: 'brand', label: 'Stremio', logo: require('/assets/images/stremio_symbol.png'), href: '/' },
    { id: 'search', label: 'SEARCH', icon: 'search', href: '/search' },
    { id: 'board', label: 'Board', icon: 'home', href: '/' },
    { id: 'discover', label: 'Discover', icon: 'discover', href: '/discover' },
    { id: 'library', label: 'Library', icon: 'library', href: '/library' },
    { id: 'addons', label: 'ADDONS', icon: 'addons', href: '/addons' },
    { id: 'settings', label: 'SETTINGS', icon: 'settings', href: '/settings' },
];

type Props = {
    className: string,
    route?: string,
    query?: string,
    children?: React.ReactNode,
};

const MainNavBars = memo(({ className, route, children }: Props) => {
    const navRef = React.useRef(null);
    const contentRef = React.useRef(null);
    const navRoute = route === 'continue_watching' ? 'library' : (route ?? '');

    useContentGamepadNavigation(contentRef, navRoute);
    useVerticalNavGamepadNavigation(navRef, navRoute);

    return (
        <div className={classnames(className, styles['main-nav-bars-container'])}>
            <VerticalNavBar
                ref={navRef}
                className={styles['vertical-nav-bar']}
                selected={route}
                tabs={TABS}
            />
            <div ref={contentRef} className={styles['nav-content-container']}>{children}</div>
        </div>
    );
});

export default MainNavBars;
