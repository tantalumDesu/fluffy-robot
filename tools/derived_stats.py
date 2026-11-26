"""Compose an actor's size, build, equipped gear and active effects into sheet totals."""
from fractions import Fraction

from .companion_sheet import project_companion
from .alignment import weapon_alignment_tags
from .damage_reduction import project_damage_reduction
from .creature_size import armor_fit, carrying_limits, equipment_size, size_adjusted_abilities, size_profile, weapon_fit
from .locked_gauntlet import ITEM_ID as LOCKED_GAUNTLET_ID, project_gauntlets
from .negative_levels import summarize_negative_levels, weapon_negative_levels
from .sheet_effects import modifier_total


def expand_conditions(policies, condition_ids):
    conditions = set(condition_ids)
    while True:
        expanded = conditions | {child for key in conditions
                                 for child in policies.get(key, {}).get('operations', {}).get('implies', [])}
        if expanded == conditions:
            break
        conditions = expanded
    return conditions - {other for key in conditions
                         for other in policies.get(key, {}).get('operations', {}).get('supersedes', [])}


def condition_state(core, condition_ids):
    policies = core['effects']['sheetConditionRulesById']
    flags, modifiers, review = set(), [], []
    for key in sorted(expand_conditions(policies, condition_ids)):
        rule = policies.get(key)
        if rule is None:
            review.append(key)
            continue
        flags.update(rule['flags'])
        modifiers.extend(rule['modifiers'])
    return flags, modifiers, review


def derive_sheet(core, history, race_id, scores, *, equipment=(), active_effects=(), condition_ids=(),
                 negative_levels=(), alignment_id=None, carried_weight_lb=None, attack_context=None, skill_ranks=None, damage_reduction_grants=(),
                 companion_links=(), master_max_hp=None):
    """Derive a basic humanoid sheet, without mutating inventory or build history.

    Scores already include racial adjustments; equipped item instances supply
    instanceId, itemId, sizeId and, where relevant, proficiency, fit and held state.
    The caller supplies recursively aggregated listed item weights, not vehicle cargo.
    The sheet adjusts fitted replacement gauntlets against those listed weights.
    """
    race = next(r['effective'] for r in core['progression']['races'] if r['id'] == race_id)
    condition_ids = tuple(condition_ids)
    flags, conditions, review = condition_state(core, condition_ids)
    equipment = list(equipment)
    secured_weapons = {e.get('securedWeaponInstanceId') for e in equipment
                       if e['itemId'] == LOCKED_GAUNTLET_ID}
    dropped = [item['instanceId'] for item in equipment if item.get('held') and 'drop-held' in flags
               and item['instanceId'] not in secured_weapons]
    if 'drop-held' in flags and secured_weapons - {None}:
        review.append('adjudicate-drop-secured-weapon')
    equipped = [item for item in equipment if item['instanceId'] not in dropped]
    effects = list(active_effects)
    profile = size_profile(core, race_id, active_effects=effects)
    effects.extend((e, {}) for e in [*profile['modifiers'].values(), *conditions])
    wielded = {item['instanceId']: item['alignmentPropertyIds'] for item in equipped
               if item.get('held') and item.get('alignmentPropertyIds')}
    if wielded and alignment_id is None:
        raise ValueError('Alignment is required to evaluate a wielded aligned weapon')
    levels = list(negative_levels) + (weapon_negative_levels(core, alignment_id, wielded) if wielded else [])
    drain = summarize_negative_levels(core['mechanics']['negativeLevels'], levels, history['characterLevel'])
    effects.extend((effect, {}) for effect in drain['modifiers'])
    skill_ids = {skill['name'].casefold(): skill['id'] for skill in core['skills']['skills']}
    for i, rule in enumerate(race['skillBonuses']):
        if rule['sizeModifier'] or rule['bonusType'] == 'size':
            continue
        if rule.get('qualifier') or any(name.casefold() not in skill_ids for name in rule['skills']):
            review.append('conditional-racial-skill-bonus')
            continue
        for name in rule['skills']:
            effects.append((dict(id=f'racial-skill:{i}:{name}', operation='modifier',
                                 statId='skill:' + skill_ids[name.casefold()], amount=rule['amount'],
                                 bonusType=rule['bonusType'], stacking='highest-same-type'), {}))
    adjusted = size_adjusted_abilities(profile, scores)
    abilities = {key: None if value is None else value + modifier_total('ability:' + key, effects) for key, value in adjusted.items()}
    policies = core['effects']['sheetConditionRulesById']
    active_conditions = expand_conditions(policies, condition_ids)
    for key in sorted(active_conditions):
        for ability, score in policies.get(key, {}).get('operations', {}).get('effectiveScores', {}).items():
            if abilities[ability] is not None:
                abilities[ability] = score
    nonability = core['mechanics']['abilityScoreNonability']
    ability_mod = {key: nonability['modifier'] if value is None else (value - 10) // 2
                   for key, value in abilities.items()}
    limits = (None if abilities['str'] is None else
              dict(lightLb=0, mediumLb=0, heavyLb=0) if abilities['str'] == 0 else
              carrying_limits(core, abilities['str'], profile['sizeId']))
    load_band = None
    load_rules = core['inventory']['encumbranceByBand']
    caps = []
    armor_check = 0
    base_speed = race['speed']['landFeet']
    speed_candidates = [base_speed] if base_speed is not None else []
    dwarf_style = {(kind, band) for rule in race['speed']['exceptions'] for kind in ('load', 'armor')
                   for band in rule.get(kind, [])}
    fits = []
    items = core['inventory']['itemsById']
    weapons = []
    worn_armor = []
    for entry in equipped:
        item = items[entry['itemId']]
        if item['kind'] not in ('weapon', 'armor', 'shield'):
            continue
        manufactured = entry.get('sizeId', 'medium')
        current = equipment_size(core, profile, manufactured, affected_by_size_change=entry.get('resizedBySpell', False))
        if item['kind'] == 'weapon':
            weapons.append((entry, item, current))
            continue
        fit = armor_fit(core, item, profile['sizeId'], manufactured, armor_shape=entry.get('shape', 'humanoid'),
                        wearer_shape=entry.get('wearerShape', 'humanoid'), fitted_for_wearer=entry.get('fitted'),
                        effective_armor_size=current)
        fits.append(dict(instanceId=entry['instanceId'], fits=fit['fits']))
        if not fit['fits']:
            continue
        if item['kind'] == 'armor':
            worn_armor.append(item)
        effects.append((dict(id=entry['instanceId'], operation='modifier', statId='ac', amount=fit['armorClassBonus'],
                             bonusType=item['kind'], stacking='highest-same-type'), {}))
        if item['maxDexBonus'] is not None:
            caps.append(item['maxDexBonus'])
        armor_check += item['armorCheckPenalty'] or 0
        band = item['category'].lower().split()[0]
        reduced = item['speedByBaseFt'].get(str(base_speed))
        if reduced is not None and ('armor', band) not in dwarf_style:
            speed_candidates.append(reduced)
    gauntlets = project_gauntlets(core, equipped, worn_armor)
    disarm_bonuses = {g['securedWeaponInstanceId']: g['disarmDefenseBonus'] for g in gauntlets
                      if g['securedWeaponInstanceId'] is not None}
    weight_adjustment = sum(g['effectiveWeightLb'] - items[LOCKED_GAUNTLET_ID]['weightLb'] for g in gauntlets)
    if carried_weight_lb is not None:
        weight = Fraction(str(carried_weight_lb))
        if weight < 0:
            raise ValueError('Carried weight must not be negative')
        weight += weight_adjustment
        if weight < 0:
            raise ValueError('Carried weight must include listed equipment weights')
        if limits is None:
            review.append('carrying-capacity-without-strength')
        else:
            load_band = next((key for key in ('light', 'medium', 'heavy') if weight <= limits[key + 'Lb']), 'overloaded')
        if load_band == 'overloaded':
            review.append('overloaded-movement')
    load = load_rules.get(load_band, {})
    if 'maxDexBonus' in load:
        caps.append(load['maxDexBonus'])
    if ('load', load_band) not in dwarf_style and str(base_speed) in load.get('speedByBaseFt', {}):
        speed_candidates.append(load['speedByBaseFt'][str(base_speed)])
    natural = (race['naturalArmor'] or {}).get('bonus', 0) + modifier_total('natural-armor', effects)
    effects.append((dict(id='natural-armor-subtotal', operation='modifier', statId='ac', amount=natural,
                         bonusType='natural-armor', stacking='highest-same-type'), {}))
    dex = min([ability_mod['dex'], *caps])
    ac = {}
    context = dict(attack_context or {})
    flags.update(context.get('flags', ()))
    for key, mode, flat in (('normal', None, False), ('touch', 'touch', False),
                            ('flatFooted', None, True), ('incorporealTouch', 'incorporeal-touch', False)):
        ac_flags = flags | ({'denied-dex-to-ac'} if flat else set())
        dex_part = min(0, dex) if 'denied-dex-to-ac' in ac_flags else dex
        other = modifier_total('ac', effects, dict(context, flags=ac_flags, attackMode=mode))
        ac[key] = dict(total=10 + dex_part + other, base=10, dexterity=dex_part, modifiers=other)
    combat = history['classBaseCombat']
    epic = history.get('epicCharacterBonuses') or {}
    racial = race.get('racialHitDice') or {}
    saves = {key: combat[key] + (racial.get('saves') or {}).get(long, 0) + epic.get('saveBonus', 0)
             + ability_mod[ability] + modifier_total('save:' + key, effects)
             for key, long, ability in (('fort', 'fortitude', 'con'), ('ref', 'reflex', 'dex'), ('will', 'will', 'wis'))}
    prone_restriction = core['effects']['sheetConditionRulesById']['prone']['operations']['prohibitedWeaponUse']
    prone = 'prone' in expand_conditions(core['effects']['sheetConditionRulesById'], condition_ids)
    attacks = []
    if not weapons:
        item = items[core['inventory']['fallbackWeaponId']]
        weapons.append(({'instanceId': 'unarmed', 'proficient': True}, item, profile['sizeId']))
    for entry, item, current in weapons:
        line = weapon_fit(core, item, profile['sizeId'], current, proficient=entry.get('proficient', False))
        line.update(instanceId=entry['instanceId'], itemId=item['id'], physicalDamage=item.get('physicalDamage'))
        line['damageBypassTags'] = sorted(set(entry.get('damageBypassTags', ())) |
                                           weapon_alignment_tags(core, entry.get('alignmentPropertyIds', ())))
        if line['status'] == 'wieldable':
            ranged = item['category'] == 'Ranged Weapon' or entry.get('attackKind') == 'ranged'
            kind = 'ranged' if ranged else 'melee'
            blocked = prone and ranged and item['id'] not in prone_restriction['exceptWeaponIds']
            if blocked:
                line['blockedReason'] = 'prone-ranged-weapon-restriction'
            attack_facts = dict(context, weaponId=item['id'], attackKind=kind, flags=flags)
            parts = dict(baseAttack=combat['bab'] + racial.get('babBonus', 0) + epic.get('attackBonus', 0),
                         ability=ability_mod['dex' if ranged else 'str'], sizeFit=line['sizeAttackPenalty'],
                         proficiency=line['nonproficiencyPenalty'], effects=modifier_total('attack', effects, attack_facts))
            line.update(attackKind=kind, attackBonus=sum(parts.values()), breakdown=parts, canAct=not blocked and not flags.intersection({'no-actions', 'mental-actions-only', 'attention-only', 'single-move-only', 'flee-only'}))
        if entry['instanceId'] in disarm_bonuses:
            line['disarmDefenseBonus'] = disarm_bonuses[entry['instanceId']]
        if item['id'] == core['inventory']['fallbackWeaponId'] and gauntlets:
            line['allowsLethalViaGauntlet'] = True
        attacks.append(line)
    check_penalty = min(armor_check, load.get('checkPenalty', 0))
    skills = {}
    for skill in core['skills']['skills']:
        key = skill['id']
        if skill_ranks is None or key not in skill_ranks:
            continue
        ability = (skill.get('keyAbility') or '').lower()
        if ability not in ability_mod:
            continue
        skill_context = dict(context, blindnessPhysicalSkillPenalty=(key != 'search' and ability in ('str', 'dex')
                             and key not in context.get('blindnessSkillExceptions', ())))
        skills[key] = skill_ranks[key] + ability_mod[ability] + modifier_total('skill:' + key, effects, skill_context)
        if skill.get('armorCheckPenalty'):
            skills[key] += check_penalty * (2 if key == 'swim' else 1)
    speed = min(speed_candidates) if speed_candidates else None
    if 'immobile' in flags:
        speed = 0
    elif speed is not None and 'half-speed' in flags:
        speed = Fraction(speed, 2)
    return dict(conditionFlags=sorted(flags), size=profile['sizeId'], reachFt=profile['reachFt'], abilityScores=abilities, abilityModifiers=ability_mod, ac=ac, saves=saves,
                companions=[project_companion(core, history, link, master_max_hp=master_max_hp,
                                              master_skill_ranks=skill_ranks) for link in companion_links],
                attacks=attacks, lockedGauntlets=gauntlets, carriedWeightAdjustmentLb=weight_adjustment, skillTotals=skills, armorFit=fits, loadBand=load_band, carryingLimits=limits,
                landSpeedFt=speed, armorCheckPenalty=check_penalty,
                damageReduction=project_damage_reduction(core, history.get('classLevels', {}), damage_reduction_grants),
                negativeLevels=drain, droppedInstanceIds=dropped, canAct='no-actions' not in flags,
                needsReview=review)
