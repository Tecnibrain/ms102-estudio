# -*- coding: utf-8 -*-
"""Repara texto OCR de data/interactivas.json: l->I, palabras pegadas, espacios."""
import json, re, sys
from difflib import SequenceMatcher

VOCAB = """the a an and or of to in for on with from by not none all only both neither
is are was were be can cannot must should will would may
image images device devices computer computers user users group groups app apps
application applications policy policies profile profiles setting settings feature features
update updates upgrade install installed enroll enrolled enrollment join joined joins
register registered registration configure configured configuration deploy deployment
windows microsoft intune entra azure defender endpoint endpoints autopilot
compliance compliant conditional access security account protection encryption
disk attack surface reduction detection response quality version edition enterprise
pro business standard client task sequence share driver drivers folder file files
csv name key days day hours hour minutes time date server share network
management admin center portal console tool tools store business select selected
onboarding advanced tenant subscription license licenses assign assigned assignment
remote desktop session gateway firewall bitlocker recovery reset wipe retire
run running create created delete removed remove add added modify modified
data protection scope tag tags ring rings channel target targeted mode kiosk
shared multi single sign log logs audit report reports analytics warehouse
number required information serial hardware hash mac address enable enabled
disable disabled available start startup restart deadline grace period status
company portal line business lob win32 msi appx msix intunewin ipa apk
role administrator administrators helpdesk global local power performance readers
system managed accounts event later into onto within before after during
template templates custom baseline ADMX GPO OMA URI hybrid cloud tunnel
service principal enterprise registration privilege monitored sanctioned
unsanctioned enforce anonymization asset rule collection collector
requires additional hardware before upgraded activated license activate
saves spreadsheet format used automatic new will elevation rules approved
printer printers certificate certificates wifi vpn email exchange sharepoint
teams onedrive edge browser control application guard smartscreen exploit
deferred deferral indefinitely immediately connectors tokens diagnostic diagnostics
multifactor authentication authenticator strength session grant require required
purview export exported hash hardware connector directory active local remote
themselves additional desktop desktops modify modifying prevented create creating
credentials credential pin password passphrase biometric hello windows10 windows11
every minutes hourly daily weekly monthly hour eight three five fifteen thirty
enforced restrictions restriction owners readers operators guests
add-ons addons settings setting collector initiated subscription event forwarding
baseline baselines categories identifiers corporate personal byod
optimization bandwidth cache peer branch delivery
public key pair certificate certificates protocol scep pkcs imported
retained reset cached workspace database analytics
uninstall uninstalled available featured store"""
WORDS = sorted(set(VOCAB.split()), key=len, reverse=True)
WSET = set(WORDS)

LFIX = {'lmage': 'Image', 'lntune': 'Intune', 'lnstall': 'Install', 'lmport': 'Import',
        'lOS': 'iOS', 'lmages': 'Images', 'lmade': 'Image', 'lncluded': 'Included',
        'lidentity': 'Identity', 'lnformation': 'Information',
        'limport': 'Import', 'lmplement': 'Implement', 'lnclude': 'Include',
        'Seauence': 'Sequence', 'seauence': 'sequence', 'Cornorate': 'Corporate',
        'WInaows': 'Windows', 'Reauirements': 'Requirements', 'reauirements': 'requirements',
        'Cateaories': 'Categories', 'cateaories': 'categories', 'Confiaurator': 'Configurator',
        'Deliverv': 'Delivery', 'onfimization': 'optimization', 'Punview': 'Purview',
        'Microsoit': 'Microsoft', 'multitactor': 'multifactor', 'Auinenticator': 'Authenticator', 'onlhe': 'on the', 'Power Bl': 'Power BI',
        'conmgurauomproile': 'configuration profile', 'aevice': 'device'}


def split_run(run):
    """Separa una secuencia pegada de letras usando el vocabulario (greedy)."""
    low = run.lower()
    out, i = [], 0
    while i < len(low):
        hit = None
        for w in WORDS:
            if len(w) >= 2 and low.startswith(w, i):
                hit = w; break
        if hit:
            out.append(run[i:i + len(hit)]); i += len(hit)
        else:
            if out:
                out[-1] += run[i]
            else:
                out = [run[i]]
            i += 1
    # solo aceptar si la mayoría de trozos son palabras conocidas
    good = sum(1 for p in out if p.lower() in WSET)
    if len(out) > 1 and good >= max(2, len(out) - 1):
        return ' '.join(out)
    return run


def fuzzy_word(w):
    """Corrige una palabra desconocida por la más parecida del vocabulario."""
    lw = w.lower()
    if len(lw) < 6 or lw in WSET:
        return w
    best, bw = 0.0, None
    for v in WSET:
        if abs(len(v) - len(lw)) > 2:
            continue
        r = SequenceMatcher(None, lw, v).ratio()
        if r > best:
            best, bw = r, v
    if best >= 0.85 and bw:
        return bw.capitalize() if w[0].isupper() else bw
    return w


CMDLET = re.compile(r'^[A-Z][a-z]+-[A-Za-z0-9]+$')


def repair(t):
    if not t:
        return t
    if any(CMDLET.match(w) for w in t.split()):
        for bad, good in LFIX.items():
            t = re.sub(r'' + bad, good, t)
        return re.sub(r'\s+', ' ', t).strip()
    for bad, good in LFIX.items():
        t = re.sub(r'\b' + bad, good, t)
    t = re.sub(r'([A-Za-z])(\d)', r'\1 \2', t)          # Windows10 -> Windows 10
    t = re.sub(r'(\d)([A-Za-z]{2,})', r'\1 \2', t)      # 10andlater -> 10 andlater
    t = re.sub(r'([a-záéíóúñ])([A-ZÁÉÍÓÚÑ])', r'\1 \2', t)
    t = re.sub(r',(\S)', r', \1', t)
    t = re.sub(r'\.([A-Za-z]{2,})', r'. \1', t)
    # separar secuencias largas de minúsculas pegadas
    t = re.sub(r'[A-Za-z]{7,}', lambda m: split_run(m.group(0)), t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def main():
    P = 'data/interactivas.json'
    d = json.load(open(P, encoding='utf-8'))
    n = 0
    for k, v in d.items():
        for bl in v.get('blanks', []):
            for i, o in enumerate(bl['options']):
                r = repair(o)
                if r != o:
                    bl['options'][i] = r; n += 1
            if bl.get('label'):
                bl['label'] = repair(bl['label'])
        for s in v.get('statements', []):
            s['t'] = repair(s['t'])
    if '--apply' in sys.argv:
        json.dump(d, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f'aplicado: {n} textos reparados')
    else:
        print(f'se repararían {n} textos')


if __name__ == '__main__':
    main()
