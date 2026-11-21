import json
import unittest

from tools.level_history import advance_level_history, replay_level_history
from tools.organize_core import PATH


class LevelHistoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = json.loads(PATH.read_bytes())

    def test_alternating_classes_select_only_their_next_row(self):
        history = replay_level_history(self.core, ['fighter', 'barbarian', 'fighter', 'barbarian'], xp=6000)
        self.assertEqual(history['classLevels'], {'fighter': 2, 'barbarian': 2})
        self.assertEqual([(e['characterLevel'], e['classLevel'], e['progressionRow']['level']) for e in history['entries']],
                         [(1, 1, 1), (2, 1, 1), (3, 2, 2), (4, 2, 2)])
        self.assertEqual([e['firstCharacterLevel'] for e in history['entries']], [True, False, False, False])
        self.assertEqual([e['generalFeatChoices'] for e in history['entries']], [1, 0, 1, 0])
        self.assertEqual(history['entries'][-1]['abilityScoreIncrease'], 1)

    def test_xp_and_choice_commit_together(self):
        choices = ['fighter', 'barbarian', 'fighter']
        result = advance_level_history(self.core, choices, 5000, 6000, class_id='barbarian')
        self.assertEqual((result['xp'], result['characterLevel'], result['discardedXp']), (9999, 4, 1001))
        self.assertEqual(result['classChoices'], choices + ['barbarian'])
        for xp, award, choice in [(5000, 1000, None), (5000, 1, 'barbarian'), (999, 1, 'fighter')]:
            with self.assertRaises(ValueError):
                advance_level_history(self.core, choices, xp, award, class_id=choice)
        self.assertEqual(advance_level_history(self.core, choices, 5000, 1)['classChoices'], choices)

    def test_racial_hit_dice_and_level_adjustment_are_distinct(self):
        result = advance_level_history(self.core, ['fighter'], 6000, 4000, class_id='barbarian',
                                       racial_hit_dice=2, level_adjustment=1)
        self.assertEqual((result['characterLevel'], result['effectiveCharacterLevel']), (4, 5))
        self.assertEqual(result['entries'][-1]['abilityScoreIncrease'], 1)
        self.assertEqual(result['entries'][-1]['classLevel'], 1)

    def test_epic_continuation_and_invalid_choices(self):
        history = replay_level_history(self.core, ['fighter'] * 21, xp=210000)
        self.assertEqual(history['classLevels'], {'fighter': 21})
        self.assertEqual(history['entries'][-1]['progressionClassId'], 'epic-fighter')
        for choices in [['epic-fighter'], ['archmage'] * 6, ['unknown'], [['fighter', 'barbarian']]]:
            with self.assertRaises(ValueError):
                replay_level_history(self.core, choices)
