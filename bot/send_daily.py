# -*- coding: utf-8 -*-
"""Reto diario MD-102 (cron de GitHub Actions)."""
import os, sys, time, random, datetime
import core, state

if not core.TOKEN or not core.CHAT_ID:
    print('ERROR: faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID'); sys.exit(1)

SALUDOS = [
    '☀️ ¡Buenos días! Tu dosis diaria de MD-102 está lista.',
    '🌅 Nuevo día, nuevas preguntas. ¡A por la certificación!',
    '⚡ Arrancamos el día entrenando para el MD-102.',
    '🎯 Tres minutos hoy valen más que tres horas el día antes del examen.',
    '📚 Hora de sumar puntos hacia tu certificación.',
    '🚀 Cada reto diario te acerca al aprobado.',
]
CIERRES = [
    '✅ ¡Listo por hoy! ¿Quieres más? /mas',
    '✅ Reto completado. Prueba un simulacro con /examen 🎓',
    '✅ Terminaste. Mira cómo vas con /stats 📊',
    '✅ ¡Bien hecho! Si fallaste alguna, repásala con /debiles 🔁',
]


def pick_today(n):
    """Permutación fija; ventana por día para no repetir hasta agotar el banco."""
    order = list(range(len(core.DATA)))
    random.Random(20240102).shuffle(order)
    day = (datetime.date.today() - datetime.date(2024, 1, 1)).days
    start = (day * n) % len(order)
    return [core.DATA[order[(start + i) % len(order)]] for i in range(n)]


def main():
    st = state.load()
    core.set_commands()
    n = st.get('daily', int(os.environ.get('DAILY_COUNT', '3')))
    racha = state.bump_streak(st)
    qs = pick_today(n)

    cab = random.choice(SALUDOS)
    if racha > 1:
        cab += f'\n🔥 Racha: {racha} días seguidos. ¡No la rompas!'
    cab += f'\n\nHoy: {len(qs)} preguntas.'
    core.send_msg(cab)

    for i, q in enumerate(qs, 1):
        core.deliver(q, i, len(qs), st=st)
        time.sleep(0.6)

    cierre = random.choice(CIERRES)
    if core.WEB_URL:
        cierre += f'\n🌐 App web: {core.WEB_URL}'
    core.send_msg(cierre)
    state.save(st)


if __name__ == '__main__':
    main()
