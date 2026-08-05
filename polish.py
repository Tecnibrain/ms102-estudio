# -*- coding: utf-8 -*-
"""Pulido final de textos: versiones (22H 2) y extensiones (the. ods)."""
import json, re

VER = re.compile(r'(\d+H)\s(\d)\b')
EXT = re.compile(r'([a-záéíóúñ])\.\s([a-z]{2,5})\b')
DOT = re.compile(r'\s+\.\s+([a-z]{2,5})\b')


def polish(t):
    t = VER.sub(lambda m: m.group(1) + m.group(2), t)
    t = EXT.sub(lambda m: m.group(1) + ' .' + m.group(2), t)
    t = DOT.sub(lambda m: ' .' + m.group(1), t)
    return re.sub(r'\s+', ' ', t).strip()


P = 'data/interactivas.json'
d = json.load(open(P, encoding='utf-8'))
n = 0
for v in d.values():
    for bl in v.get('blanks', []):
        for i, o in enumerate(bl['options']):
            r = polish(o)
            if r != o:
                bl['options'][i] = r; n += 1
        if bl.get('label'):
            bl['label'] = polish(bl['label'])
    for s in v.get('statements', []):
        r = polish(s['t'])
        if r != s['t']:
            s['t'] = r; n += 1
    for i, o in enumerate(v.get('options', [])):
        r = polish(o)
        if r != o:
            v['options'][i] = r; n += 1
json.dump(d, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'pulidos: {n}')
