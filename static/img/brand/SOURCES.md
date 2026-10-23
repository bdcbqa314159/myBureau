# Where these marks came from

Nothing in this folder is ours. Each file is an **unmodified** brand
asset, renamed and nothing else, downloaded from the brand owner's own
resources page by accepting that page's terms — which is the licence to
use it. They are the owners' trademarks, they are **not** covered by this
repository's LICENSE, and they are here for one purpose: to link to the
site owner's own profile on each service.

Taking any of these from a third-party icon pack, a search result or
another website is not permitted by any of the three owners. If a file
here did not come from the page named below, replace it.

| file | from | the asset, as that kit names it |
|---|---|---|
| `instagram-white.svg` | <https://www.facebook.com/brand/resources/instagram/icons> | `02 White Glyph/Instagram_Glyph_White.svg` |
| `instagram-black.svg` | same | `03 Black Glyph/Instagram_Glyph_Black.svg` |
| `youtube-white.png` | <https://brand.youtube/> | `Digital/03 White/yt_icon_white_digital.png` |
| `youtube-black.png` | same | `Digital/02 Almost Black/yt_icon_almostblack_digital.png` |
| `spotify-white.png` | <https://developer.spotify.com/documentation/design> → `2024-spotify-logo-icon.zip` | `Spotify_Primary_Logo_RGB_White.png` |
| `spotify-black.png` | same | `Spotify_Primary_Logo_RGB_Black.png` |

YouTube's dark variant is their **Almost Black** (#212121), not pure
black — that is the asset they publish, and the filename here says
`-black` only so the three services can be named the same way.

Instagram ships SVG, the other two ship PNG for digital use. That is
what each kit contains; nothing was converted.

## Two colours, because this site has two kinds of page

A white mark is invisible on a cream project page, and **none of the
three owners allows you to recolour their mark yourself** — YouTube's
branding guidelines say outright that the icons "cannot have their colors
modified". So both variants are taken from the kit and CSS picks one.
Nothing in this site tints, masks, filters or fades a mark.

That is also why the dock darkens the *ground behind* the marks on
photograph pages rather than putting a drop-shadow on them: a shadow on
the artwork is an added effect, which all three forbid. See "the dock" in
`static/css/site.css`.

## What is still owed before this goes live

The urls in `social` (config.toml) point at the three services' own
homepages, because they are placeholders like the photographs. All three
owners permit the mark **as a link to your own presence** and none of
them permit it as decoration. Real profile urls are a condition of
shipping these marks, not a nicety.

## Sizes the owners require

Spotify sets the floor: the icon never below **21px**, with clear space
of half its height. The dock renders its ink at 22.3px with a 13.6px gap,
which clears both.

**The three are not framed alike**, which is why they are not sized
alike. Measured, the ink inside each file fills:

| | ink fills | ink aspect |
|---|---|---|
| `instagram-*.svg` | 100% x 100% | 1.00 |
| `spotify-*.png` | 97% x 97% | 1.00 |
| `youtube-*.png` | **66% x 54%** | 1.43 |

YouTube ships its icon with the required clear space built into the file.
Give all three the same height and YouTube's mark renders at barely half
the visual size of the other two. So each is scaled until the ink reads
as one size, and the per-mark numbers live in `site.css` with the
arithmetic written out.

Scaling proportionally is what every one of the three owners allows, and
what their minimum-size rules presume. Nothing here is stretched,
cropped or trimmed — the clear space inside YouTube's file scales with
the file, so it stays above their minimum rather than under it.

## LinkedIn

Asked for, then dropped — she does not want it. Nothing here is a
LinkedIn asset. If it ever comes back, note that LinkedIn is the one of
the four that does **not** publish a white variant for online use: their
rule is colour online, solid black where colour is not practical. Do not
make a white one.
