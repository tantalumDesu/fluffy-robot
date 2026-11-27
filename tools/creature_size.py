"""Shared size rules for race profiles, loads, and equipment fit."""
from fractions import Fraction


SIZE_HEADING = '5. Table: Creature Size Modifiers (size-modifiers)'
ARMOR_HEADING = 'ARMOR FOR UNUSUAL CREATURES'
DAMAGE_HEADING = 'Table: Tiny and Large Weapon Damage'


def catalogs(lines, table):
    sizes = {}
    for order, (line, (name, combat, grapple, hide, space, reach, biped, quadruped)) in enumerate(table('RULES.txt', SIZE_HEADING)):
        sizes[name.lower()] = dict(order=order, acAndAttack=int(combat), grapple=int(grapple), hide=int(hide),
                                  spaceFt=float(space.removesuffix(' ft.')), reachFt=float(reach.removesuffix(' ft.')),
                                  carryMultipliers={'biped': biped.removeprefix('×'), 'quadruped': quadruped.removeprefix('×')},
                                  source={'file': 'RULES.txt', 'line': line})
    armor_text = lines('ARMOR.txt')
    start = next(i for i, line in enumerate(armor_text) if line.startswith('Size \tCost')) + 1
    armor = {}
    for offset, line in enumerate(armor_text[start:], start + 1):
        if not line.strip():
            break
        name, h_cost, h_weight, other_cost, other_weight, ac = (cell.strip() for cell in line.split('\t'))
        armor[name.lower()] = dict(humanoid={'cost': h_cost[1:], 'weight': h_weight[1:]},
                                   nonhumanoid={'cost': other_cost[1:], 'weight': other_weight[1:]},
                                   armorBonusMultiplier=ac[1:], source={'file': 'ARMOR.txt', 'line': offset})
    damage = {medium: {'tiny': tiny, 'large': large} for _, (medium, tiny, large)
              in table('WEAPONS.txt', DAMAGE_HEADING)}
    if set(sizes) != set(armor) or len(sizes) != 9:
        raise ValueError('Incomplete size lookup')
    return sizes, dict(armorBySize=armor, weaponDamageByMediumDice=damage, weaponPenaltyPerSizeStep=-2,
                       weaponNonproficiencyPenalty=-4, armorRequiresFit=True,
                       fullPlateRefit={'costDice': '2d4', 'multiplierCp': 10000,
                                       'source': {'file': 'ARMOR.txt', 'headingOrLead': 'Full Plate:'}},
                       weaponSource={'file': 'WEAPONS.txt', 'headingOrLead': 'Inappropriately Sized Weapons:'},
                       armorSource={'file': 'ARMOR.txt', 'headingOrLead': ARMOR_HEADING})


def stepped_size(sizes, size_id, steps):
    by_order = {entry['order']: key for key, entry in sizes.items()}
    target = by_order.get(sizes[size_id]['order'] + steps)
    if target is None:
        raise ValueError('Resulting size is outside the catalog')
    return target


def race_size_id(core, race_id):
    """Resolve an explicit size or follow the race's inheritance reference."""
    races = {race['id']: race for race in core['progression']['races']}
    names = {race['name'].casefold(): race['id'] for race in races.values()}
    visited = set()
    while race_id not in visited:
        visited.add(race_id)
        race = races[race_id]
        if 'sizeId' in race:
            return race['sizeId']
        parent = race.get('inherits')
        if not parent or parent.casefold() not in names:
            raise ValueError(f'Race {race_id} needs a source-backed size')
        race_id = names[parent.casefold()]
    raise ValueError('Cyclic race size inheritance')


def size_profile(core, race_id, *, active_effects=()):
    """Return size-derived modifiers only; do not also apply legacy racial size bonuses."""
    race = next(r for r in core['progression']['races'] if r['id'] == race_id)
    size = race_size_id(core, race_id)
    if size is None:
        raise ValueError('Race needs a source-backed size')
    sizes = core['mechanics']['sizeCategoriesById']
    changes = [effect for effect, _ in active_effects if effect['operation'] == 'size-change']
    if changes:
        change = changes[0]
        if any(effect['steps'] != change['steps'] for effect in changes):
            raise ValueError('Resolve opposing size changes before deriving size')
        if change['requiresCreatureType'] != (race['effective'].get('creatureType') or {}).get('type'):
            raise ValueError('Creature type is not eligible for this size change')
        size = stepped_size(sizes, size, change['steps'])
    result = dict(sizes[size], sizeId=size, equipmentSizeSteps=changes[0]['steps'] if changes else 0)
    result['modifiers'] = {stat: dict(id='creature-size:' + stat, operation='modifier', statId=stat,
                                     amount=amount, bonusType='size', stacking='highest-same-type')
                           for stat, amount in (('ac', result['acAndAttack']), ('attack', result['acAndAttack']),
                                                ('grapple', result['grapple']), ('skill:hide', result['hide']))}
    if changes:
        result.update(sizeAbilityAdjustments=change['sizeAbilityAdjustments'],
                      minimumAdjustedAbilityScore=change['minimumAdjustedAbilityScore'],
                      bodyWeightMultiplier=change['bodyWeightMultiplier'])
    if not changes and (reach := race['effective'].get('reach')):
        result.update(spaceFt=reach['space'], reachFt=reach['reach'])
    return result


def size_adjusted_abilities(profile, scores):
    """Apply the active size change once to already race-adjusted ability scores."""
    adjusted = scores.copy()
    for ability, delta in profile.get('sizeAbilityAdjustments', {}).items():
        if scores[ability] is not None:
            adjusted[ability] = max(profile['minimumAdjustedAbilityScore'], scores[ability] + delta)
    return adjusted


def equipment_size(core, profile, manufactured_size, *, affected_by_size_change=False):
    """Pass True only for gear still affected by the confirmed cast."""
    return stepped_size(core['mechanics']['sizeCategoriesById'], manufactured_size,
                        profile['equipmentSizeSteps'] if affected_by_size_change else 0)


def carrying_limits(core, strength, size_id, locomotion='biped', *, explicit=None):
    """Use explicit stat-block limits first. Return exact pound values as Fractions."""
    keys = ('lightLb', 'mediumLb', 'heavyLb')
    if explicit is not None:
        return {key: Fraction(str(explicit[key])) for key in (*keys, 'dragLb') if key in explicit}
    row = next((r for r in core['inventory']['carryingCapacity'] if r['strength'] == strength), None)
    if row is None:
        raise ValueError('Strength outside the sourced carrying table')
    size = core['mechanics']['sizeCategoriesById'][size_id]
    multiplier = Fraction(size['carryMultipliers'][locomotion])
    return {key: Fraction(row[key]) * multiplier for key in keys}


def weapon_fit(core, item, wielder_size, weapon_size, *, proficient):
    """Check wielding and damage for the actual equipment size, not the race's base size."""
    sizes = core['mechanics']['sizeCategoriesById']
    rules = core['inventory']['equipmentSizeRules']
    if item['kind'] != 'weapon':
        raise ValueError('Expected a weapon')
    if item.get('attackProfile', {}).get('kind') == 'equipment-attack':
        return dict(status='needs-review', reason='Resolve the equipped host and its attack rules first')
    intrinsic = item.get('attackProfile', {}).get('kind') == 'intrinsic'
    if intrinsic:
        weapon_size = wielder_size
    delta = sizes[weapon_size]['order'] - sizes[wielder_size]['order']
    effort = ['Light Melee Weapon', 'One-Handed Melee Weapon', 'Two-Handed Melee Weapon']
    category = item['category']
    if not intrinsic and delta and category not in effort:
        return dict(status='needs-review', sizeAttackPenalty=abs(delta) * rules['weaponPenaltyPerSizeStep'],
                    reason='Source does not give a generic handedness rule for this category')
    if category in effort:
        used = effort.index(category) + delta
        if not 0 <= used < len(effort):
            return dict(status='cannot-wield', sizeSteps=delta)
        category = effort[used]
    dice = item['damageDice'].get(weapon_size)
    if dice is None and weapon_size in ('tiny', 'large'):
        parts = [rules['weaponDamageByMediumDice'].get(die, {}).get(weapon_size)
                 for die in item['damageDice']['medium'].split('/')]
        if all(parts):
            dice = '/'.join(parts)
    return dict(status='wieldable', sizeSteps=delta, effectiveCategory=category, damageDice=dice,
                sizeAttackPenalty=abs(delta) * rules['weaponPenaltyPerSizeStep'],
                nonproficiencyPenalty=0 if proficient else rules['weaponNonproficiencyPenalty'])


def armor_fit(core, item, wearer_size, armor_size, *, wearer_shape='humanoid', armor_shape='humanoid',
              fitted_for_wearer=None, effective_armor_size=None):
    """Price and weight a manufactured size; refuse AC until fit is confirmed."""
    if item['kind'] not in ('armor', 'shield'):
        raise ValueError('Expected an armor or shield definition')
    rule = core['inventory']['equipmentSizeRules']['armorBySize'][armor_size]
    shape = rule[armor_shape]
    price = Fraction(str(item['priceCp'])) * Fraction(shape['cost'])
    weight = Fraction(str(item['weightLb'])) * Fraction(shape['weight'])
    effective_size = armor_size if effective_armor_size is None else effective_armor_size
    effective_rule = core['inventory']['equipmentSizeRules']['armorBySize'][effective_size]
    fit = wearer_size == effective_size and wearer_shape == armor_shape and fitted_for_wearer is not False
    if item['id'] == 'armor:full-plate':
        fit = fit and fitted_for_wearer is True
    return dict(fits=fit, priceCp=price, manufacturedWeightLb=weight,
                weightLb=weight if effective_size == armor_size else None,
                armorClassBonus=int(item['armorClassBonus'] * Fraction(effective_rule['armorBonusMultiplier'])) if fit else None)
