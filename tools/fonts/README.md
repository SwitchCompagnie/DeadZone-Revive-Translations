# Game fonts: adding the accented letters

The game draws body text in **HelveticaNeueCond** (regular and bold) and titles in
**AlternateGothic** (see `<styles>` at the top of `en.xml`). The only copy of these
fonts the game ships is `lang/fonts/en.swf`, and it embeds **ASCII only**. Every
accented letter the translations use (é, ü, ñ, ç, ğ, ş, ı, İ, Œ, «», curly quotes, ...)
is missing from it.

The Flash client loads `lang/fonts/<lang>.swf` for the selected language
(`Language.setLanguage`). None of the community languages has one, so those letters
are either not drawn or drawn in a different font.

`extend_glyphs.py` adds every missing character to the fonts, built from the
fonts' own glyphs so they match the original style. The accented letters combine the
base letter with a mark made from the font's period, comma and stroke weight. ß is
drawn as "ss", German's standard spelling when ß isn't available.

## Usage

You need Python 3 and fontTools (`pip install fonttools`), plus the fonts as TTF files
exported from `en.swf`.

```bash
python3 tools/fonts/extend_glyphs.py HelveticaNeueCond.ttf HelveticaNeueCond-Bold.ttf AlternateGothic.ttf --out build/fonts
```

The script reads the characters it needs from `en.xml` and every
`translations_<lang>.json`, and reports anything that is still missing.
`--check` runs that report alone and changes nothing. Run it again whenever a new
language adds new characters.

To use the result in the Flash client, embed the extended faces into a font SWF under
the same names (HelveticaNeueCond, HelveticaNeueCond bold, AlternateGothic) and serve
it as `lang/fonts/<lang>.swf` for each language.

**The fonts are Con Artist Games' commercial typefaces. Never commit the TTFs or the
SWF to this repository.** `build/` is git-ignored.
