# -*- coding: utf-8 -*-
"""
Extractor del banco MD-102 (PDF con respuestas) -> data/preguntas.json + imagenes.
- Opcion multiple (mc): parsea enunciado, opciones y detecta la(s) correcta(s) por negrita (font *Bold*).
- Tipos imagen (hotspot/drag/yesno): enunciado en texto + imagen del area de respuesta (ya marcada en el PDF).
"""
import fitz, re, json, os

PDF = 'D:/Estudio/MD 102 - Con Respuestas.pdf'
OUT_DIR = 'D:/Estudio/ms102/data'
IMG_DIR = os.path.join(OUT_DIR, 'img')
os.makedirs(IMG_DIR, exist_ok=True)

doc = fitz.open(PDF)

# 1) Construir un stream ordenado de items (texto/imagen) con posicion global
items = []  # cada item: dict(kind, page, bidx, y0, y1, x0, x1, text, bold)
for pno, page in enumerate(doc):
    d = page.get_text('dict')
    # PyMuPDF lista imagenes despues del texto: reordenar por posicion vertical (lectura)
    blocks = sorted(d['blocks'], key=lambda b: (round(b['bbox'][1], 1), b['bbox'][0]))
    for bidx, b in enumerate(blocks):
        x0, y0, x1, y1 = b['bbox']
        if b.get('type') == 1:  # imagen
            items.append(dict(kind='img', page=pno, bidx=bidx, y0=y0, y1=y1, x0=x0, x1=x1,
                              text='', bold=False))
        else:
            txt = ''
            anybold = False
            for l in b.get('lines', []):
                for s in l['spans']:
                    txt += s['text']
                    if 'Bold' in s['font']:
                        anybold = True
                txt += '\n'
            items.append(dict(kind='text', page=pno, bidx=bidx, y0=y0, y1=y1, x0=x0, x1=x1,
                              text=txt, bold=anybold))

# 2) Localizar inicios de pregunta ("Pregunta N")
q_re = re.compile(r'^\s*Pregunta\s+(\d+)\s*$', re.M)
starts = []  # (item_index, qnum)
for i, it in enumerate(items):
    if it['kind'] == 'text':
        m = re.search(r'Pregunta\s+(\d+)', it['text'])
        # asegurar que la linea sea el encabezado (bold y corto)
        if m and it['bold'] and len(it['text'].strip()) < 20:
            starts.append((i, int(m.group(1))))

print('preguntas encontradas:', len(starts))

def render_region(pno, y_top, y_bot, path, dpi=140):
    page = doc[pno]
    r = fitz.Rect(0, max(0, y_top-4), page.rect.width, min(page.rect.height, y_bot+4))
    if r.height < 5:
        return False
    pix = page.get_pixmap(dpi=dpi, clip=r)
    pix.save(path)
    return True

def clean(t):
    t = t.replace('\r', '')
    t = re.sub(r'[ \t]+', ' ', t)
    t = re.sub(r'\n{3,}', '\n\n', t)
    return t.strip()

OPT_RE = re.compile(r'^\s*([A-F])[\.\)]\s*(.*)$')

questions = []
for si, (i, qnum) in enumerate(starts):
    j = starts[si+1][0] if si+1 < len(starts) else len(items)
    blk = items[i+1:j]  # items del cuerpo (sin el encabezado)
    last_page = blk[-1]['page'] if blk else items[i]['page']
    next_start_item = items[starts[si+1][0]] if si+1 < len(starts) else None

    body_text_items = [b for b in blk if b['kind'] == 'text']
    img_items = [b for b in blk if b['kind'] == 'img']
    full_text = '\n'.join(b['text'] for b in body_text_items)

    # clasificar tipo
    if 'ARRASTRAR Y SOLTAR' in full_text:
        qtype = 'drag'
    elif re.search(r'\bA[\.\)]\s*S[íi]\b', full_text) and re.search(r'\bB[\.\)]\s*No\b', full_text) \
            and not re.search(r'\bC[\.\)]', full_text):
        # "¿Esto cumple el objetivo? A. Sí / B. No" -> es opción múltiple normal
        qtype = 'mc'
    else:
        # contar opciones tipo A. B. C.
        opt_lines = [ln for b in body_text_items for ln in b['text'].split('\n')
                     if OPT_RE.match(ln)]
        letters = [OPT_RE.match(ln).group(1) for ln in opt_lines]
        if len(set(letters)) >= 2 and 'PUNTO DE ACCESO' not in full_text:
            qtype = 'mc'
        else:
            qtype = 'hotspot'

    entry = dict(id=qnum, type=qtype, page=items[i]['page']+1)

    if qtype == 'mc':
        # separar enunciado de opciones; correctas = opciones en negrita
        options = []
        correct = []
        stem_parts = []
        for b in body_text_items:
            for ln in b['text'].split('\n'):
                m = OPT_RE.match(ln)
                if m and len(m.group(1)) == 1:
                    letter = m.group(1)
                    txt = m.group(2).strip()
                    options.append(dict(letter=letter, text=txt))
                    if b['bold']:
                        correct.append(letter)
                else:
                    if ln.strip():
                        stem_parts.append(ln)
        # imagenes de contexto (tablas necesarias para leer la pregunta)
        ctx_imgs = []
        for k, im in enumerate(img_items):
            p = f'q{qnum:03d}_ctx{k+1}.png'
            if render_region(im['page'], im['y0'], im['y1'], os.path.join(IMG_DIR, p)):
                ctx_imgs.append(p)
        entry.update(stem=clean('\n'.join(stem_parts)),
                     options=options, correct=correct, context_images=ctx_imgs)
    else:
        # tipos imagen: enunciado en texto + imagen(es) del area de respuesta
        # enunciado = texto antes de la primera imagen
        first_img_y = None
        first_img_page = None
        if img_items:
            first_img_page = img_items[0]['page']
            first_img_y = img_items[0]['y0']
        stem_items = []
        for b in blk:
            if b['kind'] == 'img':
                break
            stem_items.append(b['text'])
        stem = clean('\n'.join(stem_items))
        # renderizar region de respuesta: desde primera imagen hasta siguiente pregunta
        ans_imgs = []
        if img_items:
            pages_span = range(first_img_page, last_page+1)
            for p in pages_span:
                y_top = first_img_y if p == first_img_page else 0
                if p == last_page and next_start_item and next_start_item['page'] == p:
                    y_bot = next_start_item['y0']
                else:
                    y_bot = doc[p].rect.height
                fn = f'q{qnum:03d}_ans_p{p}.png'
                if render_region(p, y_top, y_bot, os.path.join(IMG_DIR, fn)):
                    ans_imgs.append(fn)
        entry.update(stem=stem, answer_images=ans_imgs)

    questions.append(entry)

with open(os.path.join(OUT_DIR, 'preguntas.json'), 'w', encoding='utf-8') as f:
    json.dump(questions, f, ensure_ascii=False, indent=1)

# resumen
from collections import Counter
c = Counter(q['type'] for q in questions)
mc = [q for q in questions if q['type'] == 'mc']
mc_no_correct = [q['id'] for q in mc if not q['correct']]
mc_multi = [q['id'] for q in mc if len(q['correct']) > 1]
print('tipos:', dict(c))
print('mc sin correcta detectada:', len(mc_no_correct), mc_no_correct[:20])
print('mc con multiples correctas:', len(mc_multi))
print('total imagenes en', IMG_DIR, ':', len(os.listdir(IMG_DIR)))
