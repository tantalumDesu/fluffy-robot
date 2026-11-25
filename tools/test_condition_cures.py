import json
from pathlib import Path
import unittest

from tools.condition_cures import active_condition_ids, apply_condition_cure, cure_actor
from tools.drain_history import remove_negative_level
from tools.encounter_conditions import advance_turn, cure_encounter_conditions, set_condition_overrides
from tools.game_time import new_encounter, spend_action

CORE = json.loads((Path(__file__).resolve().parents[1] / 'dnd-core.json').read_text())


class ConditionCureTest(unittest.TestCase):
    def test_midturn_heal_only_changes_overlays(self):
        state, _ = advance_turn(CORE, new_encounter(['a']))
        state = spend_action(state, 'move')
        stunned = dict(id='hit', conditionId='stunned')
        state = set_condition_overrides(CORE, state, 'a', [stunned])
        cured = cure_encounter_conditions(CORE, state, 'a', 'heal', resolved=True)
        self.assertEqual(state['actorConditions']['a']['conditionOverrides'], [stunned])
        self.assertEqual(cured['actions']['move'], 0)
        self.assertEqual(cured['actions']['standard'], 1)

    def test_fear_suppression_expires_and_cause_fear_is_dispelled(self):
        instances = [dict(id='a', conditionId='shaken', effectFamily='fear'),
                     dict(id='b', conditionId='shaken', effectFamily='fear', sourceSpellId='cause-fear')]
        result = apply_condition_cure(CORE, 'remove-fear', instances, 10, resolved=True)
        self.assertEqual(active_condition_ids(result, 609), [])
        self.assertEqual(active_condition_ids(result, 610), ['shaken'])
        self.assertEqual([i['id'] for i in result], ['a'])

    def test_heal_does_not_cure_undead_or_remove_negative_levels(self):
        actor = dict(abilityScores={'str': 12}, abilityDamage={'str': 3}, negativeLevels=[{'id': 'one'}])
        self.assertEqual(cure_actor(CORE, actor, 'heal', 1, resolved=True, target_kind='undead'), actor)
        result = cure_actor(CORE, actor, 'heal', 1, resolved=True)
        self.assertEqual(result['abilityDamage'], {})
        self.assertEqual(result['abilityScores'], actor['abilityScores'])
        self.assertEqual(result['negativeLevels'], actor['negativeLevels'])

    def test_remove_one_negative_level_unlocks_only_its_recovery_slot(self):
        actor = dict(xp=1000, negativeLevels=[dict(id=k, kind='energy-drain') for k in ('a', 'b')],
                     spellLedgers={'wizard': {'slots': {k: dict(negativeLevelId=k, negativeLevelLoss='recovery')
                                                        for k in ('a', 'b')}}})
        result = remove_negative_level(actor, 'a')
        self.assertEqual([i['id'] for i in result['negativeLevels']], ['b'])
        self.assertEqual(result['spellLedgers']['wizard']['slots']['a'], {})
        self.assertEqual(result['spellLedgers']['wizard']['slots']['b']['negativeLevelLoss'], 'recovery')
        self.assertEqual(result['xp'], actor['xp'])
