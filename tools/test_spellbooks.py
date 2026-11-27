import json
import unittest

from tools.organize_core import PATH
from tools.spellbooks import learn_wizard_spells, new_spellbook, pages_used
from tools.spellcasting import new_slots, plan_cast, prepare_spell, spend_slot


class SpellbookTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = json.loads(PATH.read_bytes())

    def test_learning_uses_wizard_levels_and_capacity_atomically(self):
        blank = new_spellbook(self.core, 'book')
        self.assertEqual(blank['capacityPages'], 100)
        rule = self.core['magic']['wizardSpellbook']
        spells = ['read-magic', 'magic-missile', 'scorching-ray', 'fireball']
        book = learn_wizard_spells(self.core, blank, spells)
        self.assertEqual(pages_used(book, rule), 7)
        self.assertEqual(learn_wizard_spells(self.core, book, spells), book)
        with self.assertRaisesRegex(ValueError, 'capacity'):
            learn_wizard_spells(self.core, dict(blank, capacityPages=6), spells)
        self.assertEqual(blank['spellsById'], {})
        with self.assertRaisesRegex(ValueError, 'requires a spellbook'):
            learn_wizard_spells(self.core, None, spells)

    def test_bookless_wizard_cannot_prepare_but_other_tracks_are_unaffected(self):
        wizard = plan_cast(self.core, 'wizard', 'read-magic', 16)
        slots = new_slots('wizard', {('regular', 0): 1})
        access = {'accessible_spell_ids': {'read-magic'}}
        blank = new_spellbook(self.core, 'book')
        for books in ([], [blank]):
            with self.assertRaisesRegex(ValueError, 'accessible spellbook'):
                prepare_spell(slots, 'regular:0:0', wizard, accessible_spellbooks=books, **access)
        book = learn_wizard_spells(self.core, blank, ['read-magic'])
        ready = prepare_spell(slots, 'regular:0:0', wizard, accessible_spellbooks=[book], **access)
        self.assertTrue(spend_slot(ready, 'regular:0:0', wizard)['slots']['regular:0:0']['expended'])
        bard = plan_cast(self.core, 'bard', 'read-magic', 16)
        self.assertTrue(spend_slot(new_slots('bard', {('regular', 0): 1}), 'regular:0:0', bard,
                                   known_spell_ids={'read-magic'})['slots']['regular:0:0']['expended'])
        cleric = plan_cast(self.core, 'cleric', 'bless', 16)
        ready = prepare_spell(new_slots('cleric', {('regular', 1): 1}), 'regular:1:0', cleric,
                              accessible_spell_ids={'bless'})
        self.assertIsNotNone(ready['slots']['regular:1:0']['preparation'])

    def test_scroll_study_and_inscription_are_separate(self):
        from tools.spellbooks import (begin_wizard_study, finish_wizard_study, inscribe_understood_spell,
                                      new_wizard_learning, wizard_specialization)
        book = new_spellbook(self.core, 'destination')
        source = dict(kind='scroll', instanceId='scroll', spellId='fireball')
        specialty = wizard_specialization(self.core, 'evocation', ['illusion', 'necromancy'])
        pending = begin_wizard_study(self.core, new_wizard_learning(), book, source, 'fireball',
                                    day=1, spellcraft_ranks=6, specialization=specialty)
        self.assertEqual(pending['pendingStudy']['checkDc'], 18)
        with self.assertRaises(ValueError):
            finish_wizard_study(self.core, pending, day=1, spellcraft_total=16)
        done = finish_wizard_study(self.core, pending, day=2, spellcraft_total=16)
        self.assertTrue(done['success'])
        self.assertEqual(done['consumedScrollInstanceId'], 'scroll')
        self.assertEqual(done['learning']['knownSpellIds'], [])
        for day, funds in ((2, 300), (3, 299)):
            with self.assertRaises(ValueError):
                inscribe_understood_spell(self.core, done['learning'], book, 'fireball', start_day=2,
                                          day=day, materials_gp=funds, specialization=specialty)
        result = inscribe_understood_spell(self.core, done['learning'], book, 'fireball', start_day=2,
                                           day=3, materials_gp=350, specialization=specialty)
        self.assertEqual(result['learning']['knownSpellIds'], ['fireball'])
        self.assertEqual(result['book']['spellsById'], {'fireball': 3})
        self.assertEqual(result['materialsGpRemaining'], 50)

    def test_failed_study_requires_ranks_and_never_consumes_source_book(self):
        from tools.spellbooks import begin_wizard_study, finish_wizard_study, new_wizard_learning
        destination = new_spellbook(self.core, 'mine')
        source = dict(learn_wizard_spells(self.core, new_spellbook(self.core, 'theirs'), ['shield']), kind='spellbook')
        pending = begin_wizard_study(self.core, new_wizard_learning(), destination, source, 'shield', day=0, spellcraft_ranks=4)
        failed = finish_wizard_study(self.core, pending, day=1, spellcraft_total=15)
        self.assertFalse(failed['success'])
        with self.assertRaisesRegex(ValueError, 'another Spellcraft rank'):
            begin_wizard_study(self.core, failed['learning'], destination, source, 'shield', day=1, spellcraft_ranks=4)
        retried = begin_wizard_study(self.core, failed['learning'], destination, source, 'shield', day=1, spellcraft_ranks=5)
        done = finish_wizard_study(self.core, retried, day=2, spellcraft_total=16)
        self.assertTrue(done['success'])
        self.assertIsNone(done['consumedScrollInstanceId'])
        self.assertEqual(source['spellsById'], {'shield': 1})

    def test_specialization_gates_wizard_learning_casting_and_extra_slots(self):
        from tools.spellbooks import wizard_specialization, wizard_spell_item_school_allowed
        from tools.spellcasting import slot_budget
        specialty = wizard_specialization(self.core, 'evocation', ['illusion', 'necromancy'])
        with self.assertRaises(ValueError):
            wizard_specialization(self.core, 'evocation', ['illusion', 'divination'])
        self.assertEqual(wizard_specialization(self.core, 'divination', ['illusion'])['prohibitedSchoolIds'], ['illusion'])
        with self.assertRaisesRegex(ValueError, 'prohibited'):
            plan_cast(self.core, 'wizard', 'silent-image', 16, specialization=specialty)
        self.assertFalse(wizard_spell_item_school_allowed(self.core, 'silent-image', specialty))
        with self.assertRaises(ValueError):
            learn_wizard_spells(self.core, new_spellbook(self.core, 'mine'), ['silent-image'], specialization=specialty)
        self.assertEqual(plan_cast(self.core, 'bard', 'silent-image', 16, specialization=specialty)['pool'], 'regular')
        self.assertEqual(slot_budget(self.core, 'wizard', 1, 16, specialization=specialty)['specialist', 1], 1)
        self.assertEqual(plan_cast(self.core, 'wizard', 'magic-missile', 16, specialization=specialty,
                                   specialist_slot=True)['pool'], 'specialist')
        with self.assertRaisesRegex(ValueError, 'specialty school'):
            plan_cast(self.core, 'wizard', 'shield', 16, specialization=specialty, specialist_slot=True)

    def test_specialization_is_optional_first_wizard_level_and_permanent(self):
        from tools.spellbooks import choose_wizard_specialization
        pick = dict(specialty_school_id='divination', prohibited_school_ids=['illusion'])
        chosen = choose_wizard_specialization(self.core, wizard_class_level=1, **pick)
        generalist = choose_wizard_specialization(self.core, wizard_class_level=1)
        self.assertIsNone(generalist['specialtySchoolId'])
        self.assertEqual(chosen['specialtySchoolId'], 'divination')
        for level in (0, 2, 20):
            with self.assertRaisesRegex(ValueError, 'class level 1'):
                choose_wizard_specialization(self.core, wizard_class_level=level, **pick)
        for existing in (chosen, generalist):
            with self.assertRaisesRegex(ValueError, 'already recorded'):
                choose_wizard_specialization(self.core, wizard_class_level=1, existing_choice=existing, **pick)

    def test_partial_wizard_preparation_needs_full_rest_and_study(self):
        from tools.spellcasting import prepare_wizard_session
        plan = plan_cast(self.core, 'wizard', 'magic-missile', 16)
        slots = new_slots('wizard', {('regular', 1): 2})
        book = learn_wizard_spells(self.core, new_spellbook(self.core, 'book'), ['magic-missile'])
        args = dict(start_seconds=28800, end_seconds=32400, verified_rest_seconds=28800,
                    accessible_spell_ids={'magic-missile'}, accessible_spellbooks=[book])
        picks = [('regular:1:0', plan)]
        for override in (dict(verified_rest_seconds=28799), dict(end_seconds=32399)):
            with self.assertRaisesRegex(ValueError, 'rest and study'):
                prepare_wizard_session(self.core, slots, picks, **dict(args, **override))
        updated = prepare_wizard_session(self.core, slots, picks, **args)
        self.assertIsNotNone(updated['slots']['regular:1:0']['preparation'])
        self.assertIsNone(updated['slots']['regular:1:1']['preparation'])
