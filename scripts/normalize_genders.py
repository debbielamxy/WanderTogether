#!/usr/bin/env python3
"""Normalize gender values in simulated_profiles.json to only 'male' or 'female'.

Mapping rule for any non 'male'/'female' value: use id parity (even -> male, odd -> female)
to preserve determinism.
"""
import json
from pathlib import Path

JS = Path('simulated_profiles.json')

def normalize_gender(g, pid):
    if not g:
        return 'male' if pid % 2 == 0 else 'female'
    g = str(g).strip().lower()
    if g in ('male','m'):
        return 'male'
    if g in ('female','f'):
        return 'female'
    # fallback deterministic mapping
    return 'male' if pid % 2 == 0 else 'female'

def main():
    data = json.loads(JS.read_text())
    before = {}
    for p in data:
        before.setdefault(p.get('gender'),0)
        before[p.get('gender')] += 1
    for p in data:
        p['gender'] = normalize_gender(p.get('gender'), p.get('id',0) or 0)
    after = {}
    for p in data:
        after.setdefault(p.get('gender'),0)
        after[p.get('gender')] += 1
    JS.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print('Before:', before)
    print('After:', after)
    print('Sample:')
    for p in data[:10]:
        print(p['id'], p['name'], p['gender'])

if __name__ == '__main__':
    main()
