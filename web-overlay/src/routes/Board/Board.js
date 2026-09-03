// Copyright (C) 2017-2023 Smart code 203358507
// Stremio for Vero 4K+ TV presentation overlay.

const React = require('react');
const classnames = require('classnames');
const useTranslate = require('stremio/common/useTranslate');
const {
    useStreamingServer: useStreamingServerState,
    useNotifications,
    withCoreSuspender,
    useProfile,
} = require('stremio/common');
const {
    ContinueWatchingItem,
    EventModal,
    Image,
    MainNavBars,
    MetaItem,
} = require('stremio/components');
const useBoard = require('./useBoard');
const useContinueWatchingPreview = require('./useContinueWatchingPreview');
const styles = require('./styles');
const { default: StreamingServerWarning } = require('./StreamingServerWarning');

const MAX_CATALOGS = 24;
const MAX_ITEMS = 12;

const Board = () => {
    const t = useTranslate();
    const streamingServer = useStreamingServerState();
    const continueWatchingPreview = useContinueWatchingPreview();
    const [board, loadBoardRows] = useBoard();
    const notifications = useNotifications();
    const profile = useProfile();
    const [activeRow, setActiveRow] = React.useState(0);
    const [activeItem, setActiveItem] = React.useState(0);
    const pendingFocus = React.useRef(null);

    const rows = React.useMemo(() => {
        const availableRows = [];

        if (continueWatchingPreview.items.length > 0) {
            availableRows.push({
                key: 'continue-watching',
                title: t.string('BOARD_CONTINUE_WATCHING'),
                items: continueWatchingPreview.items,
                itemComponent: ContinueWatchingItem,
                notifications,
            });
        }

        board.catalogs.forEach((catalog, index) => {
            if (catalog.content?.type !== 'Ready' || catalog.content.content.length === 0) {
                return;
            }

            availableRows.push({
                key: `${catalog.id || 'catalog'}-${index}`,
                title: t.catalogTitle(catalog),
                items: catalog.content.content,
                itemComponent: MetaItem,
            });
        });

        return availableRows;
    }, [board.catalogs, continueWatchingPreview.items, notifications, t]);

    React.useEffect(() => {
        loadBoardRows({ start: 0, end: MAX_CATALOGS });
    }, [loadBoardRows]);

    React.useEffect(() => {
        if (rows.length === 0) {
            setActiveRow(0);
            setActiveItem(0);
            return;
        }

        if (activeRow >= rows.length) {
            setActiveRow(rows.length - 1);
            setActiveItem(0);
        }
    }, [rows.length, activeRow]);

    React.useLayoutEffect(() => {
        if (pendingFocus.current === null) {
            return;
        }

        const { row, item } = pendingFocus.current;
        pendingFocus.current = null;
        const target = document.querySelector(`[data-tv-row="${row}"][data-tv-item="${item}"]`);
        if (target !== null) {
            target.focus();
        }
    }, [activeRow]);

    const row = rows[activeRow] || null;
    const selectedItem = row?.items[Math.min(activeItem, row.items.length - 1)] || null;
    const heroArtwork = selectedItem?.background || selectedItem?.poster || null;

    const changeRow = React.useCallback((direction, itemIndex) => {
        if (rows.length === 0) {
            return;
        }

        const nextRow = Math.max(0, Math.min(rows.length - 1, activeRow + direction));
        if (nextRow === activeRow) {
            return;
        }

        const nextItem = Math.min(itemIndex, Math.max(0, rows[nextRow].items.length - 1));
        pendingFocus.current = { row: nextRow, item: nextItem };
        setActiveRow(nextRow);
        setActiveItem(nextItem);
    }, [rows, activeRow]);

    const onItemKeyDown = React.useCallback((event) => {
        const itemIndex = Number(event.currentTarget.dataset.tvItem);
        if (event.key === 'ArrowLeft' && itemIndex === 0) {
            const selectedNavItem = document.querySelector('nav a.selected');
            if (selectedNavItem !== null) {
                event.preventDefault();
                selectedNavItem.focus();
            }
        } else if (event.key === 'ArrowDown') {
            event.preventDefault();
            changeRow(1, itemIndex);
        } else if (event.key === 'ArrowUp') {
            event.preventDefault();
            changeRow(-1, itemIndex);
        }
    }, [changeRow]);

    const showStreamingServerWarning = React.useMemo(() => {
        return streamingServer.settings !== null && streamingServer.settings.type === 'Err' && (
            isNaN(profile.settings.streamingServerWarningDismissed.getTime()) ||
            profile.settings.streamingServerWarningDismissed.getTime() < Date.now());
    }, [profile.settings, streamingServer.settings]);

    const renderImageFallback = React.useCallback(() => null, []);

    return (
        <div className={styles['board-container']}>
            <EventModal />
            <MainNavBars className={styles['board-content-container']} route={'board'}>
                <div className={styles['tv-board']}>
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
                                {
                                    selectedItem.description ?
                                        <p className={styles['hero-description']}>{selectedItem.description}</p>
                                        :
                                        null
                                }
                            </section>
                            :
                            null
                    }
                    {
                        row !== null ?
                            <section className={styles['catalog-stage']}>
                                <h2 className={styles['catalog-title']}>{row.title}</h2>
                                <div className={styles['catalog-row']}>
                                    {row.items.slice(0, MAX_ITEMS).map((item, index) => {
                                        return React.createElement(row.itemComponent, {
                                            ...item,
                                            key: `${row.key}-${item.id || item._id || index}`,
                                            className: classnames(styles['tv-card'], {
                                                [styles['selected-card']]: activeItem === index,
                                            }),
                                            notifications: row.notifications,
                                            'data-tv-row': activeRow,
                                            'data-tv-item': index,
                                            onFocus: () => setActiveItem(index),
                                            onKeyDown: onItemKeyDown,
                                        });
                                    })}
                                </div>
                                <div className={styles['catalog-position']}>
                                    {activeRow + 1} / {rows.length}
                                </div>
                            </section>
                            :
                            <div className={styles['loading-message']}>Stremio</div>
                    }
                </div>
            </MainNavBars>
            {
                showStreamingServerWarning ?
                    <StreamingServerWarning className={styles['board-warning-container']} />
                    :
                    null
            }
        </div>
    );
};

const BoardFallback = () => (
    <div className={styles['board-container']}>
        <MainNavBars className={styles['board-content-container']} route={'board'}>
            <div className={styles['tv-board']}>
                <div className={styles['loading-message']}>Stremio</div>
            </div>
        </MainNavBars>
    </div>
);

module.exports = withCoreSuspender(Board, BoardFallback);
