# -*- coding: utf-8 -*-
"""
Reto diario MD-102 por Telegram (sin servidor, se ejecuta desde GitHub Actions).
- Opción múltiple de 1 respuesta -> encuesta tipo QUIZ (Telegram la califica al tocar).
- Opción múltiple de varias respuestas -> mensaje + respuesta oculta (spoiler).
- Tipo imagen (hotspot/arrastrar/sí-no) -> enunciado + imagen de respuesta borrosa (spoiler).
Selección determinista por día: recorre todo el banco sin repetir hasta agotarlo.
"""
import os, json, sys, time, random, datetime, pathlib
import requests

TOKEN   = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
N       = int(os.environ.get('DAILY_COUNT', '3'))
WEB_URL = os.environ.get('WEB_URL', '').strip()

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = json.load(open(ROOT / 'data' / 'preguntas.json', encoding='utf-8'))
IMGDIR = ROOT / 'data' / 'img'
API = f'https://api.telegram.org/bot{TOKEN}/'

if not TOKEN or not CHAT_ID:
    print('ERROR: faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID'); sys.exit(1)


def api(method, **kw):
    r = requests.post(API + method, **kw, timeout=60)
    j = r.json()
    if not j.get('ok'):
        print(f'  ! Telegram {method}: {j.get("description")}')
    return j


def send_msg(text, md=False):
    p = {'chat_id': CHAT_ID, 'text': text, 'disable_web_page_preview': True}
    if md:
        p['parse_mode'] = 'MarkdownV2'
    return api('sendMessage', data=p)


def send_photo(path, caption=None, spoiler=False):
    with open(path, 'rb') as f:
        data = {'chat_id': CHAT_ID, 'has_spoiler': 'true' if spoiler else 'false'}
        if caption:
            data['caption'] = caption
        return api('sendPhoto', data=data, files={'photo': f})


def send_quiz(question, options, correct_idx, explanation=None):
    p = {'chat_id': CHAT_ID, 'question': question[:300],
         'options': json.dumps([o[:100] for o in options], ensure_ascii=False),
         'type': 'quiz', 'correct_option_id': correct_idx,
         'is_anonymous': 'false'}
    if explanation:
        p['explanation'] = explanation[:200]
    return api('sendPoll', data=p)


def pick_today():
    """Permutación fija; ventana por día para no repetir hasta agotar el banco."""
    order = list(range(len(DATA)))
    random.Random(20240102).shuffle(order)
    day_index = (datetime.date.today() - datetime.date(2024, 1, 1)).days
    start = (day_index * N) % len(order)
    idx = [order[(start + i) % len(order)] for i in range(N)]
    return [DATA[i] for i in idx]


def esc(t):  # MarkdownV2
    for c in r'_*[]()~`>#+-=|{}.!':
        t = t.replace(c, '\\' + c)
    return t


def deliver(q, num):
    tema = q.get('tema', '')
    stem = (q.get('stem') or '').strip()
    header = f'🎯 Reto MD-102 · {num}/{N}  ·  #{q["id"]}\n📚 {tema}'

    if q['type'] == 'mc' and q.get('options'):
        opts = [o['text'] for o in q['options']]
        letters = [o['letter'] for o in q['options']]
        correct = q.get('correct', [])
        single = len(correct) == 1 and all(o.strip() for o in opts) and 2 <= len(opts) <= 10

        # imagen de contexto (tabla) si la pregunta la necesita
        for im in q.get('context_images', []):
            send_photo(IMGDIR / im)

        if single:
            cidx = letters.index(correct[0])
            # el enunciado va como mensaje si es largo; la encuesta lleva versión corta
            if len(stem) <= 250:
                qtext = f'{header}\n\n{stem}'
                if len(qtext) <= 300:
                    send_quiz(qtext, opts, cidx, f'Respuesta correcta: {correct[0]}')
                    return
            send_msg(f'{header}\n\n{stem}')
            send_quiz('¿Cuál es la respuesta correcta?', opts, cidx,
                      f'Respuesta correcta: {correct[0]}')
        else:
            # varias respuestas -> opciones en texto + respuesta oculta
            body = f'{header}\n\n{stem}\n\n'
            body += '\n'.join(f'{o["letter"]}. {o["text"]}' for o in q['options'])
            body += f'\n\n(Selecciona {len(correct)})'
            send_msg(body)
            send_msg('Respuesta: ||' + ', '.join(correct) + '||', md=True)
    else:
        # tipo imagen -> flashcard con respuesta borrosa
        send_msg(f'{header}\n\n{stem}\n\n👁️ Toca la imagen para ver la respuesta:')
        imgs = q.get('answer_images', [])
        for k, im in enumerate(imgs):
            send_photo(IMGDIR / im, spoiler=True)
            time.sleep(0.4)


def main():
    qs = pick_today()
    send_msg('☀️ ¡Buenos días! Aquí va tu reto MD-102 de hoy. '
             f'{len(qs)} preguntas para acercarte a la certificación. ¡Vamos! 💪')
    for i, q in enumerate(qs, 1):
        deliver(q, i)
        time.sleep(0.6)
    tail = '✅ ¡Listo por hoy! Repasa cuando quieras.'
    if WEB_URL:
        tail += f'\n🌐 Más práctica: {WEB_URL}'
    send_msg(tail)


if __name__ == '__main__':
    main()
