// Copyright (C) 2017-2026 Smart code 203358507

const React = require('react');
const { useTranslation } = require('react-i18next');
const { useNavigate } = require('react-router-dom');
const { default: Icon } = require('@stremio/stremio-icons/react');
const { useCore } = require('stremio/core');
const { interfaceLanguages } = require('stremio/common');
const { Button, Image } = require('stremio/components');

const styles = require('./styles');

const LINK_LIFETIME_SECONDS = 5 * 60;
const LINK_POLL_INTERVAL_MS = 2 * 1000;

const readyContent = (loadable) => loadable && loadable.type === 'Ready' ? loadable.content : null;

const useAuthLink = (core, loadLinkAction) => {
    const [authLink, setAuthLink] = React.useState({ code: null, data: null });

    React.useEffect(() => {
        let mounted = true;
        const updateAuthLink = async (models) => {
            if (Array.isArray(models) && !models.includes('auth_link')) return;
            try {
                const state = await core.transport.getState('auth_link');
                if (mounted) setAuthLink(state);
            } catch (_error) {
                if (mounted) setAuthLink({ code: null, data: null });
            }
        };

        core.on('state', updateAuthLink);
        core.transport.dispatch(loadLinkAction, 'auth_link');
        updateAuthLink(['auth_link']);

        return () => {
            mounted = false;
            core.off('state', updateAuthLink);
            core.transport.dispatch({ action: 'Unload' }, 'auth_link');
        };
    }, [core, loadLinkAction]);

    return authLink;
};

const Intro = () => {
    const core = useCore();
    const navigate = useNavigate();
    const { i18n } = useTranslation();
    const authenticatedTokenRef = React.useRef(null);
    const requestButtonRef = React.useRef(null);
    const [secondsRemaining, setSecondsRemaining] = React.useState(LINK_LIFETIME_SECONDS);
    const [authenticationError, setAuthenticationError] = React.useState(null);
    const loadLinkAction = React.useMemo(() => ({
        action: 'Load',
        args: { model: 'Link' }
    }), []);
    const authLink = useAuthLink(core, loadLinkAction);
    const linkCode = readyContent(authLink.code);
    const linkData = readyContent(authLink.data);

    React.useEffect(() => {
        if (linkCode !== null && requestButtonRef.current) requestButtonRef.current.focus();
    }, [linkCode && linkCode.code]);

    const requestNewLink = React.useCallback(() => {
        authenticatedTokenRef.current = null;
        setAuthenticationError(null);
        setSecondsRemaining(LINK_LIFETIME_SECONDS);
        core.transport.dispatch(loadLinkAction, 'auth_link');
    }, [loadLinkAction]);

    React.useEffect(() => {
        if (linkCode === null) return undefined;
        const poll = () => core.transport.dispatch({
            action: 'Link',
            args: { action: 'ReadData' }
        }, 'auth_link');
        poll();
        const interval = window.setInterval(poll, LINK_POLL_INTERVAL_MS);
        return () => window.clearInterval(interval);
    }, [linkCode && linkCode.code]);

    React.useEffect(() => {
        if (linkCode === null) return undefined;
        setSecondsRemaining(LINK_LIFETIME_SECONDS);
        const interval = window.setInterval(() => {
            setSecondsRemaining((current) => Math.max(0, current - 1));
        }, 1000);
        return () => window.clearInterval(interval);
    }, [linkCode && linkCode.code]);

    React.useEffect(() => {
        const token = linkData && linkData.authKey;
        if (typeof token !== 'string' || token.length === 0 || authenticatedTokenRef.current === token) return;
        authenticatedTokenRef.current = token;
        setAuthenticationError(null);
        core.transport.dispatch({
            action: 'Ctx',
            args: {
                action: 'Authenticate',
                args: { type: 'LoginWithToken', token }
            }
        });
    }, [linkData && linkData.authKey]);

    React.useEffect(() => {
        const onCoreEvent = (name) => {
            if (name === 'UserAuthenticated') navigate('/', { replace: true });
        };
        const onCoreError = (source) => {
            if (source.event === 'UserAuthenticated') {
                authenticatedTokenRef.current = null;
                setAuthenticationError('Could not sign in. Request a new link and try again.');
            }
        };
        core.on('event', onCoreEvent);
        core.on('error', onCoreError);
        return () => {
            core.off('event', onCoreEvent);
            core.off('error', onCoreError);
        };
    }, [navigate]);

    const minutes = Math.floor(secondsRemaining / 60);
    const seconds = String(secondsRemaining % 60).padStart(2, '0');
    const languageCode = i18n.resolvedLanguage || i18n.language || 'en-US';
    const language = interfaceLanguages.find(({ codes }) => codes.includes(languageCode))?.name || languageCode;

    return (
        <main className={styles['intro-container']}>
            <div className={styles['background-container']} />
            <div className={styles['brand-container']}>
                <Image className={styles['brand-logo']} src={require('/assets/images/logo.png')} alt={'Stremio'} />
            </div>
            <div className={styles['language-container']}>
                <Icon className={styles['language-icon']} name={'language'} />
                <span>{language}</span>
            </div>
            <section className={styles['link-container']} aria-live={'polite'}>
                {
                    linkCode === null ?
                        <div className={styles['loading-container']}>
                            <Icon className={styles['loading-icon']} name={'person'} />
                            <span>Creating a secure sign-in link…</span>
                        </div>
                        :
                        <React.Fragment>
                            <div className={styles['qr-frame']}>
                                <img className={styles['qr-code']} src={linkCode.qrcode} alt={'Stremio sign-in QR code'} />
                            </div>
                            <ol className={styles['instructions']}>
                                <li>
                                    <span>Scan the QR code above or go to</span>
                                    <span className={styles['link-label']}>{linkCode.link}</span>
                                </li>
                                <li>Log in to your Stremio account</li>
                            </ol>
                            <Button
                                ref={requestButtonRef}
                                className={styles['request-button']}
                                role={'button'}
                                aria-label={'Request a new link'}
                                onClick={requestNewLink}
                            >
                                <Icon className={styles['request-icon']} name={'cloud-sync'} />
                                <span>Request a new link</span>
                            </Button>
                            <div className={styles['expiry-label']}>
                                {secondsRemaining > 0 ? `Expires in ${minutes}:${seconds}` : 'Link expired'}
                            </div>
                        </React.Fragment>
                }
                {authenticationError ? <div className={styles['error-label']}>{authenticationError}</div> : null}
            </section>
        </main>
    );
};

module.exports = Intro;
