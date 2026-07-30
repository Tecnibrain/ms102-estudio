# -*- coding: utf-8 -*-
"""Fusiona data/explicaciones.json en preguntas.json y regenera preguntas.js."""
import json

P = 'data/preguntas.json'
q = json.load(open(P, encoding='utf-8'))
try:
    expl = json.load(open('data/explicaciones.json', encoding='utf-8'))
except FileNotFoundError:
    expl = {}

n = 0
for e in q:
    t = expl.get(str(e['id']))
    if t:
        e['explicacion'] = t; n += 1
    elif 'explicacion' in e and not expl.get(str(e['id'])):
        pass  # conservar existente si ya lo tenía

json.dump(q, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
open('data/preguntas.js', 'w', encoding='utf-8').write(
    'window.MS102_DATA=' + json.dumps(q, ensure_ascii=False) + ';')
print(f'explicaciones aplicadas: {n} / {len(q)} preguntas')
