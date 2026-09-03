// Copyright (C) 2017-2023 Smart code 203358507

const React = require('react');
const PropTypes = require('prop-types');
const classnames = require('classnames');
const { useTranslation } = require('react-i18next');
const NavTabButton = require('./NavTabButton');
const styles = require('./styles');

const VerticalNavBar = React.memo(React.forwardRef(({ className, selected, tabs }, forwardedRef) => {
    const { t } = useTranslation();
    const localRef = React.useRef(null);
    const [expanded, setExpanded] = React.useState(false);

    const setRefs = React.useCallback((node) => {
        localRef.current = node;
        if (typeof forwardedRef === 'function') {
            forwardedRef(node);
        } else if (forwardedRef !== null) {
            forwardedRef.current = node;
        }
    }, [forwardedRef]);

    const onFocusCapture = React.useCallback(() => setExpanded(true), []);
    const onBlurCapture = React.useCallback((event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) {
            setExpanded(false);
        }
    }, []);

    return (
        <nav
            ref={setRefs}
            className={classnames(className, styles['vertical-nav-bar-container'], {
                [styles['expanded']]: expanded,
            })}
            onFocusCapture={onFocusCapture}
            onBlurCapture={onBlurCapture}
        >
            {
                Array.isArray(tabs) ?
                    tabs.map((tab, index) => (
                        <NavTabButton
                            key={index}
                            className={styles['nav-tab-button']}
                            selected={tab.id === selected}
                            expanded={expanded}
                            href={tab.href}
                            logo={tab.logo}
                            icon={tab.icon}
                            label={t(tab.label)}
                            onClick={tab.onClick}
                        />
                    ))
                    :
                    null
            }
        </nav>
    );
}));

VerticalNavBar.displayName = 'VerticalNavBar';

VerticalNavBar.propTypes = {
    className: PropTypes.string,
    selected: PropTypes.string,
    tabs: PropTypes.arrayOf(PropTypes.shape({
        id: PropTypes.string,
        label: PropTypes.string,
        logo: PropTypes.string,
        icon: PropTypes.string,
        href: PropTypes.string,
        onClick: PropTypes.func,
    })),
};

module.exports = VerticalNavBar;
