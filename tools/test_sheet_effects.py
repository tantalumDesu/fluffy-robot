import json
import unittest

from tools.organize_core import PATH
from tools.sheet_effects import modifier, modifier_total


class SheetEffectsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        effects = json.loads(PATH.read_bytes())['effects']
        cls.spells = effects['spellEffectsBySpellId']
        cls.feats = effects['featEffectsByFeatId']

    def active(self, key, **params):
        return [(effect, params) for effect in (self.spells if key in self.spells else self.feats)[key]]

    def test_armor_stacking_and_touch(self):
        effects = self.active('mage-armor') + self.active('shield') + [(modifier('ac', 6, 'armor'), {})]
        self.assertEqual(modifier_total('ac', effects), 10)
        self.assertEqual(modifier_total('ac', effects, {'attackMode': 'touch'}), 0)
        self.assertEqual(modifier_total('ac', effects, {'attackMode': 'incorporeal-touch'}), 8)

    def test_morale_and_fear(self):
        effects = self.active('bless') + self.active('aid') + self.active('heroism')
        self.assertEqual(modifier_total('save:will', effects, {'saveAgainst': 'fear'}), 2)
        self.assertEqual(modifier_total('save:will', self.active('bless')), 0)
        self.assertEqual(modifier_total('save:will', self.active('bane'), {'saveAgainst': 'fear'}), -1)

    def test_scaling_and_durations(self):
        self.assertEqual(modifier_total('natural-armor', self.active('barkskin', casterLevel=6)), 3)
        self.assertEqual(modifier_total('natural-armor', self.active('barkskin', casterLevel=15)), 5)
        self.assertEqual(modifier_total('attack', self.active('divine-favor', casterLevel=2)), 1)
        self.assertEqual(modifier_total('weapon-damage', self.active('divine-favor', casterLevel=15)), 3)
        self.assertEqual(self.spells['resistance'][0]['duration'], {'unit': 'minute', 'amount': 1})
        self.assertEqual(self.spells['shield'][0]['duration']['perCasterLevel'], 1)

    def test_feat_choices_and_repeated_grants(self):
        focus = self.active('weapon-focus', weaponId='sword')
        greater = self.active('greater-weapon-focus', weaponId='sword')
        self.assertEqual(modifier_total('attack', focus * 2 + greater, {'weaponId': 'sword'}), 2)
        self.assertEqual(modifier_total('attack', focus, {'weaponId': 'axe'}), 0)
        self.assertEqual(modifier_total('max-hp', self.active('toughness') * 2), 6)
        dodge = self.active('dodge', opponentId='orc')
        self.assertEqual(modifier_total('ac', dodge, {'attackerId': 'orc'}), 1)
        self.assertEqual(modifier_total('ac', dodge, {'attackerId': 'orc', 'flags': ['denied-dex-to-ac']}), 0)

    def test_ability_enhancements_do_not_stack(self):
        effects = self.active('foxs-cunning') + self.active('foxs-cunning-mass')
        self.assertEqual(modifier_total('ability:int', effects), 4)
        self.assertFalse(self.spells['foxs-cunning'][0]['grantsSkillPoints'])
        self.assertFalse(self.spells['foxs-cunning'][0]['grantsBonusSpellSlots'])

    def test_deflection_scaling_and_alignment_context(self):
        faith = self.active('shield-of-faith', casterLevel=12)
        evil = self.active('protection-from-evil')
        self.assertEqual(modifier_total('ac', faith + evil, {'sourceAlignmentTags': ['evil']}), 4)
        self.assertEqual(modifier_total('ac', evil, {'sourceAlignmentTags': ['good']}), 0)
        self.assertEqual(modifier_total('save:ref', evil, {'sourceAlignmentTags': ['evil']}), 2)
        self.assertEqual(modifier_total('ac', self.active('shield-of-faith', casterLevel=-1)), 0)

    def test_skill_identity_and_dodge_suppression(self):
        focus = self.active('skill-focus', skillId='jump')
        self.assertEqual(modifier_total('skill:jump', focus), 3)
        self.assertEqual(modifier_total('skill:listen', focus, {'skillId': 'jump'}), 0)
        effects = [(dict(modifier('ac', amount, 'dodge'), id=id_), {})
                   for id_, amount in [('one', 1), ('two', 2)]]
        self.assertEqual(modifier_total('ac', effects + effects), 2)
        self.assertEqual(modifier_total('ac', effects, {'flags': ['denied-dex-to-ac']}), 0)

    def test_named_types_take_best_bonus_and_worst_penalty(self):
        for tag in ('morale', 'dodge', 'circumstance'):
            with self.subTest(tag=tag):
                effects = [(dict(modifier('attack', amount, tag), stacking='sum'), {})
                           for amount in (2, 4, -1, -3)]
                effects.append((modifier('attack', 3, 'luck'), {}))
                self.assertEqual(modifier_total('attack', effects), 4)
