"""Migrate v1 or refresh source-backed catalogs in v2 (Python standard library)."""
import argparse
from decimal import Decimal
from fractions import Fraction
import json
from pathlib import Path
import re
import unicodedata

if __package__:
    from .progression_rules import progression_rules
    from .sheet_effects import catalogs
else:
    from progression_rules import progression_rules
    from sheet_effects import catalogs

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'dnd-core.json'
GROUPS = {
    'progression': ('classes', 'races'),
    'skills': ('skills', 'synergies'),
    'magic': ('spells', 'spellLists', 'domains'),
    'effects': ('conditions', 'specialAbilities', 'specialAbilityTypes', 'diseases', 'poisons'),
    'mechanics': ('rules', 'listenCheckDCs'),
    'referenceIndexes': ('stats', 'stateChanges'),
}


def slug(text):
    return re.sub(r'[^a-z0-9]+', '-', unicodedata.normalize('NFKD', text).lower()).strip('-')


def lines(file):
    return (ROOT / file).read_text(encoding='utf-8').splitlines()


def source(file, **anchor):
    return {'file': file, **anchor}


def number(text, unit=''):
    text = text.removesuffix(unit).strip().replace(',', '').replace('–', '-').replace('−', '-')
    if re.fullmatch(r'[+-]?\d+(?:[./]\d+)?', text):
        value = Fraction(text)
        return int(value) if value.denominator == 1 else float(value)
    return None


def copper(text):
    match = re.fullmatch(r'([+]?\d[\d,]*(?:\.\d+)?) (gp|sp|cp|pp)', text)
    if match:
        n, unit = match.groups()
        value = Decimal(n.replace(',', '')) * {'gp': 100, 'sp': 10, 'cp': 1, 'pp': 1000}[unit]
        if value == int(value):
            return int(value)
    return None


def index(rows):
    result = {}
    for row in rows:
        key = row['id']
        if key in result:
            raise ValueError(f'Duplicate ID: {key}')
        result[key] = row
    return result


def table(file, heading):
    text = lines(file)
    start = text.index(heading) + 2
    for i in range(start, len(text)):
        if not text[i].strip():
            break
        yield i + 1, [cell.strip() for cell in text[i].split('\t')]


def feats():
    for file in ('FEATS.txt', 'EPIC FEATS.txt'):
        text = lines(file)
        headers = [(i, m) for i, line in enumerate(text) if (m := re.fullmatch(r'([A-Z][A-Z0-9 (),’\'/-]+)\s+\[([^\]]+)\]', line.strip()))]
        for j, (i, match) in enumerate(headers):
            name, category = match.groups()
            end = headers[j + 1][0] if j + 1 < len(headers) else len(text)
            yield dict(id=slug(name), name=name.strip(), category=category, epic=file.startswith('EPIC'),
                       text='\n'.join(text[i + 1:end]).strip(), automation='reference', source=source(file, line=i + 1))


def equipment():
    file = 'MUNDANE ITEMS.txt'
    gear = {}
    for line, row in table(file, 'MUNDANE ITEMS'):
        name, category, price, weight = row
        key = 'gear:' + slug(name)
        if key in gear:
            original = gear[key]
            if original['raw'][1:] != row[1:]:
                raise ValueError(f'Conflicting gear rows: {key}')
            original.setdefault('aliases', []).append({'name': name, 'source': source(file, line=line)})
        else:
            gear[key] = dict(id=key, name=name, kind='gear', category=category, priceCp=copper(price + ' gp'),
                             weightLb=number(weight), source=source(file, line=line), raw=row)
    yield from gear.values()
    file = 'ARMOR.txt'
    for line, row in table(file, 'Table: Armor and Shields'):
        name, cost, ac, dex, check, failure, speed30, speed20, weight, category = row
        yield dict(id='armor:' + slug(name), name=name, kind={'Shield': 'shield', 'Extra': 'armor-extra'}.get(category, 'armor'),
                   category=category, priceCp=copper(cost), weightLb=number(weight, ' lb.'),
                   armorClassBonus=number(ac), maxDexBonus=number(dex), armorCheckPenalty=number(check),
                   arcaneSpellFailurePercent=number(failure, '%'), speedByBaseFt={'30': number(speed30, ' ft.'), '20': number(speed20, ' ft.')},
                   raw=row, source=source(file, line=line),
                   **({'additionForKind': 'armor' if name == 'Armor spikes' else 'shield'}
                      if name in ('Armor spikes', 'Shield spikes') else {}))
    file = 'WEAPONS.txt'
    profiles = {
        'unarmed-strike': {'kind': 'intrinsic', 'fallbackWhenNoWeaponEquipped': True},
        'shield-light': {'kind': 'equipment-attack', 'hostItemIds': ['armor:shield-light-wooden', 'armor:shield-light-steel']},
        'shield-heavy': {'kind': 'equipment-attack', 'hostItemIds': ['armor:shield-heavy-wooden', 'armor:shield-heavy-steel']},
        'spiked-armor': {'kind': 'equipment-attack', 'hostKind': 'armor', 'requiredAdditionId': 'armor:armor-spikes'},
    }
    for size in ('light', 'heavy'):
        profiles['spiked-shield-' + size] = dict(profiles['shield-' + size], requiredAdditionId='armor:shield-spikes')
    for proficiency in ('Simple', 'Martial', 'Exotic'):
        for line, row in table(file, f'Table: {proficiency} Weapons'):
            name, cost, small, medium, critical, range_, weight, damage, category, special = row
            profile = profiles.get(slug(name))
            yield dict(id='weapon:' + slug(name), name=name, kind='ammunition' if category == 'Ammunition' else 'weapon',
                       proficiency=proficiency.lower(), category=category, priceCp=copper(cost), weightLb=number(weight, ' lb.'),
                       damageDice={'small': small, 'medium': medium}, critical=critical, rangeIncrementFt=number(range_, ' ft.'),
                       damageType=damage, special=special, raw=row, source=source(file, line=line),
                       **({'attackProfile': dict(profile, carriedSeparately=False)} if profile else {}))


def advancement(file, keys):
    for i, line in enumerate(lines(file), 1):
        cells = [cell.strip() for cell in line.split('\t')]
        if match := re.fullmatch(r'(\d+)(?:st|nd|rd|th)-(\d+)(?:st|nd|rd|th)', cells[0]):
            assert len(cells) == len(keys) + 2, (file, line)
            yield dict(minEffectiveLevel=int(match[1]), maxEffectiveLevel=int(match[2]),
                       **dict(zip(keys, map(number, cells[1:-1]))), special=cells[-1], source=source(file, line=i))


def creatures():
    for file in ('FAMILIARS.txt', 'ANIMAL COMPANIONS.txt', 'ALTERNATIVE ANIMAL COMPANIONS.txt'):
        text = lines(file)
        minimum, adjustment = 1, 0
        for i, line in enumerate(text):
            if tier := re.fullmatch(r'(\d+)th Level or Higher \(Level (-\d+)\)', line):
                minimum, adjustment = map(int, tier.groups())
            if line != 'Hit Dice' or i < 4:
                continue
            name_index = i - 2
            classification = None
            if text[name_index].startswith('Monster Manual'):
                name_index -= 2
            size_pattern = r'(Fine|Diminutive|Tiny|Small|Medium|Large|Huge|Gargantuan|Colossal)\s'
            if re.match(size_pattern, text[name_index]):
                classification = text[name_index]
                name_index -= 2
            name = text[name_index].strip()
            if not name or text[name_index + 1].strip():
                raise ValueError((file, i + 1, 'Unrecognized stat block'))
            scores = {}
            for j in range(i + 1, len(text) - 1):
                if text[j] == 'Hit Dice':
                    break
                if text[j] in ('STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA'):
                    scores[text[j].lower()] = number(text[j + 1].strip())
                    if len(scores) == 6:
                        break
            yield dict(id=slug(file.removesuffix('.txt')) + ':' + slug(name), name=name,
                       role='familiar' if file == 'FAMILIARS.txt' else 'animal-companion',
                       classification=classification, size=classification.split()[0].lower() if classification else None, hitDiceText=text[i + 1].strip(), abilityScores=scores,
                       minimumMasterLevel=minimum, effectiveLevelAdjustment=adjustment,
                       source=source(file, line=name_index + 1), automation='partial')


def build(old):
    meta = old['meta'].copy()
    if old.get('schemaVersion') == 2:
        groups = {group: {key: old[group][key] for key in keys} for group, keys in GROUPS.items()}
        lookups = old['mechanics']['lookups']
    else:
        groups = {group: {key: old[key] for key in keys} for group, keys in GROUPS.items()}
        assert set(old) == {'meta', *(key for keys in GROUPS.values() for key in keys)}
        lookups = meta.pop('rules')
        meta['legacySchema'] = meta.pop('schema')
        meta['legacyValidation'] = meta.pop('validation')
        meta['legacyCounts'] = meta.pop('counts')
        meta['title'] = 'Fluffy Robot — D&D 3.5 Rules Core'
    meta['placeholders'] = [entry for entry in meta.get('placeholders', [])
                            if entry.get('path') != 'spells[].description']
    meta['schemaNote'] = 'Schema version 2; see README.md for consumer paths and automation coverage.'
    groups['mechanics']['lookups'] = lookups
    generated_rules = progression_rules(lines, table, copper)
    generated_ids = {rule['id'] for rule in generated_rules}
    groups['mechanics']['rules'] = [rule for rule in groups['mechanics']['rules']
                                    if rule['id'] not in generated_ids] + generated_rules
    groups['progression']['ruleIds'] = [rule['id'] for rule in generated_rules]
    spells = []
    for spell in groups['magic']['spells']:
        spell = spell.copy()
        for alias, canonical in (('description', 'longDescription'), ('summary', 'shortDescription')):
            if alias in spell:
                if spell[alias] != spell.get(canonical):
                    raise ValueError(f"Non-duplicate spell field: {spell['id']}.{alias}")
                del spell[alias]
        spells.append(spell)
    groups['magic']['spells'] = spells
    feat_records = index(feats())
    spell_effects, feat_effects = catalogs(spells, feat_records, groups['skills']['skills'])
    groups['effects']['spellEffectsBySpellId'] = spell_effects
    groups['effects']['featEffectsByFeatId'] = feat_effects
    for key in feat_effects:
        feat_records[key]['automation'] = 'partial'
    groups['effects']['applicationPolicy'] = {
        'classEffectsPath': '/progression/classes/*/abilities/*/effects',
        'conditionDefinitionsPath': '/effects/conditions',
        'spellAutomation': 'manual-unless-explicitly-implemented',
        'referencesAreNotGrants': True,
        'persistActiveInstancesOnTarget': True,
    }
    companions = index(creatures())
    items = index(equipment())
    pack = {}
    for name, creature in {'horse-heavy': 'horse-heavy', 'horse-light': 'horse-light', 'pony': 'pony',
                           'donkey-or-mule': None, 'ox': None}.items():
        creature_id = 'animal-companions:' + creature if creature else None
        if creature_id is not None and creature_id not in companions:
            raise ValueError(f'Missing pack animal stat block: {creature_id}')
        item_id = 'gear:' + name
        pack[name] = dict(id=name, purchaseItemId=items[item_id]['id'], creatureId=creature_id,
                          automation='partial' if creature_id else 'reference')
    capacity = []
    for i, line in enumerate(lines('RULES.txt'), 1):
        if re.fullmatch(r'\d+(?:\t\d+ lb\.){3}', line):
            strength, *loads = line.split('\t')
            capacity.append(dict(strength=int(strength), **dict(zip(('lightLb', 'mediumLb', 'heavyLb'),
                                 [number(value, ' lb.') for value in loads])), source=source('RULES.txt', line=i)))
    assert [row['strength'] for row in capacity] == list(range(1, 30))
    return dict(schemaVersion=2, meta=meta, **groups, feats={'byId': feat_records},
                inventory={'itemsById': items, 'fallbackWeaponId': 'weapon:unarmed-strike', 'packAnimalsById': pack, 'carryingCapacity': capacity},
                companions={'creaturesById': companions,
                            'familiarAdvancement': list(advancement('FAMILIARS.txt', ('naturalArmorAdjustment', 'intelligence'))),
                            'animalCompanionAdvancement': list(advancement('ANIMAL COMPANIONS.txt', ('bonusHitDice', 'naturalArmorAdjustment', 'strengthDexterityAdjustment', 'bonusTricks')))},
                positioning={'automation': 'reference', 'sources': [source(f) for f in ('COMBAT STATISTICS.txt', 'COMBAT MODIFIERS.txt', 'ATTACKS OF OPPORTUNITY.txt', 'SPECIAL INITIATIVE ACTIONS.txt', 'INITIATIVE.txt')]},
                rulesets={'defaultId': 'baseline', 'byId': {'baseline': {'id': 'baseline', 'optionIds': []}},
                          'optionsById': {'multiclass-xp-penalty': {'id': 'multiclass-xp-penalty', 'defaultEnabled': False,
                          'automation': 'structured', 'ruleId': 'multiclass-xp-penalty',
                          'source': source('MULTICLASS CHARACTERS.txt', heading='XP FOR MULTICLASS CHARACTERS')}}},
                sources={path.name: {'file': path.name} for path in sorted(ROOT.glob('*.txt'))})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='fail if generated data differs')
    args = parser.parse_args()
    current = PATH.read_bytes()
    result = (json.dumps(build(json.loads(current)), ensure_ascii=False, indent=2) + '\n').replace('\n', '\r\n').encode('utf-8')
    if args.check:
        if current != result:
            parser.exit(1, 'dnd-core.json is out of date\n')
    else:
        PATH.write_bytes(result)


if __name__ == '__main__':
    main()
