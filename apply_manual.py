# -*- coding: utf-8 -*-
"""Expande data/manual_drag.json (transcrito a mano) al formato de interactivas.json.

Formato de entrada:
  "seq":  [i, j, k]           -> secuencia ordenada: Paso 1 = opción i, ...
  "pairs":[["etiqueta", i]]   -> emparejar etiqueta con opción i
"""
import json

MAN = json.load(open('data/manual_drag.json', encoding='utf-8'))
P = 'data/interactivas.json'
inter = json.load(open(P, encoding='utf-8'))

n = 0
for qid, m in MAN.items():
    opts = m['options']
    blanks = []
    if 'seq' in m:
        for i, idx in enumerate(m['seq'], 1):
            blanks.append({'label': f'Paso {i}', 'options': opts, 'correct': idx})
    else:
        for label, idx in m['pairs']:
            blanks.append({'label': label, 'options': opts, 'correct': idx})
    assert all(0 <= b['correct'] < len(opts) for b in blanks), qid
    inter[qid] = {'kind': 'select', 'context_images': m.get('context_images', []),
                  'blanks': blanks, 'pool': m.get('pool', ''), 'manual': True}
    n += 1

json.dump(inter, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'transcripciones aplicadas: {n} | total interactivas: {len(inter)}')
