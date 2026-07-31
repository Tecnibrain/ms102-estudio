# -*- coding: utf-8 -*-
"""OCR + detección de óvalos para convertir preguntas Sí/No a interactivas."""
import json, os, sys, re
import numpy as np
from PIL import Image
from scipy import ndimage
from rapidocr_onnxruntime import RapidOCR

DIR = 'data/img'
OCR = RapidOCR()


def ocr_lines(path):
    res, _ = OCR(path)
    out = []
    for box, txt, conf in (res or []):
        xs = [p[0] for p in box]; ys = [p[1] for p in box]
        out.append(dict(t=txt.strip(), x=sum(xs)/4, y=sum(ys)/4,
                        x0=min(xs), x1=max(xs), y0=min(ys), y1=max(ys), conf=conf))
    return out


def find_ovals(path):
    im = np.array(Image.open(path).convert('RGB')).astype(int)
    r, g, b = im[:, :, 0], im[:, :, 1], im[:, :, 2]
    mask = (b > 110) & (r < 100) & (g > 60) & (g < 170) & (b >= g)
    lbl, n = ndimage.label(mask)
    ov = []
    for i in range(1, n + 1):
        yy, xx = np.where(lbl == i)
        if 120 < len(xx) < 450:                 # óvalo de radio (no botones grandes)
            w = xx.max() - xx.min(); h = yy.max() - yy.min()
            if 0.5 < (w / max(h, 1)) < 2.2 and w < 40 and h < 40:
                ov.append((xx.mean(), yy.mean(), len(xx)))
    return ov, im.shape[0], im.shape[1]


def convert(qid, answer_images):
    # localizar la imagen con óvalos
    oval_img = None
    for im in answer_images:
        p = os.path.join(DIR, im)
        if not os.path.exists(p):
            continue
        ov, H, W = find_ovals(p)
        if len(ov) >= 1:
            oval_img = (im, p, ov, H, W); break
    if not oval_img:
        return None, 'sin ovalos'
    im, p, ov, H, W = oval_img
    lines = ocr_lines(p)

    # inicio del area de respuesta
    marker = [l for l in lines if 'answer area' in l['t'].lower()
              or 'statements' in l['t'].lower()]
    ans_y = min([l['y'] for l in marker]) if marker else min(o[1] for o in ov) - 40
    ov = [o for o in ov if o[1] > ans_y - 20]   # solo óvalos dentro del área de respuesta
    if not ov:
        return None, 'sin ovalos validos'

    # cabeceras Yes / No: en la fila de encabezados del área de respuesta
    yes = [l for l in lines if l['t'].lower() in ('yes', 'sí', 'si') and l['y'] > ans_y - 15]
    no = [l for l in lines if l['t'].lower() == 'no' and l['y'] > ans_y - 15]
    if not (yes and no):
        return None, 'sin cabeceras Yes/No'   # evita falsos positivos
    yes_x, no_x = yes[0]['x'], no[0]['x']

    left_x = min(yes_x, no_x) - 30
    left = [l for l in lines if l['x'] < left_x and l['y'] > ans_y - 5 and len(l['t']) > 4
            and 'answer area' not in l['t'].lower() and 'statement' not in l['t'].lower()]
    stmts = []
    for o in ov:
        ox, oy, _ = o
        a = 'yes' if abs(ox - yes_x) <= abs(ox - no_x) else 'no'
        band = sorted([l for l in left if abs(l['y'] - oy) < 34], key=lambda l: l['y'])
        if not band:
            continue
        txt = ' '.join(l['t'] for l in band)
        stmts.append((oy, txt, a))
    stmts.sort(key=lambda s: s[0])
    statements = [{'t': clean(t), 'a': a} for _, t, a in stmts]
    if not statements:
        return None, 'sin afirmaciones'

    # contexto: imágenes sin óvalos + recorte encima del Answer Area si aplica
    ctx = []
    for other in answer_images:
        if other == im:
            continue
        ctx.append(other)
    if ans_y > 130:   # hay contexto (tablas) en la misma imagen -> recortar
        crop = Image.open(p).convert('RGB').crop((0, 0, W, int(ans_y) - 8))
        cname = f'q{qid:03d}_ctxauto.png'
        crop.save(os.path.join(DIR, cname))
        ctx.insert(0, cname)

    return {'kind': 'yesno', 'context_images': ctx, 'statements': statements}, 'ok'


def clean(t):
    t = re.sub(r'\s+', ' ', t).strip()
    t = re.sub(r'([a-záéíóúñ])([A-ZÁÉÍÓÚÑ])', r'\1 \2', t)   # aB -> a B
    t = re.sub(r',(\S)', r', \1', t)                        # coma + espacio
    t = re.sub(r'\s+[Oo0]\s*$', '', t)                      # artefacto del óvalo vacío
    return t.strip()


def run_all():
    data = json.load(open('data/preguntas.json', encoding='utf-8'))
    manual = {'12'}   # desplegable hecho a mano
    try:
        old = json.load(open('data/interactivas.json', encoding='utf-8'))
    except FileNotFoundError:
        old = {}
    inter = {k: old[k] for k in manual if k in old}   # regenerar el resto desde cero
    ok = skip = 0
    for e in data:
        if e['type'] not in ('hotspot', 'yesno', 'drag'):
            continue
        if str(e['id']) in manual:
            continue
        res, status = convert(e['id'], e.get('answer_images', []))
        if res and len(res['statements']) >= 2:
            inter[str(e['id'])] = res; ok += 1
        else:
            skip += 1
    json.dump(inter, open('data/interactivas.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'convertidas Sí/No: {ok} | omitidas (drag/captura/otras): {skip}')
    print(f'total interactivas: {len(inter)}')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'all':
        run_all()
    else:
        q = {x['id']: x for x in json.load(open('data/preguntas.json', encoding='utf-8'))}
        ids = [int(a) for a in sys.argv[1:]] if len(sys.argv) > 1 else [8, 15]
        for i in ids:
            inter, status = convert(i, q[i].get('answer_images', []))
            print(f'=== #{i}: {status}')
            if inter:
                print('  contexto:', inter['context_images'])
                for s in inter['statements']:
                    print(f'   [{s["a"].upper():3}] {s["t"]}')
