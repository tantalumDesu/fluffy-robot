"""Catalogue-only environment profiles in the core state-transition format."""

# Template ID: independent switches, with pointers into the original prose.
# A switch represents a resolved table fact, not a player's choice or a map query.
PROFILES = {
    'half-scrag': [('immersed-in-water', (0,), 'round')],
    'ooze-elemental-creature': [('wood-or-metal-contact', (2,), 'round')],
    'wood-elemental-creature': [('plant-contact-within-sense-range', (2,), None)],
    'katane': [('bright-sunlight', (12,), None), ('daylight-spell', (12,), None)],
    'air-elemental-creature': [('airborne-opponent', (0,), None)],
    'earth-elemental-creature': [('both-touch-ground', (0,), None), ('opponent-in-air-or-water', (1,), None),
                                 ('ground-contact-within-sense-range', (2,), None)],
    'water-elemental-creature': [('both-touch-water', (0,), None), ('either-on-land', (2,), None)],
    'entropic-creature': [('negative-dominant-environment', (0,), None)],
    'vivacious-creature': [('positive-dominant-environment', (0,), None)],
    'shadow-creature': [('shadow-blend-available', (1,), None)],
    'bodak': [('sunlight-exposure', (5,), 'round')],
    'cauldron-spawn': [('away-from-cauldron', (1,), 'day')],
    'dry-lich': [('arid-without-water-effect', (1,), 'round')],
    'spectral': [('natural-sunlight', (5,), None)],
    'drowned-one': [('unshielded-direct-sunlight', (9,), None)],
    'necromental': [('near-matching-element', (3,), 'round')],
    'vampire-moonbane': [('moonlight-exposure', (0,), None)],
    'dustform': [('sandy-or-dusty-environment', (8,), None)],
    'mirage-mullah': [('natural-sunlight', (0,), None), ('away-from-origin-oasis', (1,), 'hour')],
    'faerzress-infused': [('faerzress-region', (0,), None), ('faerzress-or-earth-node', (1,), None)],
    'shadow-vampire': [('shadows-or-darkness', (13,), None), ('daylight-spell-in-shadow-form', (14,), None),
                       ('daylight-weakness', (17,), None)],
}
VAMPIRES = {
    'vampire': (21, 22, 17, 19, 18), 'savage-vampire': (13, 14, None, None, None),
    'shadow-vampire': (22, 23, 18, 20, 19), 'terror-vampire': (21, 22, 17, 19, 18),
}


def transition(event, before, after, **extra):
    return {'event': event, 'from': [before], 'to': after, **extra}


def attach_environment(entry):
    key = entry['id']
    profiles = list(PROFILES.get(key, ()))
    if key in VAMPIRES:
        sunlight, water, garlic, crossing, repulsion = VAMPIRES[key]
        profiles += [('vampire-sunlight', (sunlight,), None), ('running-water-immersion', (water,), None)]
        for name, index in [('garlic-area', garlic), ('running-water-crossing', crossing),
                            ('presented-holy-symbol-or-mirror', repulsion)]:
            if index is not None:
                profiles.append((name, (index,), None))
    entry.pop('environmentStatesById', None)
    if not profiles:
        return
    machines = entry['environmentStatesById'] = {}
    for name, indices, cadence in profiles:
        if not all(0 <= i < len(entry['other_effects']) for i in indices):
            raise ValueError(f'Invalid environment source: {key}/{name}')
        machine = dict(initial='clear', referenceOnly=True,
                       source=dict(file='dnd35_templates.json', templateId=key, effectIndexes=list(indices)),
                       transitions=[transition('exposure-on', 'clear', 'exposed'),
                                    transition('exposure-off', 'exposed', 'clear')],
                       statesById={'exposed': {'sourceEffectsActive': True}})
        machines[name] = machine
        if cadence:
            machine['transitions'].append(transition(f'exposed-{cadence}-elapsed', 'exposed', 'exposed',
                                                     emit=['resolve-source-effect']))
        if name == 'vampire-sunlight':
            machine['transitions'].append(transition('next-round-still-exposed', 'exposed', 'destroyed'))
            machine['statesById']['exposed'].update(allowedActionChoice=['move', 'attack'], actionsMaximum=1)
        elif name == 'running-water-immersion':
            machine['transitions'] = [transition('exposure-on', 'clear', 'exposed',
                                                 requires={'baseCreatureHasNaturalSwimSpeed': False})]
            for state in ('exposed', 'one-round', 'two-rounds'):
                machine['transitions'].append(transition('exposure-off', state, 'clear'))
                machine['statesById'][state] = {'sourceEffectsActive': True}
            for before, after in [('exposed', 'one-round'), ('one-round', 'two-rounds'), ('two-rounds', 'destroyed')]:
                machine['transitions'].append(transition('exposed-round-elapsed', before, after,
                                                         emit=['resolve-source-effect'] if after != 'destroyed' else []))
