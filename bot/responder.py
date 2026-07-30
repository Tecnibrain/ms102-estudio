# -*- coding: utf-8 -*-
"""
Responde comandos de Telegram bajo demanda (/mas, /reto, /cantidad, ...).
Se ejecuta periódicamente por GitHub Actions. Sin estado: confirma los
updates con 'offset' para no reprocesarlos.
"""
import sys, requests
import core
import send_daily

if not core.TOKEN or not core.CHAT_ID:
    print('ERROR: faltan credenciales'); sys.exit(1)

AYUDA = (
    '🤖 *Bot de estudio MD\\-102*\n\n'
    'Comandos:\n'
    '/reto \\- reto del día\n'
    '/mas \\- 3 preguntas más\n'
    '/mas5 \\- 5 preguntas más\n'
    '/mas10 \\- 10 preguntas más\n'
    '/cantidad N \\- preguntas por día \\(ej: /cantidad 5\\)\n'
    '/web \\- abrir la app web\n'
    '/ayuda \\- esta ayuda'
)


def handle(text, chat):
    t = text.strip().lower()
    cmd = t.split()[0].lstrip('/').split('@')[0] if t else ''
    n_daily = core.get_config().get('daily', 3)

    if cmd in ('start', 'ayuda', 'help'):
        core.send_msg(AYUDA, md=True, chat=chat)
        if core.WEB_URL:
            core.send_msg(f'🌐 App web: {core.WEB_URL}', chat=chat)
    elif cmd == 'reto':
        qs = send_daily.pick_today(n_daily)
        core.send_msg(f'🎯 Aquí está tu reto ({len(qs)} preguntas):', chat=chat)
        for i, q in enumerate(qs, 1):
            core.deliver(q, i, len(qs), chat=chat)
    elif cmd == 'mas':
        core.send_batch(3, chat=chat, header_msg='➕ 3 preguntas más:')
    elif cmd == 'mas5':
        core.send_batch(5, chat=chat, header_msg='➕ 5 preguntas más:')
    elif cmd == 'mas10':
        core.send_batch(10, chat=chat, header_msg='➕ 10 preguntas más:')
    elif cmd == 'cantidad':
        parts = t.split()
        if len(parts) >= 2 and parts[1].isdigit():
            n = max(1, min(15, int(parts[1])))
            cfg = core.get_config(); cfg['daily'] = n; core.set_config(cfg)
            core.send_msg(f'✅ Ahora recibirás {n} preguntas por día.', chat=chat)
        else:
            core.send_msg('Uso: /cantidad 5', chat=chat)
    elif cmd == 'web':
        core.send_msg(f'🌐 {core.WEB_URL or "app web no configurada"}', chat=chat)
    else:
        core.send_msg('No reconozco ese comando. Escribe /ayuda', chat=chat)


def main():
    r = requests.get(core.API + 'getUpdates', params={'timeout': 0}, timeout=40).json()
    updates = r.get('result', [])
    if not updates:
        print('sin novedades'); return
    max_id = max(u['update_id'] for u in updates)
    # confirmar de inmediato para no reprocesar en la próxima corrida
    requests.get(core.API + 'getUpdates', params={'offset': max_id + 1, 'timeout': 0}, timeout=40)

    for u in updates:
        msg = u.get('message') or u.get('edited_message')
        if not msg:
            continue
        chat = str(msg.get('chat', {}).get('id', ''))
        text = msg.get('text', '') or ''
        if chat != str(core.CHAT_ID):     # bot personal: ignorar a otros
            continue
        if text.startswith('/'):
            print('comando:', text)
            handle(text, chat)


if __name__ == '__main__':
    main()
