"""Natural weapon types shared by racial, creature and transformation rosters."""
import re

TYPES = {
    'bite': ('bludgeoning', 'piercing', 'slashing'),
    'claw': ('piercing', 'slashing'), 'talon': ('piercing', 'slashing'),
    'gore': ('piercing',), 'slam': ('bludgeoning',), 'hoof': ('bludgeoning',),
    'stamp': ('bludgeoning',), 'tail-slap': ('bludgeoning',),
    'arm': ('bludgeoning',), 'tentacle': ('bludgeoning',), 'sting': ('piercing',),
    'quill': ('piercing',), 'rake': ('piercing', 'slashing'), 'wing': ('bludgeoning',),
}
ALIASES = {'quills': 'quill', 'claws': 'claw', 'foreclaws': 'claw', 'talons': 'talon', 'hooves': 'hoof',
           'stamps': 'stamp', 'arms': 'arm', 'tentacles': 'tentacle', 'tail slap': 'tail-slap'}
FEAT = 'improved-natural-attack'


def catalog():
    progressions = ('1 1d2 1d3 1d4 1d6 1d8 2d6 3d6 4d6 6d6 8d6 12d6',
                    '1d10 2d8 3d8 4d8 6d8 8d8 12d8')
    steps = {a: b for seq in progressions for a, b in zip(seq.split(), seq.split()[1:])}
    steps.update({'2d4': '2d6', '1d12': '3d6'})
    return dict(typesById={key: dict(name=key.replace('-', ' ').title(), damageTypes=list(types))
                           for key, types in TYPES.items()}, improvedDamageDiceByDice=steps)


def weapon(name, damage, *, count=1, damage_types=None, **details):
    key = ALIASES.get(name.lower(), name.lower())
    if key not in TYPES:
        raise ValueError(f'Unknown natural weapon type: {name}')
    dice = re.match(r'\d+(?:d\d+)?', damage)
    return dict(kind='natural-weapon', naturalAttackId=key, name=name, count=count,
                damageDice=dice[0] if dice else None, damageText=damage,
                damageTypes=list(TYPES[key] if damage_types is None else damage_types), **details)


def creature_roster(text):
    """Extract named natural attacks; keep the source routine and its alternatives."""
    rows = [line.strip() for line in text.splitlines()]
    routine = next((value for label, value in zip(rows, rows[1:]) if label == 'Full Attack'), '')
    names = '|'.join(re.escape(key) for key in sorted(TYPES.keys() | ALIASES.keys(), key=len, reverse=True))
    pattern = rf'(?:^|(?<=\s))(?:(\d+(?:d\d+)?)\s+)?({names})\s+([+−–-]\d+)\s+(melee|ranged)\*?\s*\(([^)]+)\)'
    return [weapon(name, damage, count=(count if "d" in count else int(count or 1)), attackBonus=int(bonus.replace('−', '-').replace('–', '-')),
                   attackMode=mode.lower(), routineText=routine)
            for count, name, bonus, mode, damage in re.findall(pattern, routine, re.I)]


def pounce_roster(text):
    """Rake is two extra claws after a confirmed pounce (a charge)."""
    if not re.search(r'^Pounce \(Ex\):.*\btwo rake attacks\b', text, re.M | re.I):
        return []
    rake = re.search(r'^Rake \(Ex\): Attack bonus ([+−–-]\d+) melee, damage ([^\s.]+)', text, re.M | re.I)
    if rake is None:
        return []
    bonus, damage = rake.groups()
    return [weapon('claw', damage, count=2, attackBonus=int(bonus.replace('−', '-').replace('–', '-')),
                   attackMode='melee', attackLabel='Rake', requiresConfirmedPounce=True)]


def selection_ids(*rosters):
    return {entry['naturalAttackId'] for roster in rosters for entry in roster}


def owned_types(feats):
    return {p.get('choices', {}).get('naturalAttackId') for p in feats if p.get('featId') == FEAT}


def project(core, roster, feats):
    steps = core['mechanics']['naturalWeapons']['improvedDamageDiceByDice']
    selected = owned_types(feats)
    result = []
    for entry in roster:
        attack = dict(entry)
        if attack['naturalAttackId'] in selected:
            base = attack['damageDice']
            attack['baseDamageDice'] = base
            if base not in steps:
                attack['needsReview'] = 'Confirm the Improved Natural Attack damage step for these base dice.'
            else:
                attack['damageDice'] = steps[base]
                attack['damageText'] = steps[base] + entry['damageText'][len(base):]
        result.append(attack)
    return result


def form_roster(core, form_id, custom_forms=None):
    if form_id in (custom_forms or {}):
        return [entry for entry in custom_forms[form_id] if not entry.get('requiresConfirmedPounce')]
    return core['companions']['creaturesById'][form_id]['naturalWeapons']


def form_pounce_roster(core, form_id, custom_forms=None):
    if form_id in (custom_forms or {}):
        return [entry for entry in custom_forms[form_id] if entry.get('requiresConfirmedPounce')]
    return core['companions']['creaturesById'][form_id].get('pounceNaturalWeapons', ())
