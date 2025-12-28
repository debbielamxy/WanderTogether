#!/usr/bin/env python3
"""Ensure every profile has a unique first name (first token), matching gender.

Approach:
- Use curated male/female base names and gendered modifiers
- Generate hyphenated first-name variants deterministically (id-based)
- Preserve last names, only replace the first token
"""
import json
from pathlib import Path

JS = Path('simulated_profiles.json')

MALE_BASE = [
  'Liam','Noah','Oliver','Elijah','James','William','Benjamin','Lucas','Henry','Alexander',
  'Mason','Michael','Ethan','Daniel','Jacob','Logan','Jackson','Levi','Sebastian','Mateo',
  'Jack','Owen','Samuel','Matthew','Joseph','David','Wyatt','Carter','Jayden','Luke'
]
FEMALE_BASE = [
  'Olivia','Emma','Ava','Charlotte','Sophia','Amelia','Isabella','Mia','Evelyn','Harper',
  'Camila','Gianna','Abigail','Luna','Ella','Elizabeth','Sofia','Emily','Avery','Mila',
  'Scarlett','Eleanor','Hannah','Grace','Zoey','Penelope','Nora','Riley','Victoria','Lily'
]

MALE_MOD = ['James','Lee','John','Ray','Kai','Jax','Cole','Zane','Reid','Gage','Hale','Rhys','Jude','Knox','Wade','Shane','Troy','Beau','Cruz','Dale','Finn','Grant','Hugh','Paul','Roy']
FEMALE_MOD = ['Rose','Mae','Anne','Lynn','Grace','Hope','Skye','Jade','Belle','Eve','Faith','June','Kay','Leigh','Noor','Pearl','Rae','Sage','Tess','Wren','Zoe','Amy','Gail','Iris','Joy']

def gen_variant(base_list, mod_list, idx):
    base = base_list[idx % len(base_list)]
    mod = mod_list[(idx // len(base_list)) % len(mod_list)]
    return f"{base}-{mod}"

def main():
    data = json.loads(JS.read_text())
    used = set()
    male_idx = 0
    female_idx = 0
    for p in data:
        name = p.get('name','').strip()
        parts = name.split()
        last = ' '.join(parts[1:]) if len(parts) > 1 else ''
        g = (p.get('gender') or '').lower()
        if g == 'male':
            # find next unused male variant
            while True:
                fn = gen_variant(MALE_BASE, MALE_MOD, male_idx)
                male_idx += 1
                if fn not in used:
                    used.add(fn)
                    break
        else:
            # default to female
            while True:
                fn = gen_variant(FEMALE_BASE, FEMALE_MOD, female_idx)
                female_idx += 1
                if fn not in used:
                    used.add(fn)
                    break
        p['name'] = (fn + (' ' + last if last else '')).strip()
    JS.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print('Updated', len(data), 'profiles. Sample:')
    for p in data[:12]:
        print(p['id'], p['name'], p.get('gender'))

if __name__ == '__main__':
    main()
