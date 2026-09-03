from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "web-overlay" / "src" / "routes" / "Board" / "Board.js"
NAV = ROOT / "web-overlay" / "src" / "components" / "MainNavBars" / "MainNavBars.tsx"
NAV_STYLES = ROOT / "web-overlay" / "src" / "components" / "MainNavBars" / "MainNavBars.less"
RAIL = ROOT / "web-overlay" / "src" / "components" / "NavBar" / "VerticalNavBar" / "styles.less"
RAIL_COMPONENT = ROOT / "web-overlay" / "src" / "components" / "NavBar" / "VerticalNavBar" / "VerticalNavBar.js"
RAIL_BUTTON = ROOT / "web-overlay" / "src" / "components" / "NavBar" / "VerticalNavBar" / "NavTabButton" / "NavTabButton.js"
INTRO = ROOT / "web-overlay" / "src" / "routes" / "Intro" / "Intro.js"
INTRO_STYLES = ROOT / "web-overlay" / "src" / "routes" / "Intro" / "styles.less"
DISCOVER = ROOT / "web-overlay" / "src" / "routes" / "Discover" / "Discover.js"
LIBRARY = ROOT / "web-overlay" / "src" / "routes" / "Library" / "Library.js"
META_DETAILS = ROOT / "web-overlay" / "src" / "routes" / "MetaDetails" / "MetaDetails.js"
META_DETAILS_STYLES = ROOT / "web-overlay" / "src" / "routes" / "MetaDetails" / "styles.less"
VIDEOS_STYLES = ROOT / "web-overlay" / "src" / "routes" / "MetaDetails" / "VideosList" / "styles.less"
STREAMS_STYLES = ROOT / "web-overlay" / "src" / "routes" / "MetaDetails" / "StreamsList" / "styles.less"
SEARCH = ROOT / "web-overlay" / "src" / "routes" / "Search" / "Search.js"
SEARCH_STYLES = ROOT / "web-overlay" / "src" / "routes" / "Search" / "styles.less"
ADDONS_STYLES = ROOT / "web-overlay" / "src" / "routes" / "Addons" / "styles.less"
ADDON_STYLES = ROOT / "web-overlay" / "src" / "routes" / "Addons" / "Addon" / "styles.less"
SETTINGS_STYLES = ROOT / "web-overlay" / "src" / "routes" / "Settings" / "Settings.less"
SETTINGS_MENU = ROOT / "web-overlay" / "src" / "routes" / "Settings" / "Menu" / "Menu.tsx"
SETTINGS_MENU_STYLES = ROOT / "web-overlay" / "src" / "routes" / "Settings" / "Menu" / "Menu.less"
SETTINGS_GENERAL = ROOT / "web-overlay" / "src" / "routes" / "Settings" / "General" / "General.tsx"
SETTINGS_SECTION_STYLES = ROOT / "web-overlay" / "src" / "routes" / "Settings" / "components" / "Section" / "Section.less"
SETTINGS_OPTION_STYLES = ROOT / "web-overlay" / "src" / "routes" / "Settings" / "components" / "Option" / "Option.less"


class TvUiOverlayTests(unittest.TestCase):
    def test_home_uses_real_stremio_models(self) -> None:
        source = BOARD.read_text(encoding="utf-8")
        self.assertIn("useBoard()", source)
        self.assertIn("useContinueWatchingPreview()", source)
        self.assertIn("selectedItem?.background || selectedItem?.poster", source)
        self.assertNotIn("The Whisper Man", source)
        self.assertNotIn("Babylon", source)

    def test_home_has_one_active_catalog_stage(self) -> None:
        source = BOARD.read_text(encoding="utf-8")
        self.assertEqual(source.count("<section className={styles['catalog-stage']}>") , 1)
        self.assertIn("changeRow(1, itemIndex)", source)
        self.assertIn("changeRow(-1, itemIndex)", source)

    def test_tv_rail_keeps_search_after_desktop_header_is_removed(self) -> None:
        source = NAV.read_text(encoding="utf-8")
        self.assertIn("id: 'search'", source)
        self.assertIn("id: 'board'", source)
        self.assertIn("id: 'discover'", source)
        self.assertIn("id: 'library'", source)
        self.assertNotIn("HorizontalNavBar", source)

    def test_every_tv_route_starts_close_to_the_icon_rail(self) -> None:
        nav_styles = NAV_STYLES.read_text(encoding="utf-8")
        self.assertIn("--vertical-nav-bar-size: 4.5rem", nav_styles)
        self.assertIn("--tv-content-left: clamp(0.5rem, 0.8vw, 0.8rem)", nav_styles)

        route_styles = [
            BOARD.with_name("styles.less"),
            SEARCH_STYLES,
            DISCOVER.with_name("styles.less"),
            LIBRARY.with_name("styles.less"),
            ADDONS_STYLES,
            META_DETAILS_STYLES,
            SETTINGS_STYLES,
        ]
        for path in route_styles:
            styles = path.read_text(encoding="utf-8")
            self.assertIn("var(--tv-content-left)", styles, path)
            self.assertNotIn("left: 4.25%", styles, path)

    def test_tv_rail_expands_only_while_it_has_focus(self) -> None:
        source = RAIL.read_text(encoding="utf-8")
        component = RAIL_COMPONENT.read_text(encoding="utf-8")
        self.assertIn("onFocusCapture", component)
        self.assertIn("onBlurCapture", component)
        self.assertIn("[styles['expanded']]: expanded", component)
        self.assertIn("width: 11.5rem", source)
        self.assertIn("min-width: 11.5rem", source)
        self.assertIn("justify-content: center", source)
        self.assertIn("position: absolute", source)
        self.assertIn("top: 1rem", source)
        self.assertIn("max-height: 38rem", source)
        self.assertIn("padding-top: 5.7rem", source)
        self.assertIn("width: var(--vertical-nav-bar-size)", source)

    def test_tv_rail_is_reachable_and_returns_to_content(self) -> None:
        board = BOARD.read_text(encoding="utf-8")
        button = RAIL_BUTTON.read_text(encoding="utf-8")
        self.assertIn("document.querySelector('nav a.selected')", board)
        self.assertIn("tabIndex={logo ? -1 : 0}", button)
        self.assertIn("event.key === 'ArrowUp' || event.key === 'ArrowDown'", button)
        self.assertIn("querySelectorAll('a[tabindex=\"0\"]')", button)
        self.assertIn("event.key !== 'ArrowRight'", button)
        self.assertIn("[data-tv-row][data-tv-item=\"0\"]", button)

    def test_tv_login_uses_stremio_core_account_link(self) -> None:
        intro = INTRO.read_text(encoding="utf-8")
        styles = INTRO_STYLES.read_text(encoding="utf-8")

        self.assertIn("getState('auth_link')", intro)
        self.assertIn("dispatch(loadLinkAction, 'auth_link')", intro)
        self.assertIn("model: 'Link'", intro)
        self.assertIn("action: 'ReadData'", intro)
        self.assertIn("type: 'LoginWithToken'", intro)
        self.assertIn("linkCode.qrcode", intro)
        self.assertIn("Request a new link", intro)
        self.assertIn("requestButtonRef.current.focus()", intro)
        self.assertIn("interfaceLanguages", intro)
        self.assertNotIn("type={'password'}", intro)
        self.assertIn(".qr-frame", styles)

    def test_discover_uses_real_core_catalog_in_tv_layout(self) -> None:
        source = DISCOVER.read_text(encoding="utf-8")

        self.assertIn("useDiscover(urlParams, queryParams)", source)
        self.assertIn("discover.catalog.content.content", source)
        self.assertIn("selectedItem?.background || selectedItem?.poster", source)
        self.assertEqual(source.count("<section className={styles['catalog-stage']}>") , 1)
        self.assertIn("<MetaItem", source)
        self.assertIn("data-tv-row={0}", source)
        self.assertNotIn("MetaPreview", source)
        self.assertNotIn("The Whisper Man", source)

    def test_library_uses_real_account_catalog_in_tv_layout(self) -> None:
        source = LIBRARY.read_text(encoding="utf-8")

        self.assertIn("useLibrary(model, urlParams, queryParams)", source)
        self.assertIn("selectedItem?.background || selectedItem?.poster", source)
        self.assertEqual(source.count("<section className={styles['catalog-stage']}>") , 1)
        self.assertIn("<LibItem", source)
        self.assertIn("data-tv-row={0}", source)
        self.assertIn("notifications={notifications}", source)
        self.assertNotIn("The Whisper Man", source)

    def test_details_keeps_core_actions_but_uses_tv_composition(self) -> None:
        source = META_DETAILS.read_text(encoding="utf-8")
        styles = META_DETAILS_STYLES.read_text(encoding="utf-8")

        self.assertIn("useMetaDetails(urlParams)", source)
        self.assertIn("<MainNavBars", source)
        self.assertNotIn("HorizontalNavBar", source)
        self.assertIn("compact={true}", source)
        self.assertIn("action: 'AddToLibrary'", source)
        self.assertIn("action: 'RemoveFromLibrary'", source)
        self.assertIn("<VideosList", source)
        self.assertIn("<StreamsList", source)
        self.assertIn("bottom: 3.25%", styles)

    def test_details_uses_horizontal_episode_and_source_rows(self) -> None:
        videos = VIDEOS_STYLES.read_text(encoding="utf-8")
        streams = STREAMS_STYLES.read_text(encoding="utf-8")

        self.assertIn("overflow-x: auto", videos)
        self.assertIn("flex: 0 0 20rem", videos)
        self.assertIn("overflow-x: auto", streams)
        self.assertIn("flex: 0 0 21rem", streams)

    def test_search_has_tv_keyboard_and_real_results(self) -> None:
        source = SEARCH.read_text(encoding="utf-8")
        styles = SEARCH_STYLES.read_text(encoding="utf-8")

        self.assertIn("useSearch(queryParams)", source)
        self.assertIn("useBoard()", source)
        self.assertIn("'abcdefghijklmnopqrstuvwxyz'.split('')", source)
        self.assertIn("MediaPlayPause", source)
        self.assertIn("<MetaItem", source)
        self.assertIn("data-tv-key={key.id === characterKeys[0] ? 'entry'", source)
        self.assertIn("data-tv-row={'search-results'}", source)
        self.assertIn("grid-template-columns: repeat(6", styles)
        self.assertNotIn("The Whisper Man", source)

    def test_addons_keep_official_route_with_tv_scale_and_focus(self) -> None:
        route_styles = ADDONS_STYLES.read_text(encoding="utf-8")
        card_styles = ADDON_STYLES.read_text(encoding="utf-8")

        self.assertIn("content: 'Add-ons'", route_styles)
        self.assertIn("scrollbar-width: none", route_styles)
        self.assertIn("background: rgba(27, 27, 36, 0.88)", card_styles)
        self.assertIn("&:hover, &:focus, &:focus-within", card_styles)

    def test_settings_use_tv_section_rail_and_focusable_cards(self) -> None:
        route_styles = SETTINGS_STYLES.read_text(encoding="utf-8")
        general = SETTINGS_GENERAL.read_text(encoding="utf-8")
        menu = SETTINGS_MENU.read_text(encoding="utf-8")
        menu_styles = SETTINGS_MENU_STYLES.read_text(encoding="utf-8")
        section_styles = SETTINGS_SECTION_STYLES.read_text(encoding="utf-8")
        option_styles = SETTINGS_OPTION_STYLES.read_text(encoding="utf-8")

        self.assertIn("grid-template-columns: clamp(12.5rem, 17vw, 14rem) minmax(0, 1fr)", route_styles)
        self.assertIn("padding: 1.35rem 1.5rem 1.35rem var(--tv-content-left)", route_styles)
        self.assertIn("settings-stage", route_styles)
        self.assertIn("activeSection.content", (ROOT / "web-overlay" / "src" / "routes" / "Settings" / "Settings.tsx").read_text(encoding="utf-8"))
        self.assertIn("data-tv-row={'settings-menu'}", menu)
        self.assertIn("Choose a category", menu)
        self.assertIn("onKeyDown={onKeyDown}", menu)
        self.assertIn("event.stopPropagation()", menu)
        self.assertIn("min-height: 3.45rem", menu_styles)
        self.assertIn("width: min(68rem, 100%)", section_styles)
        self.assertIn("grid-template-columns: minmax(12rem, 1fr) minmax(13rem, 0.8fr)", option_styles)
        self.assertIn("&:focus-within", option_styles)
        self.assertIn("<User profile={profile} />", general)
        self.assertNotIn("openExternal", general)
        self.assertNotIn("href={'https://", general)
        self.assertNotIn("SETTINGS_TRAKT", general)


if __name__ == "__main__":
    unittest.main()
