"""Weapon Focus choices, labels, and dynamic known-ray display."""
import re

RAY = 'weapon:ray'
GRAPPLE = 'weapon:grapple'
UNARMED = 'weapon:unarmed-strike'
FOCUS_FEATS = ('weapon-focus', 'greater-weapon-focus', 'weapon-specialization', 'greater-weapon-specialization')


def spell_attack_profile(spell):
    """Classify from the Effect field only; preserve the source text separately."""
    if re.search(r'\brays?\b', spell['target'].get('effect') or '', re.I):
        return {'kind': 'ray', 'weaponFocusChoiceId': RAY}
    return None


def special_choices():
    return {UNARMED: {'name': 'Unarmed Strike', 'kind': 'unarmed'},
            GRAPPLE: {'name': 'Grapple', 'kind': 'grapple'},
            RAY: {'name': 'Ray', 'kind': 'ray', 'requiresSpellcasterClassLevel': 1}}


def weapon_focus_choices(core, proficiencies, class_levels):
    items = core['inventory']['itemsById']
    choices = {key: items[key]['name'] for key in proficiencies
               if key in items and items[key]['kind'] == 'weapon'}
    caster_level = max((class_levels.get(c['id'], 0) for c in core['progression']['classes']
                        if c.get('spellcasting', {}).get('source') == 'own'), default=0)
    special = core['feats']['byId']['weapon-focus']['selection']['specialWeaponChoices']
    choices.update({key: option['name'] for key, option in special.items()
                    if caster_level >= option.get('requiresSpellcasterClassLevel', 0)})
    return [dict(weaponId=key, name=name) for key, name in sorted(choices.items(), key=lambda pair: pair[1].casefold())]


def weapon_focus_grants(core, feat_choices):
    items = core['inventory']['itemsById']
    special = core['feats']['byId']['weapon-focus']['selection']['specialWeaponChoices']
    grants = {}
    for feat in feat_choices:
        feat_id = feat['featId']
        if feat_id not in FOCUS_FEATS:
            continue
        key = feat.get('choices', {}).get('weaponId')
        if key not in special and (key not in items or items[key]['kind'] != 'weapon'):
            raise ValueError('Weapon Focus requires a valid weaponId')
        name = special[key]['name'] if key in special else items[key]['name']
        grants[feat_id, key] = dict(featId=feat_id, weaponId=key, name=name,
                                    label=f"{core['feats']['byId'][feat_id]['name'].title()}, {name}")
    return sorted(grants.values(), key=lambda grant: grant['name'].casefold())


def known_spell_entries(core, known_spell_levels, ray_bonus, *, ray_damage_bonus=0, feat_choices=()):
    from .spell_focus import focus_bonus

    mastered = {key for pick in feat_choices if pick['featId'] == 'spell-mastery'
                for key in pick.get('choices', {}).get('spellIds', ())}
    entries = []
    for spell in core['magic']['spells']:
        if spell['id'] not in known_spell_levels:
            continue
        entry = dict(spellId=spell['id'], name=spell['name'], level=known_spell_levels[spell['id']])
        if (spell.get('attackProfile') or {}).get('weaponFocusChoiceId') == RAY:
            if ray_bonus:
                entry['weaponFocusAttackBonus'] = ray_bonus
            if ray_damage_bonus:
                entry['weaponSpecializationDamageBonus'] = ray_damage_bonus
        if spell['id'] in mastered:
            entry['wizardSpellMastery'] = True
        bonus = focus_bonus(core, spell, feat_choices)
        if bonus and spell['savingThrow']['raw'].strip().lower() not in ('none', '—', '-'):
            entry['spellFocusSaveDcBonus'] = bonus
        entries.append(entry)
    return sorted(entries, key=lambda entry: (entry['level'], entry['name']))
