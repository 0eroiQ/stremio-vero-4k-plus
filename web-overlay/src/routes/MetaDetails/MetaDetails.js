// Copyright (C) 2017-2023 Smart code 203358507
// Stremio for Vero 4K+ TV presentation overlay.

const React = require('react');
const { useParams, useLocation, useNavigate } = require('react-router');
const { useTranslation } = require('react-i18next');
const classnames = require('classnames');
const { useCore } = require('stremio/core');
const { withCoreSuspender } = require('stremio/common');
const { useNavigateWithOrigin } = require('stremio-router');
const { Image, MainNavBars, MetaPreview } = require('stremio/components');
const StreamsList = require('./StreamsList');
const VideosList = require('./VideosList');
const useMetaDetails = require('./useMetaDetails');
const useSeason = require('./useSeason');
const styles = require('./styles');

const MetaDetails = () => {
    const { type, id, videoId } = useParams();
    const location = useLocation();
    const navigate = useNavigate();
    const { getStoredOrigin } = useNavigateWithOrigin();
    const { t } = useTranslation();
    const core = useCore();
    const urlParams = React.useMemo(() => ({
        type,
        id,
        videoId,
    }), [type, id, videoId]);
    const metaDetails = useMetaDetails(urlParams);
    const [season, setSeason] = useSeason(urlParams);
    const [metaPath, streamPath] = React.useMemo(() => {
        return metaDetails.selected !== null ?
            [metaDetails.selected.metaPath, metaDetails.selected.streamPath]
            :
            [null, null];
    }, [metaDetails.selected]);
    const video = React.useMemo(() => {
        return streamPath !== null && metaDetails.metaItem !== null && metaDetails.metaItem.content.type === 'Ready' ?
            metaDetails.metaItem.content.content.videos.reduce((result, currentVideo) => {
                return currentVideo.id === streamPath.id ? currentVideo : result;
            }, null)
            :
            null;
    }, [metaDetails.metaItem, streamPath]);

    const addToLibrary = React.useCallback(() => {
        if (metaDetails.metaItem === null || metaDetails.metaItem.content.type !== 'Ready') {
            return;
        }

        core.transport.dispatch({
            action: 'Ctx',
            args: {
                action: 'AddToLibrary',
                args: metaDetails.metaItem.content.content,
            },
        });
    }, [core.transport, metaDetails.metaItem]);

    const removeFromLibrary = React.useCallback(() => {
        if (metaDetails.metaItem === null || metaDetails.metaItem.content.type !== 'Ready') {
            return;
        }

        core.transport.dispatch({
            action: 'Ctx',
            args: {
                action: 'RemoveFromLibrary',
                args: metaDetails.metaItem.content.content.id,
            },
        });
    }, [core.transport, metaDetails.metaItem]);

    const toggleWatched = React.useCallback(() => {
        if (metaDetails.metaItem === null || metaDetails.metaItem.content.type !== 'Ready') {
            return;
        }

        core.transport.dispatch({
            action: 'MetaDetails',
            args: {
                action: 'MarkAsWatched',
                args: !metaDetails.metaItem.content.content.watched,
            },
        });
    }, [core.transport, metaDetails.metaItem]);

    const toggleNotifications = React.useCallback(() => {
        if (metaDetails.libraryItem) {
            core.transport.dispatch({
                action: 'Ctx',
                args: {
                    action: 'ToggleLibraryItemNotifications',
                    args: [metaDetails.libraryItem._id, !metaDetails.libraryItem.state.noNotif],
                },
            });
        }
    }, [core.transport, metaDetails.libraryItem]);

    const seasonOnSelect = React.useCallback((event) => {
        setSeason(event.value);
    }, [setSeason]);

    const handleEpisodeSearch = React.useCallback((selectedSeason, episode) => {
        const searchVideoHash = encodeURIComponent(`${urlParams.id}:${selectedSeason}:${episode}`);
        const url = location.pathname;
        const searchVideoPath = (urlParams.videoId === undefined || urlParams.videoId === null || urlParams.videoId === '') ?
            url + (!url.endsWith('/') ? '/' : '') + searchVideoHash
            :
            url.replace(encodeURIComponent(urlParams.videoId), searchVideoHash);
        navigate(searchVideoPath, { replace: true });
    }, [urlParams, location.pathname, navigate]);

    const renderBackgroundImageFallback = React.useCallback(() => null, []);
    const renderBackground = React.useMemo(() => !!(
        metaPath &&
        metaDetails.metaItem &&
        metaDetails.metaItem.content.type === 'Ready' &&
        typeof metaDetails.metaItem.content.content?.background === 'string' &&
        metaDetails.metaItem.content.content.background.length > 0
    ), [metaPath, metaDetails.metaItem]);

    const originPath = React.useMemo(() => getStoredOrigin('/'), [getStoredOrigin]);
    const railRoute = React.useMemo(() => {
        if (typeof originPath !== 'string') return 'board';
        if (originPath.startsWith('/library') || originPath.startsWith('/continuewatching')) return 'library';
        if (originPath.startsWith('/discover')) return 'discover';
        if (originPath.startsWith('/search')) return 'search';
        return 'board';
    }, [originPath]);

    const readyMeta = metaDetails.metaItem?.content.type === 'Ready' ?
        metaDetails.metaItem.content.content
        :
        null;

    return (
        <MainNavBars className={styles['metadetails-shell']} route={railRoute}>
            <div className={styles['metadetails-container']}>
                {
                    renderBackground ?
                        <div className={styles['background-image-layer']}>
                            <Image
                                className={styles['background-image']}
                                src={readyMeta.background}
                                renderFallback={renderBackgroundImageFallback}
                                alt={' '}
                            />
                        </div>
                        :
                        null
                }
                <div className={styles['hero-shade']} />
                <div className={styles['metadetails-content']}>
                    {
                        metaPath === null ?
                            <div className={styles['meta-message-container']}>
                                <div className={styles['message-label']}>{t('ERR_NO_META_SELECTED')}</div>
                            </div>
                            :
                            metaDetails.metaItem === null ?
                                <div className={styles['meta-message-container']}>
                                    <div className={styles['message-label']}>{t('ERR_NO_ADDONS_FOR_META')}</div>
                                </div>
                                :
                                metaDetails.metaItem.content.type === 'Err' ?
                                    <div className={styles['meta-message-container']}>
                                        <div className={styles['message-label']}>{t('ERR_NO_META_FOUND')}</div>
                                    </div>
                                    :
                                    metaDetails.metaItem.content.type === 'Loading' ?
                                        <MetaPreview.Placeholder className={styles['meta-preview']} />
                                        :
                                        <MetaPreview
                                            compact={true}
                                            className={classnames(styles['meta-preview'], 'animation-fade-in')}
                                            name={readyMeta.name}
                                            logo={readyMeta.logo}
                                            runtime={readyMeta.runtime}
                                            releaseInfo={readyMeta.releaseInfo}
                                            released={readyMeta.released}
                                            description={
                                                video !== null && typeof video.overview === 'string' && video.overview.length > 0 ?
                                                    video.overview
                                                    :
                                                    readyMeta.description
                                            }
                                            links={readyMeta.links}
                                            deepLinks={readyMeta.deepLinks}
                                            trailerStreams={readyMeta.trailerStreams}
                                            inLibrary={readyMeta.inLibrary}
                                            toggleInLibrary={readyMeta.inLibrary ? removeFromLibrary : addToLibrary}
                                            watched={readyMeta.watched}
                                            toggleWatched={toggleWatched}
                                            metaId={readyMeta.id}
                                            ratingInfo={metaDetails.ratingInfo}
                                        />
                    }
                    {
                        streamPath !== null ?
                            <StreamsList
                                className={styles['streams-list']}
                                streams={metaDetails.streams}
                                video={video}
                                type={streamPath.type}
                                onEpisodeSearch={handleEpisodeSearch}
                            />
                            :
                            metaPath !== null ?
                                <VideosList
                                    className={styles['videos-list']}
                                    metaItem={metaDetails.metaItem}
                                    libraryItem={metaDetails.libraryItem}
                                    season={season}
                                    selectedVideoId={metaDetails.libraryItem?.state?.video_id}
                                    seasonOnSelect={seasonOnSelect}
                                    toggleNotifications={toggleNotifications}
                                />
                                :
                                null
                    }
                </div>
            </div>
        </MainNavBars>
    );
};

const MetaDetailsFallback = () => (
    <MainNavBars className={styles['metadetails-shell']} route={'board'}>
        <div className={styles['metadetails-container']} />
    </MainNavBars>
);

module.exports = withCoreSuspender(MetaDetails, MetaDetailsFallback);
