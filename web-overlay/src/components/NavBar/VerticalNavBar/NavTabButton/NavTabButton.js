// Copyright (C) 2017-2023 Smart code 203358507

const React = require('react');
const PropTypes = require('prop-types');
const classnames = require('classnames');
const { default: Icon } = require('@stremio/stremio-icons/react');
const { Image } = require('stremio/components');
const styles = require('./styles');
const { Link } = require('react-router-dom');

const NavTabButton = ({ className, logo, icon, label, href, selected, expanded, onClick }) => {
    const renderLogoFallback = React.useCallback(() => (
        typeof icon === 'string' && icon.length > 0 ?
            <Icon className={styles['icon']} name={icon} />
            :
            null
    ), [icon]);
    const onDoubleClick = () => {
        const scrollableElements = document.querySelectorAll('div');
        scrollableElements.forEach((element) => {
            if (element.scrollTop > 0) {
                element.scrollTo({ top: 0, behavior: 'smooth' });
            }
        });
    };
    const onKeyDown = React.useCallback((event) => {
        if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
            const nav = event.currentTarget.closest('nav');
            const items = Array.from(nav?.querySelectorAll('a[tabindex="0"]') || []);
            const currentIndex = items.indexOf(event.currentTarget);
            const offset = event.key === 'ArrowDown' ? 1 : -1;
            const nextIndex = Math.min(Math.max(currentIndex + offset, 0), items.length - 1);

            if (currentIndex !== -1 && nextIndex !== currentIndex) {
                event.preventDefault();
                event.stopPropagation();
                items[nextIndex].focus();
            }
            return;
        }

        if (event.key !== 'ArrowRight') {
            return;
        }

        const preferredTarget = document.querySelector('[data-tv-row][data-tv-item="0"]');
        const fallbackTarget = document.querySelector('[class*="nav-content-container"] [tabindex="0"]');
        const target = preferredTarget || fallbackTarget;
        if (target !== null) {
            event.preventDefault();
            target.focus();
        }
    }, []);

    return (
        <Link
            className={classnames(className, styles['nav-tab-button-container'], {
                'selected': selected,
                [styles['expanded']]: expanded,
            })}
            title={label}
            tabIndex={logo ? -1 : 0}
            to={href}
            onClick={onClick}
            onDoubleClick={onDoubleClick}
            onKeyDown={onKeyDown}
        >
            {
                typeof logo === 'string' && logo.length > 0 ?
                    <Image
                        className={styles['logo']}
                        src={logo}
                        alt={' '}
                        renderFallback={renderLogoFallback}
                    />
                    :
                    typeof icon === 'string' && icon.length > 0 ?
                        <Icon className={styles['icon']} name={selected ? icon : `${icon}-outline`} />
                        :
                        null
            }
            {
                typeof label === 'string' && label.length > 0 ?
                    <div className={styles['label']}>{label}</div>
                    :
                    null
            }
        </Link>
    );
};

NavTabButton.propTypes = {
    className: PropTypes.string,
    logo: PropTypes.string,
    icon: PropTypes.string,
    label: PropTypes.string,
    href: PropTypes.string,
    selected: PropTypes.bool,
    expanded: PropTypes.bool,
    onClick: PropTypes.func,
};

module.exports = NavTabButton;
