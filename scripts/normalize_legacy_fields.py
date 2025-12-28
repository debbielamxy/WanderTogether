#!/usr/bin/env python3
"""Normalize legacy profile fields in simulated_profiles.json.

Currently converts `pace_text` -> numeric `pace` using a deterministic mapping
and removes the legacy key. The script is idempotent and safe to run multiple
times.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / 'simulated_profiles.json'

PACE_MAP = {
    'relaxed_itinerary': 1,
    'packed_itinerary': 2,
    'spontaneous': 3,
    'flexible': 4,
}

def main():
    data = json.loads(JS.read_text())
    found = 0
    for p in data:
        if 'pace_text' in p:
            found += 1
            txt = p.get('pace_text')
            if txt in PACE_MAP:
                p['pace'] = PACE_MAP[txt]
            # remove legacy key to canonicalize
            p.pop('pace_text', None)
    JS.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print('Normalized pace_text entries:', found)

if __name__ == '__main__':
    main()
