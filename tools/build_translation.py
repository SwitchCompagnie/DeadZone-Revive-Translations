#!/usr/bin/env python3
import gzip
import json
import re
import sys

CDATA = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.S)


def main():
    if len(sys.argv) != 3:
        print("usage: build_translation.py <lang_id> <translations.json>")
        sys.exit(2)
    lang_id, trans_path = sys.argv[1], sys.argv[2]

    with open("en.xml", encoding="utf-8") as f:
        en = f.read()
    with open(trans_path, encoding="utf-8") as f:
        trans = json.load(f)

    applied = 0
    too_long = []
    seen = set()

    def repl(m):
        nonlocal applied
        val = m.group(1)
        fr = trans.get(val)
        if fr is None or fr == "":
            return m.group(0)
        seen.add(val)
        if len(fr) > len(val):
            too_long.append((val, fr, len(val), len(fr)))
        applied += 1
        return "<![CDATA[" + fr + "]]>"

    out = CDATA.sub(repl, en)

    with open(f"{lang_id}.xml", "w", encoding="utf-8") as f:
        f.write(out)
    with open(f"{lang_id}.xml", "rb") as src, gzip.open(f"{lang_id}.xml.gz", "wb") as dst:
        dst.write(src.read())

    total_nodes = len(CDATA.findall(en))
    print(f"[{lang_id}] {applied} nodes translated / {total_nodes} total")
    unused = [k for k in trans if k not in seen]
    if unused:
        print(f"  {len(unused)} dict entries matched nothing (exact-text mismatch)")
        for k in unused[:8]:
            print(f"    - {k!r}")
    if too_long:
        over = sorted(too_long, key=lambda t: t[3] - t[2], reverse=True)
        print(f"  {len(too_long)} translations longer than original (worst overruns):")
        for en_v, fr_v, le, lf in over[:15]:
            print(f"    +{lf - le}: {en_v!r} ({le}) -> {fr_v!r} ({lf})")


if __name__ == "__main__":
    main()
