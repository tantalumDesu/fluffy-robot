import json
import unittest
from fractions import Fraction

from tools.creature_size import (armor_fit, carrying_limits, equipment_size, size_adjusted_abilities,
                                 size_profile, weapon_fit)
from tools.effect_state import active_effects, apply_spell
from tools.organize_core import PATH
from tools.sheet_effects import modifier_total


class CreatureSizeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = json.loads(PATH.read_bytes())
        cls.items = cls.core['inventory']['itemsById']

    def test_race_modifiers_and_load_overrides(self):
        result = size_profile(self.core, 'halfling')
        self.assertEqual((result['sizeId'], result['acAndAttack'], result['grapple'], result['hide']), ('small', 1, -4, 4))
        effects = [(effect, {}) for effect in result['modifiers'].values()]
        self.assertEqual(modifier_total('grapple', effects), -4)
        self.assertEqual(modifier_total('skill:hide', effects), 4)
        self.assertEqual(carrying_limits(self.core, 10, 'small')['heavyLb'], 75)
        self.assertEqual(carrying_limits(self.core, 20, 'large', 'quadruped')['lightLb'], 399)
        ox = self.core['companions']['creaturesById']['beasts-of-burden:ox']['carryingCapacity']
        self.assertEqual(carrying_limits(self.core, 20, 'large', 'quadruped', explicit=ox)['dragLb'], 6000)
        hobgoblin = size_profile(self.core, 'hobgoblin')
        self.assertEqual((hobgoblin['sizeId'], hobgoblin['acAndAttack'], hobgoblin['reachFt']), ('medium', 0, 5))

    def test_wrong_size_weapons(self):
        sword = self.items['weapon:longsword']
        result = weapon_fit(self.core, sword, 'small', 'medium', proficient=False)
        self.assertEqual((result['effectiveCategory'], result['damageDice'], result['sizeAttackPenalty'],
                          result['nonproficiencyPenalty']), ('Two-Handed Melee Weapon', '1d8', -2, -4))
        greatsword = self.items['weapon:greatsword']
        self.assertEqual(weapon_fit(self.core, greatsword, 'small', 'medium', proficient=True)['status'], 'cannot-wield')
        self.assertEqual(weapon_fit(self.core, sword, 'large', 'large', proficient=True)['damageDice'], '2d6')

    def test_armor_cost_fit_and_refit(self):
        plate = self.items['armor:full-plate']
        self.assertFalse(armor_fit(self.core, plate, 'medium', 'medium')['fits'])
        small = armor_fit(self.core, plate, 'small', 'small', fitted_for_wearer=True)
        self.assertEqual((small['weightLb'], small['priceCp'], small['armorClassBonus']), (25, 150000, 8))
        wrong = armor_fit(self.core, plate, 'small', 'medium', fitted_for_wearer=True)
        self.assertIsNone(wrong['armorClassBonus'])
        nonhumanoid = armor_fit(self.core, plate, 'large', 'large', armor_shape='nonhumanoid',
                                 wearer_shape='nonhumanoid', fitted_for_wearer=True)
        self.assertEqual((nonhumanoid['weightLb'], nonhumanoid['priceCp']), (100, 600000))

    def test_size_changing_spell_affects_gear_until_expiry(self):
        spells = self.core['effects']['spellEffectsBySpellId']
        active = apply_spell([], spells, 'enlarge-person', 1, 0, lambda sides: 1)
        profile = size_profile(self.core, 'human', active_effects=active_effects(active, spells, 9))
        self.assertEqual((profile['sizeId'], profile['reachFt']), ('large', 10))
        self.assertEqual(size_adjusted_abilities(profile, {'str': 14, 'dex': 2}), {'str': 16, 'dex': 1})
        enchanted = equipment_size(self.core, profile, 'medium', affected_by_size_change=True)
        self.assertEqual(enchanted, 'large')
        self.assertEqual(equipment_size(self.core, profile, 'medium'), 'medium')
        plate = armor_fit(self.core, self.items['armor:full-plate'], 'large', 'medium', fitted_for_wearer=True,
                          effective_armor_size=enchanted)
        self.assertTrue(plate['fits'])
        self.assertEqual(plate['manufacturedWeightLb'], Fraction(50))
        self.assertIsNone(plate['weightLb'])
        self.assertEqual(size_profile(self.core, 'human', active_effects=active_effects(active, spells, 10))['sizeId'], 'medium')
