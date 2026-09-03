// Copyright (C) 2017-2023 Smart code 203358507
// Stremio for Vero 4K+ TV presentation overlay.

const React = require('react');
const { useParams } = require('react-router');
const { useSearchParams } = require('react-router-dom');
const classnames = require('classnames');
const { useTranslate, withCoreSuspender } = require('stremio/common');
const {
    Image,
    MainNavBars,
    MetaItem,
    MultiselectMenu,
} = require('stremio/components');
const useDiscover = require('./useDiscover');
const useSelectableInputs = require('./useSelectableInputs');
const styles = require('./styles');

const MAX_ITEMS = 20;

const Discover = () => {
    const { type, transportUrl, catalogId } = useParams();
    const urlParams = React.useMemo(() => ({
        type,
        transportUrl,
        catalogId,
    }), [type, transportUrl, catalogId]);
    const [queryParams] = useSearchParams();
    const t = useTranslate();
    const [discover, loadNextPage] = useDiscover(urlParams, queryParams);
    const [selectInputs, hasNextPage] = useSelectableInputs(discover);
    const [activeItem, setActiveItem] = React.useState(0);
    const requestedPageSize = React.useRef(0);
    const pendingInitialFocus = React.useRef(true);

    const items = React.useMemo(() => {
        return discover.catalog?.content.type === 'Ready' ?
            discover.catalog.content.content
            :
            [];
    }, [discover.catalog]);

    const selectedCatalog = React.useMemo(() => {
        return discover.selectable.catalogs.find(({ selected }) => selected) || null;
    }, [discover.selectable.catalogs]);

    const catalogTitle = selectedCatalog !== null ?
        t.catalogTitle(selectedCatalog)
        :
        t.string('DISCOVER');

    const selectionIdentity = React.useMemo(() => {
        const request = discover.selected?.request;
        return request ? `${request.base}/${request.path?.type}/${request.path?.id}` : 'discover';
    }, [discover.selected]);

    React.useEffect(() => {
        setActiveItem(0);
        requestedPageSize.current = 0;
        pendingInitialFocus.current = true;
    }, [selectionIdentity]);

    React.useEffect(() => {
        if (items.length > 0 && activeItem >= items.length) {
            setActiveItem(items.length - 1);
        }
    }, [items.length, activeItem]);

    React.useLayoutEffect(() => {
        if (!pendingInitialFocus.current || items.length === 0) {
            return;
        }

        const target = document.querySelector('[data-tv-route="discover"][data-tv-item="0"]');
        if (target !== null) {
            target.focus();
            pendingInitialFocus.current = false;
        }
    }, [items.length, selectionIdentity]);

    const selectedItem = items[Math.min(activeItem, Math.max(0, items.length - 1))] || null;
    const heroArtwork = selectedItem?.background || selectedItem?.poster || null;

    const focusRail = React.useCallback(() => {
        const selectedNavItem = document.querySelector('nav a.selected');
        if (selectedNavItem !== null) {
            selectedNavItem.focus();
        }
    }, []);

    const focusSelectedCard = React.useCallback(() => {
        const target = document.querySelector(`[data-tv-route="discover"][data-tv-item="${activeItem}"]`);
        if (target !== null) {
            target.focus();
        }
    }, [activeItem]);

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
            index >= items.length - 2 &&
            requestedPageSize.current !== items.length
        ) {
            requestedPageSize.current = items.length;
            loadNextPage();
        }
    }, [hasNextPage, items.length, loadNextPage]);

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

    const message = discover.catalog === null ?
        t.string('NO_CATALOG_SELECTED')
        :
        discover.catalog.content.type === 'Err' ?
            discover.catalog.content.content
            :
            discover.catalog.content.type === 'Loading' ?
                'Stremio'
                :
                items.length === 0 ? t.string('CATALOG_EMPTY') : null;

    return (
        <MainNavBars className={styles['discover-container']} route={'discover'}>
            <div className={styles['tv-discover']}>
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
                {
                    selectInputs.length > 0 ?
                        <div className={styles['filter-strip']}>
                            {selectInputs.map((input, index) => (
                                <div
                                    key={index}
                                    className={styles['filter-control']}
                                    data-tv-filter={index}
                                    onKeyDown={onFilterKeyDown}
                                >
                                    <MultiselectMenu {...input} />
                                </div>
                            ))}
                        </div>
                        :
                        null
                }
                {
                    items.length > 0 ?
                        <section className={styles['catalog-stage']}>
                            <h2 className={styles['catalog-title']}>{catalogTitle}</h2>
                            <div className={styles['catalog-row']}>
                                {items.slice(0, MAX_ITEMS).map((item, index) => (
                                    <MetaItem
                                        {...item}
                                        key={`${item.id || item._id || index}`}
                                        className={classnames(styles['tv-card'], {
                                            [styles['selected-card']]: activeItem === index,
                                        })}
                                        data-tv-row={0}
                                        data-tv-route={'discover'}
                                        data-tv-item={index}
                                        onFocus={() => onItemFocus(index)}
                                        onKeyDown={onItemKeyDown}
                                    />
                                ))}
                            </div>
                        </section>
                        :
                        message !== null ? <div className={styles['loading-message']}>{message}</div> : null
                }
            </div>
        </MainNavBars>
    );
};

const DiscoverFallback = () => (
    <MainNavBars className={styles['discover-container']} route={'discover'}>
        <div className={styles['tv-discover']}>
            <div className={styles['loading-message']}>Stremio</div>
        </div>
    </MainNavBars>
);

module.exports = withCoreSuspender(Discover, DiscoverFallback);
