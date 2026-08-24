#!/usr/bin/env python3
import json
import re
import sys

CDATA = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.S)


def main():
    if len(sys.argv) != 2:
        print("usage: new_language.py <lang_id>")
        sys.exit(2)
    lang = sys.argv[1]

    with open("en.xml", encoding="utf-8") as f:
        keys = []
        seen = set()
        for value in CDATA.findall(f.read()):
            if value not in seen:
                seen.add(value)
                keys.append(value)

    path = f"translations_{lang}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({k: "" for k in keys}, f, ensure_ascii=False, indent=1)

    print(f"wrote {path} with {len(keys)} entries to translate (empty = stays English)")


if __name__ == "__main__":
    main()
