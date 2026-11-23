#!/usr/bin/env python3
"""bdf2xbf.py - convert a monospaced BDF bitmap font into an xbmfont C header.

Usage:
    python3 bdf2xbf.py FONT.bdf NAME OUTPUT.h [--extra RANGES] [--license FILE]

NAME becomes the C identifier, e.g. "fixed_6x13" -> xbf_fixed_6x13.
Code points 0x20-0xFF (ASCII + Latin-1) always form the main table; glyphs the
font lacks there are marked missing and drawn as '?' by the library.

--extra adds a sparse set of further code points, as hex ranges such as
"0100-017F,20AC". "default" (the default) is Latin Extended-A, the rest of
Windows-1252 (curly quotes, dashes, ellipsis, euro, ...), arrows and a few UI
symbols - see DEFAULT_EXTRA. "none" leaves them out. Extra code points the
font does not have are simply not included.

Licence check: a font is only converted if its COPYRIGHT property says
"Public domain". For a font under another licence, pass the licence text with
--license FILE: the header then says which licence applies, and FILE must be
shipped next to the header (and its notice reproduced where the licence asks).

Part of xbmfont - zlib License, Copyright (c) 2026 M.Glargaard aka realgraybox
"""
import argparse
import hashlib
import os
import re
import sys

FIRST, LAST = 0x20, 0xFF

DEFAULT_EXTRA = ",".join([
    "0100-017F",              # Latin Extended-A: Central European, Baltic, Turkish ...
    "0192,0218-021B",         # f hook, Romanian S/T comma
    "02C6-02C7,02D8-02DD",    # spacing accents (Windows-1252 circumflex, tilde ...)
    "2010-2015,2018-201E",    # hyphens, dashes, curly quotes
    "2020-2022,2026,2030",    # daggers, bullet, ellipsis, per mille
    "2039-203A,20AC,2122",    # single guillemets, euro, trade mark
    "2190-2193,2212",         # arrows, minus
    "25A0,25B2,25B6,25BC,25C0",  # square, triangles (stop, up, play, down, back)
    "266A-266B,2713",         # notes, check mark
])


def parse_ranges(text):
    if text == "none":
        return []
    if text == "default":
        text = DEFAULT_EXTRA
    cps = set()
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        a, _, b = part.partition("-")
        lo, hi = int(a, 16), int(b or a, 16)
        if lo > hi or hi > 0xFFFF:
            sys.exit("bad range %r (code points up to FFFF)" % part)
        cps.update(range(lo, hi + 1))
    return sorted(c for c in cps if c > LAST)


def parse_bdf(path):
    props = {}
    glyphs = {}
    with open(path, encoding="latin-1") as f:
        lines = f.read().splitlines()
    i = 0
    cur = None
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line:
            continue
        key, _, rest = line.partition(" ")
        if cur is None:
            if key == "STARTCHAR":
                cur = {"name": rest}
            elif key in ("FONT", "COPYRIGHT", "FONT_ASCENT", "FONT_DESCENT",
                         "FONTBOUNDINGBOX", "SPACING", "NOTICE"):
                props[key] = rest
            continue
        if key == "ENCODING":
            cur["enc"] = int(rest.split()[0])
        elif key == "DWIDTH":
            cur["dwidth"] = int(rest.split()[0])
        elif key == "BBX":
            cur["bbx"] = [int(v) for v in rest.split()]
        elif key == "BITMAP":
            rows = []
            while lines[i].strip() != "ENDCHAR":
                rows.append(lines[i].strip())
                i += 1
            i += 1
            cur["bitmap"] = rows
            if cur.get("enc", -1) >= 0:
                glyphs[cur["enc"]] = cur
            cur = None
    return props, glyphs


def compact(cps):
    """[0x100, 0x101, 0x102, 0x20AC] -> "0100-0102 20AC" """
    out, i = [], 0
    while i < len(cps):
        j = i
        while j + 1 < len(cps) and cps[j + 1] == cps[j] + 1:
            j += 1
        out.append("%04X" % cps[i] if i == j else "%04X-%04X" % (cps[i], cps[j]))
        i = j + 1
    return " ".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("bdf")
    ap.add_argument("name", help="C name without the xbf_ prefix, e.g. fixed_6x13")
    ap.add_argument("output")
    ap.add_argument("--extra", metavar="RANGES", default="default",
                    help='extra code points: hex ranges, "default" or "none"')
    ap.add_argument("--license", metavar="FILE",
                    help="licence text of a font that is not public domain")
    a = ap.parse_args()

    if not re.fullmatch(r"[a-z0-9_]+", a.name):
        sys.exit("NAME must be lower case letters, digits and underscores")

    props, glyphs = parse_bdf(a.bdf)
    copyright_ = props.get("COPYRIGHT", "").strip().strip('"')
    if a.license:
        if not os.path.isfile(a.license):
            sys.exit("licence file not found: %s" % a.license)
        licence_note = "Licence: see %s (ship it with this header)." % os.path.basename(a.license)
    elif "public domain" in copyright_.lower():
        licence_note = "Public domain."
    else:
        sys.exit("refusing %s: its COPYRIGHT property is %r, not public domain.\n"
                 "Check the font's licence and pass it with --license FILE."
                 % (a.bdf, copyright_))

    try:
        ascent = int(props["FONT_ASCENT"])
        descent = int(props["FONT_DESCENT"])
    except KeyError:
        sys.exit("FONT_ASCENT / FONT_DESCENT missing")
    height = ascent + descent

    extra = [c for c in parse_ranges(a.extra) if c in glyphs]

    widths = {g["dwidth"] for c, g in glyphs.items() if FIRST <= c <= LAST and "dwidth" in g}
    if len(widths) != 1:
        sys.exit("not a monospaced font in 0x20-0xFF (advances: %s)" % sorted(widths))
    width = widths.pop()
    odd = [c for c in extra if glyphs[c].get("dwidth", width) != width]
    if odd:   # e.g. double-width glyphs: leave them out
        extra = [c for c in extra if c not in odd]
    row_bytes = (width + 7) // 8

    out_rows = []      # per glyph: list of row byte-lists
    missing = []
    for c in list(range(FIRST, LAST + 1)) + extra:
        g = glyphs.get(c)
        cell = [[0] * width for _ in range(height)]
        if g is None:
            missing.append(c)
        else:
            bw, bh, bx, by = g["bbx"]
            for r, hexrow in enumerate(g["bitmap"]):
                bits = int(hexrow, 16)
                nbits = len(hexrow) * 4
                y = ascent - (by + bh) + r
                for col in range(bw):
                    if bits >> (nbits - 1 - col) & 1:
                        x = bx + col
                        if 0 <= x < width and 0 <= y < height:
                            cell[y][x] = 1
        rows = []
        for y in range(height):
            rb = []
            for b in range(row_bytes):
                v = 0
                for k in range(8):
                    x = b * 8 + k
                    if x < width and cell[y][x]:
                        v |= 0x80 >> k
                rb.append(v)
            rows.append(rb)
        out_rows.append(rows)

    # Code points 0x7F-0x9F are control characters: not having them is normal
    real_missing = [c for c in missing if not (0x7F <= c <= 0x9F)]

    with open(a.bdf, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()

    cname = "xbf_" + a.name
    guard = "XBF_FONT_" + a.name.upper() + "_H"
    o = []
    o.append("/* %s - generated by tools/bdf2xbf.py, do not edit." % os.path.basename(a.output))
    o.append(" *")
    o.append(" * Source: %s (sha256 %s)" % (os.path.basename(a.bdf), sha[:16]))
    o.append(" * FONT %s" % props.get("FONT", "?"))
    o.append(" * COPYRIGHT \"%s\"" % copyright_)
    o.append(" * %s" % licence_note)
    o.append(" * Cell %dx%d, ascent %d, code points 0x%02X-0x%02X%s" % (
        width, height, ascent, FIRST, LAST,
        (", missing: " + " ".join("0x%02X" % c for c in real_missing)) if real_missing else ""))
    if extra:
        o.append(" * Extra: %d code points %s" % (len(extra), compact(extra)))
    o.append(" */")
    o.append("#ifndef %s" % guard)
    o.append("#define %s" % guard)
    o.append("")
    o.append('#include "xbmfont.h"')
    o.append("")
    order = list(range(FIRST, LAST + 1)) + extra
    o.append("static const unsigned char %s_bits[%d] = {" % (cname, len(order) * height * row_bytes))
    for c, rows in zip(order, out_rows):
        flat = ",".join("0x%02x" % v for rb in rows for v in rb)
        label = chr(c) if 0x20 < c < 0x7F and chr(c) not in "\\*/" else "U+%04X" % c
        o.append("    %s, /* %s */" % (flat, label))
    o.append("};")
    if missing:
        bitset = [0] * ((LAST - FIRST + 1 + 7) // 8)
        for c in missing:
            i = c - FIRST
            bitset[i // 8] |= 1 << (i % 8)
        o.append("static const unsigned char %s_missing[%d] = {%s};" % (
            cname, len(bitset), ",".join("0x%02x" % v for v in bitset)))
    if extra:
        o.append("static const unsigned short %s_extra[%d] = {" % (cname, len(extra)))
        for k in range(0, len(extra), 12):
            o.append("    " + ",".join("0x%04X" % c for c in extra[k:k + 12]) + ",")
        o.append("};")
    o.append("")
    o.append("static const xbf_font %s = {" % cname)
    o.append('    "%s", %d, %d, %d, 0x%02X, %d, %s_bits, %s, %d, %s' % (
        a.name.replace("_", " "), width, height, ascent, FIRST, LAST - FIRST + 1,
        cname, (cname + "_missing") if missing else "0",
        len(extra), (cname + "_extra") if extra else "0"))
    o.append("};")
    o.append("")
    o.append("#endif")
    with open(a.output, "w") as f:
        f.write("\n".join(o) + "\n")
    print("%s: %dx%d ascent %d, %d + %d extra glyphs%s" % (
        a.output, width, height, ascent, LAST - FIRST + 1 - len(missing), len(extra),
        (", missing " + " ".join("0x%02X" % c for c in real_missing)) if real_missing else ""))


if __name__ == "__main__":
    main()
