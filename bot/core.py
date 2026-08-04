# -*- coding: utf-8 -*-
"""Núcleo compartido del bot MD-102: carga de datos, envío y entrega de preguntas."""
import os, json, time, random, pathlib
import requests

TOKEN   = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
WEB_URL = os.environ.get('WEB_URL', '').strip()

ROOT   = pathlib.Path(__file__).resolve().parent.parent
DATA   = json.load(open(ROOT / 'data' / 'preguntas.json', encoding='utf-8'))
IMGDIR = ROOT / 'data' / 'img'
CONFIG = ROOT / 'bot' / 'config.json'
API    = f'https://api.telegram.org/bot{TOKEN}/'


def get_config():
    try:
        return json.load(open(CONFIG, encoding='utf-8'))
    except Exception:
        return {'daily': 3}


def set_config(cfg):
    json.dump(cfg, open(CONFIG, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def api(method, chat=None, **kw):
    r = requests.post(API + method, **kw, timeout=60)
    j = r.json()
    if not j.get('ok'):
        print(f'  ! Telegram {method}: {j.get("description")}')
    return j


def send_msg(text, md=False, chat=None):
    p = {'chat_id': chat or CHAT_ID, 'text': text, 'disable_web_page_preview': True}
    if md:
        p['parse_mode'] = 'MarkdownV2'
    return api('sendMessage', data=p)


def send_photo(path, caption=None, spoiler=False, chat=None):
    with open(path, 'rb') as f:
        data = {'chat_id': chat or CHAT_ID, 'has_spoiler': 'true' if spoiler else 'false'}
        if caption:
            data['caption'] = caption
        return api('sendPhoto', data=data, files={'photo': f})


def send_quiz(question, options, correct_idx, explanation=None, chat=None,
              qid=None, tema=None, st=None, exam=None):
    p = {'chat_id': chat or CHAT_ID, 'question': question[:300],
         'options': json.dumps([o[:100] for o in options], ensure_ascii=False),
         'type': 'quiz', 'correct_option_id': correct_idx, 'is_anonymous': 'false'}
    if explanation:
        p['explanation'] = explanation[:200]
    r = api('sendPoll', data=p)
    # registrar la encuesta para poder puntuar la respuesta más tarde
    if st is not None and r.get('ok'):
        poll = (r.get('result') or {}).get('poll') or {}
        pid = poll.get('id')
        if pid:
            st['polls'][pid] = {'q': qid, 'c': correct_idx, 'tema': tema, 'x': exam}
    return r


def deliver(q, num, total, chat=None, st=None, exam=None):
    tema = q.get('tema', '')
    stem = (q.get('stem') or '').strip()
    expl = (q.get('explicacion') or '').strip()
    header = f'🎯 MD-102 · {num}/{total}  ·  #{q["id"]}\n📚 {tema}'

    it = q.get('inter')
    if it:
        # interactiva: enunciado + contexto y luego una encuesta por hueco
        send_msg(f'{header}\n\n{stem}', chat=chat)
        for im in it.get('context_images', []):
            p = IMGDIR / im
            if p.exists():
                send_photo(p, chat=chat)
                time.sleep(0.3)
        if it['kind'] == 'multi':
            letras = 'ABCDEFGHIJ'
            body = '\n'.join(f'{letras[i]}. {o}' for i, o in enumerate(it['options']))
            send_msg(f'{body}\n\n(Selecciona {len(it["correct"])})', chat=chat)
            send_msg('Respuesta: ||' + ', '.join(letras[i] for i in it['correct']) + '||',
                     md=True, chat=chat)
            if expl:
                send_msg('💡 ' + expl, chat=chat)
        elif it['kind'] == 'yesno':
            for s in it['statements']:
                send_quiz(s['t'][:300], ['Sí', 'No'],
                          0 if s['a'] == 'yes' else 1, expl or None, chat=chat,
                          qid=q['id'], tema=tema, st=st, exam=exam)
                time.sleep(0.4)
        else:
            for bl in it['blanks']:
                label = bl.get('label') or 'Elige la opción correcta'
                send_quiz(label[:300], bl['options'], bl['correct'], expl or None,
                          chat=chat, qid=q['id'], tema=tema, st=st, exam=exam)
                time.sleep(0.4)
        return

    if q['type'] == 'mc' and q.get('options'):
        opts = [o['text'] for o in q['options']]
        letters = [o['letter'] for o in q['options']]
        correct = q.get('correct', [])
        single = len(correct) == 1 and all(o.strip() for o in opts) and 2 <= len(opts) <= 10
        for im in q.get('context_images', []):
            send_photo(IMGDIR / im, chat=chat)
        exp_txt = expl or (f'Respuesta correcta: {correct[0]}' if correct else None)
        if single:
            cidx = letters.index(correct[0])
            qtext = f'{header}\n\n{stem}'
            if len(stem) <= 250 and len(qtext) <= 300:
                send_quiz(qtext, opts, cidx, exp_txt, chat=chat,
                          qid=q['id'], tema=tema, st=st, exam=exam)
            else:
                send_msg(f'{header}\n\n{stem}', chat=chat)
                send_quiz('¿Cuál es la respuesta correcta?', opts, cidx, exp_txt,
                          chat=chat, qid=q['id'], tema=tema, st=st, exam=exam)
        else:
            body = f'{header}\n\n{stem}\n\n' + '\n'.join(
                f'{o["letter"]}. {o["text"]}' for o in q['options'])
            body += f'\n\n(Selecciona {len(correct)})'
            send_msg(body, chat=chat)
            reveal = 'Respuesta: ||' + ', '.join(correct) + '||'
            send_msg(reveal, md=True, chat=chat)
            if expl:
                send_msg('💡 ' + expl, chat=chat)
    else:
        send_msg(f'{header}\n\n{stem}\n\n👁️ Toca la imagen para ver la respuesta:', chat=chat)
        for im in q.get('answer_images', []):
            send_photo(IMGDIR / im, spoiler=True, chat=chat)
            time.sleep(0.4)
        if expl:
            send_msg('💡 ' + expl, chat=chat)


def send_batch(n, chat=None, header_msg=None):
    """Envía n preguntas al azar (uso bajo demanda)."""
    qs = random.sample(DATA, min(n, len(DATA)))
    if header_msg:
        send_msg(header_msg, chat=chat)
    for i, q in enumerate(qs, 1):
        deliver(q, i, len(qs), chat=chat)
        time.sleep(0.6)


def set_commands():
    cmds = [
        {'command': 'reto',      'description': '🎯 El reto de hoy'},
        {'command': 'mas',       'description': '➕ 3 preguntas más'},
        {'command': 'flash',     'description': '⚡ 5 preguntas rápidas'},
        {'command': 'mas10',     'description': '➕ 10 preguntas más'},
        {'command': 'examen',    'description': '🎓 Simulacro de examen'},
        {'command': 'resultado', 'description': '📋 Calificar el simulacro'},
        {'command': 'stats',     'description': '📊 Tu progreso y precisión'},
        {'command': 'debiles',   'description': '🔁 Repasar lo que más fallas'},
        {'command': 'tema',      'description': '📚 Elegir dominio del examen'},
        {'command': 'cantidad',  'description': '⚙️ Preguntas por día (ej: /cantidad 5)'},
        {'command': 'web',       'description': '🌐 Abrir la app web'},
        {'command': 'ayuda',     'description': '❓ Ver la ayuda'},
    ]
    api('setMyCommands', data={'commands': json.dumps(cmds, ensure_ascii=False)})
