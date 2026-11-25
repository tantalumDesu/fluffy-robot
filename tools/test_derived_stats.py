import json
import unittest
from pathlib import Path

from tools.derived_stats import derive_sheet
from tools.game_time import new_encounter, spend_action, start_next_turn


class DerivedSheetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = json.loads((Path(__file__).resolve().parents[1] / 'dnd-core.json').read_text())

    def sheet(self, race='human', **kwargs):
        return derive_sheet(self.core, dict(characterLevel=3, classBaseCombat=dict(bab=3, fort=3, ref=1, will=1)),
                            race, dict(str=14, dex=16, con=12, int=10, wis=10, cha=10), **kwargs)

    def test_load_and_armor(self):
        armor = dict(instanceId='armor', itemId='armor:leather')
        sheet = self.sheet(equipment=[armor], carried_weight_lb=150)
        self.assertEqual(sheet['loadBand'], 'heavy')
        self.assertEqual(sheet['landSpeedFt'], 20)
        self.assertEqual(sheet['armorCheckPenalty'], -6)
        self.assertEqual({key: sheet['ac'][key]['total'] for key in ('normal', 'touch', 'flatFooted')},
                         dict(normal=13, touch=11, flatFooted=12))
        self.assertEqual(self.sheet('dwarf', carried_weight_lb=150)['landSpeedFt'], 20)

    def test_stun_drops_opposed_weapon_and_blocks_turn(self):
        weapon = dict(instanceId='blade', itemId='weapon:longsword', proficient=True, held=True,
                      alignmentPropertyIds=['holy'])
        ready = self.sheet(equipment=[weapon], alignment_id='NE')
        stunned = self.sheet(equipment=[weapon], alignment_id='NE', condition_ids=['stunned'])
        self.assertEqual(ready['attacks'][0]['attackBonus'], 4)
        self.assertEqual(stunned['saves']['fort'], ready['saves']['fort'] + 1)
        self.assertEqual(stunned['droppedInstanceIds'], ['blade'])
        self.assertEqual(stunned['attacks'][0]['itemId'], 'weapon:unarmed-strike')
        self.assertEqual(stunned['ac']['normal']['total'], 8)
        turn, _ = start_next_turn(new_encounter(['actor']), condition_flags_by_actor={'actor': stunned['conditionFlags']})
        with self.assertRaisesRegex(ValueError, 'cannot take actions'):
            spend_action(turn, 'standard')

    def test_absent_constitution_is_not_zero_and_ignores_bonuses(self):
        history = dict(characterLevel=3, classBaseCombat=dict(bab=3, fort=3, ref=1, will=1))
        scores = dict(str=14, dex=16, con=None, int=10, wis=10, cha=10)
        effect = dict(id='test-con', operation='modifier', statId='ability:con', amount=4, stacking='sum')
        absent = derive_sheet(self.core, history, 'human', scores, active_effects=[(effect, {})])
        self.assertIsNone(absent['abilityScores']['con'])
        self.assertEqual(absent['abilityModifiers']['con'], 0)
        self.assertEqual(absent['saves']['fort'], 3)
        zero = derive_sheet(self.core, history, 'human', dict(scores, con=0))
        self.assertEqual(zero['abilityModifiers']['con'], -5)

    def test_all_named_conditions_have_structured_rules(self):
        conditions = self.core['effects']['conditions']
        rules = self.core['effects']['sheetConditionRulesById']
        self.assertEqual(len(conditions), 38)
        self.assertEqual({c['id']: c['mechanics'] for c in conditions}, rules)
        for rule in rules.values():
            self.assertTrue(any(rule[k] for k in ('flags', 'modifiers', 'operations')))

    def test_condition_modifiers_and_implications(self):
        sheet = self.sheet(condition_ids=['sickened', 'frightened', 'shaken', 'entangled'])
        self.assertEqual(sheet['abilityScores']['dex'], 12)
        self.assertEqual(sheet['saves']['fort'], 0)
        self.assertEqual(sheet['landSpeedFt'], 15)
        paralyzed = self.sheet(condition_ids=['paralyzed'])
        self.assertEqual(paralyzed['abilityScores']['str'], 0)
        self.assertEqual(paralyzed['abilityScores']['dex'], 0)
        self.assertEqual(paralyzed['landSpeedFt'], 0)
        self.assertFalse(paralyzed['attacks'][0]['canAct'])

    def test_limited_turn_budgets(self):
        for condition in ('staggered', 'disabled', 'nauseated'):
            flags = self.sheet(condition_ids=[condition])['conditionFlags']
            turn, _ = start_next_turn(new_encounter(['actor']), condition_flags_by_actor={'actor': flags})
            with self.assertRaises(ValueError):
                spend_action(turn, 'full-round')
            turn = spend_action(turn, 'move')
            with self.assertRaises(ValueError):
                spend_action(turn, 'move')
