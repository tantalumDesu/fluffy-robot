"""Commit drain saves and restoration against a preserved level history."""
from copy import deepcopy

from .character_advancement import minimum_xp
from .level_history import _rules, replay_level_history
from .negative_levels import (active_negative_levels, apply_drain_restoration, resolve_drain_level,
                              summarize_negative_levels, drain_death_aftermath)


def projected_history(core, character):
    """Replay the active prefix; original class choices and selection facts stay intact."""
    choices = character['classChoices']
    active = len(choices) - len(character.get('permanentLosses', ()))
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
    prior = projected_history(core, result)
    resolved = resolve_drain_level(core['mechanics']['negativeLevels'], levels, level_id, now,
                                   fortitude_total=fortitude_total)
    result['negativeLevels'] = resolved['levels']
    if resolved['permanentLevelLoss']:
        if prior['characterLevel'] < 1:
            raise ValueError('No level remains to lose')
        result.setdefault('permanentLosses', []).append(dict(id=level_id, lostAtSeconds=now,
            characterLevel=prior['characterLevel'], classId=prior['entries'][-1]['classId'] if prior['entries'] else None))
        current = projected_history(core, result)
        track, _ = _rules(core)
        effective = current['effectiveCharacterLevel']
        result['drainXpOverride'] = ((minimum_xp(effective, track) + minimum_xp(effective + 1, track)) // 2
                        if current['characterLevel'] else 0)
    status = drain_status(core, result, now)
    if status['slain']:
        result['dead'] = True
    return result


def restore_character_drain(core, character, spell_id, now, caster_level):
    """Clear removable drain and restore eligible losses in reverse loss order."""
    result = deepcopy(character)
    losses = result.setdefault('permanentLosses', [])
    restored = apply_drain_restoration(core, spell_id, result.get('negativeLevels', ()), losses, now, caster_level)
    result['negativeLevels'] = restored['levels']
    eligible = {record['id'] for record in restored['restorePermanentLosses']}
    if not result.get('dead'):
        count = 0
        while losses and losses[-1]['id'] in eligible:
            record = losses.pop()
            result.setdefault('restoredLosses', []).append(dict(record, restoredAtSeconds=now, spellId=spell_id))
            count += 1
        if count:
            track, _ = _rules(core)
            result['drainXpOverride'] = minimum_xp(projected_history(core, result)['effectiveCharacterLevel'], track)
    return result


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
