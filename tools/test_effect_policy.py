import unittest

from tools.effect_policy import application_mode
from tools.sheet_effects import modifier_total


class EffectPolicyTest(unittest.TestCase):
    def test_non_sheet_and_other_target_effects_are_manual(self):
        self.assertEqual(application_mode({'operation': 'immunity', 'amount': 2}), 'adjudicate')
        effect = dict(operation='modifier', target='opponent', statId='ac', amount=2,
                      stacking='sum', applicationMode='adjudicate')
        self.assertEqual(application_mode(effect), 'adjudicate')
        self.assertEqual(modifier_total('ac', [(effect, {})]), 0)
        self.assertEqual(application_mode(dict(effect, target='recipient')), 'recipient-sheet')
