import json
import unittest

from tools.feat_selection import check_feat_selection
from tools.improved_familiars import check_improved_familiar
from tools.organize_core import PATH


class ImprovedFamiliarTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = json.loads(PATH.read_bytes())

    def test_feat_and_acquisition_are_separate(self):
        feats = self.core['feats']['byId']
        self.assertEqual(check_feat_selection(feats, 'improved-familiar', {
            'feats': [], 'hasFamiliarAcquisitionAbility': True})['status'], 'eligible')
        facts = dict(feats=[{'featId': 'improved-familiar'}], canAcquireFamiliar=True,
                     classLevels={'wizard': 5}, alignmentId='N', baseAttackBonus=5)

        def status(option='blink-dog', **updates):
            return check_improved_familiar(self.core, option, dict(facts, **updates))['status']

        self.assertEqual(status(), 'eligible')
        self.assertEqual(status(baseAttackBonus=4), 'ineligible')
        self.assertEqual(status(baseAttackBonus=None), 'needs-review')
        self.assertEqual(status(classLevels={'sorcerer': 10}), 'ineligible')
        self.assertEqual(status(alignmentId='CE'), 'ineligible')
        self.assertEqual(status(canAcquireFamiliar=False), 'ineligible')
        self.assertEqual(status('imp'), 'needs-review')
        self.assertEqual(status('fire-elemental-small', baseAttackBonus=None), 'eligible')

    def test_vargouille_excludes_kiss_and_retains_source(self):
        options = self.core['companions']['improvedFamiliarOptionsById']
        option = options['vargouille-without-kiss']
        self.assertEqual(option['excludedAbilityIds'], ['kiss'])
        self.assertIn('does not have Kiss', option['adjudicationText'])
        self.assertTrue(all(o['statBlockText'] for o in options.values()))
