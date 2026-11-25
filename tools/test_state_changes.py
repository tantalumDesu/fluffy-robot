import json
from pathlib import Path
import unittest

from tools.state_changes import end_rage, transition
from tools.derived_stats import condition_state
from tools.sheet_effects import modifier_total

CORE = json.loads((Path(__file__).resolve().parents[1] / 'dnd-core.json').read_text())


class StateChangesTest(unittest.TestCase):
    def test_post_rage_uses_shared_fatigue(self):
        raging, _ = transition(CORE, 'rage', None, 'rage-started')
        ordinary, _ = transition(CORE, 'fatigue', None, 'fatigue-applied')
        ended, fatigue = end_rage(CORE, raging, None, 16)
        self.assertEqual(fatigue['id'], 'fatigued')
        self.assertEqual(end_rage(CORE, ended, fatigue, 16)[1], fatigue)
        self.assertEqual(end_rage(CORE, raging, ordinary, 17)[1], ordinary)
        self.assertEqual(transition(CORE, 'fatigue', fatigue, 'encounter-ended')[0]['id'], 'clear')
        self.assertEqual(transition(CORE, 'fatigue', ordinary, 'encounter-ended')[0], ordinary)
        exhausted = end_rage(CORE, raging, ordinary, 16)[1]
        self.assertEqual(exhausted['id'], 'exhausted')
        self.assertEqual(transition(CORE, 'fatigue', exhausted, 'encounter-ended')[0], exhausted)
        self.assertEqual(transition(CORE, 'fatigue', exhausted, 'one-hour-complete-rest')[0], ordinary)
        flags, modifiers, _ = condition_state(CORE, ['fatigued', 'exhausted'])
        self.assertIn('half-speed', flags)
        self.assertEqual(modifier_total('ability:str', [(m, {}) for m in modifiers]), -6)

    def test_fear_and_sunlight_use_same_transition_shape(self):
        state = None
        for expected in ('shaken', 'frightened', 'panicked'):
            state, _ = transition(CORE, 'fear', state, 'shaken-applied')
            self.assertEqual(state['id'], expected)
        state, _ = transition(CORE, 'vampire-sunlight', None, 'sunlight-entered')
        self.assertEqual(transition(CORE, 'vampire-sunlight', state, 'sunlight-left')[0]['id'], 'clear')
        self.assertEqual(transition(CORE, 'vampire-sunlight', state, 'next-round-still-exposed')[0]['id'], 'destroyed')

    def test_catalogue_water_machine_uses_core_transition_helper(self):
        catalogue = json.loads((Path(__file__).resolve().parents[1] / 'dnd35_templates.json').read_text())
        vampire = next(t for t in catalogue['templates'] if t['id'] == 'vampire')
        core = {'effects': {'stateChangesById': vampire['environmentStatesById']}}
        key = 'running-water-immersion'
        self.assertEqual(transition(core, key, None, 'exposure-on')[0]['id'], 'clear')
        state, _ = transition(core, key, None, 'exposure-on', facts={'baseCreatureHasNaturalSwimSpeed': False})
        for expected in ('one-round', 'two-rounds', 'destroyed'):
            state, _ = transition(core, key, state, 'exposed-round-elapsed')
            self.assertEqual(state['id'], expected)
        self.assertEqual(transition(core, key, state, 'exposure-off')[0]['id'], 'destroyed')
