"""Apply canon state transitions to caller-owned actor state (no encounter clock)."""
from copy import deepcopy


def transition(core, machine_id, state, event, *, facts=None):
    """Return (new state, emitted events); callers supply timing/eligibility facts."""
    machine = core['effects']['stateChangesById'][machine_id]
    state = deepcopy(state) if state is not None else {'id': machine['initial']}
    facts = facts or {}
    for rule in machine['transitions']:
        if rule['event'] != event or state['id'] not in rule['from']:
            continue
        if any(facts.get(key) != value for key, value in rule.get('requires', {}).items()):
            continue
        if rule.get('onlyOrigin') and state.get('origin') != rule['onlyOrigin']:
            continue
        return {'id': rule['to'], **({'origin': rule['origin']} if 'origin' in rule else {})}, deepcopy(rule.get('emit', []))
    return state, []


def end_rage(core, rage, fatigue, barbarian_level):
    """End an active rage once, whether it expired or was ended voluntarily."""
    rage, events = transition(core, 'rage', rage, 'rage-ended',
                              facts={'tirelessRage': barbarian_level >= 17})
    for event in events:
        fatigue, _ = transition(core, 'fatigue', fatigue, event)
    return rage, fatigue
