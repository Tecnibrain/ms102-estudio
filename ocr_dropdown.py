# -*- coding: utf-8 -*-
"""
Convierte preguntas hotspot de tipo LISTA DESPLEGABLE a interactivas.
La respuesta correcta viene marcada con un recuadro/elipse negra gruesa
(o resaltado amarillo). Detecta el marcador, agrupa las opciones de cada
lista y extrae la etiqueta de la izquierda.
"""
import json, os, sys, re
import numpy as np
from PIL import Image
from scipy import ndimage
from rapidocr_onnxruntime import RapidOCR

DIR = 'data/img'
OCR = RapidOCR()


_CACHE = {}


def ocr_lines(path):
    if path in _CACHE:
        return _CACHE[path]
    # margen blanco + escalado: evita que el borde del cuadro se coma la 1ª letra
    src = Image.open(path).convert('RGB')
    big = Image.new('RGB', (src.width + 24, src.height + 24), 'white')
    big.paste(src, (12, 12))
    big = big.resize((int(big.width * 1.6), int(big.height * 1.6)), Image.LANCZOS)
    arr = np.array(big)
    res, _ = OCR(arr)
    sc, off = 1.6, 12
    out = []
    for box, txt, conf in (res or []):
        xs = [p[0] for p in box]; ys = [p[1] for p in box]
        t = txt.strip()
        if not t:
            continue
        f = lambda v: v / sc - off      # volver a coordenadas de la imagen original
        out.append(dict(t=t, x=f(sum(xs)/4), y=f(sum(ys)/4), x0=f(min(xs)),
                        x1=f(max(xs)), y0=f(min(ys)), y1=f(max(ys)), conf=conf))
    _CACHE[path] = out
    return out


def find_marks(path):
    """Devuelve bboxes de las marcas de respuesta (anillo negro o resaltado amarillo)."""
    im = np.array(Image.open(path).convert('RGB')).astype(int)
    r, g, b = im[:, :, 0], im[:, :, 1], im[:, :, 2]
    marks = []

    # 1) anillo negro grueso -> erosión deja solo trazos gruesos
    dark = (r < 90) & (g < 90) & (b < 90)
    er = ndimage.binary_erosion(dark, structure=np.ones((3, 3)), iterations=1)
    lbl, n = ndimage.label(er, structure=np.ones((3, 3)))
    for i in range(1, n + 1):
        yy, xx = np.where(lbl == i)
        if len(xx) < 150:
            continue
        x0, x1, y0, y1 = xx.min(), xx.max(), yy.min(), yy.max()
        w, h = x1 - x0, y1 - y0
        if w >= 55 and 15 <= h <= 70 and (len(xx) / max(w * h, 1)) < 0.55:
            marks.append((x0, y0, x1, y1, 'ring'))

    # 1b) recuadro verde (otra forma de marcar la opción correcta)
    grn = (g > 150) & (r < 140) & (b < 140) & (g - r > 50) & (g - b > 50)
    if grn.sum() > 60:
        lbl, n = ndimage.label(grn, structure=np.ones((3, 3)))
        for i in range(1, n + 1):
            yy, xx = np.where(lbl == i)
            if len(xx) < 60:
                continue
            x0, x1, y0, y1 = xx.min(), xx.max(), yy.min(), yy.max()
            w, h = x1 - x0, y1 - y0
            if w >= 55 and 10 <= h <= 70 and (len(xx) / max(w * h, 1)) < 0.6:
                marks.append((x0, y0, x1, y1, 'green'))

    # 2) resaltado amarillo
    yel = (r > 200) & (g > 190) & (b < 150)
    if yel.sum() > 120:
        lbl, n = ndimage.label(yel, structure=np.ones((3, 3)))
        for i in range(1, n + 1):
            yy, xx = np.where(lbl == i)
            if len(xx) < 120:
                continue
            x0, x1, y0, y1 = xx.min(), xx.max(), yy.min(), yy.max()
            if (x1 - x0) >= 30 and 8 <= (y1 - y0) <= 60:
                marks.append((x0, y0, x1, y1, 'hl'))
    return marks


def inside(line, m, pad=6):
    x0, y0, x1, y1, _ = m
    cx, cy = line['x'], line['y']
    return (x0 - pad) <= cx <= (x1 + pad) and (y0 - pad) <= cy <= (y1 + pad)


def group_options(lines, mark, all_lines):
    """Agrupa la lista de opciones a la que pertenece la marca."""
    mx0, my0, mx1, my1, _ = mark
    # candidatos: líneas cuyo inicio x está alineado con el de la marca (±25)
    cands = [l for l in all_lines
             if abs(l['x0'] - mx0) < 30 and l['x1'] > mx0 - 5
             and len(l['t']) > 1
             and not re.fullmatch(r'[▼vV\W_]+', l['t'])]
    if not cands:
        return None
    cands.sort(key=lambda l: l['y'])
    # tomar el bloque contiguo (separación vertical similar) que contiene la marca
    my = (my0 + my1) / 2
    idx = min(range(len(cands)), key=lambda i: abs(cands[i]['y'] - my))
    block = [cands[idx]]
    step = 46
    # hacia arriba
    i = idx - 1
    while i >= 0 and (block[0]['y'] - cands[i]['y']) <= step:
        block.insert(0, cands[i]); i -= 1
    # hacia abajo
    i = idx + 1
    while i < len(cands) and (cands[i]['y'] - block[-1]['y']) <= step:
        block.append(cands[i]); i += 1
    return block


def convert(qid, answer_images):
    for im in answer_images:
        p = os.path.join(DIR, im)
        if not os.path.exists(p):
            continue
        marks = find_marks(p)
        if not marks:
            continue
        lines = ocr_lines(p)
        if not lines:
            continue
        # descartar cabeceras
        body = [l for l in lines if 'answer area' not in l['t'].lower()]
        blanks = []
        used_y = []
        for m in sorted(marks, key=lambda m: m[1]):
            block = group_options(lines, m, body)
            if not block or len(block) < 2:
                continue
            opts = [clean(l['t']) for l in block]
            corr = None
            for j, l in enumerate(block):
                if inside(l, m):
                    corr = j; break
            if corr is None:
                continue
            # etiqueta: texto a la izquierda de la lista, cerca del tope del bloque
            top = block[0]['y0']
            left = [l for l in body if l['x1'] < m[0] - 10
                    and (top - 60) <= l['y'] <= (block[-1]['y1'] + 10)]
            left.sort(key=lambda l: l['y'])
            label = clean(' '.join(l['t'] for l in left[:2])) if left else ''
            if any(abs(top - u) < 12 for u in used_y):
                continue
            used_y.append(top)
            blanks.append({'label': label[:110], 'options': opts, 'correct': corr})
        if len(blanks) >= 1:
            ctx = [o for o in answer_images if o != im]
            return {'kind': 'select', 'context_images': ctx, 'blanks': blanks}, 'ok'
    return None, 'sin marcas'


FIX = {
    'Iniect': 'Inject', 'lniect': 'Inject', 'lnject': 'Inject',
    'Microsof': 'Microsoft', 'Windovs': 'Windows', 'lntune': 'Intune',
    'lnstall': 'Install', 'Azure AD': 'Azure AD', 'lOS': 'iOS',
    'Defende': 'Defender', 'Compliancy': 'Compliance', 'Autopilo': 'Autopilot',
}


def clean(t):
    t = re.sub(r'\s+', ' ', t).strip()
    for bad, good in FIX.items():
        t = re.sub(r'\b' + re.escape(bad) + r'\b', good, t)
    t = re.sub(r'([a-záéíóúñ])([A-ZÁÉÍÓÚÑ])', r'\1 \2', t)      # aB -> a B
    t = re.sub(r'\b(that|you|must|use|to|which|folder|the|in|a|of|for|is|are)\b(?=[a-z])',
               r'\1 ', t)                                        # pega palabras comunes
    t = re.sub(r'^[|\[\]]\s*', '', t)
    return re.sub(r'\s+', ' ', t).strip(' :')


def run_all():
    data = json.load(open('data/preguntas.json', encoding='utf-8'))
    inter = json.load(open('data/interactivas.json', encoding='utf-8'))
    manual = set(inter.keys())
    ok = 0
    for e in data:
        if e['type'] not in ('hotspot', 'drag'):
            continue
        if str(e['id']) in manual:
            continue
        res, st = convert(e['id'], e.get('answer_images', []))
        if res:
            inter[str(e['id'])] = res; ok += 1
            print(f'  #{e["id"]}: {len(res["blanks"])} listas')
    json.dump(inter, open('data/interactivas.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'nuevas desplegables: {ok} | total interactivas: {len(inter)}')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'all':
        run_all()
    else:
        q = {x['id']: x for x in json.load(open('data/preguntas.json', encoding='utf-8'))}
        for i in [int(a) for a in sys.argv[1:]] or [147]:
            res, st = convert(i, q[i].get('answer_images', []))
            print(f'=== #{i}: {st}')
            if res:
                for bl in res['blanks']:
                    print(f'  [{bl["label"]}]')
                    for j, o in enumerate(bl['options']):
                        print(f'     {"✔" if j==bl["correct"] else " "} {o}')
