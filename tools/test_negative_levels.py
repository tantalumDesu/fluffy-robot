import json
import unittest

from tools.negative_levels import (allocate_spell_losses, create_drain_levels, drain_death_aftermath,
                                   resolve_drain_level, summarize_negative_levels, weapon_negative_levels)
from tools.organize_core import PATH
from tools.sheet_effects import modifier_total
from tools.spellcasting import new_slots, plan_cast, prepare_spell, recover_slots, slot_budget, spend_slot


class NegativeLevelsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = json.loads(PATH.read_bytes())
        cls.rules = cls.core['mechanics']['negativeLevels']

    def test_opposed_weapon_is_conditional_and_distinct_from_drain(self):
        levels = weapon_negative_levels(self.core, 'CE', {'sword': ['holy', 'axiomatic', 'unholy']})
        self.assertEqual(len(levels), 2)
        status = summarize_negative_levels(self.rules, levels, 2)
        self.assertTrue(status['slain'])
        self.assertEqual((status['hitPointPenalty'], status['effectiveLevel']), (-10, 0))
        effects = [(e, {}) for e in status['modifiers']]
        for stat in ('skill:hide', 'ability-check:str', 'attack', 'save:fort'):
            self.assertEqual(modifier_total(stat, effects), -2)
        self.assertEqual(weapon_negative_levels(self.core, 'N', {'sword': ['holy']}), [])
        self.assertEqual(weapon_negative_levels(self.core, 'CE', {}), [])
        with self.assertRaises(ValueError):
            resolve_drain_level(self.rules, levels, levels[0]['id'], 86400, restoration=True)

    def test_energy_drain_is_resolved_per_level(self):
        drain = create_drain_levels(self.rules, 'hit', 2, 12, kind='creature', attacker_hd=7, attacker_cha_modifier=2)
        self.assertEqual(drain['bestowerTemporaryHp'], 10)
        levels = drain['levels']
        self.assertEqual((levels[0]['saveDc'], levels[0]['saveDueAtSeconds']), (15, 86412))
        with self.assertRaises(ValueError):
            resolve_drain_level(self.rules, levels, levels[0]['id'], 86411, fortitude_total=19)
        result = resolve_drain_level(self.rules, levels, levels[0]['id'], 86412, fortitude_total=14)
        self.assertEqual((result['permanentLevelLoss'], result['levels']), (1, levels[1:]))
        self.assertEqual(resolve_drain_level(self.rules, levels, levels[0]['id'], 12, restoration=True)
                         ['permanentLevelLoss'], 0)
        self.assertEqual(create_drain_levels(self.rules, 'spell', 1, 0, kind='spell-or-similar', save_dc=14)
                         ['bestowerTemporaryHp'], 0)
        self.assertEqual(drain_death_aftermath()['creatureTypeId'], 'wight')

    def test_slot_loss_chooses_highest_and_reduces_recovery(self):
        ledger = new_slots('wizard', slot_budget(self.core, 'wizard', 3, 14))
        lower = plan_cast(self.core, 'wizard', 'mage-armor', 14)
        higher = plan_cast(self.core, 'wizard', 'mage-armor', 14, metamagic=['extend-spell'], owned_feats=['extend-spell'])
        ledger = prepare_spell(ledger, 'regular:1:0', lower, accessible_spell_ids={'mage-armor'})
        ledger = prepare_spell(ledger, 'regular:2:0', higher, accessible_spell_ids={'mage-armor'})
        level = [dict(id='drain:1', kind='energy-drain')]
        result = allocate_spell_losses(self.core, {'wizard': ledger}, level, [])['wizard']
        with self.assertRaises(ValueError):
            spend_slot(result, 'regular:2:0', higher)
        self.assertFalse(ledger['slots']['regular:2:0'].get('negativeLevelLoss'))
        recovered = recover_slots(self.core, result, start_seconds=28800, end_seconds=32400, verified_rest_seconds=28800)
        with self.assertRaisesRegex(ValueError, 'Choose'):
            allocate_spell_losses(self.core, {'wizard': recovered}, level, [], recovery=True)
        reduced = allocate_spell_losses(self.core, {'wizard': recovered}, level, [('wizard', 'regular:2:1')], recovery=True)
        self.assertEqual(reduced['wizard']['slots']['regular:2:1']['negativeLevelLoss'], 'recovery')
        self.assertFalse(reduced['wizard']['slots']['regular:1:0'].get('negativeLevelLoss'))
