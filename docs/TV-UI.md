# Stremio TV UI contract

The visible product targets the living-room Stremio experience used by the
Apple TV and Android TV applications. Stremio Web remains an upstream source
for the real Stremio Core connection and route behavior; its desktop layout is
not the product UI.

## Home behavior

- A narrow icon rail stays on the left. It shows only icons while content has
  focus, expands to reveal labels when the rail receives focus, and collapses
  again when focus returns to content.
- The selected real catalog item supplies the hero artwork, logo or title,
  release information, runtime, type, and description.
- There are no hero action buttons on Home.
- Exactly one catalog row is visible at the bottom of the screen.
- Left and right change the selected item and therefore the hero.
- Up and down change the active catalog while preserving the closest item
  position.
- Selecting an item opens the existing Stremio detail route.

## Discover and Library behavior

Discover, Library, and Continue Watching use the same living-room composition
as Home: the focused real Stremio item fills the hero and exactly one horizontal
catalog row remains in the lower part of the screen. Discover keeps its real
catalog filters and Library keeps its real type and sort controls, but presents
them as compact remote-friendly controls instead of the upstream desktop grid
and preview panel.

Moving focus changes the hero. Selecting a card continues through the existing
Stremio detail route; Library actions and account state remain owned by Stremio
Core. The left rail stays narrow until it receives focus.

## Detail behavior

Detail pages keep the same full-screen hero and left rail, but this is where
hero actions are allowed. The real Stremio detail model continues to own Play,
Trailer, Library, watched state, ratings, seasons, episodes, and stream source
selection. Series episodes and stream sources are presented as one horizontal
remote-friendly row in the lower part of the screen instead of a desktop side
panel.

## Search behavior

Search uses a single-line TV keyboard with ABC/123 switching, Space, characters,
and backspace. Play/Pause may switch keyboard modes when the remote reports that
key. Physical keyboard characters also update the same query. Results always
come from Stremio Core; before the user enters a query, the screen uses the first
available real Stremio catalog as its TV trending view.

## Add-ons and Settings behavior

Add-ons keeps the official Stremio install, configure, remove, share, filtering,
and URL flows. The route is presented as a compact ten-foot list with clear
remote focus and no replacement or hardcoded add-on data.

Settings keeps the official Stremio sections and the Vero 4K+ Device section in
a two-plane TV layout: a section rail at the left and large focusable setting
cards at the right. This is a presentation change only; the same Core and Vero
settings adapters remain responsible for the values.

No media title, artwork, description, catalog, or account content may be
hardcoded in the Vero overlay. All such content must originate in Stremio Core.

## TV sign-in

The unauthenticated route uses Stremio Core's `auth_link` model and official
account-link flow. It shows the short-lived QR code and link returned by Core,
polls for approval, and authenticates with the returned one-time token. The TV
never asks the user to type or store their Stremio password.

The presentation follows the official Android TV layout: Stremio branding in
the upper-left, language in the upper-right, a centered QR code, two short
instructions, a remote-focusable `Request a new link` action, and a five-minute
countdown. No QR code, link code, or account token is committed to this repo.
