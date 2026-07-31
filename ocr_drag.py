# -*- coding: utf-8 -*-
"""
Convierte preguntas de ARRASTRAR Y SOLTAR a interactivas (menús desplegables).
Estructura típica: columna izquierda = opciones disponibles;
"Answer Area" a la derecha = filas "Etiqueta: [valor asignado]".
"""
import json, os, sys, re
from difflib import SequenceMatcher
import numpy as np
from PIL import Image
from rapidocr_onnxruntime import RapidOCR

DIR = 'data/img'
OCR = RapidOCR()
_C = {}


def ocr_lines(path):
    if path in _C:
        return _C[path]
    src = Image.open(path).convert('RGB')
    big = Image.new('RGB', (src.width + 24, src.height + 24), 'white')
    big.paste(src, (12, 12))
    big = big.resize((int(big.width * 1.6), int(big.height * 1.6)), Image.LANCZOS)
    res, _ = OCR(np.array(big))
    out = []
    for box, txt, conf in (res or []):
        t = txt.strip()
        if not t:
            continue
        xs = [p[0] for p in box]; ys = [p[1] for p in box]
        f = lambda v: v / 1.6 - 12
        out.append(dict(t=t, x=f(sum(xs)/4), y=f(sum(ys)/4), x0=f(min(xs)),
                        x1=f(max(xs)), y0=f(min(ys)), y1=f(max(ys)), conf=conf))
    _C[path] = out
    return out


def clean(t):
    t = re.sub(r'\s+', ' ', t).strip()
    t = re.sub(r'([a-záéíóúñ])([A-ZÁÉÍÓÚÑ])', r'\1 \2', t)
    return t.strip(' :·')


def norm(t):
    return re.sub(r'[^a-z0-9]', '', t.lower())


def convert(qid, imgs):
    for im in imgs:
        p = os.path.join(DIR, im)
        if not os.path.exists(p):
            continue
        lines = ocr_lines(p)
        aa = [l for l in lines if 'answer area' in l['t'].lower()]
        if not aa:
            continue
        aa = aa[0]
        body = [l for l in lines if 'answer area' not in l['t'].lower()]
        if len(body) < 4:
            continue
        # columna izquierda = lista de opciones disponibles
        minx = min(l['x0'] for l in body)
        col = sorted([l for l in body if l['x0'] <= minx + 110
                      and l['x1'] < aa['x0'] - 20], key=lambda l: l['y'])
        if len(col) < 3 or col[0]['x0'] > aa['x0'] - 40:
            continue                                   # sin lista de opciones a la izquierda
        header = col[0]
        # fusionar opciones partidas en dos renglones ("Modify a Windows 11" +
        # "operating system setting.")
        merged, i2 = [], 1
        while i2 < len(col):
            t = clean(col[i2]['t'])
            j2 = i2 + 1
            while (j2 < len(col) and not re.search(r'[.)\]]$', t)
                   and (col[j2]['y0'] - col[j2 - 1]['y1']) < 14
                   and len(t) < 60):
                t = (t + ' ' + clean(col[j2]['t'])).strip(); j2 += 1
            merged.append(t); i2 = j2
        opts, seen_o = [], set()
        for t in merged:
            if len(t) > 1 and norm(t) not in seen_o:
                seen_o.add(norm(t)); opts.append(t)
        if len(opts) < 2:
            continue
        split = max(l['x1'] for l in col) + 8

        # valores asignados: cualquier texto a la derecha que coincida con una opción
        def match(v):
            """Coincidencia difusa: tolera erratas de OCR pero rechaza fragmentos."""
            nv = norm(v)
            if not nv or len(nv) < 8:
                return None
            for j, o in enumerate(opts):
                if norm(o) == nv:
                    return j
            best, bj = 0.0, None
            for j, o in enumerate(opts):
                no = norm(o)
                if not no:
                    continue
                r = SequenceMatcher(None, nv, no).ratio()
                if r > best:
                    best, bj = r, j
            return bj if best >= 0.82 else None

        # agrupar el área de respuesta en FILAS (una caja puede ocupar 2 renglones)
        right = sorted([l for l in body if l['x0'] >= split and l['y'] > aa['y0'] - 5],
                       key=lambda l: l['y'])
        rows, cur = [], []
        for l in right:
            if cur and (l['y0'] - max(c['y1'] for c in cur)) > 12:
                rows.append(cur); cur = []
            cur.append(l)
        if cur:
            rows.append(cur)

        blanks, unmatched = [], 0
        for n, row in enumerate(rows, 1):
            row = sorted(row, key=lambda m: (m['x0']))
            # buscar el sufijo de la fila que corresponde a una opción
            best = None
            for k in range(len(row) - 1, -1, -1):   # sufijo más corto primero
                j = match(clean(' '.join(m['t'] for m in row[k:])))
                if j is not None:
                    best = (k, j); break
            if not best:
                unmatched += 1     # fila del área de respuesta no reconocida
                continue
            k, j = best
            label = clean(' '.join(m['t'] for m in row[:k]))[:120]
            label = re.sub(r'^\d+\s*', '', label) or f'Paso {n}'
            blanks.append({'label': label, 'options': opts, 'correct': j})
        if unmatched:
            return None, f'respuesta incompleta ({unmatched} filas sin leer)'
        if len(blanks) >= 2:
            ctx = [o for o in imgs if o != im]
            return {'kind': 'select', 'context_images': ctx, 'blanks': blanks,
                    'pool': clean(header['t'])}, 'ok'
    return None, 'no convertible'


def run_all():
    data = json.load(open('data/preguntas.json', encoding='utf-8'))
    inter = json.load(open('data/interactivas.json', encoding='utf-8'))
    ok = 0
    for e in data:
        if e['type'] != 'drag' or str(e['id']) in inter:
            continue
        res, st = convert(e['id'], e.get('answer_images', []))
        if res:
            inter[str(e['id'])] = res; ok += 1
            print(f'  #{e["id"]}: {len(res["blanks"])} huecos, {len(res["blanks"][0]["options"])} opciones')
    json.dump(inter, open('data/interactivas.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'nuevas drag: {ok} | total interactivas: {len(inter)}')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'all':
        run_all()
    else:
        q = {x['id']: x for x in json.load(open('data/preguntas.json', encoding='utf-8'))}
        for i in [int(a) for a in sys.argv[1:]] or [7, 3]:
            res, st = convert(i, q[i].get('answer_images', []))
            print(f'=== #{i}: {st}')
            if res:
                for bl in res['blanks']:
                    print(f'  [{bl["label"]}] -> {bl["options"][bl["correct"]]}')
                    for j, o in enumerate(bl['options']):
                        print(f'      {"✔" if j == bl["correct"] else " "} {o}')
                    break
