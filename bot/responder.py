# -*- coding: utf-8 -*-
"""
Atiende comandos y respuestas de encuestas (se ejecuta cada 5 min por GitHub Actions).
Sin servidor: confirma los updates con 'offset' y guarda el estado en state.json.
"""
import sys, random, requests
import core, state
import send_daily

if not core.TOKEN or not core.CHAT_ID:
    print('ERROR: faltan credenciales'); sys.exit(1)

APROBADO = 70          # % para aprobar el MD-102 (700/1000)
EXAM_N = 10

AYUDA = """🤖 *Bot de estudio MD\\-102*

*Practicar*
/reto \\- el reto del día
/mas \\- 3 preguntas más
/mas5 · /mas10 \\- más preguntas
/flash \\- 5 preguntas rápidas ⚡

*Simulacro*
/examen \\- simulacro de {n} preguntas 🎓
/resultado \\- calificar el simulacro

*Progreso*
/stats \\- tu avance y precisión 📊
/debiles \\- repasar lo que más fallas 🔁

*Ajustes*
/cantidad N \\- preguntas por día
/tema \\- elegir dominio
/web \\- abrir la app web""".format(n=EXAM_N)

ANIMO_OK = ['¡Vas muy bien! 🚀', '¡Esa la dominas! 💪', '¡Sigue así! ⭐',
            '¡Excelente! 🎯', '¡Crack! 🔥']
ANIMO_MAL = ['Tranquilo, esa es de las difíciles 💭', 'Anótala, te la volveré a preguntar 🔁',
             'De los errores se aprende 📚', 'Casi. Repásala y listo 👊']


def barra(pct, n=10):
    llenos = round(pct / 100 * n)
    return '█' * llenos + '░' * (n - llenos)


def temas():
    return sorted({q.get('tema', '') for q in core.DATA if q.get('tema')})


def elegibles(tema=None):
    qs = [q for q in core.DATA if q['type'] == 'mc' or q.get('inter')]
    if tema:
        qs = [q for q in qs if q.get('tema') == tema]
    return qs or core.DATA


def cmd_stats(st, chat):
    s = st['stats']
    tot, ok = s['total'], s['correct']
    if not tot:
        core.send_msg('Aún no has respondido ninguna encuesta. '
                      'Escribe /reto o /examen para empezar 🎯', chat=chat)
        return
    pct = round(ok / tot * 100)
    inter = sum(1 for q in core.DATA if q['type'] == 'mc' or q.get('inter'))
    vistas = len(s['q'])
    txt = (f'📊 TU PROGRESO\n\n'
           f'{barra(pct)}  {pct}% de acierto\n'
           f'✅ {ok} aciertos de {tot} respuestas\n'
           f'📚 {vistas} preguntas distintas (de {inter} interactivas)\n'
           f'🔥 Racha: {st["streak"]["count"]} día(s)\n\nPOR TEMA\n')
    for t, v in sorted(s['tema'].items(), key=lambda x: -x[1]['n']):
        p = round(v['ok'] / v['n'] * 100) if v['n'] else 0
        txt += f'{barra(p, 8)} {p:3d}%  {t[:30]}\n'
    txt += ('\n🎓 ¡Vas en nivel de aprobar!' if pct >= APROBADO
            else f'\n🎯 Te faltan {APROBADO - pct} puntos para el nivel de aprobación')
    core.send_msg(txt, chat=chat)


def cmd_debiles(st, chat):
    """Preguntas con más fallos."""
    q = st['stats']['q']
    malas = sorted([(k, v) for k, v in q.items() if v['n'] > v['ok']],
                   key=lambda x: (x[1]['ok'] - x[1]['n']))
    if not malas:
        core.send_msg('🎉 No tienes preguntas falladas pendientes. ¡Buen trabajo!', chat=chat)
        return
    byid = {str(x['id']): x for x in core.DATA}
    sel = [byid[k] for k, _ in malas[:5] if k in byid]
    core.send_msg(f'🔁 Repaso de tus {len(sel)} preguntas más falladas:', chat=chat)
    for i, qq in enumerate(sel, 1):
        core.deliver(qq, i, len(sel), chat=chat, st=st)


def cmd_examen(st, chat):
    qs = [q for q in elegibles() if q['type'] == 'mc' and len(q.get('correct', [])) == 1]
    qs = random.sample(qs, min(EXAM_N, len(qs)))
    st['exam'] = {'ids': [q['id'] for q in qs], 'ok': 0, 'n': 0}
    core.send_msg(f'🎓 *SIMULACRO MD\\-102*\n\n{EXAM_N} preguntas\\. '
                  f'Necesitas {APROBADO}% para aprobar\\.\n'
                  'Responde todas y luego escribe /resultado\\.\n\n¡Mucha suerte\\! 🍀',
                  md=True, chat=chat)
    for i, q in enumerate(qs, 1):
        core.deliver(q, i, len(qs), chat=chat, st=st, exam=True)


def cmd_resultado(st, chat):
    ex = st.get('exam')
    if not ex or not ex['n']:
        core.send_msg('No hay un simulacro en curso. Escribe /examen para empezar 🎓', chat=chat)
        return
    pct = round(ex['ok'] / ex['n'] * 100)
    aprob = pct >= APROBADO
    cara = '🏆' if pct >= 90 else '🎓' if aprob else '📚'
    txt = (f'{cara} *RESULTADO DEL SIMULACRO*\n\n'
           f'{barra(pct)}  {pct}%\n'
           f'Aciertos: {ex["ok"]} de {ex["n"]}\n\n')
    txt += ('✅ *APROBADO* \\- ¡estás listo\\!' if aprob
            else f'❌ No aprobado \\(necesitas {APROBADO}%\\)\\. ¡Sigue practicando\\!')
    core.send_msg(txt, md=True, chat=chat)
    st['exam'] = None


def handle(text, chat, st):
    t = text.strip().lower()
    cmd = t.split()[0].lstrip('/').split('@')[0] if t else ''

    if cmd in ('start', 'ayuda', 'help'):
        core.send_msg(AYUDA, md=True, chat=chat)
    elif cmd == 'reto':
        qs = send_daily.pick_today(st.get('daily', 3))
        core.send_msg(f'🎯 Tu reto ({len(qs)} preguntas):', chat=chat)
        for i, q in enumerate(qs, 1):
            core.deliver(q, i, len(qs), chat=chat, st=st)
    elif cmd in ('mas', 'mas5', 'mas10', 'flash'):
        n = {'mas': 3, 'mas5': 5, 'mas10': 10, 'flash': 5}[cmd]
        tema = st.get('tema')
        qs = random.sample(elegibles(tema), min(n, len(elegibles(tema))))
        head = '⚡ Ronda relámpago:' if cmd == 'flash' else f'➕ {n} preguntas más:'
        core.send_msg(head + (f'\n📚 {tema}' if tema else ''), chat=chat)
        for i, q in enumerate(qs, 1):
            core.deliver(q, i, len(qs), chat=chat, st=st)
    elif cmd == 'examen':
        cmd_examen(st, chat)
    elif cmd == 'resultado':
        cmd_resultado(st, chat)
    elif cmd == 'stats':
        cmd_stats(st, chat)
    elif cmd == 'debiles':
        cmd_debiles(st, chat)
    elif cmd == 'tema':
        arg = text.strip()[5:].strip()
        ts = temas()
        if not arg:
            lista = '\n'.join(f'{i+1}. {t}' for i, t in enumerate(ts))
            core.send_msg(f'📚 Elige un tema con /tema N\n\n{lista}\n\n0. Todos', chat=chat)
        elif arg == '0':
            st['tema'] = None; core.send_msg('✅ Practicarás con todos los temas.', chat=chat)
        elif arg.isdigit() and 1 <= int(arg) <= len(ts):
            st['tema'] = ts[int(arg) - 1]
            core.send_msg(f'✅ Tema fijado: {st["tema"]}', chat=chat)
        else:
            core.send_msg('Uso: /tema 2', chat=chat)
    elif cmd == 'cantidad':
        parts = t.split()
        if len(parts) >= 2 and parts[1].isdigit():
            st['daily'] = max(1, min(15, int(parts[1])))
            core.send_msg(f'✅ Ahora recibirás {st["daily"]} preguntas por día.', chat=chat)
        else:
            core.send_msg('Uso: /cantidad 5', chat=chat)
    elif cmd == 'web':
        core.send_msg(f'🌐 {core.WEB_URL or "app web no configurada"}', chat=chat)
    else:
        core.send_msg('No reconozco ese comando. Escribe /ayuda', chat=chat)


def on_poll_answer(pa, st):
    pid = pa.get('poll_id')
    info = st['polls'].get(pid)
    if not info:
        return
    opts = pa.get('option_ids') or []
    ok = bool(opts) and opts[0] == info['c']
    state.record(st, info.get('q'), info.get('tema'), ok)
    if info.get('x') and st.get('exam'):
        st['exam']['n'] += 1
        if ok:
            st['exam']['ok'] += 1
        if st['exam']['n'] >= len(st['exam']['ids']):
            core.send_msg('✅ Terminaste el simulacro. Escribe /resultado para ver tu nota 🎓')
    else:
        # ánimo ocasional para no saturar
        if random.random() < 0.25:
            core.send_msg(random.choice(ANIMO_OK if ok else ANIMO_MAL))
    del st['polls'][pid]


def main():
    st = state.load()
    r = requests.get(core.API + 'getUpdates',
                     params={'timeout': 0, 'allowed_updates': '["message","poll_answer"]'},
                     timeout=40).json()
    updates = r.get('result', [])
    if not updates:
        print('sin novedades'); state.save(st); return
    max_id = max(u['update_id'] for u in updates)
    requests.get(core.API + 'getUpdates',
                 params={'offset': max_id + 1, 'timeout': 0}, timeout=40)

    for u in updates:
        if 'poll_answer' in u:
            on_poll_answer(u['poll_answer'], st)
            continue
        msg = u.get('message') or u.get('edited_message')
        if not msg:
            continue
        chat = str(msg.get('chat', {}).get('id', ''))
        text = msg.get('text', '') or ''
        if chat != str(core.CHAT_ID):
            continue
        if text.startswith('/'):
            print('comando:', text)
            handle(text, chat, st)
    state.save(st)


if __name__ == '__main__':
    main()
