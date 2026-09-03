# Stremio Supporters compatibility

Stremio for Vero 4K+ must use the user's real Stremio account and the official
service entitlement. It must not duplicate, locally unlock, or bypass paid
Stremio Supporter features.

Official references checked on 2026-09-03:

- <https://blog.stremio.com/stremio-supporters-a-way-to-sustain-our-development/>
- <https://www.stremio.com/donate>

## Vero target

| Feature | Vero target | Integration note |
| --- | --- | --- |
| User profiles and PIN | Yes | Profile selection is a TV screen; profile management remains account-backed. |
| Skip intro and outro | Yes, after playback bridge support | The hidden Kodi player must receive and expose the markers/actions. |
| Move, hide, and rename catalogs | Yes | Respect the account's catalog order first; add remote-friendly management only if the official API exposes it safely. |
| Stream filters | Yes | Apply account filters to the real Stremio stream list; creation may remain on Web/Desktop initially. |
| Enhanced Cinemeta | Yes | Catalogs and recommendations arrive through the signed-in Stremio account. |
| Download manager | Later, not automatic | Stremio currently lists this for Desktop and Android Mobile, not TV. Vero storage and lifecycle need a separate design. |
| Live subtitle sync | Later, not automatic | Stremio currently lists it for Desktop and Web. Kodi playback hand-off needs a dedicated bridge. |
| Appearance choices | Yes where exposed | Map account-backed choices to the TV presentation without permitting a desktop layout. |

The Basic account path remains supported. Supporter-only controls are shown
only when the official Stremio account reports that the feature is available.
