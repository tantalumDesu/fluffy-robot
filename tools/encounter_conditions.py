"""Encounter condition state, including explicit DM rulings."""
from copy import deepcopy

from .condition_rules import condition_policies
from .condition_cures import active_condition_ids, apply_condition_cure
from .derived_stats import condition_state
from .game_time import apply_turn_conditions, encounter_clock, start_next_turn
from .state_changes import transition


def effective_conditions(encounter, actor):
    entry = encounter.get('actorConditions', {}).get(actor, {})
    ids = set(entry.get('conditions', ()))
    ids.update(active_condition_ids(entry.get('conditionOverrides', ()), encounter_clock(encounter)['gameSeconds']))
    for machine in ('fatigue', 'fear'):
        state = entry.get(machine) or {}
        if state.get('id') not in (None, 'clear'):
            ids.add(state['id'])
    return sorted(ids)


def _flags(core, encounter, actor):
    flags, _, _ = condition_state(core, effective_conditions(encounter, actor))
    override = encounter.get('actorConditions', {}).get(actor, {}).get('turnFlagsOverride')
    return flags if override is None else set(override)


def advance_turn(core, encounter):
    return start_next_turn(encounter, condition_flags_at_turn=lambda state, actor: _flags(core, state, actor))


def change_conditions(core, encounter, actor, *, machine=None, event=None, facts=None,
                      add=(), remove=(), dm_override=None):
    """Apply a condition change transactionally, with optional recorded DM fiat.

    Override keys: reason (required), skipEvent, machineState, conditionIds and
    turnFlags (null releases an earlier flag override). This never edits canon.
    """
    if actor not in encounter['order']:
        raise ValueError('Actor not in encounter')
    if (machine is None) != (event is None):
        raise ValueError('Supply machine and event together')
    if machine not in (None, 'rage', 'fear', 'fatigue'):
        raise ValueError('Unsupported encounter condition machine')
    override = dm_override or {}
    if dm_override is not None and not str(override.get('reason') or '').strip():
        raise ValueError('Provide a reason for the DM ruling')
    result = deepcopy(encounter)
    entry = result.setdefault('actorConditions', {}).setdefault(actor, {})
    ids = set(entry.get('conditions', ()))
    ids.update(add)
    ids.difference_update(remove)
    # Use one condition state per progressive family, regardless of entry path.
    for family, severity in [('fatigue', ('fatigued', 'exhausted')),
                             ('fear', ('shaken', 'frightened', 'panicked'))]:
        if entry.get(family, {}).get('id') in remove:
            entry.pop(family, None)
        current = entry.get(family, {}).get('id')
        highest = next((key for key in reversed(severity) if key in ids or key == current), None)
        if highest and highest != current:
            entry[family] = {'id': highest, 'origin': 'ordinary'}
        ids.difference_update(severity)
    if machine is not None:
        events = []
        if not override.get('skipEvent') and 'machineState' not in override:
            entry[machine], events = transition(core, machine, entry.get(machine), event, facts=facts)
        if 'machineState' in override:
            entry[machine] = deepcopy(override['machineState'])
        for emitted in events:
            if emitted == 'post-rage-fatigue':
                entry['fatigue'], _ = transition(core, 'fatigue', entry.get('fatigue'), emitted)
    if 'conditionIds' in override:
        ids = set(override['conditionIds'])
        for family in ('fatigue', 'fear'):
            if entry.get(family, {}).get('id') not in ids:
                entry.pop(family, None)
    if not ids <= condition_policies(core).keys():
        raise ValueError('Unknown condition ID')
    entry['conditions'] = sorted(ids)
    if 'turnFlags' in override:
        entry['turnFlagsOverride'] = deepcopy(override['turnFlags'])
    if dm_override is not None:
        result.setdefault('dmRulings', []).append(dict(actorId=actor, machine=machine, event=event,
                                                       ruling=deepcopy(override)))
    if result['phase'] in ('start', 'acting') and result['order'][result['index']] == actor:
        apply_turn_conditions(result, _flags(core, result, actor))
    return result


def set_condition_overrides(core, encounter, actor, instances):
    """Replace only this actor's sourced condition overlays and refresh the turn."""
    if actor not in encounter['order'] or any(i['conditionId'] not in condition_policies(core) for i in instances):
        raise ValueError('Unknown actor or condition')
    if len({i['id'] for i in instances}) != len(instances):
        raise ValueError('Condition instance IDs must be unique')
    result = deepcopy(encounter)
    result.setdefault('actorConditions', {}).setdefault(actor, {})['conditionOverrides'] = deepcopy(instances)
    if result['phase'] in ('start', 'acting') and result['order'][result['index']] == actor:
        apply_turn_conditions(result, _flags(core, result, actor))
    return result


def cure_encounter_conditions(core, encounter, actor, spell_id, **facts):
    """Apply a cure to sourced encounter conditions; other overlays remain separate."""
    entry = encounter.get('actorConditions', {}).get(actor, {})
    now = encounter_clock(encounter)['gameSeconds']
    instances = list(entry.get('conditionOverrides', ()))
    existing_ids = {i['id'] for i in instances}
    # Project direct and progressive defaults as temporary cure inputs.
    defaults = {f'condition:{key}': dict(id=f'condition:{key}', conditionId=key)
                for key in entry.get('conditions', ())}
    for family in ('fear', 'fatigue'):
        current = entry.get(family, {}).get('id')
        if current and current != 'clear':
            defaults[f'condition:{family}'] = dict(id=f'condition:{family}', conditionId=current, effectFamily=family)
    if existing_ids.intersection(defaults):
        raise ValueError('Condition override ID conflicts with a projected default')
    cured = apply_condition_cure(core, spell_id, instances + list(defaults.values()), now, **facts)
    kept = {i['id'] for i in cured if defaults.get(i['id']) == i}
    result = change_conditions(core, encounter, actor, remove=[i['conditionId'] for key, i in defaults.items() if key not in kept])
    return set_condition_overrides(core, result, actor, [i for i in cured if i['id'] not in kept])
