#!/usr/bin/env python3
"""Add the accented letters and punctuation the translations need to the game's fonts.

The fonts the game embeds (HelveticaNeueCond, its bold, AlternateGothic) only
contain ASCII, so every accented letter (é, ü, ç, ğ, ş, ı, ...) is missing. This
tool builds the missing characters from glyphs the font already has, in its own
style:

- Diacritics are made from the font's own shapes or drawn to match its stroke:
  the period becomes the dot and the dieresis, the comma becomes the cedilla, and
  the acute, grave, circumflex, caron, breve, ring and tilde are drawn at the
  font's stroke weight.
- Accented letters are composites: the base letter plus a mark.
- Others are derived: ı (the i without its dot), ¡ and ¿ (rotated), « »
  (scaled < >), – — (stretched hyphen), curly quotes (raised commas), ª º
  (small a/o with a bar), Œ œ (O and E joined) and ß, which is drawn as "ss"
  (German's own fallback spelling) because no glyph in these fonts makes a
  convincing sharp s.

The fonts are Con Artist Games' commercial typefaces: share the results
privately and never commit them to this repository.

usage:
  extend_glyphs.py <font.ttf> [<font.ttf> ...] --out <dir>
  extend_glyphs.py <font.ttf> ... --check          # report what the translations still miss

Requires fontTools (pip install fonttools).
"""
import argparse
import glob
import io
import json
import math
import os
import re
import sys

from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# letter -> (base, mark, position); position "above" or "below"
COMPOSITES = {}
for base, marks in {
    "A": "grave acute circumflex tilde dieresis ring",
    "E": "grave acute circumflex dieresis",
    "I": "grave acute circumflex dieresis dotaccent",
    "O": "grave acute circumflex tilde dieresis",
    "U": "grave acute circumflex dieresis",
    "N": "tilde", "Y": "acute dieresis",
    "C": "cedilla", "S": "cedilla caron", "Z": "caron",
    "G": "breve",
}.items():
    for mark in marks.split():
        for case in (base, base.lower()):
            src = case if case != "i" else "dotlessi"
            if case == "i" and mark == "dotaccent":
                continue  # i already has its dot
            COMPOSITES[(case, mark)] = src

ACCENT_CHARS = {
    "grave": "̀", "acute": "́", "circumflex": "̂", "tilde": "̃",
    "dieresis": "̈", "ring": "̊", "cedilla": "̧", "breve": "̆",
    "dotaccent": "̇", "caron": "̌",
}
BELOW = {"cedilla"}


def char_for(base, mark):
    import unicodedata
    composed = unicodedata.normalize("NFC", base + ACCENT_CHARS[mark])
    return composed if len(composed) == 1 else None


class Builder:
    def __init__(self, font):
        self.font = font
        self.glyf = font["glyf"]
        self.hmtx = font["hmtx"]
        self.cmap = font.getBestCmap()
        self.gs = font.getGlyphSet()
        self.added = []
        m = self.metrics = {}
        m["x"] = self.bbox(self.g("x"))[3]
        m["cap"] = self.bbox(self.g("H"))[3]
        x0, y0, x1, y1 = self.bbox(self.g("."))
        m["dot_w"], m["dot_h"] = x1 - x0, y1 - y0
        lx0, _, lx1, _ = self.bbox(self.g("l"))
        m["stem"] = lx1 - lx0
        hy0, hy1 = self.bbox(self.g("-"))[1::2]
        m["bar"] = hy1 - hy0
        m["gap"] = m["dot_h"] * 0.45

    # ---- helpers
    def g(self, ch):
        return self.cmap[ord(ch)]

    def has(self, ch):
        return ord(ch) in self.cmap

    def bbox(self, gname):
        glyph = self.glyf[gname]
        glyph.recalcBounds(self.glyf)
        if not hasattr(glyph, "xMin"):
            return 0, 0, 0, 0
        return glyph.xMin, glyph.yMin, glyph.xMax, glyph.yMax

    def adv(self, gname):
        return self.hmtx[gname][0]

    def put(self, gname, glyph, advance, ch=None):
        self.glyf[gname] = glyph
        glyph.recalcBounds(self.glyf)
        self.hmtx[gname] = (int(round(advance)), getattr(glyph, "xMin", 0))
        order = self.font.getGlyphOrder()
        if gname not in order:
            order.append(gname)
            self.font.setGlyphOrder(order)
        if ch:
            for table in self.font["cmap"].tables:
                if table.isUnicode():
                    table.cmap[ord(ch)] = gname
            self.cmap[ord(ch)] = gname
            self.added.append(ch)

    def contours(self, gname):
        rec = DecomposingRecordingPen(self.gs)
        self.gs[gname].draw(rec)
        out, cur = [], []
        for op, args in rec.value:
            cur.append((op, args))
            if op in ("closePath", "endPath"):
                out.append(cur)
                cur = []
        return out

    def draw(self, pen, contours, t=(1, 0, 0, 1, 0, 0)):
        tp = TransformPen(pen, t)
        for c in contours:
            for op, args in c:
                getattr(tp, op)(*args)

    def shape(self, parts):
        """parts: list of (glyph name, transform, contour filter or None) -> new simple glyph."""
        pen = TTGlyphPen(None)
        for gname, t, keep in parts:
            cs = self.contours(gname)
            if keep:
                cs = [c for c in cs if keep(c)]
            self.draw(pen, cs, t)
        return pen.glyph()

    @staticmethod
    def polygon(pen, pts):
        # TrueType outer contours run clockwise (negative shoelace area in y-up space)
        area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
        if area > 0:
            pts = pts[::-1]
        pen.moveTo(pts[0])
        for p in pts[1:]:
            pen.lineTo(p)
        pen.closePath()

    @staticmethod
    def stroke(a, b, w):
        """A quad of width w (measured horizontally) from point a to point b."""
        return [(a[0] - w / 2, a[1]), (a[0] + w / 2, a[1]), (b[0] + w / 2, b[1]), (b[0] - w / 2, b[1])]

    # ---- marks, drawn with their bottom on y=0 (top on y=0 for marks below), centred on x=0
    def build_marks(self):
        m = self.metrics
        dw, dh, stem = m["dot_w"], m["dot_h"], m["stem"]
        px0, py0, _, _ = self.bbox(self.g("."))
        h = dh * 1.15          # accent height
        w = stem * 0.85        # stroke width of slanted accents

        def mark(name, build):
            pen = TTGlyphPen(None)
            build(pen)
            self.put("mark." + name, pen.glyph(), 0)

        mark("dotaccent", lambda p: self.draw(p, self.contours(self.g(".")), (1, 0, 0, 1, -(px0 + dw / 2), -py0)))

        def dieresis(p):
            sep = dw * 0.75
            for dx in (-(sep / 2 + dw), sep / 2):
                self.draw(p, self.contours(self.g(".")), (1, 0, 0, 1, dx - px0, -py0))
        mark("dieresis", dieresis)

        mark("acute", lambda p: self.polygon(p, self.stroke((-dw * 0.45, 0), (dw * 0.45, h), w)))
        mark("grave", lambda p: self.polygon(p, self.stroke((dw * 0.45, 0), (-dw * 0.45, h), w)))

        def chevron(p, flip):
            span, top = dw * 0.95, h * 0.9
            thick = m["bar"] * 0.95
            if not flip:  # ^
                outer = [(-span, 0), (0, top), (span, 0)]
            else:         # v
                outer = [(-span, top), (0, 0), (span, top)]
            # two strokes meeting at the middle point
            for a, b in ((outer[0], outer[1]), (outer[1], outer[2])):
                dx, dy = b[0] - a[0], b[1] - a[1]
                ln = math.hypot(dx, dy)
                nx, ny = -dy / ln * thick / 2, dx / ln * thick / 2
                self.polygon(p, [(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny), (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)])
        mark("circumflex", lambda p: chevron(p, False))
        mark("caron", lambda p: chevron(p, True))

        def arc(p, r_out, thick, cy, start, end, steps=20):
            r_in = r_out - thick
            outer = [(r_out * math.cos(start + (end - start) * k / steps), cy + r_out * math.sin(start + (end - start) * k / steps)) for k in range(steps + 1)]
            inner = [(r_in * math.cos(end - (end - start) * k / steps), cy + r_in * math.sin(end - (end - start) * k / steps)) for k in range(steps + 1)]
            self.polygon(p, outer + inner)

        rb = dw * 1.2
        mark("breve", lambda p: arc(p, rb, m["bar"] * 0.85, rb, math.pi, 2 * math.pi))

        def ring(p):
            r, t = dh * 0.62, m["bar"] * 0.7
            steps = 28
            outer = [(r * math.cos(2 * math.pi * k / steps), r + r * math.sin(2 * math.pi * k / steps)) for k in range(steps)]
            inner = [((r - t) * math.cos(2 * math.pi * k / steps), r + (r - t) * math.sin(2 * math.pi * k / steps)) for k in range(steps)]
            self.polygon(p, outer)  # clockwise
            # the hole runs counter-clockwise (increasing angle)
            p.moveTo(inner[0])
            for q in inner[1:]:
                p.lineTo(q)
            p.closePath()
        mark("ring", ring)

        def tilde(p):
            span, amp, t = dw * 1.15, dh * 0.28, m["bar"] * 0.8
            steps = 24
            # one sine period: up, down, up again; the stroke is the curve and a copy t lower
            top = [(-span + 2 * span * k / steps, t + amp + amp * math.sin(2 * math.pi * k / steps)) for k in range(steps + 1)]
            bottom = [(x, y - t) for x, y in reversed(top)]
            self.polygon(p, top + bottom)
        mark("tilde", tilde)

        cx0, cy0, cx1, cy1 = self.bbox(self.g(","))
        s = 0.8
        mark("cedilla", lambda p: self.draw(p, self.contours(self.g(",")), (s, 0, 0, s, -(cx0 + cx1) / 2 * s, -cy1 * s + dh * 0.15)))

    # ---- letters
    def dotless_i(self):
        top = self.metrics["x"] * 0.9

        def not_dot(c):
            ys = [pt[1] for _, args in c for pt in args if isinstance(pt, tuple)]
            return not ys or min(ys) < top
        self.put("dotlessi", self.shape([(self.g("i"), (1, 0, 0, 1, 0, 0), not_dot)]), self.adv(self.g("i")), "ı")

    def composite(self, ch, base_name, mark):
        m = self.metrics
        bx0, by0, bx1, by1 = self.bbox(base_name)
        cx = (bx0 + bx1) / 2
        sx, sy = 1.0, 1.0
        if mark in BELOW:
            y = 0
        else:
            upper = ch.upper() == ch and ch.lower() != ch
            ref = m["cap"] if upper else m["x"]
            y = max(ref, by1 if not upper else ref) + m["gap"] * (0.8 if upper else 1)
            if upper:
                sy = 0.82  # flatter accents on capitals keep them inside the line
        pen = TTGlyphPen(self.gs)
        pen.addComponent(base_name, (1, 0, 0, 1, 0, 0))
        pen.addComponent("mark." + mark, (sx, 0, 0, sy, round(cx), round(y)))
        self.put("uni%04X" % ord(ch), pen.glyph(), self.adv(base_name), ch)

    def letters(self):
        for (case, mark), src in sorted(COMPOSITES.items()):
            ch = char_for(case, mark) if case != "dotlessi" else None
            if not ch or self.has(ch):
                continue
            base = "dotlessi" if src == "dotlessi" else self.g(src)
            self.composite(ch, base, mark)
        # İ is I with a dot (covered above as I + dotaccent)

    # ---- punctuation and specials
    def specials(self):
        m = self.metrics
        cap, x, dh = m["cap"], m["x"], m["dot_h"]

        def rotated(ch, src):
            gname = self.g(src)
            x0, y0, x1, y1 = self.bbox(gname)
            adv = self.adv(gname)
            # rotate 180 degrees around the glyph centre, then hang it so its top is at x-height (Spanish style)
            t = (-1, 0, 0, -1, x0 + x1, y1 + y0)
            g = self.shape([(gname, t, None)])
            g.recalcBounds(self.glyf)
            shift = x - g.yMax
            g = self.shape([(gname, (-1, 0, 0, -1, x0 + x1, y1 + y0 + shift), None)])
            self.put("uni%04X" % ord(ch), g, adv, ch)
        if self.has("!"):
            rotated("¡", "!")
        if self.has("?"):
            rotated("¿", "?")

        # dashes from the hyphen
        hy = self.g("-")
        hx0, _, hx1, _ = self.bbox(hy)
        for ch, width in (("–", self.adv(self.g("n"))), ("—", self.adv(self.g("M")) * 1.2)):
            sx = (width * 0.92) / (hx1 - hx0)
            g = self.shape([(hy, (sx, 0, 0, 1, -hx0 * sx + width * 0.04, 0), None)])
            self.put("uni%04X" % ord(ch), g, width, ch)

        # quotes from the comma
        cm = self.g(",")
        cx0, cy0, cx1, cy1 = self.bbox(cm)
        cw = cx1 - cx0
        comma_adv = self.adv(cm)
        lift = cap - cy1
        lsb = cx0

        def quote(ch, n, rotate, y_off):
            pen = TTGlyphPen(None)
            for k in range(n):
                dx = k * (cw + m["stem"] * 0.35)
                if rotate:
                    t = (-1, 0, 0, -1, cx0 + cx1 + dx, cy0 + cy1 + y_off)
                else:
                    t = (1, 0, 0, 1, dx, y_off)
                self.draw(pen, self.contours(cm), t)
            self.put("uni%04X" % ord(ch), pen.glyph(), comma_adv + (n - 1) * (cw + m["stem"] * 0.35), ch)
        top_y = cap - (cy1 - cy0)
        quote("’", 1, False, lift)
        quote("‘", 1, True, top_y - cy0)
        quote("”", 2, False, lift)
        quote("“", 2, True, top_y - cy0)
        quote("„", 2, False, 0)
        quote("‚", 1, False, 0)

        # guillemets from < >
        for ch, src in (("«", "<"), ("»", ">")):
            if not self.has(src):
                continue
            gname = self.g(src)
            x0, y0, x1, y1 = self.bbox(gname)
            s = 0.62
            w = (x1 - x0) * s
            mid = x * 0.5 - (y0 + y1) / 2 * s
            pen = TTGlyphPen(None)
            for k in range(2):
                self.draw(pen, self.contours(gname), (s, 0, 0, s, -x0 * s + lsb + k * w * 0.8, mid))
            self.put("uni%04X" % ord(ch), pen.glyph(), lsb * 2 + w * 1.8, ch)

        # ordinal indicators ª º: small raised letter with a bar under it
        for ch, src in (("ª", "a"), ("º", "o")):
            gname = self.g(src)
            x0, y0, x1, y1 = self.bbox(gname)
            s = 0.55
            base_y = cap - (y1 - y0) * s
            hy0, hy1 = self.bbox(hy)[1::2]
            pen = TTGlyphPen(None)
            self.draw(pen, self.contours(gname), (s, 0, 0, s, -x0 * s + lsb, base_y))
            bar_y = base_y - m["bar"] * 0.6 - m["bar"] * 0.7
            barsx = ((x1 - x0) * s) / (hx1 - hx0)
            self.draw(pen, self.contours(hy), (barsx, 0, 0, 0.7, -hx0 * barsx + lsb, bar_y - hy0 * 0.7))
            self.put("uni%04X" % ord(ch), pen.glyph(), (x1 - x0) * s + lsb * 2, ch)

        # Œ œ: O (or o) joined to E (or e), sharing the stem/curve
        for ch, a, b, overlap in (("Œ", "O", "E", 0.42), ("œ", "o", "e", 0.38)):
            ga, gb = self.g(a), self.g(b)
            ax0, _, ax1, _ = self.bbox(ga)
            bx0, _, _, _ = self.bbox(gb)
            shift = ax1 - (ax1 - ax0) * overlap - bx0
            pen = TTGlyphPen(self.gs)
            pen.addComponent(ga, (1, 0, 0, 1, 0, 0))
            pen.addComponent(gb, (1, 0, 0, 1, round(shift), 0))
            self.put("uni%04X" % ord(ch), pen.glyph(), shift + self.adv(gb), ch)

        # ß: drawing a convincing sharp s from these fonts' glyphs is not possible, so it is "ss", the spelling German
        # uses wherever ß is unavailable (as with capitals). Replace it if someone draws a real one.
        gs_ = self.g("s")
        pen = TTGlyphPen(self.gs)
        pen.addComponent(gs_, (1, 0, 0, 1, 0, 0))
        pen.addComponent(gs_, (1, 0, 0, 1, self.adv(gs_), 0))
        self.put("germandbls", pen.glyph(), self.adv(gs_) * 2, "ß")

    def run(self):
        self.build_marks()
        self.dotless_i()
        self.letters()
        self.specials()
        self.font["maxp"].recalc(self.font)
        return self.added


def needed_chars():
    cdata = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.S)
    chars = set()
    en = os.path.join(REPO, "en.xml")
    if os.path.exists(en):
        with open(en, encoding="utf-8") as f:
            chars |= set("".join(cdata.findall(f.read())))
    for path in glob.glob(os.path.join(REPO, "translations_*.json")):
        with open(path, encoding="utf-8") as f:
            chars |= set("".join(json.load(f).values()))
    return {c for c in chars if ord(c) > 0x7E}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fonts", nargs="+")
    ap.add_argument("--out", help="directory to write the extended fonts to (same file names)")
    ap.add_argument("--check", action="store_true", help="only report characters the translations use that a font lacks")
    args = ap.parse_args()
    need = needed_chars()
    status = 0
    for path in args.fonts:
        with open(path, "rb") as f:
            font = TTFont(io.BytesIO(f.read()))  # in memory, so --out may be the fonts' own folder
        if not args.check:
            added = Builder(font).run()
            os.makedirs(args.out, exist_ok=True)
            dst = os.path.join(args.out, os.path.basename(path))
            font.save(dst)
            font = TTFont(dst)
            print(f"{os.path.basename(path)}: added {len(added)} characters -> {dst}")
        cmap = font.getBestCmap()
        missing = sorted(c for c in need if ord(c) not in cmap)
        print(f"  missing for the translations: {''.join(missing) if missing else 'none'}")
        status |= bool(missing)
    sys.exit(1 if args.check and status else 0)


if __name__ == "__main__":
    main()
