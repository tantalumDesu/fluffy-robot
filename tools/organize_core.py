"""Migrate v1 or refresh source-backed catalogs in v2 (Python standard library)."""
import argparse
from decimal import Decimal
from fractions import Fraction
import json
from pathlib import Path
import re
import unicodedata

if __package__:
    from .locked_gauntlet import ITEM_ID as LOCKED_GAUNTLET_ID, locked_gauntlet_rule
    from .damage_types import PHYSICAL, physical_profile
    from .source_text import normalized, spell_sources
    from .effect_policy import POLICY, annotate
    from .condition_cures import catalog as cure_catalog
    from .injury import catalog as injury_catalog
    from .condition_rules import catalog as condition_catalog
    from .alignment import alignment_catalog
    from .creature_size import catalogs as size_catalogs
    from .animal_training import training_rules
    from .feat_selection import encode_feats
    from .negative_levels import negative_level_rules, spell_drain_catalog
    from .pack_animals import beasts
    from .progression_rules import continuity_rules, progression_rules, spell_swap_rules
    from .game_time import SECONDS, casting_timing, duration_timing
    from .spellcasting import metamagic_catalog
    from .sheet_effects import catalogs
else:
    from locked_gauntlet import ITEM_ID as LOCKED_GAUNTLET_ID, locked_gauntlet_rule
    from damage_types import PHYSICAL, physical_profile
    from source_text import normalized, spell_sources
    from effect_policy import POLICY, annotate
    from condition_cures import catalog as cure_catalog
    from injury import catalog as injury_catalog
    from condition_rules import catalog as condition_catalog
    from alignment import alignment_catalog
    from creature_size import catalogs as size_catalogs
    from animal_training import training_rules
    from feat_selection import encode_feats
    from negative_levels import negative_level_rules, spell_drain_catalog
    from pack_animals import beasts
    from progression_rules import continuity_rules, progression_rules, spell_swap_rules
    from game_time import SECONDS, casting_timing, duration_timing
    from spellcasting import metamagic_catalog
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
                       damageType=damage, physicalDamage=physical_profile(damage), special=special, raw=row, source=source(file, line=line),
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
    generated_rules = progression_rules(lines, copper)
    generated_ids = {rule['id'] for rule in generated_rules}
    groups['mechanics']['rules'] = [rule for rule in groups['mechanics']['rules']
                                    if rule['id'] not in generated_ids] + generated_rules
    groups['progression']['ruleIds'] = [rule['id'] for rule in generated_rules]
    swaps = list(spell_swap_rules(lines, groups['progression']['classes']))
    swap_by_class = {rule['appliesTo']['classIds'][0]: rule['id'] for rule in swaps}
    retired_ids = {'spell-replacement', *swap_by_class.values()}
    groups['mechanics']['rules'] = [rule for rule in groups['mechanics']['rules']
                                    if rule['id'] not in retired_ids] + swaps
    classes = []
    for record in groups['progression']['classes']:
        record = record.copy()
        if record['id'] in swap_by_class:
            rule_ids = [rule_id for rule_id in record.get('ruleIds', []) if rule_id not in retired_ids]
            record['ruleIds'] = rule_ids + [swap_by_class[record['id']]]
        classes.append(record)
    continuity = list(continuity_rules(lines))
    continuity_by_class = {rule['appliesTo']['classIds'][0]: rule['id'] for rule in continuity}
    groups['mechanics']['rules'] = [rule for rule in groups['mechanics']['rules']
                                    if rule['id'] not in {'monk-continuous-levels', *continuity_by_class.values()}] + continuity
    for record in classes:
        if 'monk-continuous-levels' in record.get('ruleIds', []):
            record['ruleIds'] = [key for key in record['ruleIds'] if key != 'monk-continuous-levels']
            if not record['ruleIds']:
                del record['ruleIds']
        rule_id = continuity_by_class.get(record['id'])
        if rule_id and rule_id not in record.get('ruleIds', []):
            record['ruleIds'] = [*record.get('ruleIds', []), rule_id]
    groups['progression']['classes'] = classes
    spells = []
    source_spells = spell_sources(lines)
    for spell in groups['magic']['spells']:
        spell = spell.copy()
        for alias, canonical in (('description', 'longDescription'), ('summary', 'shortDescription')):
            if alias in spell:
                if spell[alias] != spell.get(canonical):
                    raise ValueError(f"Non-duplicate spell field: {spell['id']}.{alias}")
                del spell[alias]
        if spell['file'] == 'SPELLBOOK.txt':
            spell['shortDescription'], spell['longDescription'] = source_spells[normalized(spell['name'])]
        spells.append(spell)
    for spell in spells:
        spell['timing'] = dict(casting=casting_timing(spell['castingTime']['raw']),
                               duration=duration_timing(spell['duration']['raw']))
    groups['magic']['spells'] = spells
    feat_rule_id = 'feat-selection-uniqueness'
    groups['mechanics']['rules'] = [rule for rule in groups['mechanics']['rules'] if rule['id'] != feat_rule_id]
    groups['mechanics']['rules'].append(dict(id=feat_rule_id, name='Feat Selection Uniqueness',
        category='feat-selection', status='structured', source=source('RULES.txt', heading='FEAT SELECTION UNIQUENESS'),
        mechanic={'kind': 'feat-selection', 'defaultMaxTakes': 1, 'evaluateAt': 'selection-level',
                  'countGrantedFeats': True, 'unknownPrerequisitePolicy': 'needs-review'}))
    feat_records = encode_feats(index(feats()),
                                table('EPIC FEATS.txt', 'Table: Normal Maximum Spellcasting Prerequisites'))
    groups['magic']['metamagicByFeatId'] = metamagic_catalog(feat_records)
    groups['mechanics']['timing'] = dict(secondsByUnit=SECONDS, source=source('TIMING.txt'),
        regularTurn={'standard': 1, 'move': 1, 'fullRoundReplacesBoth': True},
        surpriseTurn={'standardOrMove': 1}, freeActions='dm-limited')
    groups['magic']['spellRecoveryByClassId'] = {
        class_id: dict(restHours=int(rest), preparationMinutes=int(preparation), scheduledDailyTime=scheduled == 'yes',
                       recentUseHours=8, source=source('TIMING.txt', line=line))
        for line, (class_id, rest, preparation, scheduled) in table('TIMING.txt', 'Table: Spell Recovery Profiles')}
    groups['magic']['dailySlotRules'] = {
        'pools': ['regular', 'domain'], 'progressionBasis': 'effective-spellcasting-class-level',
        'epicBaseSlotCapsByClassId': {class_id: {'level': 20, 'source': source(file, line=line)}
            for class_id in ('bard', 'cleric', 'druid', 'paladin', 'ranger', 'sorcerer', 'wizard')
            for file in ('EPIC ' + class_id.upper() + '.txt',)
            for line, text in enumerate(lines(file), 1)
            if 'number of spells per day does not increase after 20th level' in text},
    }
    spell_effects, feat_effects = catalogs(spells, feat_records, groups['skills']['skills'])
    groups['effects']['spellEffectsBySpellId'] = spell_effects
    groups['effects']['negativeLevelOperationsBySpellId'] = spell_drain_catalog(spells)
    condition_text = lines('CONDITIONS.txt')
    policies = condition_catalog(condition_text)
    conditions = groups['effects']['conditions']
    if set(policies) != {condition['id'] for condition in conditions}:
        raise ValueError('Typed condition catalogue does not match named conditions')
    for position, condition in enumerate(conditions):
        key = condition['id']
        condition['mechanics'] = policies[key]
        start = policies[key]['source']['line'] - 1
        end = policies[conditions[position + 1]['id']]['source']['line'] - 1 if position + 1 < len(conditions) else len(condition_text)
        condition['desc'] = '\n'.join(condition_text[start:end]).split(':', 1)[1].split(
            'Tracking progressive fatigue:', 1)[0].strip()
        if key == 'energy-drained':
            condition['references'].update(inflictedBySpells=['energy-drain', 'enervation'], mentionedInSpells=[])
    groups['effects']['sheetConditionRulesById'] = policies
    cures = cure_catalog()
    if not set(cures) <= {spell['id'] for spell in spells} or any(
            not set(rule['conditionIds']) <= policies.keys() for rule in cures.values()):
        raise ValueError('Unknown spell or condition in cure catalogue')
    groups['effects']['conditionCuresBySpellId'] = cures
    def rule(event, states, to, **extra):
        return dict(event=event, **{'from': states}, to=to, **extra)

    condition_source = lambda title: source('CONDITIONS.txt', line=next(
        i for i, text in enumerate(condition_text, 1) if text.startswith(title)))
    fatigue = ['clear', 'fatigued', 'exhausted']
    fear = ['clear', 'shaken', 'frightened', 'panicked']
    groups['effects']['stateChangesById'] = {
        'fatigue': dict(initial='clear', source=condition_source('Fatigued:'), transitions=[
            rule(event, ['clear'], 'fatigued', origin=origin)
            for event, origin in [('fatigue-applied', 'ordinary'), ('post-rage-fatigue', 'encounter')]
        ] + [rule(event, ['fatigued'], 'exhausted') for event in ('fatigue-applied', 'post-rage-fatigue')] + [
            rule('encounter-ended', ['fatigued'], 'clear', onlyOrigin='encounter'),
            rule('one-hour-complete-rest', ['exhausted'], 'fatigued', origin='ordinary'),
            rule('eight-hours-complete-rest', ['fatigued'], 'clear'),
        ]),
        'fear': dict(initial='clear', source=source('SPECIAL ABILITIES.txt', line=next(
            i for i, text in enumerate(lines('SPECIAL ABILITIES.txt'), 1) if text.startswith('Becoming Even More Fearful:'))),
            transitions=[rule(applied + '-applied', [state], fear[min(3, i + j)])
                         for i, state in enumerate(fear) for j, applied in enumerate(fear) if j]),
        'rage': dict(initial='inactive', source=source('BARBARIAN.txt', line=next(
            i for i, text in enumerate(lines('BARBARIAN.txt'), 1) if text.startswith('Rage (Ex):'))), transitions=[
            rule('rage-started', ['inactive'], 'raging'),
            rule('rage-ended', ['raging'], 'inactive', requires={'tirelessRage': True}),
            rule('rage-ended', ['raging'], 'inactive', requires={'tirelessRage': False}, emit=['post-rage-fatigue']),
        ]),
        'vampire-sunlight': dict(initial='clear', referenceOnly=True,
            source=dict(file='dnd35_templates.json', templateId='vampire', effectIndex=21),
            transitions=[rule('sunlight-entered', ['clear'], 'exposed'),
                         rule('sunlight-left', ['exposed'], 'clear'),
                         rule('next-round-still-exposed', ['exposed'], 'destroyed')],
            statesById={'exposed': {'allowedActionChoice': ['move', 'attack'], 'actionsMaximum': 1}}),
    }
    groups['effects']['featEffectsByFeatId'] = feat_effects
    for key in feat_effects:
        feat_records[key]['automation'] = 'partial'
    for entries in (*spell_effects.values(), *feat_effects.values(),
                    *(rule['modifiers'] for rule in policies.values())):
        annotate(entries)
    groups['effects']['applicationPolicy'] = {
        **POLICY,
        'classEffectsPath': '/progression/classes/*/abilities/*/effects',
        'conditionDefinitionsPath': '/effects/conditions',
        'spellAutomation': 'recipient-sheet-numbers-only',
        'referencesAreNotGrants': True,
        'persistActiveInstancesOnTarget': True,
    }
    size_categories, equipment_size_rules = size_catalogs(lines, table)
    groups['mechanics']['sizeCategoriesById'] = size_categories
    alignments, alignment_consequences = alignment_catalog(lines)
    groups['mechanics']['physicalDamageTypesById'] = {
        key: dict(id=key, name=key.title(), source=source('WEAPONS.txt', line=next(
            i for i, text in enumerate(lines('WEAPONS.txt'), 1) if text.startswith('Type: Weapons'))))
        for key in PHYSICAL}
    groups['mechanics']['injury'] = injury_catalog(lines)
    groups['mechanics']['negativeLevels'] = negative_level_rules(lines)
    groups['mechanics']['alignmentsById'] = alignments
    alignment_weapon_tags = {'Good': 'good', 'Evil': 'evil', 'Lawful': 'law', 'Chaotic': 'chaos'}
    weapon_alignment_properties = {
        slug(name): {'name': name, 'alignmentTag': alignment_weapon_tags[tag],
                     'negativeLevel': {'count': 1, 'target': 'opposed-wielder', 'duration': 'while-wielded',
                                       'permanentDrain': False}, 'source': source('WEAPONS.txt', line=line)}
        for line, (name, tag) in table('WEAPONS.txt', 'Table: Weapon Property Alignments')
    }
    groups['mechanics']['alignmentConsequencesByClassId'] = alignment_consequences
    groups['magic']['alignmentTargetRulesBySpellId'] = {
        'holy-smite': {'unaffectedAxis': 'good', 'opposedAxis': 'evil',
                       'condition': {'conditionId': 'blinded', 'rounds': 1},
                       'source': source('SPELLBOOK.txt', heading='Holy Smite')},
        'unholy-blight': {'unaffectedAxis': 'evil', 'opposedAxis': 'good',
                         'condition': {'conditionId': 'sickened', 'roundDice': '1d4'},
                         'source': source('SPELLBOOK.txt', heading='Unholy Blight')},
    }
    nonability_line = lines('RULES.txt').index('Ability Score Nonabilities') + 2
    groups['mechanics']['abilityScoreNonability'] = dict(
        score=None, modifier=0, appliesScoreAdjustments=False,
        source=source('RULES.txt', line=nonability_line))
    groups['mechanics']['sizeModifierPolicy'] = 'derive-from-current-size-do-not-add-legacy-racial-size-bonuses'

    races = []
    race_text = lines('RACES.txt')
    hobgoblin_start = race_text.index('HOBGOBLIN RACIAL TRAITS')
    hobgoblin_end = race_text.index('HUMAN', hobgoblin_start)
    size_line, size_text = next((i + 1, race_text[i].strip()) for i in range(hobgoblin_start, hobgoblin_end)
                                if race_text[i].strip().startswith('Medium size:'))
    for record in groups['progression']['races']:
        race = record.copy()
        if race['id'] == 'hobgoblin':
            traits = [trait for trait in race['traits'] if trait['id'] != 'hobgoblin-trait-size']
            traits.append(dict(id='hobgoblin-trait-size', index=len(traits) + 1, label='Medium size', text=size_text,
                               mechanics=[{'type': 'size', 'size': 'Medium'}], conditions=[],
                               source=source('RACES.txt', line=size_line)))
            race.update(traits=traits, own=dict(race['own'], size='Medium'),
                        effective=dict(race['effective'], size='Medium'))
        size = race['effective']['size']
        race['sizeId'] = size.lower() if size else None
        races.append(race)
    groups['progression']['races'] = races
    companions = index(dict(creature, sizeId=creature['size']) for creature in [*creatures(), *beasts(lines)])
    groups['skills']['animalTraining'] = training_rules(lines)
    items = index(equipment())
    gauntlet = items[LOCKED_GAUNTLET_ID]
    gauntlet['listedArcaneSpellFailurePercent'] = gauntlet['arcaneSpellFailurePercent']
    gauntlet['arcaneSpellFailurePercent'] = None  # Hand restriction, not a blanket caster penalty.
    gauntlet['lockedGauntlet'] = locked_gauntlet_rule(lines, source)
    for addition, heading in (('armor:armor-spikes', 'Armor Spikes:'), ('armor:shield-spikes', 'Shield Spikes:')):
        line, text = next((i, text) for i, text in enumerate(lines('ARMOR.txt'), 1) if text.startswith(heading))
        if 'piercing' not in text.lower():
            raise ValueError(f'Missing spike damage type: {heading}')
        items[addition]['physicalDamage'] = physical_profile('Piercing')
        items[addition]['physicalDamageSource'] = source('ARMOR.txt', line=line)

    pack = {}
    for name in ('horse-heavy', 'horse-light', 'pony', 'donkey', 'mule', 'ox'):
        creature_id = 'beasts-of-burden:' + name
        item_id = 'gear:' + name
        pack[name] = dict(id=name, purchaseItemId=items[item_id]['id'], creatureId=creature_id,
                          automation='partial', carryingCapacity=companions[creature_id]['carryingCapacity'],
                          initialTraining={'purposeId': None, 'learnedTrickIds': [], 'bonusTrickIds': []})
    vehicle_file = 'PULLED VEHICLES.txt'
    for line, (name, running_gear) in table(vehicle_file, 'Table: Pulled Vehicles'):
        item = items['gear:' + slug(name)]
        if item['category'] != 'Transport':
            raise ValueError(f'Pulled vehicle is not transport: {name}')
        item['pulledVehicle'] = dict(inventoryCarrier='vehicle', runningGear=running_gear,
                                     maxPayloadLb=None, source=source(vehicle_file, line=line))
    vehicle_rules = dict(heavyLoadMultiplier=5, teamAggregation='sum',
                         grossWeightComponents=['empty-vehicle', 'passengers', 'cargo'],
                         defaultTerrainMultiplier=1, terrainMultiplierRange=[0, 1],
                         wheeledGroundAssumption='reasonably-passable',
                         terrainReduction='dm-adjudication', source=source(vehicle_file, heading='PULLED VEHICLES'))
    encumbrance = {}
    for line, text in enumerate(lines('RULES.txt'), 1):
        if match := re.fullmatch(r'- (Medium|Heavy) load: Max Dex \+(\d+), Check Penalty [–-](\d+), Speed (\d+) ft\. \(from 30\) / (\d+) ft\. \(from 20\), Run ×(\d+)\.', text):
            band, dex, penalty, speed30, speed20, run = match.groups()
            encumbrance[band.lower()] = dict(maxDexBonus=int(dex), checkPenalty=-int(penalty),
                speedByBaseFt={'30': int(speed30), '20': int(speed20)}, runMultiplier=int(run),
                source=source('RULES.txt', line=line))
    if set(encumbrance) != {'medium', 'heavy'}:
        raise ValueError('Incomplete encumbrance policies')
    capacity = []
    for i, line in enumerate(lines('RULES.txt'), 1):
        if re.fullmatch(r'\d+(?:\t\d+ lb\.){3}', line):
            strength, *loads = line.split('\t')
            capacity.append(dict(strength=int(strength), **dict(zip(('lightLb', 'mediumLb', 'heavyLb'),
                                 [number(value, ' lb.') for value in loads])), source=source('RULES.txt', line=i)))
    assert [row['strength'] for row in capacity] == list(range(1, 30))
    return dict(schemaVersion=2, meta=meta, **groups, feats={'byId': feat_records},
                inventory={'itemsById': items, 'fallbackWeaponId': 'weapon:unarmed-strike', 'packAnimalsById': pack, 'carryingCapacity': capacity, 'pulledVehicleRules': vehicle_rules, 'equipmentSizeRules': equipment_size_rules, 'encumbranceByBand': encumbrance, 'weaponAlignmentPropertiesById': weapon_alignment_properties},
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
