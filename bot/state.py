# -*- coding: utf-8 -*-
"""Estado persistente del bot (se guarda en el repo vía GitHub Actions)."""
import json, pathlib, datetime

ROOT = pathlib.Path(__file__).resolve().parent
F = ROOT / 'state.json'
DEFAULT = {'polls': {}, 'stats': {'total': 0, 'correct': 0, 'tema': {}, 'q': {}},
           'exam': None, 'streak': {'count': 0, 'last': None}, 'daily': 3}


def load():
    try:
        s = json.load(open(F, encoding='utf-8'))
    except Exception:
        s = {}
    for k, v in DEFAULT.items():
        s.setdefault(k, v)
    return s


def save(s):
    # no dejar crecer el historial de encuestas sin límite
    if len(s.get('polls', {})) > 400:
        keep = list(s['polls'].items())[-250:]
        s['polls'] = dict(keep)
    json.dump(s, open(F, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def today():
    return datetime.date.today().isoformat()


def bump_streak(s):
    st = s['streak']
    t = today()
    if st.get('last') == t:
        return st['count']
    y = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    st['count'] = st['count'] + 1 if st.get('last') == y else 1
    st['last'] = t
    return st['count']


def record(s, qid, tema, ok):
    st = s['stats']
    st['total'] += 1
    if ok:
        st['correct'] += 1
    t = st['tema'].setdefault(tema or 'General', {'n': 0, 'ok': 0})
    t['n'] += 1
    if ok:
        t['ok'] += 1
    q = st['q'].setdefault(str(qid), {'n': 0, 'ok': 0})
    q['n'] += 1
    if ok:
        q['ok'] += 1
