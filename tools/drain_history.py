"""Commit drain saves and restoration against a preserved level history."""
from copy import deepcopy

from .character_advancement import minimum_xp
from .level_history import _rules, replay_level_history
from .negative_levels import (active_negative_levels, apply_drain_restoration, resolve_drain_level, restoration_requirements,
                              summarize_negative_levels, drain_death_aftermath)


def _suppressed_levels(character):
    return [*character.get('permanentLosses', ()), *character.get('drainedLevels', ())]


def projected_history(core, character):
    """Replay the active prefix; original class choices and selection facts stay intact."""
    choices = character['classChoices']
    active = len(choices) - len(_suppressed_levels(character))
    hd = character.get('racialHitDice', 0)
    return replay_level_history(core, choices[:max(active, 0)], racial_hit_dice=max(0, hd + min(active, 0)),
                                level_adjustment=character.get('levelAdjustment', 0),
                                alignment_by_level={int(k): v for k, v in character.get('alignmentByLevel', {}).items()
                                                    if int(k) <= hd + active})


def drain_status(core, character, now):
    levels = active_negative_levels(character.get('negativeLevels', ()), now)
    return summarize_negative_levels(core['mechanics']['negativeLevels'], levels,
                                     projected_history(core, character)['characterLevel'])


def resolve_character_drain_save(core, character, level_id, now, fortitude_total):
    """Resolve one due save. A failure suppresses the latest level and sets XP."""
    result = deepcopy(character)
    levels = active_negative_levels(result.get('negativeLevels', ()), now)
    if not any(entry['id'] == level_id for entry in levels):
        raise ValueError('Unknown active negative level')
    resolved = resolve_drain_level(core['mechanics']['negativeLevels'], levels, level_id, now,
                                   fortitude_total=fortitude_total)
    result['negativeLevels'] = resolved['levels']
    if resolved['drainedLevel']:
        result = _suppress_level(core, result, level_id, now, cause='energy-drain', restorable=True)
    status = drain_status(core, result, now)
    if status['slain']:
        result['dead'] = True
    return reconcile_character_spell_ledgers(core, result, removed_negative_ids={level_id})


def lost_level_recovery_options(core, character, now):
    """List outstanding energy-drain losses with elapsed time and cast requirements."""
    return [dict(id=loss['id'], characterLevel=loss['characterLevel'],
                 failedSaveAtSeconds=loss['failedSaveAtSeconds'],
                 spells=restoration_requirements(core, loss, now))
            for loss in sorted(character.get('drainedLevels', ()), key=lambda row: row['characterLevel'])]


def restore_character_drain(core, character, spell_id, now, caster_level):
    """Clear active negatives and restore eligible drained levels in prefix order."""
    result = deepcopy(character)
    drained = result.setdefault('drainedLevels', [])
    restored = apply_drain_restoration(core, spell_id, result.get('negativeLevels', ()), drained, now, caster_level)
    result['negativeLevels'] = restored['levels']
    eligible = {record['id'] for record in restored['restoreDrainedLevels']}
    count = 0
    while eligible and not result.get('dead') and _suppressed_levels(result):
        record = min(_suppressed_levels(result), key=lambda entry: entry['characterLevel'])
        if record['id'] not in eligible:
            break
        drained.remove(record)
        eligible.remove(record['id'])
        result.setdefault('restoredLosses', []).append(dict(record, restoredAtSeconds=now, spellId=spell_id))
        count += 1
    if count:
        # A different earned class can invalidate a later prestige target. Never
        # silently substitute a choice or commit a partially invalid rebuild.
        projected_level_grants(core, result)
        track, _ = _rules(core)
        result['drainXpOverride'] = minimum_xp(projected_history(core, result)['effectiveCharacterLevel'], track)
    removed = {r['id'] for r in character.get('negativeLevels', ())} - {r['id'] for r in result['negativeLevels']}
    result = discard_permanent_losses(core, result)
    return reconcile_character_spell_ledgers(core, result, removed_negative_ids=removed)


def commit_restoration_cast(core, caster, recipient, spell_id, now, caster_level, **cure_choices):
    """Commit a confirmed casting and its XP cost; pass recipient=None for self-casting."""
    from .condition_cures import cure_actor

    rule = core['effects']['negativeLevelOperationsBySpellId'][spell_id]
    if rule['operation'] != 'restore-negative-levels':
        raise ValueError('Choose Restoration or Greater Restoration')
    payer = deepcopy(caster)
    cost = rule['xpCost']
    if cost:
        track, _ = _rules(core)
        floor = minimum_xp(projected_history(core, payer)['effectiveCharacterLevel'], track)
        xp = effective_xp(payer)
        if xp - cost < floor:
            raise ValueError('Caster cannot pay the Restoration XP cost without losing a level')
        payer['drainXpOverride' if 'drainXpOverride' in payer else 'xp'] = xp - cost
    target = payer if recipient is None else recipient
    result = cure_actor(core, target, spell_id, now, resolved=True, caster_level=caster_level, **cure_choices)
    return dict(caster=result if recipient is None else payer, recipient=result)


def commit_negative_levels(core, character, levels, now, *, choices=(), creature_source=False, source_type=None):
    """Commit distinct new levels, immediate spell loss, and lethal drain aftermath."""
    from .negative_levels import allocate_spell_losses

    result = deepcopy(character)
    active = active_negative_levels(result.get('negativeLevels', ()), now)
    new = active_negative_levels(levels, now)
    if any(level['kind'] == 'wielded-weapon' for level in new):
        raise ValueError('Equipment negative levels are derived, not persisted')
    ids = {level['id'] for level in new}
    if len(ids) != len(new) or ids.intersection(level['id'] for level in active):
        raise ValueError('Negative level IDs must be unique')
    result['negativeLevels'] = active + deepcopy(new)
    if 'spellLedgers' in result:
        result['spellLedgers'] = allocate_spell_losses(core, result['spellLedgers'], new, choices)
    if new and drain_status(core, result, now)['slain']:
        result['dead'] = True
        if creature_source:
            result['drainAftermath'] = drain_death_aftermath(source_type)
    return result


def reconcile_character_spell_ledgers(core, character, *, removed_negative_ids=()):
    """Reconcile existing slot budgets and release recovery-only drain blocks."""
    if not character.get('spellLedgers'):
        return character
    from .spellcasting import feat_slot_budget, reconcile_slot_budget

    view = projected_level_grants(core, character)
    classes = {cls['id']: cls for cls in core['progression']['classes']}
    for track, slots in character['spellLedgers'].items():
        for slot in slots['slots'].values():
            if slot.get('negativeLevelId') in removed_negative_ids and slot.get('negativeLevelLoss') == 'recovery':
                slot.pop('negativeLevelId', None)
                slot.pop('negativeLevelLoss', None)
        if 'classId' not in slots:  # An overlay-only ledger has no progression budget.
            continue
        progression = view['spellcastingLevels'].get(track, 0)
        ability = classes[track]['spellcasting']['abilityStat'].lower()
        score = view['abilityScores'].get(ability)
        if progression and score is None:
            raise ValueError(f'Supply the casting ability score to reconcile {track} slots')
        budget = feat_slot_budget(core, track, progression, score, feat_choices=view['featChoices'],
                                  specialization=character.get('wizardSpecialization')) if progression else {}
        character['spellLedgers'][track] = reconcile_slot_budget(slots, budget)
    return character


def effective_xp(character):
    return character.get('drainXpOverride', character.get('xp'))


def remove_negative_level(character, level_id):
    """Remove one timed overlay (for example by DM fiat), not a permanent loss."""
    result = deepcopy(character)
    levels = result.get('negativeLevels', [])
    if not any(level['id'] == level_id and level['kind'] != 'wielded-weapon' for level in levels):
        raise ValueError('No removable negative level with that ID')
    result['negativeLevels'] = [level for level in levels if level['id'] != level_id]
    for ledger in result.get('spellLedgers', {}).values():
        for slot in ledger['slots'].values():
            if slot.get('negativeLevelId') == level_id and slot.get('negativeLevelLoss') == 'recovery':
                slot.pop('negativeLevelId', None)
                slot.pop('negativeLevelLoss', None)
    return result


def projected_level_grants(core, character):
    """Project saved totals, subtracting only grants tied to suppressed levels."""
    history = projected_history(core, character)
    scores = dict(character.get('abilityScores', {}))
    ranks = dict(character.get('skillRanks', {}))
    feats = list(character.get('featChoices', ()))
    maximum = character.get('maxHp')
    review = []
    for loss in _suppressed_levels(character):
        grants = loss.get('suppressedGrants', {})
        for values, key in ((scores, 'abilityIncreases'), (ranks, 'skillRanks')):
            for stat, amount in grants.get(key, {}).items():
                if stat in values and values[stat] is not None:
                    values[stat] = max(0, values[stat] - amount)
        for choice in grants.get('featChoices', ()):
            if choice in feats:
                feats.remove(choice)
        if maximum is not None:
            maximum = max(1, maximum - grants.get('hpGain', 0))
        review.extend(loss.get('needsReview', ()))
    from .spell_advancement import active_known, casting_targets
    from .spellcasting import spellcasting_levels
    return dict(history=history, abilityScores=scores, skillRanks=ranks, featChoices=feats,
                maxHp=maximum, xp=effective_xp(character), needsReview=review,
                knownSpellIdsByClassId=active_known(character, history, feats),
                spellcastingLevels=spellcasting_levels(core, history, casting_targets(character, history)))


def materialize_active_levels(core, character):
    """Make an independent active build and detach suppressed records for a transaction."""
    result = deepcopy(character)
    if not _suppressed_levels(result):
        return result
    view = projected_level_grants(core, result)
    history = view['history']
    level = history['characterLevel']
    result['classChoices'] = [entry['classId'] for entry in history['entries']]
    result['racialHitDice'] = history['racialHitDice']
    for key in ('abilityScores', 'skillRanks', 'featChoices', 'maxHp', 'xp'):
        result[key] = view[key]
    result.pop('drainXpOverride', None)
    for key in ('levelGrantsByLevel', 'alignmentByLevel'):
        result[key] = {n: value for n, value in result.get(key, {}).items() if int(n) <= level}
    result.pop('permanentLosses', None)
    result.pop('drainedLevels', None)
    return result


def forget_level_inscriptions(result, loss):
    for pick in loss['suppressedGrants']['featChoices']:
        for spell in pick.get('spellGrant', {}).get('spells', ()):
            book = result.get('spellbooksById', {}).get(spell.get('bookId'))
            if book:
                book['spellsById'].pop(spell['spellId'], None)
                if 'damagedSpellIds' in book:
                    book['damagedSpellIds'] = [key for key in book['damagedSpellIds'] if key != spell['spellId']]


def restore_suppressed_suffix(result, records):
    """Reattach still-lost records without activating their grants."""
    for loss in sorted(records, key=lambda row: row['characterLevel']):
        grants = loss['suppressedGrants']
        key = 'drainedLevels' if 'failedSaveAtSeconds' in loss else 'permanentLosses'
        result.setdefault(key, []).insert(0, loss)
        if loss['classId'] is None:
            result['racialHitDice'] = result.get('racialHitDice', 0) + 1
        else:
            result['classChoices'].append(loss['classId'])
        level = str(loss['characterLevel'])
        result.setdefault('levelGrantsByLevel', {})[level] = grants
        if loss.get('alignmentFacts') is not None:
            result.setdefault('alignmentByLevel', {})[level] = loss['alignmentFacts']
        for field, grant in (('abilityScores', 'abilityIncreases'), ('skillRanks', 'skillRanks')):
            values = result.setdefault(field, {})
            for stat, amount in grants[grant].items():
                values[stat] = values.get(stat, 0) + amount
        result.setdefault('featChoices', []).extend(grants['featChoices'])
        if result.get('maxHp') is not None:
            result['maxHp'] += grants['hpGain']
    return result


def discard_permanent_losses(core, character):
    """Commit the surviving prefix and drop irreversible records once separable."""
    if character.get('drainedLevels') or not character.get('permanentLosses'):
        return character
    result = materialize_active_levels(core, character)
    for loss in character['permanentLosses']:
        forget_level_inscriptions(result, loss)
    return result


def apply_permanent_level_loss(core, character, loss_id, now, *, cause='level-loss'):
    """Apply irrevocable level loss (including a confirmed Raise Dead cost)."""
    result = _suppress_level(core, deepcopy(character), loss_id, now, cause=cause)
    return reconcile_character_spell_ledgers(core, discard_permanent_losses(core, result))


def _suppress_level(core, character, loss_id, now, *, cause, restorable=False):
    result = deepcopy(character)
    previous = projected_history(core, result)
    level = previous['characterLevel']
    if level < 1 or any(loss['id'] == loss_id for loss in [*_suppressed_levels(result), *result.get('restoredLosses', ())]):
        raise ValueError('A level and an unused loss ID are required')
    entry = previous['entries'][-1] if previous['entries'] else {}
    ledger = result.get('levelGrantsByLevel', {})
    grants = ledger.get(str(level), ledger.get(level))
    if grants is None or not {'hpGain', 'abilityIncreases', 'skillRanks', 'featChoices'} <= grants.keys():
        raise ValueError('Permanent level loss requires a complete recorded advancement entry')
    record = dict(id=loss_id, lostAtSeconds=now, cause=cause, characterLevel=level,
                  classId=entry.get('classId'), suppressedGrants=deepcopy(grants),
                  alignmentFacts=result.get('alignmentByLevel', {}).get(str(level), result.get('alignmentByLevel', {}).get(level)))
    if not restorable:
        result.setdefault('permanentLosses', []).append(dict(record, permanentlyLostAtSeconds=now))
    else:
        result.setdefault('drainedLevels', []).append(dict(record, failedSaveAtSeconds=now))
    lower = projected_history(core, result)
    track, _ = _rules(core)
    effective = lower['effectiveCharacterLevel']
    result['drainXpOverride'] = ((minimum_xp(effective, track) + minimum_xp(effective + 1, track)) // 2
                                if lower['characterLevel'] else 0)
    return result


def derive_level_loss_sheet(core, character, race_id, *, now=None, **sheet_options):
    """Use the active prefix and surviving grants for the character and linked companions."""
    from .derived_stats import derive_sheet

    projected = projected_level_grants(core, character)
    if now is not None:
        sheet_options.setdefault('negative_levels', active_negative_levels(character.get('negativeLevels', ()), now))
    sheet_options.setdefault('natural_forms_by_id', character.get('naturalFormsById'))
    sheet_options.setdefault('natural_attacks', character.get('naturalAttacks', ()))
    sheet_options.setdefault('available_natural_form_ids', character.get('availableNaturalFormIds', ()))
    sheet_options.setdefault('active_natural_form_id', character.get('activeNaturalFormId'))
    sheet = derive_sheet(core, projected['history'], race_id, projected['abilityScores'],
                         skill_ranks=projected['skillRanks'], feat_choices=projected['featChoices'],
                         master_max_hp=projected['maxHp'], after_level_loss=bool(_suppressed_levels(character)),
                         **sheet_options)
    sheet.update(maxHp=projected['maxHp'], xp=projected['xp'], characterLevel=projected['history']['characterLevel'])
    if projected['maxHp'] is not None:
        sheet['effectiveMaxHp'] = max(0, projected['maxHp'] + sheet['negativeLevels']['hitPointPenalty'])
    sheet['knownSpellIdsByClassId'] = projected['knownSpellIdsByClassId']
    sheet['spellcastingLevels'] = projected['spellcastingLevels']
    sheet['classLevels'] = projected['history']['classLevels']
    levels_by_progression = {entry['progressionClassId']: entry['classLevel']
                             for entry in projected['history']['entries']}
    sheet['classAbilities'] = [dict(classId=cls['id'], abilityId=ability['id'], name=ability['name'],
                                    description=ability['description'])
                               for cls in core['progression']['classes'] if cls['id'] in levels_by_progression
                               for ability in cls['abilities'] if ability['gainedLevel'] is not None
                               and ability['gainedLevel'] <= levels_by_progression[cls['id']]]
    sheet['needsReview'].extend(projected['needsReview'])
    return sheet
