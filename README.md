# MD-102 · Estudio con retos diarios

Sistema didáctico para prepararte a la certificación **MS/MD-102**:
un **banco de 369 preguntas** (extraídas del PDF) que se te entregan poco a poco,
como reto diario, para que aprendas por repetición espaciada.

Dos formas de usarlo, con el **mismo banco de preguntas**:

| | Qué es | Hosting |
|---|---|---|
| 🌐 **App web (PWA)** | Quiz interactivo, progreso, repaso de falladas, estadísticas. Instalable en el móvil, funciona offline. | GitHub Pages **o** local |
| 🤖 **Bot de Telegram** | Cada mañana te envía 3 preguntas. Las de opción múltiple se autocalifican; las de imagen llegan con la respuesta oculta (spoiler). | GitHub Actions (sin servidor) |

---

## Estructura

```
index.html, app.js, styles.css, sw.js, manifest.json   → app web (PWA)
icons/                                                  → iconos PWA
data/preguntas.json   → banco de 369 preguntas
data/preguntas.js     → mismo banco (para uso offline sin servidor)
data/img/             → tablas y respuestas (imágenes)
bot/send_daily.py     → envía el reto diario a Telegram
bot/get_chat_id.py    → ayuda para obtener tu chat_id
.github/workflows/daily.yml → programa el envío diario (cron)
```

---

## 1) App web

### Opción A — Local (privado, gratis, sin exponer nada)
Solo abre `index.html` en tu navegador (usa `data/preguntas.js`, no requiere servidor).
Para instalarla como app en el móvil o usar notificaciones sí necesita estar servida por HTTPS (ver Opción B).

### Opción B — GitHub Pages (accesible desde cualquier lado)
> ⚠️ GitHub Pages gratis **requiere repositorio público**: el banco quedaría visible en internet.
1. Sube esta carpeta a un repositorio de GitHub.
2. *Settings → Pages → Build from branch → `main` / root*.
3. Tu app quedará en `https://<usuario>.github.io/<repo>/`.

---

## 2) Bot de Telegram (reto diario)

Funciona **sin servidor**: GitHub Actions lo ejecuta cada día. También corre en repos **privados** (gratis).

### Configuración (una sola vez)
1. **Crea el bot**: en Telegram abre **@BotFather** → `/newbot` → sigue los pasos → copia el **token**.
2. **Envíale un mensaje** a tu bot (ej.: "hola").
3. **Obtén tu chat_id**:
   ```
   python bot/get_chat_id.py <TU_TOKEN>
   ```
4. En tu repo de GitHub → *Settings → Secrets and variables → Actions* → **New repository secret**:
   - `TELEGRAM_BOT_TOKEN` = tu token
   - `TELEGRAM_CHAT_ID` = tu chat_id
   - (opcional) en la pestaña *Variables*: `WEB_URL` = la URL de tu app web
5. Listo. Se enviará **todos los días a las 8:00 a.m. (Colombia)**.
   Para probarlo ya: *Actions → Reto diario MD-102 → Run workflow*.

### Cambiar la hora o la cantidad
- Hora: edita el `cron` en `.github/workflows/daily.yml` (está en **UTC**; 13:00 UTC = 8:00 Colombia).
- Cantidad de preguntas: cambia `DAILY_COUNT` en el mismo archivo.

### Probar el bot localmente
```
set TELEGRAM_BOT_TOKEN=xxxx
set TELEGRAM_CHAT_ID=yyyy
python bot/send_daily.py
```

---

## Regenerar el banco (si cambia el PDF)
```
python extract.py     # PDF -> data/preguntas.json + imágenes
python enrich.py      # limpia enunciados y asigna temas
python -c "import json;open('data/preguntas.js','w',encoding='utf-8').write('window.MS102_DATA='+open('data/preguntas.json',encoding='utf-8').read()+';')"
```

## Nota sobre derechos de autor
Las preguntas provienen de material de estudio con posibles derechos de autor.
Úsalo para tu preparación personal. Si publicas el repo, hazlo bajo tu responsabilidad.
