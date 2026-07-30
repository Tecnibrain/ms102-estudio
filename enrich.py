# -*- coding: utf-8 -*-
"""Limpia enunciados y asigna un tema (dominio MD-102) a cada pregunta."""
import json, re

P = 'D:/Estudio/ms102/data/preguntas.json'
q = json.load(open(P, encoding='utf-8'))

def clean_stem(s):
    s = s.replace('PUNTO DE ACCESO', '').replace('ARRASTRAR Y SOLTAR', '')
    # quitar lineas que son solo guion o vacias al inicio
    lines = [ln.strip() for ln in s.split('\n')]
    lines = [ln for ln in lines if ln not in ('', '-', '–', '—')]
    return '\n'.join(lines).strip()

# temas (dominios del examen) por palabras clave, con prioridad
TEMAS = [
    ('Identidad y cumplimiento normativo',
     ['entra', 'azure ad', 'acceso condicional', 'condicional', 'mfa', 'autenticaci',
      'rbac', 'rol ', 'roles', 'pim', 'identity protection', 'grupo din', 'licencia',
      'sspr', 'dlp', 'etiqueta de confidencial', 'retenci', 'directiva de acceso']),
    ('Implementación de Windows',
     ['autopilot', 'piloto autom', 'provisionamiento', 'aprovisionamiento', 'imagen',
      'mdt', 'deployment toolkit', 'actualizaci', 'windows update', 'feature update',
      'wsus', 'wufb', 'en el lugar', 'in-place', 'activaci']),
    ('Aplicaciones y protección de endpoints',
     ['aplicaci', 'app1', ' app ', 'defender', 'exploit', 'asr', 'win32', 'msi',
      'lob', 'antivirus', 'protecci', 'firewall', 'cifrado', 'bitlocker', 'seguridad de windows']),
    ('Administración de dispositivos con Intune',
     ['intune', 'cumplimiento', 'compliance', 'perfil de configuraci', 'inscripci',
      'enrollment', 'mdm', 'mam', 'dispositivo', 'kiosco', 'vpn', 'wifi', 'wi-fi',
      'restriccion', 'endpoint manager']),
]

def tag(s):
    t = s.lower()
    best, bestn = 'Administración de dispositivos con Intune', 0
    for name, kws in TEMAS:
        n = sum(t.count(k) for k in kws)
        if n > bestn:
            best, bestn = name, n
    return best

for e in q:
    e['stem'] = clean_stem(e['stem'])
    e['tema'] = tag(e['stem'])
    # normalizar clave de imagenes
    if 'answer_images' not in e:
        e['answer_images'] = []
    if 'context_images' not in e:
        e['context_images'] = []
    if 'options' not in e:
        e['options'] = []
    if 'correct' not in e:
        e['correct'] = []

json.dump(q, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

from collections import Counter
print('temas:', dict(Counter(e['tema'] for e in q)))
print('OK, preguntas:', len(q))
