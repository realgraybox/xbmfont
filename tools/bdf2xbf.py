#!/usr/bin/env python3
"""bdf2xbf.py - convert a monospaced BDF bitmap font into an xbmfont C header.

Usage:
    python3 bdf2xbf.py FONT.bdf NAME OUTPUT.h [--license FILE]

NAME becomes the C identifier, e.g. "fixed_6x13" -> xbf_fixed_6x13.
Only code points 0x20-0xFF (ASCII + Latin-1) are taken; glyphs the font lacks
are marked missing and drawn as '?' by the library.

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


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("bdf")
    ap.add_argument("name", help="C name without the xbf_ prefix, e.g. fixed_6x13")
    ap.add_argument("output")
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

    widths = {g["dwidth"] for c, g in glyphs.items() if FIRST <= c <= LAST and "dwidth" in g}
    if len(widths) != 1:
        sys.exit("not a monospaced font in 0x20-0xFF (advances: %s)" % sorted(widths))
    width = widths.pop()
    row_bytes = (width + 7) // 8

    out_rows = []      # per glyph: list of row byte-lists
    missing = []
    for c in range(FIRST, LAST + 1):
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
    o.append(" */")
    o.append("#ifndef %s" % guard)
    o.append("#define %s" % guard)
    o.append("")
    o.append('#include "xbmfont.h"')
    o.append("")
    o.append("static const unsigned char %s_bits[%d] = {" % (cname, (LAST - FIRST + 1) * height * row_bytes))
    for idx, rows in enumerate(out_rows):
        c = FIRST + idx
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
    o.append("")
    o.append("static const xbf_font %s = {" % cname)
    o.append('    "%s", %d, %d, %d, 0x%02X, %d, %s_bits, %s' % (
        a.name.replace("_", " "), width, height, ascent, FIRST, LAST - FIRST + 1,
        cname, (cname + "_missing") if missing else "0"))
    o.append("};")
    o.append("")
    o.append("#endif")
    with open(a.output, "w") as f:
        f.write("\n".join(o) + "\n")
    print("%s: %dx%d ascent %d, %d glyphs%s" % (
        a.output, width, height, ascent, LAST - FIRST + 1 - len(missing),
        (", missing " + " ".join("0x%02X" % c for c in real_missing)) if real_missing else ""))


if __name__ == "__main__":
    main()
