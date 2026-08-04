# -*- coding: utf-8 -*-
"""Control de calidad de data/interactivas.json: descarta entradas con OCR roto."""
import json, re, sys

P = 'data/interactivas.json'
d = json.load(open(P, encoding='utf-8'))
MANUAL = {'12', '1', '8', '9', '15', '17', '22', '54', '84'}   # ya verificadas a mano


def bad_option(o):
    if len(o) < 1 or len(o) > 70:
        return True
    # palabra pegada larguísima (OCR fusionó todo)
    if re.search(r'[A-Za-z]{22,}', o.replace(' ', '')) and ' ' not in o:
        return True
    if re.search(r'\w{18,}', o):
        return True
    # ruido típico de rutas/comandos mal leídos
    if o.count('/') >= 3 or o.count('\\') >= 3:
        return True
    # demasiados caracteres raros
    weird = sum(1 for c in o if not (c.isalnum() or c in " .,:-()%'/\\+&*_#"))
    if weird > 2:
        return True
    return False


def score(entry):
    """Devuelve (ok, motivo)."""
    if entry['kind'] in ('yesno', 'multi'):
        return True, ''
    blanks = entry.get('blanks') or []
    if not blanks:
        return False, 'sin listas'
    for bl in blanks:
        opts = bl['options']
        if len(opts) < 2 or len(opts) > 8:
            return False, 'nº opciones raro'
        if any(bad_option(o) for o in opts):
            return False, 'opcion ilegible'
        if len(set(o.lower() for o in opts)) < len(opts):
            return False, 'opciones duplicadas'
        if not (0 <= bl['correct'] < len(opts)):
            return False, 'indice invalido'
        # opciones que en realidad son campos de formulario (captura, no lista)
        if sum(1 for o in opts if o.endswith('*') or o.endswith(':')) >= 2:
            return False, 'parece formulario'
    return True, ''


keep, drop = {}, []
for k, v in d.items():
    if k in MANUAL or v.get('manual'):     # verificadas a mano: no filtrar
        keep[k] = v; continue
    ok, why = score(v)
    if ok:
        keep[k] = v
    else:
        drop.append((k, why))

if '--apply' in sys.argv:
    json.dump(keep, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'aplicado: quedan {len(keep)}, descartadas {len(drop)}')
else:
    print(f'quedarían {len(keep)}, se descartarían {len(drop)}')
from collections import Counter
print('motivos:', dict(Counter(w for _, w in drop)))
print('descartadas:', [k for k, _ in drop])
