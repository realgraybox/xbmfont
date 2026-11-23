/* xbfview - a tiny text file viewer, as an xbmfont example.
 *
 *   xbfview [file]      (no file: shows a sample with every glyph)
 *
 * Keys: + / -        bigger / smaller text (all fonts and scales in turn)
 *       a            automatic size: about 40 lines fill the window
 *       Up/Down, PgUp/PgDn, Home/End   scroll
 *       q / Esc      quit
 *
 * The text is UTF-8 (invalid bytes are shown as Latin-1); tabs are expanded.
 *
 * zlib License - Copyright (c) 2026 M.Glargaard aka realgraybox (see LICENSE)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/keysym.h>

#define XBMFONT_IMPLEMENTATION
#include "xbmfont.h"
#include "fonts/xbf_fixed_5x8.h"
#include "fonts/xbf_fixed_6x10.h"
#include "fonts/xbf_fixed_6x13.h"
#include "fonts/xbf_fixed_6x13b.h"
#include "fonts/xbf_fixed_7x14.h"
#include "fonts/xbf_fixed_9x15.h"
#include "fonts/xbf_fixed_9x18.h"
#include "fonts/xbf_fixed_10x20.h"

static const xbf_font *const fonts[] = {
    &xbf_fixed_5x8, &xbf_fixed_6x10, &xbf_fixed_6x13, &xbf_fixed_7x14,
    &xbf_fixed_9x15, &xbf_fixed_9x18, &xbf_fixed_10x20
};
#define NFONTS ((int)(sizeof fonts / sizeof fonts[0]))

#define AUTO_LINES 40           /* automatic size: lines that should fit */
#define MAX_SIZES 64

/* Every distinct size the fonts give, smallest first: font + scale */
typedef struct { const xbf_font *font; int scale; } text_size;
static text_size sizes[MAX_SIZES];
static int nsizes = 0;

static void build_sizes(int max_line)
{
    int h;
    for (h = 1; h <= max_line && nsizes < MAX_SIZES; h++) {
        int s;
        const xbf_font *f = xbf_pick(fonts, NFONTS, h, &s);
        if (f->height * s == h) {
            sizes[nsizes].font = f;
            sizes[nsizes].scale = s;
            nsizes++;
        }
    }
}

static const char sample[] =
    "xbmfont - embedded bitmap fonts for Xlib\n"
    "\n"
    "The same look on every X server, and sharp at any size.\n"
    "Press + and - to change the size, a for automatic size.\n"
    "\n"
    "ASCII:\n"
    "  !\"#$%&'()*+,-./0123456789:;<=>?\n"
    "  @ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_\n"
    "  `abcdefghijklmnopqrstuvwxyz{|}~\n"
    "Latin-1:\n"
    "  \xc2\xa0\xc2\xa1\xc2\xa2\xc2\xa3\xc2\xa4\xc2\xa5\xc2\xa6\xc2\xa7\xc2\xa8\xc2\xa9\xc2\xaa\xc2\xab\xc2\xac\xc2\xad\xc2\xae\xc2\xaf"
    "\xc2\xb0\xc2\xb1\xc2\xb2\xc2\xb3\xc2\xb4\xc2\xb5\xc2\xb6\xc2\xb7\xc2\xb8\xc2\xb9\xc2\xba\xc2\xbb\xc2\xbc\xc2\xbd\xc2\xbe\xc2\xbf\n"
    "  \xc3\x80\xc3\x81\xc3\x82\xc3\x83\xc3\x84\xc3\x85\xc3\x86\xc3\x87\xc3\x88\xc3\x89\xc3\x8a\xc3\x8b\xc3\x8c\xc3\x8d\xc3\x8e\xc3\x8f"
    "\xc3\x90\xc3\x91\xc3\x92\xc3\x93\xc3\x94\xc3\x95\xc3\x96\xc3\x97\xc3\x98\xc3\x99\xc3\x9a\xc3\x9b\xc3\x9c\xc3\x9d\xc3\x9e\xc3\x9f\n"
    "  \xc3\xa0\xc3\xa1\xc3\xa2\xc3\xa3\xc3\xa4\xc3\xa5\xc3\xa6\xc3\xa7\xc3\xa8\xc3\xa9\xc3\xaa\xc3\xab\xc3\xac\xc3\xad\xc3\xae\xc3\xaf"
    "\xc3\xb0\xc3\xb1\xc3\xb2\xc3\xb3\xc3\xb4\xc3\xb5\xc3\xb6\xc3\xb7\xc3\xb8\xc3\xb9\xc3\xba\xc3\xbb\xc3\xbc\xc3\xbd\xc3\xbe\xc3\xbf\n"
    "\n"
    "Danish (UTF-8): blåbærgrød med fløde - Æbleskiver, Øresund, Århus\n"
    "Latin-1 bytes (not UTF-8): \xe6\xf8\xe5 \xc6\xd8\xc5\n"
    "Windows-1252 bytes: \x93quoted\x94 \x96 \x80""5 \x85\n"
    "\n"
    "Latin Extended-A: Dvořák, Chopin's Życie, Łódź, Mozart in Brno - Kraków\n"
    "  Ő ő Ű ű Š š Č č Ž ž Ę ę Ā ā Ğ ğ İ ı Ş ş Œ œ Ÿ\n"
    "Punctuation: \u201ccurly\u201d \u2018quotes\u2019 \u201elow\u201c en\u2013dash em\u2014dash \u2026 \u2022 \u2020 \u20ac \u2122 \u2030\n"
    "Symbols: \u2190 \u2191 \u2192 \u2193  \u25b6 \u25a0 \u25c0 \u25b2 \u25bc  \u266a \u266b  \u2713\n"
    "Not in the font: \u65e5\u672c \u0416 \u03a9\n"
    "\n"
    "A long line is cut with an ellipsis at the window edge: Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.\n"
    "Tab:\tafter a tab\n";

typedef struct { const char *s; int n; } line_t;

static char *text;
static line_t *lines;
static int nlines;

static int load_text(const char *path)
{
    size_t len = 0, cap = 0;
    char *t = NULL;
    int i, start;

    if (path) {
        FILE *f = fopen(path, "rb");
        if (!f) { perror(path); return -1; }
        for (;;) {
            if (len + 4096 > cap) {
                char *nt = realloc(t, cap = cap ? cap * 2 : 65536);
                if (!nt) { fclose(f); free(t); return -1; }
                t = nt;
            }
            size_t r = fread(t + len, 1, cap - len - 1, f);
            if (r == 0) break;
            len += r;
        }
        fclose(f);
    } else {
        len = sizeof sample - 1;
        t = malloc(len + 1);
        if (!t) return -1;
        memcpy(t, sample, len);
    }
    t[len] = 0;

    /* split into lines, expanding tabs to 8 columns into a new buffer */
    {
        size_t outcap = len * 2 + 64, o = 0;
        char *out = malloc(outcap);
        int col = 0;
        if (!out) { free(t); return -1; }
        for (i = 0; i < (int)len; i++) {
            unsigned char ch = (unsigned char)t[i];
            if (o + 16 >= outcap) {
                char *no = realloc(out, outcap *= 2);
                if (!no) { free(out); free(t); return -1; }
                out = no;
            }
            if (ch == '\t') {
                do { out[o++] = ' '; col++; } while (col % 8);
            } else if (ch == '\r') {
                continue;
            } else {
                out[o++] = (char)ch;
                if (ch == '\n') col = 0;
                else if ((ch & 0xC0) != 0x80) col++;   /* count code points */
            }
        }
        out[o] = 0;
        free(t);
        text = out;
        len = o;
    }

    nlines = 1;
    for (i = 0; i < (int)len; i++) if (text[i] == '\n') nlines++;
    lines = malloc(sizeof *lines * (size_t)nlines);
    if (!lines) return -1;
    nlines = 0;
    start = 0;
    for (i = 0; i <= (int)len; i++) {
        if (i == (int)len || text[i] == '\n') {
            if (i == (int)len && i == start) break;  /* no empty last line */
            lines[nlines].s = text + start;
            lines[nlines].n = i - start;
            nlines++;
            start = i + 1;
        }
    }
    return 0;
}

int main(int argc, char **argv)
{
    const char *path = argc > 1 ? argv[1] : NULL;
    Display *dpy;
    Window win;
    Pixmap back = None;
    GC gc;
    Atom wm_delete;
    xbf_ctx *txt = NULL, *bar = NULL;
    int W = 800, H = 600, bw = 0, bh = 0, cur, top = 0, autosize = 0, running = 1, dirty = 1;
    unsigned long fg, bg, barbg, dim;

    if (load_text(path) < 0) return 1;
    dpy = XOpenDisplay(NULL);
    if (!dpy) { fprintf(stderr, "cannot open display\n"); return 1; }

    {
        int scr = DefaultScreen(dpy);
        fg = 0xE0E0E0; bg = 0x101418; barbg = 0x2A3A4A; dim = 0x8090A0;
        win = XCreateSimpleWindow(dpy, RootWindow(dpy, scr), 0, 0, (unsigned)W, (unsigned)H, 0,
                                  BlackPixel(dpy, scr), bg);
    }
    XStoreName(dpy, win, path ? path : "xbfview - xbmfont sample");
    XSelectInput(dpy, win, ExposureMask | KeyPressMask | StructureNotifyMask);
    wm_delete = XInternAtom(dpy, "WM_DELETE_WINDOW", False);
    XSetWMProtocols(dpy, win, &wm_delete, 1);
    XMapWindow(dpy, win);
    gc = XCreateGC(dpy, win, 0, NULL);

    build_sizes(XBF_MAX_SCALE * 20);
    for (cur = 0; cur < nsizes; cur++)        /* start at 6x13, like X's "fixed" */
        if (sizes[cur].font == &xbf_fixed_6x13 && sizes[cur].scale == 1) break;
    if (cur == nsizes) cur = 0;
    bar = xbf_create(dpy, win, &xbf_fixed_6x13b, 1);

    while (running) {
        XEvent ev;
        XNextEvent(dpy, &ev);
        switch (ev.type) {
        case ConfigureNotify:
            if (ev.xconfigure.width != W || ev.xconfigure.height != H) {
                W = ev.xconfigure.width;
                H = ev.xconfigure.height;
                dirty = 1;
            }
            break;
        case Expose:
            if (ev.xexpose.count == 0) dirty = 1;
            break;
        case ClientMessage:
            if ((Atom)ev.xclient.data.l[0] == wm_delete) running = 0;
            break;
        case KeyPress: {
            KeySym k = XLookupKeysym(&ev.xkey, 0);
            int page = (H - xbf_line_height(bar) - 8) / (txt ? xbf_line_height(txt) : 13) - 1;
            char ch = 0;
            XLookupString(&ev.xkey, &ch, 1, NULL, NULL);
            if (page < 1) page = 1;
            if (k == XK_q || k == XK_Escape) running = 0;
            else if (ch == '+' || k == XK_KP_Add) { autosize = 0; if (cur < nsizes - 1) cur++; }
            else if (ch == '-' || k == XK_KP_Subtract) { autosize = 0; if (cur > 0) cur--; }
            else if (k == XK_a) autosize = !autosize;
            else if (k == XK_Down) top++;
            else if (k == XK_Up) top--;
            else if (k == XK_Next) top += page;
            else if (k == XK_Prior) top -= page;
            else if (k == XK_Home) top = 0;
            else if (k == XK_End) top = nlines;
            dirty = 1;
            break;
        }
        }
        if (!dirty || XPending(dpy)) continue;   /* draw once the queue is empty */
        dirty = 0;

        /* choose the size; rebuild the context only when it changes */
        if (autosize) {
            int s;
            const xbf_font *f = xbf_pick(fonts, NFONTS, (H - 20) / AUTO_LINES, &s);
            for (cur = 0; cur < nsizes; cur++)
                if (sizes[cur].font == f && sizes[cur].scale == s) break;
            if (cur == nsizes) cur = 0;
        }
        if (!txt || xbf_ctx_font(txt) != sizes[cur].font || xbf_ctx_scale(txt) != sizes[cur].scale) {
            xbf_free(txt);
            txt = xbf_create(dpy, win, sizes[cur].font, sizes[cur].scale);
            if (!txt) { fprintf(stderr, "font upload failed\n"); break; }
        }
        if (W != bw || H != bh) {          /* back buffer: no flicker */
            if (back != None) XFreePixmap(dpy, back);
            back = XCreatePixmap(dpy, win, (unsigned)W, (unsigned)H,
                                 (unsigned)DefaultDepth(dpy, DefaultScreen(dpy)));
            bw = W; bh = H;
        }

        {
            int lh = xbf_line_height(txt), barh = xbf_line_height(bar) + 8;
            int visible = (H - barh - 4) / lh, y, i;
            char status[256];

            if (top > nlines - visible) top = nlines - visible;
            if (top < 0) top = 0;

            XSetForeground(dpy, gc, bg);
            XFillRectangle(dpy, back, gc, 0, 0, (unsigned)W, (unsigned)H);
            y = 2 + xbf_ascent(txt);
            for (i = top; i < nlines && i < top + visible; i++, y += lh)
                xbf_draw_fit_n(txt, back, 6, y, fg, lines[i].s, lines[i].n, W - 12, XBF_CUT_END);

            XSetForeground(dpy, gc, barbg);
            XFillRectangle(dpy, back, gc, 0, H - barh, (unsigned)W, (unsigned)barh);
            /* status: file name (cut in the middle if needed), size, keys */
            {
                static const char keys[] = "+/- size  a auto  q quit ";
                int by = H - barh + 4 + xbf_ascent(bar), kw = xbf_text_width(bar, keys), x;
                snprintf(status, sizeof status, "  |  %s x%d (line %d px)%s  |  lines %d-%d of %d",
                         sizes[cur].font->name, sizes[cur].scale, lh, autosize ? " auto" : "",
                         nlines ? top + 1 : 0, top + visible < nlines ? top + visible : nlines,
                         nlines);
                x = 4 + xbf_draw_fit(bar, back, 4, by, 0xFFFFFF, path ? path : "sample",
                                     W - 16 - kw - xbf_text_width(bar, status), XBF_CUT_MIDDLE);
                xbf_draw_fit(bar, back, x, by, 0xFFFFFF, status, W - 12 - kw - x, XBF_CUT_END);
                xbf_draw(bar, back, W - kw - 4, by, dim, keys);
            }

            XCopyArea(dpy, back, win, gc, 0, 0, (unsigned)W, (unsigned)H, 0, 0);
            XFlush(dpy);
        }
    }

    xbf_free(txt);
    xbf_free(bar);
    if (back != None) XFreePixmap(dpy, back);
    XFreeGC(dpy, gc);
    XDestroyWindow(dpy, win);
    XCloseDisplay(dpy);
    free(lines);
    free(text);
    return 0;
}
