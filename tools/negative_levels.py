"""Track temporary negative levels without rewriting actual character levels."""
from copy import deepcopy

if __package__:
    from .effect_state import blocks_effect
    from .alignment import OPPOSITES, alignment_tags
    from .game_time import seconds
else:
    from effect_state import blocks_effect
    from alignment import OPPOSITES, alignment_tags
    from game_time import seconds


def negative_level_rules(lines):
    source = 'SPECIAL ABILITIES.txt'
    line = lines(source).index('ENERGY DRAIN AND NEGATIVE LEVELS') + 1
    return dict(modifiersPerLevel={'skill': -1, 'ability-check': -1, 'attack': -1, 'save': -1, 'hp': -5},
                effectiveLevelPenalty=1, changesClassLevels=False, changesPurchasedSkillRanks=False,
                immediateSpellLossPerLevel=1, recoverySlotLossPerLevel=1,
                drainDurationHours=24, fortitudeDcBase=10, dcAttackerHdDivisor=2,
                permanentLevelLossOnFailure=1, bestowerTemporaryHpPerLevel=5,
                source={'file': source, 'line': line})


def weapon_negative_levels(core, alignment_id, wielded_properties):
    """Return live levels for {item instance ID: property IDs}; do not persist them as drain."""
    tags = alignment_tags(core, alignment_id)
    properties = core['inventory']['weaponAlignmentPropertiesById']
    return [dict(id=f'weapon:{item_id}:{key}', kind='wielded-weapon', itemId=item_id)
            for item_id, keys in wielded_properties.items() for key in sorted(set(keys))
            if OPPOSITES[properties[key]['alignmentTag']] in tags]


def create_drain_levels(rules, event_id, count, now, *, kind, save_dc=None, attacker_hd=None, attacker_cha_modifier=None):
    """Create separately resolved negative levels and report the bestower's temp HP grant."""
    if kind not in ('creature', 'spell-or-similar') or type(count) is not int or count < 1 or type(now) is not int or now < 0:
        raise ValueError('Invalid energy drain event')
    if save_dc is None:
        if type(attacker_hd) is not int or attacker_hd < 1 or type(attacker_cha_modifier) is not int:
            raise ValueError('Provide source DC or attacker HD and Charisma modifier')
        save_dc = rules['fortitudeDcBase'] + attacker_hd // rules['dcAttackerHdDivisor'] + attacker_cha_modifier
    if type(save_dc) is not int:
        raise ValueError('Fortitude DC must be an integer')
    return dict(levels=[dict(id=f'drain:{event_id}:{i}', kind='energy-drain', saveDc=save_dc,
                             saveDueAtSeconds=now + seconds('hour', rules['drainDurationHours'])) for i in range(count)],
                bestowerTemporaryHp=count * rules['bestowerTemporaryHpPerLevel'] if kind == 'creature' else 0)


def summarize_negative_levels(rules, levels, current_level):
    count = len({level['id'] for level in levels})
    modifiers = [dict(id='negative-levels:' + stat, operation='modifier', statId=stat, bonusType=None,
                      amount=amount * count, stacking='once-per-effect')
                 for stat, amount in rules['modifiersPerLevel'].items() if count]
    if count:
        modifiers.append(dict(id='negative-levels:effective-level', operation='modifier',
                              statId='effective-level', bonusType=None,
                              amount=-count * rules['effectiveLevelPenalty'], stacking='once-per-effect'))
    return dict(count=count, modifiers=modifiers, hitPointPenalty=rules['modifiersPerLevel']['hp'] * count,
                effectiveLevel=max(0, current_level - count * rules['effectiveLevelPenalty']),
                slain=current_level < 1 or count >= current_level)


def resolve_drain_level(rules, levels, level_id, now, *, fortitude_total=None, restoration=False):
    """Remove one timed level; report permanent loss for the character ledger to process."""
    level = next(entry for entry in levels if entry['id'] == level_id)
    if level['kind'] == 'temporary-drain':
        if not restoration and now < level['expiresAtSeconds']:
            raise ValueError('Temporary drain has not expired')
        return dict(levels=[entry for entry in levels if entry['id'] != level_id], permanentLevelLoss=0)
    if level['kind'] != 'energy-drain':
        raise ValueError('Equipment negative levels end when their wielding condition ends')
    if not restoration and (type(fortitude_total) is not int or now < level['saveDueAtSeconds']):
        raise ValueError('A separate Fortitude save is required when this level becomes due')
    loss = 0 if restoration or fortitude_total >= level['saveDc'] else rules['permanentLevelLossOnFailure']
    return dict(levels=[entry for entry in levels if entry['id'] != level_id], permanentLevelLoss=loss)


def highest_slot_choices(core, ledgers, *, recovery=False):
    """Return (class ID, slot ID) choices for the next loss, highest level only.

    At recovery choose among the recovered allotment (including open prepared
    slots); for immediate losses consider castable preparations and open slots
    on spontaneous tracks. Caller supplies only the tracks being considered.
    """
    spontaneous = {c['id'] for c in core['progression']['classes'] if c.get('spellcasting', {}).get('spontaneous')}
    options = [(slot['level'], (class_id, slot_id)) for class_id, ledger in ledgers.items()
               for slot_id, slot in ledger['slots'].items()
               if not (slot['expended'] or slot.get('negativeLevelLoss'))
               and (recovery or class_id in spontaneous or slot['preparation'] is not None)]
    if not options:
        return []
    highest = (max(slot['level'] for ledger in ledgers.values() for slot in ledger['slots'].values())
               if recovery else max(level for level, _ in options))
    return [choice for level, choice in options if level == highest]


def lose_spell_slot(core, ledgers, choice, *, recovery=False):
    """Commit one selected loss; repeat with updated ledgers for additional levels."""
    if choice not in highest_slot_choices(core, ledgers, recovery=recovery):
        raise ValueError('Choose one of the highest-level eligible slots')
    class_id, slot_id = choice
    result = deepcopy(ledgers)
    result[class_id]['slots'][slot_id]['negativeLevelLoss'] = 'recovery' if recovery else 'immediate'
    return result


def allocate_spell_losses(core, ledgers, levels, choices, *, recovery=False):
    """Apply one loss per level until no slots remain; require a choice for ties.

    Pass newly gained levels at acquisition, and currently active levels when
    applying a recovered allotment. A singleton eligible slot is automatic.
    """
    chosen = iter(choices)
    result = ledgers
    for level_id in dict.fromkeys(level['id'] for level in levels):
        options = highest_slot_choices(core, result, recovery=recovery)
        if not options:
            break
        if len(options) == 1:
            choice = options[0]
        else:
            choice = next(chosen, None)
            if choice is None:
                raise ValueError('Choose which highest-level spell slot to lose')
        result = lose_spell_slot(core, result, choice, recovery=recovery)
        class_id, slot_id = choice
        result[class_id]['slots'][slot_id]['negativeLevelId'] = level_id
    if next(chosen, None) is not None:
        raise ValueError('Unused spell-slot choices for negative levels')
    return result


def drain_death_aftermath(slaying_source_type=None):
    """Report the next-night consequence of a creature-caused drain death."""
    return {'trigger': 'next-night', 'creatureTypeId': slaying_source_type or 'wight'}


def spell_drain_catalog(spells):
    data = {
        'enervation': dict(operation='inflict-negative-levels', dice='1d4', resolution='ranged-touch-and-sr',
                           expiration={'kind': 'automatic', 'hoursPerCasterLevel': 1, 'maximumHours': 15},
                           undeadTemporaryHpPerDieResult=5, undeadTemporaryHpHours=1),
        'energy-drain': dict(operation='inflict-negative-levels', dice='2d4', resolution='ranged-touch-and-sr',
                             expiration={'kind': 'fortitude-save', 'hours': 24, 'dcSource': 'spell-save-dc'},
                             undeadTemporaryHpPerDieResult=5, undeadTemporaryHpHours=1),
        'restoration': dict(operation='restore-negative-levels', removeActive='all-removable',
                            permanentLevels='one', permanentWindowUnit='day'),
        'restoration-greater': dict(operation='restore-negative-levels', removeActive='all-removable',
                                    permanentLevels='all-eligible', permanentWindowUnit='week'),
    }
    by_id = {spell['id']: spell for spell in spells}
    for key, rule in data.items():
        rule['source'] = {'file': by_id[key]['file'], 'heading': by_id[key]['name']}
    return data


def active_negative_levels(levels, now):
    """Automatically expire short drain, but keep energy drain awaiting its saves."""
    return [level for level in levels if level['kind'] != 'temporary-drain' or now < level['expiresAtSeconds']]


def apply_drain_spell(core, cast_plan, event_id, levels, now, caster_level, roll_die, *, hit,
                      spell_resistance_passed, target_kind, target_effects=(), ledgers=None, choices=()):
    """Resolve a confirmed ray against one actor. No initial Fortitude save is made."""
    # Local import keeps the generator's catalog usable both as module and script.
    from .spellcasting import numeric_spell_result

    spell_id = cast_plan['spellId']
    rule = core['effects']['negativeLevelOperationsBySpellId'][spell_id]
    if (rule['operation'] != 'inflict-negative-levels' or target_kind not in ('living', 'undead', 'other')
            or type(caster_level) is not int or caster_level < 1):
        raise ValueError('Invalid drain spell or target')
    active = active_negative_levels(levels, now)
    result = dict(levels=active, ledgers=ledgers, temporaryHp=None, bestowerTemporaryHp=0)
    if not hit or not spell_resistance_passed or target_kind == 'other' or blocks_effect(
            target_effects, spell_id=spell_id, effect_tags=('energy-drain', 'negative-energy')):
        return result
    dice, sides = map(int, rule['dice'].split('d'))
    maximized = cast_plan['transforms'].get('variableNumericEffects') == 'maximum'
    rolls = [] if maximized else [roll_die(sides) for _ in range(dice)]
    if any(type(roll) is not int or not 1 <= roll <= sides for roll in rolls):
        raise ValueError('Die roll out of range')
    count = numeric_spell_result(cast_plan, sum(rolls), dice * sides)
    if target_kind == 'undead':
        result['temporaryHp'] = {'amount': count * rule['undeadTemporaryHpPerDieResult'],
                                 'expiresAtSeconds': now + seconds('hour', rule['undeadTemporaryHpHours'])}
        return result
    rules = core['mechanics']['negativeLevels']
    expiry = rule['expiration']
    if expiry['kind'] == 'fortitude-save':
        new = create_drain_levels(rules, event_id, count, now, kind='spell-or-similar',
                                  save_dc=cast_plan['saveDc'])['levels']
    else:
        duration = min(expiry['maximumHours'], caster_level * expiry['hoursPerCasterLevel'])
        new = [dict(id=f'drain:{event_id}:{i}', kind='temporary-drain',
                    expiresAtSeconds=now + seconds('hour', duration)) for i in range(count)]
    if {level['id'] for level in active}.intersection(level['id'] for level in new):
        raise ValueError('Duplicate drain cast event ID')
    result['levels'] = active + new
    if ledgers is not None:
        result['ledgers'] = allocate_spell_losses(core, ledgers, new, choices)
    return result


def apply_drain_restoration(core, spell_id, levels, permanent_losses, now, caster_level):
    """Return removals and permanent-loss records eligible to restore, not rebuilt classes."""
    rule = core['effects']['negativeLevelOperationsBySpellId'][spell_id]
    if rule['operation'] != 'restore-negative-levels' or type(caster_level) is not int or caster_level < 1:
        raise ValueError('Invalid restoration spell or caster level')
    age_limit = seconds(rule['permanentWindowUnit'], caster_level)
    eligible = sorted((entry for entry in reversed(permanent_losses) if not entry.get('dueToDeath')
                       and 0 <= now - entry['lostAtSeconds'] <= age_limit),
                      key=lambda entry: entry['lostAtSeconds'], reverse=True)
    if rule['permanentLevels'] == 'one':
        eligible = eligible[:1]
    return dict(levels=[level for level in levels if level['kind'] == 'wielded-weapon'],
                restorePermanentLosses=eligible)
