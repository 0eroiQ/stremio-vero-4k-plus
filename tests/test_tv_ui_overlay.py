from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "web-overlay" / "src" / "routes" / "Board" / "Board.js"
NAV = ROOT / "web-overlay" / "src" / "components" / "MainNavBars" / "MainNavBars.tsx"
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

    def test_tv_rail_expands_only_while_it_has_focus(self) -> None:
        source = RAIL.read_text(encoding="utf-8")
        component = RAIL_COMPONENT.read_text(encoding="utf-8")
        self.assertIn("onFocusCapture", component)
        self.assertIn("onBlurCapture", component)
        self.assertIn("[styles['expanded']]: expanded", component)
        self.assertIn("width: 18vw", source)
        self.assertIn("width: var(--vertical-nav-bar-size)", source)

    def test_tv_rail_is_reachable_and_returns_to_content(self) -> None:
        board = BOARD.read_text(encoding="utf-8")
        button = RAIL_BUTTON.read_text(encoding="utf-8")
        self.assertIn("document.querySelector('nav a.selected')", board)
        self.assertIn("tabIndex={0}", button)
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


if __name__ == "__main__":
    unittest.main()
