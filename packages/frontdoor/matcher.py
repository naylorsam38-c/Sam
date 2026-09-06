#!/usr/bin/env python3
"""Design 3 front-door matcher. Catalogue is the only build vocabulary."""
import re
from dataclasses import dataclass, asdict
import catalogue as cat

THRESHOLD = 1.5

@dataclass
class Proposal:
    text: str
    matches: list
    not_on_shelf: list
    open_items: list

    def as_dict(self):
        return asdict(self)

def _tokens(text):
    stop = {
        "a","an","the","and","or","to","for","of","in","on","with","my","our","i","need","want",
        "something","thing","app","system","people","what","how","who","can","we","it","is","are",
        "do","does","this","that","each","their","them","they","be","as","from","at","by","after","before"
    }
    return {t for t in re.findall(r"[a-z0-9][a-z0-9'’-]*", (text or '').lower()) if t not in stop and len(t)>2} | {t[:-1] for t in re.findall(r"[a-z0-9][a-z0-9'’-]*", (text or '').lower()) if t.endswith("s") and len(t)>3}

def _score(text, card):
    raw=(text or '').lower(); toks=_tokens(raw); score=0.0; hits=[]
    for phrase in card.get('sounds_like',[]):
        pt=_tokens(phrase)
        if ' ' in phrase and phrase.lower() in raw:
            score += 4.0; hits.append(phrase)
        elif len(pt)==1 and pt <= toks:
            score += 3.0; hits.extend(pt)
    for phrase in card.get('records',[]):
        pt=_tokens(phrase)
        overlap=pt & toks
        if overlap:
            score += 2.0 * min(len(overlap),2); hits.extend(overlap)
    for phrase in card.get('you_get',[]):
        pt=_tokens(phrase); overlap=pt & toks
        if overlap:
            score += 0.75 * min(len(overlap),2); hits.extend(overlap)
    return round(score,3), sorted(set(hits))

def match(text):
    text = (text or '').strip()
    raw = text.lower()
    gaps = []
    for g in cat.NOT_ON_THE_SHELF:
        if any(p.lower() in raw for p in g.get('they_say', [])):
            gaps.append({'id': g['id'], 'plain': g['plain'], 'why': g['why'], 'instead': g['instead']})
    ranked = []
    for c in cat.CAPABILITIES:
        score, hits = _score(text, c)
        sound = any((phrase.lower() in raw if ' ' in phrase else phrase.lower() in _tokens(text))
                    for phrase in c.get('sounds_like', []))
        meaningful = len(set(hits) & _tokens(' '.join(c.get('records', []) + c.get('you_get', []))))
        if score >= THRESHOLD and (sound or score >= 5.0):
            ranked.append({'id': c['id'], 'name': c['name'], 'template': c['template'],
                           'score': score, 'hits': hits, 'one_line': c['one_line']})
    ranked.sort(key=lambda x: (-x['score'], x['id']))
    # Keep every card above threshold; the first combination is the best-ranked composition.
    picked = ranked[:3]
    open_items = [
        {'id': 'who', 'kind': 'choice', 'label': 'Who uses it?',
         'help': 'I will not guess who the people using this are.'},
        {'id': 'density', 'kind': 'choice', 'label': 'How much on screen at once?',
         'help': 'I will not guess how dense you like a screen.'},
        {'id': 'mark', 'kind': 'choice', 'label': 'Your mark',
         'help': 'Goes in the top corner of every screen -- I will not guess your brand.'},
        {'id': 'must_not', 'kind': 'text', 'label': 'Anything it must NOT do?',
         'help': 'Say “nothing” if there are no exclusions.'},
    ]
    if len(picked) > 1:
        supers = []
        import json, os
        here = os.path.dirname(os.path.abspath(__file__))
        templates = os.path.join(here, '..', 'requirements-engine', 'templates')
        for p in picked:
            t = json.load(open(os.path.join(templates, p['template'] + '.json'), encoding='utf-8'))
            if t.get('super_role') and t['super_role'] not in supers:
                supers.append(t['super_role'])
        if len(supers) > 1:
            open_items.insert(1, {'id': 'boss', 'kind': 'choice', 'label': 'Who is in charge?',
                                  'help': 'The selected pieces each bring a person in charge, so I need the tie-break.'})
    return Proposal(text, picked, gaps, open_items)
