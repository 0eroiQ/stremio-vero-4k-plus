// Copyright (C) 2017-2023 Smart code 203358507
// Stremio for Vero 4K+ TV presentation overlay.

const React = require('react');
const { useTranslation } = require('react-i18next');
const { useLocation, useParams, useNavigate } = require('react-router');
const { useSearchParams } = require('react-router-dom');
const PropTypes = require('prop-types');
const classnames = require('classnames');
const NotFound = require('stremio/routes/NotFound');
const { useProfile, useNotifications, withCoreSuspender } = require('stremio/common');
const { default: toPath } = require('stremio-router/toPath');
const {
    Chips,
    Image,
    LibItem,
    MainNavBars,
    MultiselectMenu,
} = require('stremio/components');
const { default: Placeholder } = require('./Placeholder');
const useLibrary = require('./useLibrary');
const useSelectableInputs = require('./useSelectableInputs');
const styles = require('./styles');

const MAX_ITEMS = 20;

function withModel(Library) {
    const WithModel = () => {
        const location = useLocation();
        const model = React.useMemo(() => {
            return typeof location.pathname === 'string' ?
                location.pathname.match('/library') ?
                    'library'
                    :
                    location.pathname.match('/continuewatching') ?
                        'continue_watching'
                        :
                        null
                :
                null;
        }, [location?.pathname]);

        if (model === null) return <NotFound />;

        return <Library model={model} />;
    };
    WithModel.displayName = 'withModel';
    return WithModel;
}

const Library = ({ model }) => {
    const { type } = useParams();
    const urlParams = React.useMemo(() => ({ type }), [type]);
    const [queryParams] = useSearchParams();
    const navigate = useNavigate();
    const { t } = useTranslation();
    const profile = useProfile();
    const notifications = useNotifications();
    const [library, loadNextPage] = useLibrary(model, urlParams, queryParams);
    const [typeSelect, sortChips, hasNextPage] = useSelectableInputs(library);
    const [activeItem, setActiveItem] = React.useState(0);
    const requestedPageSize = React.useRef(0);
    const pendingInitialFocus = React.useRef(true);

    const selectionIdentity = React.useMemo(() => {
        const request = library.selected?.request;
        return `${model}/${request?.type || 'all'}/${request?.sort || 'default'}`;
    }, [library.selected, model]);

    React.useEffect(() => {
        if (!library.selected?.type && typeSelect.value) {
            navigate(toPath(typeSelect.value));
        }
    }, [typeSelect.value, library.selected, navigate]);

    React.useEffect(() => {
        setActiveItem(0);
        requestedPageSize.current = 0;
        pendingInitialFocus.current = true;
    }, [selectionIdentity]);

    React.useEffect(() => {
        if (library.catalog.length > 0 && activeItem >= library.catalog.length) {
            setActiveItem(library.catalog.length - 1);
        }
    }, [library.catalog.length, activeItem]);

    React.useLayoutEffect(() => {
        if (!pendingInitialFocus.current || library.catalog.length === 0) {
            return;
        }

        const target = document.querySelector(`[data-tv-route="${model}"][data-tv-item="0"]`);
        if (target !== null) {
            target.focus();
            pendingInitialFocus.current = false;
        }
    }, [library.catalog.length, selectionIdentity, model]);

    const selectedItem = library.catalog[Math.min(activeItem, Math.max(0, library.catalog.length - 1))] || null;
    const heroArtwork = selectedItem?.background || selectedItem?.poster || null;

    const focusRail = React.useCallback(() => {
        const selectedNavItem = document.querySelector('nav a.selected');
        if (selectedNavItem !== null) {
            selectedNavItem.focus();
        }
    }, []);

    const focusSelectedCard = React.useCallback(() => {
        const target = document.querySelector(`[data-tv-route="${model}"][data-tv-item="${activeItem}"]`);
        if (target !== null) {
            target.focus();
        }
    }, [activeItem, model]);

    const onFilterKeyDown = React.useCallback((event) => {
        if (event.key === 'ArrowDown') {
            event.preventDefault();
            focusSelectedCard();
        } else if (event.key === 'ArrowLeft' && event.currentTarget.dataset.tvFilter === '0') {
            event.preventDefault();
            focusRail();
        }
    }, [focusRail, focusSelectedCard]);

    const onItemFocus = React.useCallback((index) => {
        setActiveItem(index);
        if (
            hasNextPage &&
            index >= library.catalog.length - 2 &&
            requestedPageSize.current !== library.catalog.length
        ) {
            requestedPageSize.current = library.catalog.length;
            loadNextPage();
        }
    }, [hasNextPage, library.catalog.length, loadNextPage]);

    const onItemKeyDown = React.useCallback((event) => {
        const itemIndex = Number(event.currentTarget.dataset.tvItem);
        if (event.key === 'ArrowLeft' && itemIndex === 0) {
            event.preventDefault();
            focusRail();
        } else if (event.key === 'ArrowUp') {
            const firstFilter = document.querySelector('[data-tv-filter="0"] button');
            if (firstFilter !== null) {
                event.preventDefault();
                firstFilter.focus();
            }
        }
    }, [focusRail]);

    const renderImageFallback = React.useCallback(() => null, []);
    const title = model === 'library' ? t('LIBRARY') : t('BOARD_CONTINUE_WATCHING');

    const content = library.selected === null ?
        model === 'library' ? t('LIBRARY_NOT_LOADED') : t('BOARD_CONTINUE_WATCHING_NOT_LOADED')
        :
        library.catalog.length === 0 ?
            model === 'library' ? t('LIBRARY_EMPTY') : t('BOARD_CONTINUE_WATCHING_EMPTY')
            :
            null;

    return (
        <MainNavBars className={styles['library-container']} route={model}>
            {
                profile.auth !== null ?
                    <div className={styles['tv-library']}>
                        {
                            heroArtwork !== null ?
                                <div className={styles['hero-artwork-layer']}>
                                    <Image
                                        className={styles['hero-artwork']}
                                        src={heroArtwork}
                                        alt={' '}
                                        renderFallback={renderImageFallback}
                                    />
                                </div>
                                :
                                null
                        }
                        <div className={styles['hero-shade']} />
                        {
                            selectedItem !== null ?
                                <section className={styles['hero-info']} aria-live={'polite'}>
                                    {
                                        typeof selectedItem.logo === 'string' && selectedItem.logo.length > 0 ?
                                            <Image
                                                className={styles['hero-logo']}
                                                src={selectedItem.logo}
                                                alt={selectedItem.name || ' '}
                                                renderFallback={renderImageFallback}
                                            />
                                            :
                                            <h1 className={styles['hero-title']}>{selectedItem.name}</h1>
                                    }
                                    <div className={styles['hero-facts']}>
                                        {selectedItem.releaseInfo ? <span>{selectedItem.releaseInfo}</span> : null}
                                        {selectedItem.runtime ? <span>{selectedItem.runtime}</span> : null}
                                        {selectedItem.type ? <span>{selectedItem.type}</span> : null}
                                    </div>
                                    {selectedItem.description ? <p className={styles['hero-description']}>{selectedItem.description}</p> : null}
                                </section>
                                :
                                null
                        }
                        <div className={styles['filter-strip']}>
                            <div className={styles['filter-control']} data-tv-filter={'0'} onKeyDown={onFilterKeyDown}>
                                <MultiselectMenu {...typeSelect} />
                            </div>
                            <div className={styles['sort-control']} data-tv-filter={'1'} onKeyDown={onFilterKeyDown}>
                                <Chips {...sortChips} />
                            </div>
                        </div>
                        {
                            library.catalog.length > 0 ?
                                <section className={styles['catalog-stage']}>
                                    <h2 className={styles['catalog-title']}>{title}</h2>
                                    <div className={styles['catalog-row']}>
                                        {library.catalog.slice(0, MAX_ITEMS).map((item, index) => (
                                            <LibItem
                                                {...item}
                                                key={`${item._id || item.id || index}`}
                                                className={classnames(styles['tv-card'], {
                                                    [styles['selected-card']]: activeItem === index,
                                                })}
                                                notifications={notifications}
                                                removable={model === 'library'}
                                                detailsVideosFirst={model === 'library'}
                                                data-tv-row={0}
                                                data-tv-route={model}
                                                data-tv-item={index}
                                                onFocus={() => onItemFocus(index)}
                                                onKeyDown={onItemKeyDown}
                                            />
                                        ))}
                                    </div>
                                </section>
                                :
                                <div className={styles['loading-message']}>{content}</div>
                        }
                    </div>
                    :
                    <Placeholder />
            }
        </MainNavBars>
    );
};

Library.propTypes = {
    model: PropTypes.oneOf(['library', 'continue_watching']),
};

const LibraryFallback = ({ model }) => (
    <MainNavBars className={styles['library-container']} route={model}>
        <div className={styles['tv-library']}>
            <div className={styles['loading-message']}>Stremio</div>
        </div>
    </MainNavBars>
);

LibraryFallback.propTypes = Library.propTypes;

module.exports = withModel(withCoreSuspender(Library, LibraryFallback));
