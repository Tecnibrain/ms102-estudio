# -*- coding: utf-8 -*-
"""
Ayuda para obtener tu TELEGRAM_CHAT_ID.
1) Crea el bot con @BotFather y copia el token.
2) En Telegram, ENVÍALE cualquier mensaje a tu bot (ej: "hola").
3) Ejecuta:  python bot/get_chat_id.py  <TU_TOKEN>
   Te mostrará tu chat_id.
"""
import sys, requests

if len(sys.argv) < 2:
    print('Uso: python bot/get_chat_id.py <TU_TOKEN>'); sys.exit(1)

token = sys.argv[1].strip()
r = requests.get(f'https://api.telegram.org/bot{token}/getUpdates', timeout=30).json()
if not r.get('ok'):
    print('Token inválido:', r.get('description')); sys.exit(1)
ids = []
for u in r.get('result', []):
    msg = u.get('message') or u.get('channel_post') or {}
    chat = msg.get('chat', {})
    if chat.get('id'):
        ids.append((chat['id'], chat.get('first_name') or chat.get('title') or ''))
if not ids:
    print('No hay mensajes todavía. Envíale un mensaje a tu bot en Telegram y vuelve a ejecutar.')
else:
    for cid, name in set(ids):
        print(f'CHAT_ID = {cid}   ({name})')
