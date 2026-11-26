import json
import unittest

from tools.feat_selection import check_feat_selection
from tools.organize_core import PATH


class FeatSelectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.feats = json.loads(PATH.read_bytes())['feats']['byId']

    def status(self, feat, facts, **kwargs):
        return check_feat_selection(self.feats, feat, facts, **kwargs)['status']

    def test_all_feats_have_metadata(self):
        for feat in self.feats.values():
            self.assertTrue(feat['benefitText'])
            self.assertEqual(bool(feat['prerequisites']['text']) or feat['epic'], bool(feat['prerequisites']['allOf']))
            if feat['epic']:
                self.assertTrue(any(r['kind'] == 'level' and r['key'] == 'character' and r['minimum'] == 21
                                    for r in feat['prerequisites']['allOf']))
            for requirement in feat['prerequisites']['allOf']:
                if requirement['kind'] == 'feat':
                    self.assertIn(requirement['featId'], self.feats)

    def test_prerequisites_and_unknowns(self):
        self.assertEqual(self.status('power-attack', {'feats': [], 'abilityScores': {'str': 13}}), 'eligible')
        self.assertEqual(self.status('power-attack', {'feats': [], 'abilityScores': {'str': 12}}), 'ineligible')
        self.assertEqual(self.status('power-attack', {'feats': []}), 'needs-review')
        self.assertEqual(self.status('improved-familiar', {'feats': []}), 'needs-review')

    def test_targeted_prerequisites_and_repeatability(self):
        snapshot = {'feats': [{'featId': 'spell-focus', 'choices': {'schoolId': 'evocation'}}],
                    'validChoiceIdsByKey': {'schoolId': ['evocation', 'illusion']}}
        self.assertEqual(self.status('greater-spell-focus', snapshot, choices={'schoolId': 'illusion'}), 'ineligible')
        self.assertEqual(self.status('greater-spell-focus', snapshot, choices={'schoolId': 'evocation'}), 'eligible')
        self.assertEqual(self.status('spell-focus', snapshot, choices={'schoolId': 'evocation'}), 'ineligible')
        self.assertEqual(self.status('spell-focus', snapshot, choices={'schoolId': 'illusion'}), 'eligible')
        self.assertEqual(self.status('toughness', {'feats': [{'featId': 'toughness'}]}), 'eligible')
        self.assertEqual(self.status('alertness', {'feats': [{'featId': 'alertness', 'granted': True}]}), 'ineligible')

    def test_monk_bonus_slot_and_epic_gate(self):
        snapshot = {'feats': [], 'classLevels': {'monk': 1}, 'baseAttackBonus': 0}
        self.assertEqual(self.status('stunning-fist', snapshot), 'ineligible')
        self.assertEqual(self.status('stunning-fist', snapshot, monk_bonus_slot=1), 'eligible')
        self.assertEqual(self.status('stunning-fist', snapshot, monk_bonus_slot=2), 'ineligible')
        facts = {'feats': [], 'characterLevel': 20, 'sneakAttackDice': 8}
        self.assertEqual(self.status('improved-sneak-attack', facts), 'ineligible')
        self.assertEqual(self.status('improved-sneak-attack', dict(facts, characterLevel=21)), 'eligible')

    def test_exotic_strength_gate_uses_catalog_ids(self):
        snapshot = {'feats': [], 'baseAttackBonus': 1, 'abilityScores': {'str': 12}}
        self.assertEqual(self.status('exotic-weapon-proficiency', snapshot,
                                     choices={'weaponId': 'weapon:sword-bastard'}), 'ineligible')

    def test_maximum_normal_casting_thresholds_and_tradition(self):
        def qualifies(feat, levels, scores, **kwargs):
            facts = {'feats': [], 'characterLevel': 21, 'spellcastingLevels': levels, 'abilityScores': scores}
            return self.status(feat, facts, **kwargs)

        capacity, knowledge = 'improved-spell-capacity', 'spell-knowledge'
        for class_id, ability, level, score in (
                ('wizard', 'int', 17, 19), ('sorcerer', 'cha', 18, 19),
                ('cleric', 'wis', 17, 19), ('druid', 'wis', 17, 19),
                ('ranger', 'wis', 14, 20), ('ranger', 'wis', 15, 14),
                ('paladin', 'wis', 14, 20), ('paladin', 'wis', 15, 14),
                ('bard', 'cha', 16, 24), ('bard', 'cha', 17, 16),
                ('assassin', 'int', 7, 20), ('assassin', 'int', 8, 14),
                ('blackguard', 'wis', 7, 20), ('blackguard', 'wis', 8, 14)):
            with self.subTest(class_id=class_id, level=level):
                self.assertEqual(qualifies(capacity, {class_id: level}, {ability: score}), 'eligible')
                self.assertEqual(qualifies(capacity, {class_id: level}, {ability: score - 1}), 'ineligible')
                arcane = class_id in ('wizard', 'sorcerer', 'bard', 'assassin')
                self.assertEqual(qualifies(knowledge, {class_id: level}, {ability: score}),
                                 'eligible' if arcane else 'ineligible')

        self.assertEqual(qualifies(capacity, {'wizard': 17, 'druid': 16}, {'int': 18, 'wis': 30}), 'ineligible')
        self.assertEqual(qualifies(capacity, {'wizard': 17, 'ranger': 14}, {'int': 19, 'wis': 14},
                                   choices={'castingClassId': 'ranger'}), 'ineligible')
        self.assertEqual(qualifies(knowledge, {'wizard': 17}, {}), 'needs-review')
        self.assertEqual(self.status(knowledge, {'feats': [], 'characterLevel': 21, 'casterLevel': 30,
                                                'abilityScores': {'int': 19}}), 'needs-review')

    def test_familiar_spell_requires_intelligence_and_confirmed_familiar(self):
        facts = dict(characterLevel=21, feats=[], abilityScores={'int': 25}, hasFamiliar=True,
                     eligibleChoiceIdsByFeat={'familiar-spell': ['chain-lightning']})
        def status(**updates):
            return self.status('familiar-spell', dict(facts, **updates), choices={'spellId': 'chain-lightning'})
        self.assertEqual(status(), 'eligible')
        self.assertEqual(status(hasFamiliar=False), 'ineligible')
        self.assertEqual(status(hasFamiliar=None), 'needs-review')
        self.assertEqual(status(abilityScores={'int': 24, 'cha': 30}), 'ineligible')

    def test_spell_mastery_can_be_taken_again_for_known_spells(self):
        facts = dict(feats=[{'featId': 'spell-mastery', 'choices': {'spellIds': ['read-magic']}}],
                     classLevels={'wizard': 2}, abilityScores={'int': 14}, knownWizardSpellIds=['grease', 'shield'])
        self.assertEqual(self.status('spell-mastery', facts, choices={'spellIds': ['grease', 'shield']}), 'eligible')
        self.assertEqual(self.status('spell-mastery', facts, choices={'spellIds': ['grease', 'fireball']}), 'ineligible')
