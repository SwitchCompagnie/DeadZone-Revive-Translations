# Contributing translations

Thanks for helping translate Dead Zone Revive.
This guide explains how to make
a change that will be accepted quickly.

## Workflow

1. **Fork** this repository and clone your fork.
2. Create a branch, e.g. `fr-fix-alliance-help`.
3. Edit the `translations_<lang>.json` file for your language.
4. **Validate** before committing:
   ```bash
   python3 tools/validate_translation.py translations_<lang>.json
   ```
   It must report `0 errors`. Length warnings are acceptable but try to reduce
   them (see below).
5. Commit and open a **pull request** describing what you changed.

Continuous integration runs the validator on every pull request. A PR with
placeholder or tag errors will fail the check.

## Rules

Each entry maps an **English string** (the key) to your translation (the value).
Only edit the value. Never edit the key, and never edit `en.xml`.

### Keep placeholders

Placeholders such as `%s`, `%d`, `%u`, `%1`, `%2` are replaced at runtime with
live values (a name, a number, a level...). Your translation must contain the
**same placeholders, the same number of times**. You may move them to fit the
grammar of your language.

- English: `Level %s`
- Good: `Niveau %s`
- Bad: `Niveau` (placeholder dropped — the number disappears in-game)

### Keep the tags

Text may contain HTML-like tags: `<br/>`, `<b>`, `</b>`, `<u>`, `<font color="#79CF1F">`.
Keep the **same tags**, unchanged (including the exact colour codes). You may
reorder them to match your sentence, but do not add, remove or rewrite them.

- English: `<b>Get more</b>`
- Good: `<b>Obtenir plus</b>`
- Bad: `Obtenir plus` (bold lost) or `<b>Obtenir plus` (unclosed tag)

### Keep it short

The interface has fixed-size boxes. A translation much longer than the English
may overflow or get cut off. Aim for a length close to the original. Short
labels and buttons (`OK`, `Cancel`, `Level %s`) are the most sensitive — keep
those tight. Long help paragraphs have more room.

The validator warns when a value is noticeably longer than its English source.
Warnings will not block your PR, but fewer is better.

### Match the tone

- Preserve UPPERCASE where the English is uppercase (button labels, warnings).
- Keep the same punctuation intent. Leading/trailing spaces in the English are
  usually there for layout — keep them.
- Use natural, in-game wording, not a literal word-for-word translation.

## Questions

Open an issue if a string is unclear, if you found an English typo, or if you
want to propose a new language.
