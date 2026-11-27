import json
import unittest

from tools.test_level_drain_lifecycle import fail_drain

from tools.drain_history import apply_permanent_level_loss, projected_level_grants, restore_character_drain
from tools.level_choices import record_level_choices
from tools.organize_core import PATH
from tools.spellcasting import new_slots, plan_cast, reconcile_slot_budget, spend_slot


class SpellAdvancementTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = json.loads(PATH.read_bytes())

    def test_prestige_gains_swap_and_loss_restore(self):
        core = self.core
        actor = dict(classChoices=[], xp=0, abilityScores=dict(con=12, cha=16, int=12))
        def choices(learn, feats=(), **spell):
            return dict(hitDieRoll=4, abilityIncreases={}, skillRanks={}, featChoices=list(feats),
                        spellChoicesByClassId={'sorcerer': dict(learn=learn, **spell)})
        actor = record_level_choices(core, actor, 'elf', class_id='sorcerer', choices=choices(
            ['acid-splash', 'detect-magic', 'light', 'read-magic', 'magic-missile', 'shield'],
            [{'featId': 'toughness'}]))
        actor = record_level_choices(core, actor, 'elf', class_id='sorcerer', xp_award=1000,
                                     choices=choices(['mage-hand']))
        actor = record_level_choices(core, actor, 'elf', class_id='sorcerer', xp_award=2000,
                                     choices=choices(['burning-hands'], [{'featId': 'iron-will'}]))
        # Admission prerequisites are table-owned; this fixture exercises the advancement row.
        fourth = dict(choices(['message', 'scorching-ray'], swap={'remove': 'light', 'learn': 'flare'}),
                      castingTargets=['sorcerer'], abilityIncreases={'cha': 1})
        with self.assertRaisesRegex(ValueError, 'prestige casting target'):
            record_level_choices(core, actor, 'elf', class_id='loremaster', xp_award=3000,
                                 choices=dict(fourth, castingTargets=[]))
        advanced = record_level_choices(core, actor, 'elf', class_id='loremaster', xp_award=3000, choices=fourth)
        active = projected_level_grants(core, advanced)
        self.assertEqual(active['spellcastingLevels'], {'sorcerer': 4})
        self.assertIn('flare', active['knownSpellIdsByClassId']['sorcerer'])
        self.assertNotIn('light', active['knownSpellIdsByClassId']['sorcerer'])
        lost = fail_drain(core, advanced, 'lost')
        lowered = projected_level_grants(core, lost)
        self.assertEqual(lowered['spellcastingLevels'], {'sorcerer': 3})
        self.assertIn('light', lowered['knownSpellIdsByClassId']['sorcerer'])
        self.assertNotIn('scorching-ray', lowered['knownSpellIdsByClassId']['sorcerer'])
        restored = restore_character_drain(core, lost, 'restoration', 86401, 7)
        self.assertEqual(projected_level_grants(core, restored)['knownSpellIdsByClassId'], active['knownSpellIdsByClassId'])

    def test_slot_budget_change_does_not_refund_spent_slot(self):
        core = self.core
        plan = plan_cast(core, 'sorcerer', 'magic-missile', 16)
        state = new_slots('sorcerer', {('regular', 1): 2})
        state = spend_slot(state, 'regular:1:1', plan, known_spell_ids=['magic-missile'], game_seconds=50)
        lowered = reconcile_slot_budget(state, {('regular', 1): 1})
        self.assertTrue(lowered['slots']['regular:1:1']['outsideBudget'])
        restored = reconcile_slot_budget(lowered, {('regular', 1): 2})
        self.assertNotIn('outsideBudget', restored['slots']['regular:1:1'])
        self.assertEqual(restored['slots']['regular:1:1']['spentAtSeconds'], 50)

    def test_magewright_mastery_gains_extra_cantrip_on_new_tier(self):
        core = self.core
        actor = dict(classChoices=[], xp=0, abilityScores=dict(con=12, int=14))
        def choices(learn, feats=(), intelligence=0):
            return dict(hitDieRoll=4, abilityIncreases={'int': 1} if intelligence else {}, skillRanks={},
                        featChoices=list(feats), spellChoicesByClassId={'magewright': dict(learn=learn)})
        actor = record_level_choices(core, actor, 'elf', class_id='magewright', choices=choices(
            ['alarm', 'identify'], [{'featId': 'toughness'}]))
        actor = record_level_choices(core, actor, 'elf', class_id='magewright', xp_award=1000, choices=choices([]))
        actor = record_level_choices(core, actor, 'elf', class_id='magewright', xp_award=2000,
                                     choices=choices([], [{'featId': 'iron-will'}]))
        advanced = record_level_choices(core, actor, 'elf', class_id='magewright', xp_award=3000,
                                        choices=choices(['arcane-lock', 'augury', 'detect-magic'], intelligence=1))
        self.assertEqual(projected_level_grants(core, advanced)['knownSpellIdsByClassId']['magewright'],
                         ['alarm', 'arcane-lock', 'augury', 'detect-magic', 'identify'])
