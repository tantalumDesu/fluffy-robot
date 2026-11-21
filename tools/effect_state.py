"""State helpers for confirmed spell applications on a single actor.

Times are integer rounds on the caller's clock (10 rounds/minute). The caller
handles targeting, saves, SR, and the order of consumption for distinct pools.
"""

_ROUNDS = {'round': 1, 'minute': 10, 'hour': 600}


def active_spells(instances, now):
    return [instance for instance in instances if now < instance['expiresAtRound']]


def apply_spell(instances, catalog, spell_id, caster_level, now, roll_die, *, opposed_spell_ids=()):
    """Apply a confirmed cast; opt in to removing confirmed opposing effects.

    Refuse a second active casting with the same spell ID so the caller can
    keep the existing instance or explicitly replace it without stacking pools.
    """
    if type(caster_level) is not int or caster_level < 1:
        raise ValueError('Expected a positive caster level')
    effects = catalog[spell_id]
    current = active_spells(instances, now)
    if any(instance['spellId'] == spell_id for instance in current):
        raise ValueError('Choose which casting to keep before applying the spell again')
    allowed = set(effects[0].get('countersAndDispels', ()))
    opposed = set(opposed_spell_ids)
    if not opposed <= allowed:
        raise ValueError('The spell does not dispel the selected effect')
    if opposed.intersection(instance['spellId'] for instance in current):
        return [instance for instance in current if instance['spellId'] not in opposed]
    duration = effects[0]['duration']
    rounds = _ROUNDS[duration['unit']] * (duration.get('amount') or duration['perCasterLevel'] * caster_level)
    pools = {}
    for effect in effects:
        if effect['operation'] != 'temporary-hp':
            continue
        amount = effect.get('amount', 0)
        if 'dice' in effect:
            count, sides = map(int, effect['dice'].split('d'))
            for _ in range(count):
                result = roll_die(sides)
                if type(result) is not int or not 1 <= result <= sides:
                    raise ValueError('Die roll out of range')
                amount += result
        if 'casterLevelBonusMax' in effect:
            amount += min(caster_level, effect['casterLevelBonusMax'])
        pools[effect['id']] = amount
    return current + [dict(spellId=spell_id, casterLevel=caster_level, expiresAtRound=now + rounds, temporaryHp=pools)]


def consume_temporary_hp(instance, effects, effect_id, damage):
    """Consume one chosen pool. Return (updated instance or None, remaining damage)."""
    if type(damage) is not int or damage < 0:
        raise ValueError('Expected nonnegative integer damage')
    effect = next(e for e in effects if e['id'] == effect_id and e['operation'] == 'temporary-hp')
    pools = instance['temporaryHp'].copy()
    absorbed = min(pools[effect_id], damage)
    pools[effect_id] -= absorbed
    if not pools[effect_id] and effect.get('endsWhenPoolDepleted'):
        return None, damage - absorbed
    return dict(instance, temporaryHp=pools), damage - absorbed


def constitution_hp_delta(old_score, new_score, hit_dice):
    """Apply to both current and maximum HP, never to temporary HP pools."""
    return ((new_score - 10) // 2 - (old_score - 10) // 2) * hit_dice


def active_effects(instances, catalog, now):
    """Adapt persisted spell instances to the sheet resolver input contract."""
    return [(effect, {'casterLevel': instance['casterLevel']})
            for instance in active_spells(instances, now)
            for effect in catalog[instance['spellId']]]


def movement_speed(base_speed, instances, other_enhancement=0):
    """Resolve one existing movement mode; enhancement bonuses do not stack."""
    best = other_enhancement
    for effect, _ in instances:
        if effect['operation'] == 'movement-enhancement' and base_speed > 0:
            best = max(best, min(effect['amountFt'], base_speed * (effect['maxSpeedMultiplier'] - 1)))
    return base_speed + best if base_speed > 0 else 0


def opportunity_attack_limit(dexterity_modifier, flat_footed, instances):
    """Return the per-round allowance, not attacks already spent."""
    eligible = [e for e, _ in instances if e['operation'] == 'opportunity-attacks']
    if flat_footed and not any(e.get('allowedWhileFlatFooted') for e in eligible):
        return 0
    return 1 + (max(0, dexterity_modifier) if any(e.get('extraFrom') == 'positive-dexterity-modifier'
                                               for e in eligible) else 0)


def full_attack_extra_attacks(instances, *, full_attack, held_weapon, other_noncumulative=0):
    """Return additional attacks at full BAB, not additional actions."""
    if not full_attack or not held_weapon:
        return 0
    return max([other_noncumulative] + [effect['amount'] for effect, _ in instances
                                       if effect['operation'] == 'extra-full-attack-attack'])


def blocks_effect(instances, *, spell_id=None, effect_tags=()):
    """Check explicit defenses after the caller has identified the incoming effect."""
    return any((e['operation'] == 'spell-defense' and e.get('negatesSpellId') == spell_id)
               or (e['operation'] == 'immunity' and e.get('effectTag') in effect_tags)
               for e, _ in instances)
