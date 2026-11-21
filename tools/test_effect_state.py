import json
import unittest

from tools.effect_state import (active_effects, active_spells, apply_spell, blocks_effect, constitution_hp_delta,
                                consume_temporary_hp, full_attack_extra_attacks, movement_speed, opportunity_attack_limit)
from tools.organize_core import PATH
from tools.sheet_effects import modifier_total


class EffectStateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = json.loads(PATH.read_bytes())
        cls.spells = cls.core['effects']['spellEffectsBySpellId']
        cls.feats = cls.core['effects']['featEffectsByFeatId']

    def test_equipment_and_creature_updates(self):
        inventory = self.core['inventory']
        items = inventory['itemsById']
        self.assertEqual(inventory['fallbackWeaponId'], 'weapon:unarmed-strike')
        for item in items.values():
            profile = item.get('attackProfile')
            if profile:
                self.assertEqual(item['weightLb'], 0)
                self.assertFalse(profile['carriedSeparately'])
                self.assertTrue(all(id_ in items for id_ in profile.get('hostItemIds', [])))
                if profile.get('requiredAdditionId'):
                    self.assertEqual(items[profile['requiredAdditionId']]['weightLb'], 0)
        creatures = self.core['companions']['creaturesById']
        self.assertEqual(creatures['alternative-animal-companions:ape']['size'], 'large')
        self.assertEqual(creatures['alternative-animal-companions:bear-black']['size'], 'medium')

    def test_expiry_and_dispel(self):
        active = apply_spell([], self.spells, 'bless', 1, 12, lambda sides: sides)
        self.assertEqual(modifier_total('attack', active_effects(active, self.spells, 21)), 1)
        self.assertEqual(active_spells(active, 22), [])
        self.assertEqual(apply_spell(active, self.spells, 'bane', 1, 13, lambda sides: sides,
                                     opposed_spell_ids=['bless']), [])
        with self.assertRaises(ValueError):
            apply_spell(active, self.spells, 'bless', 1, 13, lambda sides: sides)

    def test_temporary_hp_and_constitution(self):
        cast, = apply_spell([], self.spells, 'false-life', 12, 0, lambda sides: 5)
        effect, = self.spells['false-life']
        self.assertEqual(cast['temporaryHp'][effect['id']], 15)
        self.assertEqual(consume_temporary_hp(cast, [effect], effect['id'], 17), (None, 2))
        self.assertEqual(cast['temporaryHp'][effect['id']], 15)
        self.assertEqual(constitution_hp_delta(11, 15, 6), 12)
        self.assertEqual(constitution_hp_delta(15, 11, 6), -12)

    def test_new_feat_and_spell_context(self):
        point_blank = [(e, {}) for e in self.feats['point-blank-shot']]
        self.assertEqual(modifier_total('attack', point_blank, {'attackKind': 'ranged', 'distanceFt': 30}), 1)
        self.assertEqual(modifier_total('attack', point_blank, {'attackKind': 'ranged', 'distanceFt': 31}), 0)
        defense = [(e, {}) for e in self.feats['two-weapon-defense']]
        self.assertEqual(modifier_total('ac', defense, {'qualifiesForTwoWeaponDefense': True, 'defensiveStance': True}), 2)
        reflexes = [(e, {}) for e in self.feats['combat-reflexes']]
        self.assertEqual(opportunity_attack_limit(3, True, reflexes), 4)
        self.assertEqual(opportunity_attack_limit(3, True, []), 0)
        haste = [(e, {}) for e in self.spells['haste']]
        self.assertEqual(movement_speed(20, haste * 2), 40)
        self.assertEqual(movement_speed(40, haste, other_enhancement=10), 70)
        self.assertEqual(movement_speed(0, haste), 0)

        self.assertEqual(full_attack_extra_attacks(haste * 2, full_attack=True, held_weapon=True,
                                                  other_noncumulative=1), 1)
        self.assertEqual(full_attack_extra_attacks(haste, full_attack=False, held_weapon=True), 0)
        shield = [(effect, {}) for effect in self.spells['shield']]
        self.assertTrue(blocks_effect(shield, spell_id='magic-missile'))
        self.assertFalse(blocks_effect(shield, spell_id='fireball'))
