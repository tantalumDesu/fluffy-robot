import json
import unittest

from tools.test_level_drain_lifecycle import fail_drain

from tools.drain_history import (apply_permanent_level_loss, derive_level_loss_sheet,
                                 projected_level_grants)
from tools.organize_core import PATH


class LevelLossTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = json.loads(PATH.read_bytes())

    def test_recorded_grants_and_companion_reproject(self):
        feat = {'featId': 'toughness'}
        grants = dict(hpGain=5, abilityIncreases={}, skillRanks={'jump': 2}, featChoices=[feat])
        actor = dict(classChoices=['druid'] * 3, xp=3100, maxHp=25, featChoices=[feat],
                     abilityScores=dict(str=16, dex=12, con=12, int=10, wis=16, cha=10),
                     skillRanks={'jump': 4}, levelGrantsByLevel={'3': grants})
        lost = apply_permanent_level_loss(self.core, actor, 'loss:1', 0)
        projected = projected_level_grants(self.core, lost)
        self.assertEqual(projected['xp'], 2000)
        self.assertEqual(projected['history']['classBaseCombat']['bab'], 1)
        self.assertEqual(projected['skillRanks']['jump'], 2)
        self.assertEqual(projected['featChoices'], [])
        self.assertEqual(projected['maxHp'], 20)
        self.assertEqual(actor['featChoices'], [feat])
        sheet = derive_level_loss_sheet(self.core, lost, 'human', companion_links=[
            dict(instanceId='wolf', definitionId='animal-companions:wolf', bonusHitDieRolls=[4, 5])])
        self.assertEqual(sheet['companions'][0]['effectiveMasterLevel'], 2)
        self.assertEqual(sheet['companions'][0]['bonusHitDice'], 0)

    def test_missing_allocations_are_rejected(self):
        actor = dict(classChoices=['fighter'] * 4, xp=6100,
                     abilityScores={'str': 18, 'dex': 12}, skillRanks={'jump': 7, 'climb': 3})
        with self.assertRaisesRegex(ValueError, 'complete recorded advancement'):
            apply_permanent_level_loss(self.core, actor, 'loss:2', 0)

    def test_level_up_records_exact_grants_and_award_is_atomic(self):
        from tools.level_choices import record_level_choices
        actor = dict(classChoices=[], xp=0, abilityScores=dict(str=16, dex=12, con=13, int=10, wis=16, cha=10))
        first = dict(hitDieRoll=8, abilityIncreases={}, skillRanks={'concentration': 4}, featChoices=[
            {'featId': 'toughness'}, {'featId': 'iron-will', 'source': 'racial'}])
        actor = record_level_choices(self.core, actor, 'human', class_id='druid', choices=first)
        self.assertEqual(actor['maxHp'], 12)
        for award, feats in ((1000, []), (2000, [{'featId': 'great-fortitude'}])):
            actor = record_level_choices(self.core, actor, 'human', class_id='druid', xp_award=award,
                                         choices=dict(hitDieRoll=4, abilityIncreases={}, skillRanks={}, featChoices=feats))
        fourth = dict(hitDieRoll=5, abilityIncreases={'con': 1}, skillRanks={'concentration': 2}, featChoices=[])
        with self.assertRaisesRegex(ValueError, 'Hit Die'):
            record_level_choices(self.core, actor, 'human', class_id='druid', xp_award=3000,
                                 choices=dict(fourth, hitDieRoll=9))
        self.assertEqual(actor['xp'], 3000)
        advanced = record_level_choices(self.core, actor, 'human', class_id='druid', xp_award=3000, choices=fourth)
        self.assertEqual(advanced['levelGrantsByLevel']['4']['hpGain'], 10)
        self.assertEqual(advanced['skillRanks']['concentration'], 6)
        lost = fail_drain(self.core, advanced, 'loss:4')
        lower = projected_level_grants(self.core, lost)
        self.assertEqual(lower['maxHp'], actor['maxHp'])
        self.assertEqual(lower['abilityScores'], actor['abilityScores'])
        self.assertEqual(lower['skillRanks'], actor['skillRanks'])
        from tools.drain_history import restore_character_drain
        restored = restore_character_drain(self.core, lost, 'restoration', 86401, 7)
        active = projected_level_grants(self.core, restored)
        for field in ('maxHp', 'abilityScores', 'skillRanks', 'featChoices'):
            self.assertEqual(active[field], advanced[field])
