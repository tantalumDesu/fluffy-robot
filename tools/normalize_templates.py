"""Normalize standalone template stat lines into core-v2 race field shapes."""
if __package__:
    from .template_environment import attach_environment
else:
    from template_environment import attach_environment

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'dnd35_templates.json'
ABILITIES = dict(zip(('Str', 'Dex', 'Con', 'Int', 'Wis', 'Cha'),
                     ('Strength', 'Dexterity', 'Constitution', 'Intelligence', 'Wisdom', 'Charisma')))


# Curated from template-specific text, not inferred from transformation keywords.
# Source indices are zero-based into the owning record's other_effects.
FORM_PROFILES = {
    'half-doppelganger': ('alternate-shapes', [('chosen-humanoid', (0,))]),
    'fetch': ('spirit-separation', [('ghost', (11,))]),
    'pseudonatural': ('appearance', [('grotesque', (2,))]),
    'vampire': ('alternate-shapes', [(f, (11,)) for f in ('bat', 'dire-bat', 'wolf', 'dire-wolf')]
                + [('gaseous', (13, 14))]),
    'savage-vampire': ('alternate-shapes', [('wild-shape-animal', (11,)), ('recovery-animal', (10,))]),
    'shadow-vampire': ('alternate-shapes', [('shadow', (13, 14))]),
    'terror-vampire': ('alternate-shapes', [('gaseous', (11, 12))]),
    'ghost': ('manifestation', [('manifested', (0, 1))]),
    'ghost-brute': ('manifestation', [('manifested', (0, 1))]),
    'sacred-watcher': ('manifestation', [('manifested', (0, 1))]),
    'spirit-animal': ('manifestation', [('manifested', (0, 1))]),
    'suel-lich': ('possession', [('unhosted', (2, 4)), ('possessing-host', (2, 3))]),
    'phantom-greater': ('corporeality', [('corporeal', (2,)), ('incorporeal', (2, 4))]),
    'swarm-shifter': ('alternate-shapes', [
        (name, (*range(6), *rows)) for name, rows in (
            ('bats', (7, 8)), ('beetles', (9, 10)), ('centipedes', (11,)), ('flies', (12,)),
            ('leeches', (13, 14)), ('maggots', (15, 16)), ('body-parts', (17,)), ('rats', (18,)),
            ('sand-or-dirt', (19,)), ('scorpions', (20, 21)), ('spiders', (22, 23)),
        )]),
    'vampire-swarmform': ('alternate-shapes', [('bat-swarm', (0,)), ('rat-swarm', (0,))]),
    'ti-khana': ('alternate-shapes', [('viper', (4,))]),
    'aleax': ('alternate-shapes', [('shapechange-form', (4,))]),
}

CONTEXTUAL_MODES = {
    'phantom-lesser': [('incorporeal-while-moving', 'movement-triggered', 2)],
    'wendigo': [('wind-walk', 'spell-effect-state', 7)],
    'half-nymph': [('awesome-beauty', 'feature-suppression', 2)],
    'entropic-creature': [('negative-energy-aura', 'feature-suppression', 3)],
    'vivacious-creature': [('positive-energy-aura', 'feature-suppression', 4)],
    'vampire-psychic': [('wisdom-drain-aura', 'feature-suppression', 2)],
    'terror-vampire': [('vampiric-repression', 'feature-suppression', 15)],
}


def normalize_forms(catalogue):
    by_id = {entry['id']: entry for entry in catalogue['templates']}
    for entry in by_id.values():
        for field in ('formProfiles', 'formGroupPatch', 'contextualModes'):
            entry.pop(field, None)
    for owner_id, (group, profiles) in FORM_PROFILES.items():
        entry = by_id[owner_id]
        group_id = f'{owner_id}:{group}'
        if owner_id == 'vampire-swarmform':
            group_id = 'vampire:alternate-shapes'
            entry['formGroupPatch'] = dict(groupId=group_id, replacesFormIds=['bat', 'dire-bat', 'wolf', 'dire-wolf'])
        entry['formProfiles'] = [dict(id=name, overrideLayer='activeForm', formGroupId=group_id,
                                      sourceEffectIndexes=list(indices), referenceOnly=True)
                                 for name, indices in profiles]
    for owner_id, modes in CONTEXTUAL_MODES.items():
        by_id[owner_id]['contextualModes'] = [dict(id=name, kind=kind, sourceEffectIndexes=[index], referenceOnly=True)
                                              for name, kind, index in modes]
    for entry in by_id.values():
        for profile in entry.get('formProfiles', []) + entry.get('contextualModes', []):
            if not all(0 <= i < len(entry['other_effects'] or []) for i in profile['sourceEffectIndexes']):
                raise ValueError(f"Invalid form source reference: {entry['id']} / {profile['id']}")
    return catalogue


def normalize(catalogue):
    """Keep source fields intact; return derived data in a separate namespace."""
    catalogue['overrideModel'] = {
        'layerOrder': ['baseCreature', 'persistentTemplate', 'activeForm', 'temporaryEffects'],
        'formSelection': 'one-active-form-per-group',
        'selectionStorage': 'character-state',
    }
    for entry in catalogue['templates']:
        if entry.get('formOf'):
            entry['overrideLayer'] = 'activeForm'
            entry['formGroupId'] = entry['formOf']
        else:
            entry['overrideLayer'] = None if entry.get('listing_only') else 'persistentTemplate'
            entry.pop('formGroupId', None)
        attach_environment(entry)
        entry.pop('typedReferenceEffects', None)
        entry.pop('coreV2Reference', None)
        stats = entry['stats']
        if not stats:
            continue
        fields, source_lines, unsupported = {}, {}, []

        def record(field, value, line, *, many=False):
            if many:
                fields.setdefault(field, []).append(value)
                source_lines.setdefault(field, []).append(line)
            else:
                fields[field] = value
                source_lines[field] = line

        for i, raw in enumerate(stats['raw'].splitlines(), 1):
            text = raw.strip().rstrip('.')
            if match := re.fullmatch(r'(Str|Dex|Con|Int|Wis|Cha)\s+([+–−-]?\d+|—)', text):
                abbr, value = match.groups()
                value = value.replace('–', '-').replace('−', '-')
                fact = dict(ability=ABILITIES[abbr], abbr=abbr)
                if value.startswith(('+', '-')) and stats['parsed'].get(abbr.lower()) == int(value):
                    record('abilityAdjustments', dict(fact, amount=int(value)), i, many=True)
                elif value == '—':
                    unsupported.append(dict(operation='remove', **fact, rawLine=i))
                elif value.isdecimal() and stats['parsed'].get(abbr.lower()) == int(value):
                    unsupported.append(dict(operation='set', **fact, value=int(value), rawLine=i))
            elif match := re.fullmatch(r'Darkvision (\d+)[’\']', text, re.I):
                record('darkvisionFeet', int(match[1]), i)
            elif match := re.fullmatch(r'(Acid|Cold|Electricity|Fire|Sonic) Resistance (\d+)', text, re.I):
                record('energyResistance', dict(damageType=match[1].title(), value=int(match[2])), i, many=True)
            elif match := re.fullmatch(r'Lvl \+(\d+)', text):
                if stats['parsed'].get('level_adjustment') == int(match[1]):
                    record('levelAdjustment', int(match[1]), i)
        if fields or unsupported:
            entry['coreV2Reference'] = dict(effectiveContributions=fields, sourceLines=source_lines,
                                            unsupportedAbilityChanges=unsupported)
    return normalize_forms(catalogue)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify derived data is current without writing')
    args = parser.parse_args()
    original = PATH.read_text()
    updated = json.dumps(normalize(json.loads(original)), ensure_ascii=False, indent=2) + '\n'
    if args.check:
        if original != updated:
            raise SystemExit('Template catalogue normalization is stale; run tools/normalize_templates.py')
    else:
        PATH.write_text(updated)
