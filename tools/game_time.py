"""Typed elapsed time, spell timing, and initiative-ordered encounter transitions."""
import re
from copy import deepcopy

SECONDS = {'round': 6, 'minute': 60, 'hour': 3600, 'day': 86400, 'week': 604800}
_ACTIONS = {'standard', 'move', 'full-round', 'free'}


def seconds(unit, amount):
    if type(amount) is not int or amount < 0:
        raise ValueError('Elapsed amount must be a nonnegative integer')
    return SECONDS[unit] * amount


def casting_timing(raw):
    text = raw.strip().lower().replace('one ', '1 ')
    if m := re.fullmatch(r'1 (standard|move|full-round|free) action', text):
        return dict(action=m[1], completion='current-turn', raw=raw)
    if m := re.fullmatch(r'(\d+) (?:full )?(round|minute|hour|day)s?', text):
        count, unit = int(m[1]), m[2]
        return dict(action='full-round', completion='initiative' if unit == 'round' else 'elapsed',
                    elapsed={'unit': unit, 'amount': count}, continuous=True, raw=raw)
    return dict(action=None, completion='manual', raw=raw)


def duration_timing(raw):
    text = raw.strip().lower()
    for key in ('instantaneous', 'permanent', 'concentration'):
        if text.startswith(key):
            return {'kind': key, 'raw': raw}
    if m := re.fullmatch(r'(\d+)\s*(round|min(?:ute)?|hr|hour|day|week)s?\.?(?:(?:/| per )level)?(?: \(d\))?', text):
        unit = {'min': 'minute', 'hr': 'hour'}.get(m[2], m[2])
        scaling = '/level' in text or ' per level' in text
        return dict(kind='initiative' if unit == 'round' else 'elapsed', unit=unit,
                    **{'perCasterLevel' if scaling else 'amount': int(m[1])}, raw=raw)
    return {'kind': 'manual', 'raw': raw}


def new_encounter(actor_order, *, start_seconds=0, surprise_actors=None, encounter_id=None):
    actors = list(actor_order)
    aware = None if surprise_actors is None else list(surprise_actors)
    if not actors or len(set(actors)) != len(actors) or (aware is not None and not set(aware) <= set(actors)):
        raise ValueError('Invalid initiative roster')
    if aware is not None and (not aware or set(aware) == set(actors)):
        aware = None
    return dict(order=actors, surpriseActors=aware, round=0 if aware is not None else 1,
                index=-1, startSeconds=start_seconds, encounterId=start_seconds if encounter_id is None else encounter_id,
                phase='between-turns', actions={}, pending={})


def encounter_clock(encounter):
    return dict(gameSeconds=encounter['startSeconds'] + (encounter['round'] -
                (0 if encounter['surpriseActors'] is not None else 1)) * SECONDS['round'],
                round=encounter['round'], initiativeIndex=encounter['index'], phase=encounter['phase'],
                encounterId=encounter['encounterId'])


def start_next_turn(encounter, *, condition_flags_by_actor=None, condition_flags_at_turn=None):
    """Advance in initiative order and return (state, completed cast plans)."""
    if encounter['phase'] not in ('between-turns', 'end'):
        raise ValueError('End the current turn first')
    state = deepcopy(encounter)
    while True:
        state['index'] += 1
        if state['index'] == len(state['order']):
            state['index'] = 0
            state['round'] += 1
        actor = state['order'][state['index']]
        if state['round'] != 0 or actor in state['surpriseActors']:
            break
    state['phase'] = 'start'
    state['actions'] = dict(standard=1, move=int(state['round'] != 0), quickened=False)
    state['spentActions'] = []
    state['castingConsumedTurn'] = False
    flags = (condition_flags_at_turn(state, actor) if condition_flags_at_turn is not None
             else (condition_flags_by_actor or {}).get(actor, ()))
    apply_turn_conditions(state, flags)
    if state['actions'].get('blocked') or 'allowed' in state['actions']:
        return state, []
    completed = []
    pending = state['pending'].get(actor)
    if pending:
        clock = encounter_clock(state)
        ready = (clock['round'] >= pending['readyRound'] if 'readyRound' in pending
                 else clock['gameSeconds'] >= pending['readySeconds'])
        if ready and not pending['plan']['timing'].get('extraFullRoundActions'):
            completed.append(state['pending'].pop(actor)['plan'])
        else:
            # Continuing a cast consumes the turn; the extra metamagic
            # full-round action, if due, completes at the end of this turn.
            if ready:
                pending['completeAtEnd'] = True
            state['actions'].update(standard=0, move=0)
            state['castingConsumedTurn'] = True
    return state, completed


def apply_turn_conditions(state, flags):
    """Recompute budgets from actions actually spent; never refund a spent action."""
    budget = dict(standard=1, move=int(state['round'] != 0), quickened=state['actions'].get('quickened', False))
    spent = state.get('spentActions', ())
    flags = set(flags)
    for payment in spent:
        for kind in payment:
            budget[kind] = 0
    if state.get('castingConsumedTurn'):
        budget.update(standard=0, move=0)
    if flags & {'no-actions', 'attention-only', 'mental-actions-only'}:
        budget.update(standard=0, move=0, blocked=True)
    elif 'single-move-only' in flags:
        budget.update(standard=0, move=int(not spent and not state.get('castingConsumedTurn')), allowed=['move'])
    elif 'single-move-or-standard' in flags:
        budget['singleAction'] = True
        if spent:
            budget.update(standard=0, move=0)
    if budget.get('blocked') or 'allowed' in budget:
        state['pending'].pop(state['order'][state['index']], None)
    state['actions'] = budget


def spend_action(encounter, action):
    if encounter['phase'] not in ('start', 'acting') or action not in _ACTIONS:
        raise ValueError('Not an available action phase or action type')
    state = deepcopy(encounter)
    actor = state['order'][state['index']]
    if state['actions'].get('blocked'):
        raise ValueError('Actor cannot take actions')
    if actor in state['pending']:
        raise ValueError('Caster is occupied by a continuous cast')
    budget = state['actions']
    if 'allowed' in budget and action not in budget['allowed']:
        raise ValueError('Action prohibited by condition')
    if action == 'full-round':
        if budget.get('singleAction'):
            raise ValueError('Full-round action prohibited by condition')
        if not (budget['standard'] and budget['move']):
            raise ValueError('A full-round action requires both actions')
        budget.update(standard=0, move=0)
        state.setdefault('spentActions', []).append(['standard', 'move'])
    elif action in ('move', 'standard'):
        pay = 'standard' if action == 'move' and not budget['move'] else action
        if not budget[pay]:
            raise ValueError('Action already spent')
        budget[pay] = 0
        state.setdefault('spentActions', []).append([pay])
        if budget.get('singleAction'):
            budget.update(standard=0, move=0)
    state['phase'] = 'acting'
    return state


def schedule_cast(encounter, actor, plan):
    """Commit the action; delayed spells return only when their timing resolves."""
    if encounter['index'] < 0 or encounter['order'][encounter['index']] != actor:
        raise ValueError('Not the caster’s turn')
    if plan.get('componentCheck', {}).get('status') == 'blocked':
        raise ValueError('Casting components unavailable: ' + ', '.join(plan['componentCheck']['blockedReasons']))
    if actor in encounter['pending']:
        raise ValueError('Finish or interrupt the pending cast before starting another')
    timing = plan['timing']
    if timing['completion'] == 'manual':
        raise ValueError('This casting time needs an explicit ruling')
    if 'quicken-spell' in plan['metamagic'] and encounter['actions'].get('quickened'):
        raise ValueError('Already quickened a spell this turn')
    state = spend_action(encounter, timing['action'])
    if 'quicken-spell' in plan['metamagic']:
        state['actions']['quickened'] = True
    if timing['completion'] == 'current-turn':
        return state, [deepcopy(plan)]
    elapsed = timing['elapsed']
    pending = {'plan': deepcopy(plan)}
    if timing['completion'] == 'initiative':
        pending['readyRound'] = state['round'] + elapsed['amount']
    else:
        pending['readySeconds'] = encounter_clock(state)['gameSeconds'] + seconds(elapsed['unit'], elapsed['amount'])
    state['pending'][actor] = pending
    return state, []


def end_turn(encounter):
    if encounter['phase'] not in ('start', 'acting'):
        raise ValueError('No active turn')
    state = deepcopy(encounter)
    state['phase'] = 'end'
    actor = state['order'][state['index']]
    pending = state['pending'].get(actor)
    return state, [state['pending'].pop(actor)['plan']] if pending and pending.get('completeAtEnd') else []


def interrupt_cast(encounter, actor):
    state = deepcopy(encounter)
    if actor not in state['pending']:
        raise ValueError('No pending cast')
    del state['pending'][actor]
    return state


def expiry_at(clock, unit, amount):
    if unit == 'round' and 'initiativeIndex' in clock:
        return {'kind': 'initiative', 'round': clock['round'] + amount,
                'initiativeIndex': clock['initiativeIndex'], 'encounterId': clock.get('encounterId'),
                'gameSeconds': clock['gameSeconds'] + seconds(unit, amount)}
    return {'kind': 'elapsed', 'gameSeconds': clock['gameSeconds'] + seconds(unit, amount)}


def expired(expiry, clock):
    if (expiry['kind'] == 'initiative' and 'initiativeIndex' in clock
            and expiry.get('encounterId') == clock.get('encounterId')):
        return (clock['round'], clock['initiativeIndex']) >= (expiry['round'], expiry['initiativeIndex'])
    return clock['gameSeconds'] >= expiry['gameSeconds']


def schedule_downtime_cast(plan, game_seconds):
    """Return a completion timestamp for a cast outside initiative, without spending slots."""
    if plan.get('componentCheck', {}).get('status') == 'blocked':
        raise ValueError('Casting components unavailable: ' + ', '.join(plan['componentCheck']['blockedReasons']))
    timing = plan['timing']
    if timing['completion'] == 'manual':
        raise ValueError('This casting time needs an explicit ruling')
    interval = timing.get('elapsed')
    delay = seconds(interval['unit'], interval['amount']) if interval else 0
    delay += seconds('round', timing.get('extraFullRoundActions', 0))
    return {'completion': {'kind': 'elapsed', 'gameSeconds': game_seconds + delay},
            'plan': deepcopy(plan)}
