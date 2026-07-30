# -*- coding: utf-8 -*-
"""Reto diario MD-102 (ejecutado por GitHub Actions con cron)."""
import os, sys, time, random, datetime
import core

if not core.TOKEN or not core.CHAT_ID:
    print('ERROR: faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID'); sys.exit(1)

N = core.get_config().get('daily', int(os.environ.get('DAILY_COUNT', '3')))


def pick_today(n):
    """Permutación fija; ventana por día para no repetir hasta agotar el banco."""
    order = list(range(len(core.DATA)))
    random.Random(20240102).shuffle(order)
    day_index = (datetime.date.today() - datetime.date(2024, 1, 1)).days
    start = (day_index * n) % len(order)
    idx = [order[(start + i) % len(order)] for i in range(n)]
    return [core.DATA[i] for i in idx]


def main():
    core.set_commands()
    qs = pick_today(N)
    core.send_msg('☀️ ¡Buenos días! Aquí va tu reto MD-102 de hoy. '
                  f'{len(qs)} preguntas para acercarte a la certificación. ¡Vamos! 💪\n'
                  'Escribe /mas cuando quieras más preguntas.')
    for i, q in enumerate(qs, 1):
        core.deliver(q, i, len(qs))
        time.sleep(0.6)
    tail = '✅ ¡Listo por hoy! Escribe /mas para seguir practicando.'
    if core.WEB_URL:
        tail += f'\n🌐 App web: {core.WEB_URL}'
    core.send_msg(tail)


if __name__ == '__main__':
    main()
