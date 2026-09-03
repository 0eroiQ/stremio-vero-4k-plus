// Copyright (C) 2017-2023 Smart code 203358507
// Stremio for Vero 4K+ TV presentation overlay.

const React = require('react');
const classnames = require('classnames');
const { useNavigate, useSearchParams } = require('react-router-dom');
const useTranslate = require('stremio/common/useTranslate');
const { withCoreSuspender } = require('stremio/common');
const { Button, MainNavBars, MetaItem } = require('stremio/components');
const useBoard = require('../Board/useBoard');
const useSearch = require('./useSearch');
const styles = require('./styles');

const LETTERS = 'abcdefghijklmnopqrstuvwxyz'.split('');
const NUMBERS = '1234567890'.split('');
const MAX_CATALOGS = 24;
const MAX_RESULTS = 12;

const Search = () => {
    const [queryParams] = useSearchParams();
    const navigate = useNavigate();
    const t = useTranslate();
    const [search, loadSearchRows] = useSearch(queryParams);
    const [board, loadBoardRows] = useBoard();
    const [keyboardMode, setKeyboardMode] = React.useState('letters');
    const [activeRow, setActiveRow] = React.useState(0);
    const query = queryParams.get('search') ?? queryParams.get('query') ?? '';

    React.useEffect(() => {
        loadBoardRows({ start: 0, end: MAX_CATALOGS });
    }, [loadBoardRows]);

    React.useEffect(() => {
        if (search.catalogs.length > 0) {
            loadSearchRows({ start: 0, end: Math.min(MAX_CATALOGS, search.catalogs.length) });
        }
    }, [search.catalogs.length, loadSearchRows]);

    const availableRows = React.useMemo(() => {
        const catalogs = query.length > 0 ? search.catalogs : board.catalogs;
        return catalogs.filter((catalog) => (
            catalog.content?.type === 'Ready' && catalog.content.content.length > 0
        ));
    }, [query, search.catalogs, board.catalogs]);

    React.useEffect(() => {
        setActiveRow(0);
    }, [query]);

    React.useEffect(() => {
        if (availableRows.length > 0 && activeRow >= availableRows.length) {
            setActiveRow(availableRows.length - 1);
        }
    }, [activeRow, availableRows.length]);

    const row = availableRows[activeRow] || null;
    const items = row?.content.content || [];
    const rowTitle = row !== null ?
        t.catalogTitle(row)
        :
        query.length > 0 ? t.string('SEARCH') : t.string('DISCOVER');

    const setQuery = React.useCallback((nextQuery) => {
        const normalized = nextQuery.slice(0, 80);
        navigate(
            normalized.length > 0 ? `/search?search=${encodeURIComponent(normalized)}` : '/search',
            { replace: true },
        );
    }, [navigate]);

    const toggleKeyboard = React.useCallback(() => {
        setKeyboardMode((mode) => mode === 'letters' ? 'numbers' : 'letters');
    }, []);

    React.useEffect(() => {
        const onWindowKeyDown = (event) => {
            if (event.ctrlKey || event.metaKey || event.altKey) {
                return;
            }

            if (event.key === 'MediaPlayPause') {
                event.preventDefault();
                toggleKeyboard();
            } else if (event.key === 'Backspace') {
                event.preventDefault();
                setQuery(query.slice(0, -1));
            } else if (event.key === ' ' && event.target?.dataset?.tvKey) {
                return;
            } else if (event.key.length === 1 && /^[a-zA-Z0-9 ]$/.test(event.key)) {
                event.preventDefault();
                setQuery(query + event.key.toLowerCase());
            }
        };

        window.addEventListener('keydown', onWindowKeyDown);
        return () => window.removeEventListener('keydown', onWindowKeyDown);
    }, [query, setQuery, toggleKeyboard]);

    React.useLayoutEffect(() => {
        const currentFocus = document.activeElement;
        if (currentFocus === document.body || currentFocus === document.documentElement) {
            const firstKey = document.querySelector('[data-tv-key="entry"]');
            if (firstKey !== null) {
                firstKey.focus();
            }
        }
    }, [keyboardMode]);

    const focusRail = React.useCallback(() => {
        const selectedNavItem = document.querySelector('nav a.selected');
        if (selectedNavItem !== null) {
            selectedNavItem.focus();
        }
    }, []);

    const focusFirstResult = React.useCallback(() => {
        const target = document.querySelector('[data-tv-row="search-results"][data-tv-item="0"]');
        if (target !== null) {
            target.focus();
        }
    }, []);

    const onKeyboardKeyDown = React.useCallback((event) => {
        const keyIndex = Number(event.currentTarget.dataset.tvKeyIndex);
        if (event.key === 'ArrowLeft' && keyIndex === 0) {
            event.preventDefault();
            focusRail();
        } else if (event.key === 'ArrowDown') {
            event.preventDefault();
            focusFirstResult();
        }
    }, [focusFirstResult, focusRail]);

    const onResultKeyDown = React.useCallback((event) => {
        const itemIndex = Number(event.currentTarget.dataset.tvItem);
        if (event.key === 'ArrowLeft' && itemIndex === 0) {
            event.preventDefault();
            focusRail();
        } else if (event.key === 'ArrowUp') {
            event.preventDefault();
            const firstKey = document.querySelector('[data-tv-key="entry"]');
            if (firstKey !== null) {
                firstKey.focus();
            }
        } else if (event.key === 'PageDown' && activeRow < availableRows.length - 1) {
            event.preventDefault();
            setActiveRow((index) => index + 1);
        } else if (event.key === 'PageUp' && activeRow > 0) {
            event.preventDefault();
            setActiveRow((index) => index - 1);
        }
    }, [activeRow, availableRows.length, focusRail]);

    const characterKeys = keyboardMode === 'letters' ? LETTERS : NUMBERS;
    const keyboardKeys = [
        {
            id: 'mode',
            label: keyboardMode === 'letters' ? '123' : 'ABC',
            onClick: toggleKeyboard,
        },
        {
            id: 'space',
            label: t.string('SPACE'),
            onClick: () => setQuery(query + ' '),
        },
        ...characterKeys.map((character) => ({
            id: character,
            label: character,
            onClick: () => setQuery(query + character),
        })),
        {
            id: 'backspace',
            label: '⌫',
            onClick: () => setQuery(query.slice(0, -1)),
        },
    ];

    const message = query.length > 0 && search.catalogs.length === 0 ?
        t.string('STREMIO_TV_SEARCH_NO_ADDONS')
        :
        'Stremio';

    return (
        <MainNavBars className={styles['search-container']} route={'search'} query={query}>
            <div className={styles['tv-search']}>
                <div className={styles['query-bar']}>
                    <div className={styles['query-label']}>{query.length > 0 ? query : t.string('SEARCH')}</div>
                    <div className={styles['keyboard-hint']}>Press ⏯ to change keyboards</div>
                </div>
                <div className={styles['keyboard-row']}>
                    {keyboardKeys.map((key, index) => (
                        <Button
                            key={key.id}
                            className={classnames(styles['keyboard-key'], {
                                [styles['wide-key']]: key.id === 'space',
                                [styles['utility-key']]: key.id === 'mode' || key.id === 'backspace',
                            })}
                            title={key.label}
                            data-tv-key={key.id === characterKeys[0] ? 'entry' : key.id}
                            data-tv-key-index={index}
                            data-tv-row={key.id === characterKeys[0] ? 'search-keyboard' : undefined}
                            data-tv-item={key.id === characterKeys[0] ? 0 : undefined}
                            onClick={key.onClick}
                            onKeyDown={onKeyboardKeyDown}
                        >
                            {key.label}
                        </Button>
                    ))}
                </div>
                <div className={styles['divider']} />
                {
                    items.length > 0 ?
                        <section className={styles['results-stage']}>
                            <h1 className={styles['results-title']}>{rowTitle}</h1>
                            <div className={styles['results-grid']}>
                                {items.slice(0, MAX_RESULTS).map((item, index) => (
                                    <MetaItem
                                        {...item}
                                        key={`${item.id || item._id || index}`}
                                        className={styles['result-card']}
                                        data-tv-row={'search-results'}
                                        data-tv-item={index}
                                        onKeyDown={onResultKeyDown}
                                    />
                                ))}
                            </div>
                            {
                                availableRows.length > 1 ?
                                    <div className={styles['catalog-position']}>{activeRow + 1} / {availableRows.length}</div>
                                    :
                                    null
                            }
                        </section>
                        :
                        <div className={styles['message']}>{message}</div>
                }
            </div>
        </MainNavBars>
    );
};

const SearchFallback = () => (
    <MainNavBars className={styles['search-container']} route={'search'}>
        <div className={styles['tv-search']}>
            <div className={styles['message']}>Stremio</div>
        </div>
    </MainNavBars>
);

module.exports = withCoreSuspender(Search, SearchFallback);
