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
