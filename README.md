# xbmfont

Embedded bitmap fonts for Xlib programs, in one header.

Programs that draw text with the X server's core fonts (`XLoadQueryFont`,
`XDrawString`) look different from machine to machine: "fixed" is whatever the
server's font path makes of it, minimal X servers may only have one size, and
bitmap core fonts do not grow with the screen. xbmfont compiles the fonts into
the program instead:

- **the same look everywhere** - no dependency on the server's fonts
- **sharp at any size** - native sizes from 8 to 20 pixels, plus whole-number
  scaling (2×, 3×, ...) for large screens
- **UTF-8 text** with ASCII, Latin-1 (æ ø å ä ö ü é ...), Latin Extended-A
  (ř ł ő š ž ...), curly quotes, dashes, "…", €, arrows and a few symbols
  (▶ ■ ♪ ✓); a byte that is not valid UTF-8 is taken as Windows-1252, so old
  8-bit file names and MIDI texts still show right
- **text that fits**: shorten with "…" at the end, in the middle or at the start
- **small and plain**: Xlib only, C99, no other libraries; 3-16 KB per font size

The bundled fonts are the classic X11 **misc-fixed** fonts (public domain), so
text looks just like X's own `fixed` - but now on every machine. See
[fonts/README.md](fonts/README.md) for sources and licence details.

## Use

```c
#define XBMFONT_IMPLEMENTATION      /* in exactly one .c file */
#include "xbmfont.h"
#include "fonts/xbf_fixed_6x13.h"   /* each font you want */

xbf_ctx *t = xbf_create(dpy, window, &xbf_fixed_6x13, 2);   /* 2 = double size */
xbf_draw(t, window, 10, 40, 0xFFFFFF, "Grøn æblegrød");     /* x, baseline y */
int w = xbf_text_width(t, "Grøn æblegrød");
xbf_free(t);
```

Coordinates work like `XDrawString`: `x` is the left edge, `y` the baseline.
The colour is passed with each call; the library has its own GC and never
changes yours.

To fit text to the window, let the library choose a font and scale:

```c
static const xbf_font *const fonts[] = {
    &xbf_fixed_6x13, &xbf_fixed_7x14, &xbf_fixed_9x15, &xbf_fixed_10x20
};
int scale;
const xbf_font *f = xbf_pick(fonts, 4, window_height / 40, &scale);
xbf_ctx *t = xbf_create(dpy, window, f, scale);
```

`xbf_pick` returns the largest size whose line height is not above the one
asked for, and prefers a native size over a scaled one of the same height.

### API

| Function | |
|---|---|
| `xbf_create(dpy, like, font, scale)` | upload a font at a scale; `like` is any drawable of the depth you draw on |
| `xbf_free(ctx)` | |
| `xbf_draw(ctx, d, x, y, pixel, utf8)` | draw text, returns its width |
| `xbf_draw_n(ctx, d, x, y, pixel, utf8, bytes)` | the same for text that is not 0-terminated |
| `xbf_draw_fit(ctx, d, x, y, pixel, utf8, max_px, cut)` | draw into at most `max_px`, shortened with "…" if needed: `XBF_CUT_END`, `XBF_CUT_MIDDLE` or `XBF_CUT_START`; returns the width |
| `xbf_fit_width(ctx, utf8, max_px)` | the width `xbf_draw_fit` will draw, e.g. to right-align |
| `xbf_fit_bytes(ctx, utf8, bytes, max_px)` | bytes of the longest start that fits, never splitting a character (for wrapping) |
| `xbf_font_has(font, codepoint)` | 1 if the font has the character, else it is drawn as `?` |
| `xbf_text_width(ctx, utf8)` | width in pixels |
| `xbf_char_width`, `xbf_line_height`, `xbf_ascent`, `xbf_descent` | metrics at the context's scale |
| `xbf_strlen(utf8)` | characters, counted as drawn |
| `xbf_pick(fonts, n, line_px, &scale)` | best font and scale for a line height |
| `xbf_ctx_font`, `xbf_ctx_scale` | what a context was made with |

A context belongs to one X connection. A program with two connections (for
example a file dialog that opens its own) makes one context for each.
Every function taking a 0-terminated string also has an `_n` variant taking a
byte count (`xbf_draw_n`, `xbf_draw_fit_n`, `xbf_text_width_n`, `xbf_fit_width_n`).
Define `XBMFONT_STATIC` before the include to make all functions `static`.

Shortening a file name to a column:

```c
xbf_draw_fit(t, win, x, y, fg, "/home/me/midi/classic/Dvořák – Humoreske.mid",
             column_px, XBF_CUT_MIDDLE);   /* "/home/me/mi…Humoreske.mid" */
```

### How it works

`xbf_create` draws all glyphs of the font, scaled, into a 1-bit pixmap and
uploads it to the X server once. Each character is then a stippled rectangle
from that pixmap: two small requests, and nothing that waits for the server.

## Example: xbfview

`examples/xbfview.c` is a small text file viewer (about 300 lines). Long lines
end in "…" at the window edge, and a long file name is shortened in the middle
in the status bar:

    make
    ./examples/xbfview README.md      # or no file for a sample of every glyph

`+` / `-` step through all sizes, `a` picks the size from the window height,
arrows / PgUp / PgDn / Home / End scroll, `q` quits.

## Fonts

| | Native line heights | With scaling |
|---|---|---|
| bundled | 8, 10, 13, 14, 15, 18, 20 px | any multiple of those, up to 16× |

Each font has the 191 printable characters of ASCII + Latin-1 and about 175
more: Latin Extended-A, the rest of Windows-1252, arrows (← ↑ → ↓), media
symbols (▶ ■ ◀ ▲ ▼), ♪ ♫ and ✓. A few sizes lack a few of the symbols; see
[fonts/README.md](fonts/README.md).

`tools/bdf2xbf.py` converts any monospaced BDF font; `--extra` chooses which
characters beyond Latin-1 to include. It refuses a font whose
COPYRIGHT property does not say "Public domain" unless you give it the font's
licence file - see [fonts/README.md](fonts/README.md).

## Licence

zlib - see [LICENSE](LICENSE). The bundled fonts are public domain.
