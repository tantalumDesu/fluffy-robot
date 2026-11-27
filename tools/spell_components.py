"""Generated component facts and per-cast checks against confirmed actor state."""
import re


if __package__:
    from .condition_rules import condition_policies
else:
    from condition_rules import condition_policies

def component_profile(spell):
    components = spell['components']
    codes = list(dict.fromkeys(row['code'] for row in components['codes']))
    text = spell['longDescription']
    material = [p for p in re.split(r'\n\s*\n', text) if re.search(r'\bmaterial components?\b', p, re.I)]
    if spell['id'] == 'binding':
        material.extend(p for p in text.split('\n\n') if p.startswith('In addition to the specially made props'))
    named = [p for p in material if re.match(r'(?:[\w /-]+ )?material components?\s*:', p, re.I)]
    priced = [p for p in material if re.search(r'\b\d[\d,.]*\s*(?:gp|sp|cp)\b', p, re.I)]
    amounts = {(amount.replace(',', ''), unit.lower()) for p in priced for amount, unit in
               re.findall(r'\b(\d[\d,.]*)\s*(gp|sp|cp)\b', p, re.I)}
    return dict(codes=codes, divineAlternatives=re.findall(r'\b(M|F)\s*/\s*DF\b', components['raw']),
                material=dict(kind='priced' if priced else 'unpriced',
                              requiresActualItem=bool(priced),
                              **({'itemText': named} if named else {}),
                              **({'costText': priced, 'statedAmounts': [dict(amount=amount, unit=unit) for amount, unit in sorted(amounts)]} if priced else {})) if 'M' in codes else None)


def component_rules(lines, source):
    line = lines('RULES.txt').index('SPELL COMPONENT ACCESS') + 1
    return dict(source=source('RULES.txt', line=line), pouchItemId='gear:spell-component-pouch', eschewFeatId='eschew-materials',
                holySymbolItemIds=['gear:holy-symbol-silver', 'gear:holy-symbol-wooden'],
                natureFocusItemIds=['gear:holly', 'gear:mistletoe'],
                focusKindByClassId={**dict.fromkeys(('cleric', 'paladin', 'blackguard'), 'holy-symbol'),
                                    **dict.fromkeys(('druid', 'ranger'), 'nature')},
                silenceSpellId='silence', deafenedConditionId='deafened',
                holyWeaponChoiceClassId='cleric', holyWeaponChoiceClassLevel=1)


def annotate_divine_focus_items(items, rules):
    for kind, keys in (('holy-symbol', rules['holySymbolItemIds']), ('nature', rules['natureFocusItemIds'])):
        for key in keys:
            items[key]['divineFocus'] = dict(kind=kind, requiresEquipped=False, source=rules['source'])


def divine_focus_profile(core, item_id, holy_weapon_id=None):
    """A selected deity weapon inherits focus typing for this actor, not globally."""
    item = core['inventory']['itemsById'].get(item_id, {})
    if item_id == holy_weapon_id and item.get('kind') == 'weapon':
        return dict(kind='holy-symbol', requiresEquipped=True, via='deity-weapon')
    return item.get('divineFocus')


def choose_cleric_holy_weapon(core, weapon_id, *, cleric_class_level, deity_weapon_id, existing_choice=None):
    rule = core['magic']['componentRules']
    if existing_choice is not None or type(cleric_class_level) is not int or cleric_class_level != rule['holyWeaponChoiceClassLevel']:
        raise ValueError('Holy weapon can only be designated at first Cleric level and cannot change')
    if weapon_id != deity_weapon_id or core['inventory']['itemsById'].get(weapon_id, {}).get('kind') != 'weapon':
        raise ValueError('Choose the confirmed deity weapon type')
    return weapon_id


def effective_codes(profile, tradition):
    codes = list(profile['codes'])
    alternatives = profile['divineAlternatives']
    if alternatives:
        if tradition == 'divine':
            codes = [code for code in codes if code not in alternatives]
        else:
            codes = [code for code in codes if code != 'DF']
    return codes


def check_components(core, spell, class_id, codes, owned_feats, context, *, spell_level):
    """Check only confirmed facts; a chance is returned for table resolution."""
    if context is None:
        return dict(status='not-checked', blockedReasons=[], failureChancePercent=None)
    rule = core['magic']['componentRules']
    equipped, accessible = (set(context.get(key, ())) for key in ('equippedItemIds', 'accessibleItemIds'))
    accessible |= equipped
    conditions = set(context.get('conditionIds', ()))
    policies = condition_policies(core)
    flags = set(context.get('conditionFlags', ())) | {flag for key in conditions for flag in policies.get(key, {}).get('flags', ())}
    blocked = []
    if flags & {'no-actions', 'mental-actions-only', 'attention-only', 'single-move-only'}:
        blocked.append('condition-prevents-casting')
    if 'V' in codes and (context.get('silenced') or rule['silenceSpellId'] in context.get('activeSpellIds', ())):
        blocked.append('verbal-blocked-by-silence')
    if 'S' in codes and context.get('hasFreeSomaticHand') is False:
        blocked.append('somatic-hand-unavailable')
    if 'M' in codes:
        material = spell['componentProfile']['material']
        if material['requiresActualItem']:
            confirmed = set(context.get('accessibleMaterialSpellIds', ())) | set(context.get('accessiblePricedMaterialSpellIds', ()))
            if spell['id'] not in confirmed:
                blocked.append('priced-material-unavailable')
        elif rule['pouchItemId'] not in equipped and rule['eschewFeatId'] not in owned_feats:
            blocked.append('equipped-component-pouch-required')
    if 'F' in codes and rule['pouchItemId'] not in accessible:
        blocked.append('accessible-component-pouch-required')
    if 'DF' in codes:
        kind = rule['focusKindByClassId'].get(class_id)
        focus_items = [(key, divine_focus_profile(core, key, context.get('holyWeaponId'))) for key in accessible]
        available = any(profile and profile['kind'] == kind and
                        (not profile['requiresEquipped'] or key in equipped) for key, profile in focus_items)
        if not (available or (kind is None and context.get('divineFocusConfirmed'))):
            blocked.append('divine-focus-unavailable')
    chance = 0
    if 'V' in codes and rule['deafenedConditionId'] in conditions:
        deafness = policies[rule['deafenedConditionId']]['operations']
        chance = deafness['spellFailure']['chancePercent']
        if context.get('deafnessAdapted'):
            chance //= deafness['adaptation']['numericDivisor']
    concentration = policies['entangled']['operations']['castingCheck'] if 'entangled' in conditions else None
    return dict(concentrationDc=concentration['dcBase'] + spell_level if concentration else None, status='blocked' if blocked else 'ready', blockedReasons=blocked, failureChancePercent=chance)


def resolve_component_cast(plan, *, percentile_roll=None, concentration_total=None):
    """Resolve confirmed deafness and entanglement checks before applying effects."""
    check = plan['componentCheck']
    if check['status'] != 'ready':
        raise ValueError('Casting components must be checked and available')
    chance, dc = check['failureChancePercent'], check.get('concentrationDc')
    if chance and (type(percentile_roll) is not int or not 1 <= percentile_roll <= 100):
        raise ValueError('Supply a percentile roll from 1 to 100')
    if dc is not None and type(concentration_total) is not int:
        raise ValueError('Supply a Concentration check total')
    failed = bool(chance and percentile_roll <= chance or dc is not None and concentration_total < dc)
    return dict(failed=failed, spellToApply=None if failed else plan)
