# Dead Zone Revive - Translations

Community translations for **The Last Stand: Dead Zone** (Dead Zone Revive).
Help translate the game or fix existing translations by opening a pull request.

The game runs in English. The server can serve a different language file in
place of the English one, so translating the game is simply a matter of
providing a good translation for every English string.

> **Status: in testing.** Translations are a mix of community and machine work
> and are still being reviewed. Some strings may be wrong or overflow their box
> in the interface. Reporting and fixing those is exactly what this repo is for.

## Languages

| Code | Language   | File                     |
|------|------------|--------------------------|
| `en` | English    | `en.xml` (source, do not edit) |
| `fr` | Français   | `translations_fr.json`   |
| `es` | Español    | `translations_es.json`   |
| `de` | Deutsch    | `translations_de.json`   |
| `it` | Italiano   | `translations_it.json`   |
| `pt` | Português  | `translations_pt.json`   |

Only Latin-script languages are supported for now (the in-game font covers
Latin characters and their accents). Languages that need another script, such
as Cyrillic or CJK, need a matching font first and are not accepted yet.

## How it works

- `en.xml` is the English master. Every translatable string lives inside a
  `<![CDATA[ ... ]]>` block.
- `translations_<lang>.json` maps each **English string** to its translation:

  ```json
  {
    "Level %s": "Niveau %s",
    "Get more": "Obtenir plus"
  }
  ```

- The build tool copies `en.xml` and replaces each English string with its
  translation, producing `<lang>.xml.gz`, which the game server serves in place
  of the English file.
- An empty value (`""`) means "not translated yet" and stays English in-game.

## Repository layout

```
en.xml                     English source (reference only, do not edit)
languages.xml              List of languages offered in-game
translations_<lang>.json   The editable translation dictionaries
tools/build_translation.py Build a <lang>.xml.gz from a dictionary
tools/validate_translation.py  Check placeholders, tags and length
tools/new_language.py      Create an empty dictionary for a new language
```

Built `*.xml` / `*.xml.gz` files are generated and are not committed.

## Edit a translation

1. Open the `translations_<lang>.json` file for your language.
2. Find the English string (the key) and edit its value.
3. Keep these intact — see [CONTRIBUTING.md](CONTRIBUTING.md) for details:
   - **Placeholders** like `%s`, `%d`, `%u` — same ones, same count.
   - **HTML tags** like `<br/>`, `<b>`, `<font color="#...">` — same tags.
   - **Length** — keep it close to the English so it fits on screen.

Then validate:

```bash
python3 tools/validate_translation.py translations_<lang>.json
```

Optionally build the file to preview it:

```bash
python3 tools/build_translation.py <lang> translations_<lang>.json
# produces <lang>.xml.gz
```

## Start a new language

```bash
python3 tools/new_language.py <lang>      # e.g. pl, tr
# creates translations_<lang>.json with every English string, empty
```

Translate the entries, then open a pull request. A maintainer adds the language
to `languages.xml` and to the website language selector.

## For maintainers

Merged `translations_<lang>.json` files are copied into the game data
(`deadnet game/data/lang/`), rebuilt with `build_translation.py`, and deployed.
The website language selector and the server language route pick them up.
