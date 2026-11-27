import json
import unittest

from tools.effect_state import active_effects, apply_spell
from tools.negative_levels import (active_negative_levels, apply_drain_restoration, apply_drain_spell,
                                   resolve_drain_level, summarize_negative_levels, weapon_negative_levels)
from tools.organize_core import PATH
from tools.sheet_effects import modifier_total
from tools.spellcasting import new_slots, plan_cast, slot_budget


class SpellDrainTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = json.loads(PATH.read_bytes())
        cls.rules = cls.core['mechanics']['negativeLevels']

    def ray(self, spell_id, **kwargs):
        plan = plan_cast(self.core, 'wizard', spell_id, 20)
        return apply_drain_spell(self.core, plan, 'ray', kwargs.pop('levels', []), 0, 20, lambda sides: 2,
                                 **dict({'hit': True, 'spell_resistance_passed': True, 'target_kind': 'living'}, **kwargs))

    def test_enervation_short_duration_and_typed_stats(self):
        slots = new_slots('sorcerer', slot_budget(self.core, 'sorcerer', 1, 12))
        result = self.ray('enervation', ledgers={'sorcerer': slots},
                          choices=[('sorcerer', 'regular:1:0'), ('sorcerer', 'regular:1:1')])
        self.assertEqual(len(result['levels']), 2)
        self.assertEqual(result['ledgers']['sorcerer']['slots']['regular:1:1']['negativeLevelLoss'], 'immediate')
        summary = summarize_negative_levels(self.rules, result['levels'], 8)
        effects = [(e, {}) for e in summary['modifiers']]
        for stat, amount in [('hp', -10), ('effective-level', -2), ('attack', -2), ('ability-check:str', -2)]:
            self.assertEqual(modifier_total(stat, effects), amount)
        self.assertEqual(len(active_negative_levels(result['levels'], 53999)), 2)
        self.assertEqual(active_negative_levels(result['levels'], 54000), [])
        self.assertEqual(resolve_drain_level(self.rules, result['levels'], result['levels'][0]['id'], 54000)
                         ['drainedLevel'], 0)

    def test_energy_drain_spell_dc_and_undead_benefit(self):
        result = self.ray('energy-drain')
        self.assertEqual(result['bestowerTemporaryHp'], 0)
        self.assertEqual(len(result['levels']), 4)
        self.assertTrue(all(level['saveDc'] == 24 for level in result['levels']))
        self.assertEqual(active_negative_levels(result['levels'], 86400), result['levels'])
        self.assertEqual(resolve_drain_level(self.rules, result['levels'], result['levels'][0]['id'], 86400,
                                             fortitude_total=23)['drainedLevel'], 1)
        undead = self.ray('energy-drain', target_kind='undead')
        self.assertEqual(undead['temporaryHp'], {'amount': 20, 'expiresAtSeconds': 3600})
        self.assertEqual(undead['levels'], [])
        self.assertEqual(self.ray('enervation', spell_resistance_passed=False)['levels'], [])

    def test_death_ward_and_restoration(self):
        catalog = self.core['effects']['spellEffectsBySpellId']
        ward = apply_spell([], catalog, 'death-ward', 10, 0, lambda sides: 1)
        levels = self.ray('enervation')['levels']
        blocked = self.ray('energy-drain', levels=levels, target_effects=active_effects(ward, catalog, 0))
        self.assertEqual(blocked['levels'], levels)
        held = weapon_negative_levels(self.core, 'LE', {'sword': ['holy']})
        losses = [{'id': 'old', 'failedSaveAtSeconds': 0, 'cause': 'energy-drain'},
                  {'id': 'new', 'failedSaveAtSeconds': 86400, 'cause': 'energy-drain'},
                  {'id': 'death', 'lostAtSeconds': 172800, 'dueToDeath': True}]
        normal = apply_drain_restoration(self.core, 'restoration', levels + held, losses, 172800, 1)
        self.assertEqual(normal['levels'], held)
        self.assertEqual([e['id'] for e in normal['restoreDrainedLevels']], ['new'])
        greater = apply_drain_restoration(self.core, 'restoration-greater', levels + held, losses, 172800, 1)
        self.assertEqual([e['id'] for e in greater['restoreDrainedLevels']], ['new', 'old'])
        condition = next(c for c in self.core['effects']['conditions'] if c['id'] == 'energy-drained')
        self.assertEqual(condition['mechanics']['modifiers'], [])
        self.assertEqual(condition['references']['inflictedBySpells'], ['energy-drain', 'enervation'])
