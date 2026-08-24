#!/usr/bin/env python3
import json
import re
import sys

CDATA = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.S)
PLACEHOLDER = re.compile(r"%[A-Za-z0-9]")
TAG = re.compile(r"<[^>]+>")


def placeholders(s):
    return sorted(PLACEHOLDER.findall(s))


def tags(s):
    return sorted(t.replace(" ", "").lower() for t in TAG.findall(s))


def main():
    if len(sys.argv) != 2:
        print("usage: validate_translation.py <translations_<lang>.json>")
        sys.exit(2)
    path = sys.argv[1]

    with open("en.xml", encoding="utf-8") as f:
        english = set(CDATA.findall(f.read()))
    with open(path, encoding="utf-8") as f:
        trans = json.load(f)

    errors = 0
    warnings = 0
    unknown = 0
    translated = 0

    for src, dst in trans.items():
        if not dst:
            continue
        translated += 1
        if src not in english:
            unknown += 1
            if unknown <= 10:
                print(f"UNKNOWN   key is not present in en.xml: {src!r}")
            continue
        if placeholders(src) != placeholders(dst):
            errors += 1
            print(f"PLACEHOLD {src!r}")
            print(f"          {placeholders(src)} != {placeholders(dst)}")
        if tags(src) != tags(dst):
            errors += 1
            print(f"TAGS      {src!r}")
            print(f"          {tags(src)} != {tags(dst)}")
        if len(dst) > len(src) + 8:
            warnings += 1

    print(f"\n{path}: {translated} translated, {errors} errors, {warnings} length warnings, {unknown} unknown keys")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
