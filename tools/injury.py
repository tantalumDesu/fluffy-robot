"""Resolve confirmed damage and healing without mutating the base build."""
from copy import deepcopy

if __package__:
    from .damage_types import resolve_physical_types
else:
    from damage_types import resolve_physical_types


def catalog(lines):
    def source(file, heading):
        return {'file': file, 'line': next(i for i, text in enumerate(lines(file), 1) if text.startswith(heading))}

    return dict(deadAtHp=-10, disabledAtHp=0, massiveDamage={'threshold': 50, 'fortitudeDc': 15,
                'singleAttackOnly': True, 'basis': 'before-temporary-hp', 'source': source('INJURY AND DEATH.txt', 'Massive Damage:')},
                stabilization={'healCheckDc': 15, 'trigger': 'end-round', 'chancePercent': 10, 'failureHpLoss': 1, 'source': source('INJURY AND DEATH.txt', 'STABLE CHARACTERS')},
                defenses={'damageReduction': 'best-applicable-shared-per-round',
                          'energyResistance': 'highest-nonstacking-per-energy-type-per-round', 'temporaryHp': 'absorb-before-hp',
                          'source': source('SPECIAL ABILITIES.txt', 'DAMAGE REDUCTION')},
                critical={'extraDiceMultiply': False, 'rollWeaponDamageSeparately': True,
                          'source': source('COMBAT STATISTICS.txt', 'Multiplying Damage:')},
                nonlethal={'storedSeparately': True, 'magicalHealingAlsoReducesNonlethal': True,
                           'source': source('INJURY AND DEATH.txt', 'NONLETHAL DAMAGE')})


def condition_ids(core, state):
    rules = core['mechanics']['injury']
    hp, nonlethal = state['hp'], state.get('nonlethal', 0)
    if state.get('dead') or hp <= rules['deadAtHp']:
        return ['dead']
    if hp < 0:
        return ['disabled'] if state.get('consciousBelowZero') else ['stable' if state.get('stable') else 'dying']
    if nonlethal > hp:
        return ['unconscious']
    if hp == rules['disabledAtHp']:
        return ['disabled']
    return ['staggered'] if nonlethal == hp else []


def grant_energy_protection(core, state, caster_level, now):
    """Apply one confirmed Protection from Energy cast with a shared pool."""
    if type(caster_level) is not int or caster_level < 1 or type(now) is not int or now < 0:
        raise ValueError('Supply a positive caster level and valid game time')
    rule = core['effects']['spellEffectsBySpellId']['protection-from-energy'][0]
    result = deepcopy(state)
    result['energyProtection'] = dict(remaining=min(rule['maximumPoints'], rule['pointsPerCasterLevel'] * caster_level),
                                      expiresAtSeconds=now + 60 * rule['duration']['perCasterLevel'] * caster_level)
    return result


def resolve_sheet_damage(core, state, defender_sheet, *, attack=None, physical_profile=None,
                         bypass_tags=(), **damage):
    """Apply confirmed rolled damage to actor HP using projected defenses and attack facts."""
    attack = attack or {}
    profile = physical_profile if physical_profile is not None else attack.get('physicalDamage')
    return resolve_damage(core, state, damage_reduction=defender_sheet['damageReduction'],
                          physical_profile=profile,
                          bypass_tags=set(bypass_tags) | set(attack.get('damageBypassTags', ())), **damage)


def resolve_damage(core, state, *, weapon=0, energy=None, nonlethal=False, bypass_tags=(),
                   damage_reduction=(), energy_resistance=None, ignores_dr=False, single_attack=True,
                   massive_save_total=None, round_id=None, dm_damage_override=None, now=None,
                   physical_profile=None, physical_choice=None, physical_immunities=()):
    """Consume already-rolled amounts. Pass full resistance ratings and a unique encounter round ID.

    DR bypass is an OR of AND clauses; no clauses means no ordinary bypass.
    Temporary HP is an already-adjudicated available pool, not a grant stack.
    """
    energy = energy or {}
    resistance = energy_resistance or {}
    physical_types = resolve_physical_types(physical_profile, physical_choice)
    tags = set(bypass_tags) | set(physical_types)
    applicable = [row['amount'] for row in damage_reduction
                  if not any(clause and set(clause) <= tags for clause in row.get('bypassAnyOf', ()))]
    amounts = [weapon, *energy.values(), *resistance.values(), *applicable]
    if dm_damage_override is not None:
        amounts.append(dm_damage_override)
    if any(type(n) is not int or n < 0 for n in amounts):
        raise ValueError('Damage and defense amounts must be nonnegative integers')
    if (applicable or resistance) and round_id is None:
        raise ValueError('Supply a round ID for per-round defenses')
    prior = state.get('defenseUsage', {})
    usage = deepcopy(prior) if round_id == prior.get('roundId') else {}
    dr_used = usage.get('damageReduction', 0)
    energy_used = usage.get('energyResistance', {})
    immune_prevented = weapon if physical_types and set(physical_types) <= set(physical_immunities) else 0
    dr = 0 if ignores_dr or immune_prevented else min(weapon, max(0, max(applicable, default=0) - dr_used))
    ward = deepcopy(state.get('energyProtection'))
    ward_prevented = {}
    if ward:
        if type(now) is not int or now < 0:
            raise ValueError('Supply game time to resolve Protection from Energy')
        if now >= ward['expiresAtSeconds']:
            ward = None
        else:
            allowed = core['effects']['spellEffectsBySpellId']['protection-from-energy'][0]['energyTypes']
            energy = dict(energy)
            for key in energy:
                if key.casefold() in allowed:
                    absorbed = min(energy[key], ward['remaining'])
                    ward_prevented[key] = absorbed
                    energy[key] -= absorbed
                    ward['remaining'] -= absorbed
            if not ward['remaining']:
                ward = None
    energy_prevented = {key: min(value, max(0, resistance.get(key, 0) - energy_used.get(key, 0)))
                        for key, value in energy.items()}
    total = weapon - immune_prevented - dr + sum(energy.values()) - sum(energy_prevented.values())
    if dm_damage_override is not None:
        total = dm_damage_override
    result = deepcopy(state)
    if ward is None:
        result.pop('energyProtection', None)
    else:
        result['energyProtection'] = ward
    if round_id is not None:
        result['defenseUsage'] = dict(roundId=round_id, damageReduction=dr_used + dr,
            energyResistance={**energy_used, **{key: energy_used.get(key, 0) + n for key, n in energy_prevented.items()}})
    if 'dead' in condition_ids(core, state):
        raise ValueError('Injury workflow does not damage dead creatures')
    absorbed = min(state.get('temporaryHp', 0), total)
    result['temporaryHp'] = state.get('temporaryHp', 0) - absorbed
    applied = total - absorbed
    if nonlethal:
        result['nonlethal'] = state.get('nonlethal', 0) + applied
    else:
        result['hp'] -= applied
        if applied and result['hp'] < 0:
            result.update(stable=False, consciousBelowZero=False)
    rules = core['mechanics']['injury']['massiveDamage']
    threshold = rules['threshold']
    if single_attack and not nonlethal and total >= threshold and 'dead' not in condition_ids(core, result):
        if type(massive_save_total) is not int:
            raise ValueError('Supply the massive-damage Fortitude save total')
        if massive_save_total < rules['fortitudeDc']:
            result['dead'] = True
    return dict(state=result, conditionIds=condition_ids(core, result), weaponPrevented=dr, physicalTypeIds=list(physical_types), physicalImmunityPrevented=immune_prevented,
                energyPrevented=energy_prevented, wardPrevented=ward_prevented, temporaryHpAbsorbed=absorbed, applied=applied,
                weaponFullyBlockedByDr=bool(weapon and dr == weapon), dmDamageOverride=dm_damage_override)


def heal_injury(core, state, amount, *, magical=False):
    if type(amount) is not int or amount < 0:
        raise ValueError('Healing must be a nonnegative integer')
    result = deepcopy(state)
    if 'dead' not in condition_ids(core, state):
        result['hp'] = min(state['maxHp'], state['hp'] + amount)
        if magical:
            result['nonlethal'] = max(0, state.get('nonlethal', 0) - amount)
        if result['hp'] > state['hp'] and result['hp'] < 0:
            result['stable'] = True
        if result['hp'] >= 0:
            result.update(stable=False, consciousBelowZero=False)
    return dict(state=result, conditionIds=condition_ids(core, result))


def stabilize_injury(core, state, heal_check_total):
    """Resolve first aid; timing-based stabilization remains a separate event."""
    if type(heal_check_total) is not int:
        raise ValueError('Supply the Heal check total')
    result = deepcopy(state)
    if ('dying' in condition_ids(core, state) and
            heal_check_total >= core['mechanics']['injury']['stabilization']['healCheckDc']):
        result['stable'] = True
    return dict(state=result, conditionIds=condition_ids(core, result))


def end_injury_round(core, state, round_id, *, stabilization_roll=None):
    """Resolve at most one stabilization roll for a dying actor per round."""
    if round_id is None:
        raise ValueError('Supply a unique round ID')
    result = deepcopy(state)
    if 'dying' in condition_ids(core, state) and state.get('lastStabilizationRound') != round_id:
        if type(stabilization_roll) is not int or not 1 <= stabilization_roll <= 100:
            raise ValueError('Supply a percentile stabilization roll')
        rule = core['mechanics']['injury']['stabilization']
        result['lastStabilizationRound'] = round_id
        if stabilization_roll <= rule['chancePercent']:
            result['stable'] = True
        else:
            result['hp'] -= rule['failureHpLoss']
    return dict(state=result, conditionIds=condition_ids(core, result))
