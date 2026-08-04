# -*- coding: utf-8 -*-
"""Fusiona data/explicaciones.json en preguntas.json y regenera preguntas.js."""
import json

P = 'data/preguntas.json'
q = json.load(open(P, encoding='utf-8'))
def load(path):
    try:
        return json.load(open(path, encoding='utf-8'))
    except FileNotFoundError:
        return {}

expl = load('data/explicaciones.json')
inter = load('data/interactivas.json')

n = m = 0
for e in q:
    t = expl.get(str(e['id']))
    if t:
        e['explicacion'] = t; n += 1
    it = inter.get(str(e['id']))
    if it:
        e['inter'] = it; m += 1
    else:
        e.pop('inter', None)      # retirada del archivo -> quitarla del banco

json.dump(q, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
open('data/preguntas.js', 'w', encoding='utf-8').write(
    'window.MS102_DATA=' + json.dumps(q, ensure_ascii=False) + ';')
print(f'explicaciones: {n} | interactivas: {m} / {len(q)} preguntas')
