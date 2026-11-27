import json
import unittest

from tools.test_level_drain_lifecycle import fail_drain

from tools.drain_history import apply_permanent_level_loss, projected_level_grants, restore_character_drain
from tools.epic_spell_feats import active_spellbooks, apply_epic_spell_pick, epic_known_levels
from tools.level_choices import record_level_choices
from tools.organize_core import PATH
from tools.spellbooks import add_spellbook
from tools.spellcasting import feat_slot_budget, new_slots, plan_cast, prepare_spell, spend_slot


class EpicSpellFeatsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = json.loads(PATH.read_bytes())

    def test_capacity_repeats_and_bonus_once(self):
        feats = []
        facts = dict(characterLevel=21, feats=feats, spellcastingLevels={'wizard': 21}, abilityScores={'int': 30})
        def add(level):
            pick, _ = apply_epic_spell_pick(self.core, {}, dict(featId='improved-spell-capacity',
                choices=dict(castingClassId='wizard', slotLevel=level)), facts)
            feats.append(pick)
        with self.assertRaisesRegex(ValueError, 'one level above'):
            add(11)
        add(10)
        add(10)
        add(11)
        budget = feat_slot_budget(self.core, 'wizard', 21, 30, feat_choices=feats)
        self.assertEqual(budget['regular', 10], 3)
        self.assertEqual(budget['regular', 11], 1)
        self.assertNotIn(('regular', 11), feat_slot_budget(self.core, 'wizard', 21, 20, feat_choices=feats))

    def test_wizard_split_books_loss_and_restoration(self):
        books = add_spellbook(self.core, add_spellbook(self.core, {}, 'a'), 'b')
        books['a']['capacityPages'] = 2
        books['b']['capacityPages'] = 2
        actor = dict(classChoices=['wizard'] * 20, xp=190000, abilityScores=dict(int=24, con=12),
                     maxHp=100, spellbooksById=books)
        spells = [dict(spellId='animal-messenger'), dict(spellId='fireball')]
        choices = dict(hitDieRoll=3, abilityIncreases={}, skillRanks={}, accessibleSpellbookIds=['a', 'b'],
                       featChoices=[dict(featId='spell-knowledge', choices=dict(castingClassId='wizard', spells=spells))])
        with self.assertRaisesRegex(ValueError, 'capacity'):
            record_level_choices(self.core, actor, 'elf', class_id='wizard', xp_award=20000, choices=choices)
        self.assertEqual(books['a']['spellsById'], {})
        books['b']['capacityPages'] = 3
        advanced = record_level_choices(self.core, actor, 'elf', class_id='wizard', xp_award=20000, choices=choices)
        feats = advanced['featChoices']
        self.assertEqual(epic_known_levels(feats, 'wizard'), {'animal-messenger': 2, 'fireball': 3})
        plan = plan_cast(self.core, 'wizard', 'animal-messenger', 24, feat_choices=feats)
        slots = new_slots('wizard', {('regular', 2): 1})
        def prepare(books):
            return prepare_spell(slots, 'regular:2:0', plan, accessible_spell_ids=(), accessible_spellbooks=books)
        prepare(active_spellbooks(advanced, feats, ['a', 'b']))
        advanced['spellbooksById']['a']['damagedSpellIds'] = ['animal-messenger']
        with self.assertRaisesRegex(ValueError, 'accessible spellbook'):
            prepare(active_spellbooks(advanced, feats, ['a', 'b']))
        lost = fail_drain(self.core, advanced, 'loss')
        self.assertEqual(projected_level_grants(self.core, lost)['featChoices'], [])
        self.assertEqual(active_spellbooks(lost, [], ['b'])[0]['spellsById'], {})
        restored = restore_character_drain(self.core, lost, 'restoration', 86401, 7)
        active = projected_level_grants(self.core, restored)['featChoices']
        self.assertEqual(epic_known_levels(active, 'wizard'), {'animal-messenger': 2, 'fireball': 3})
        self.assertEqual(active_spellbooks(restored, active, ['a', 'b'])[0]['spellsById'], {})

    def test_spontaneous_cross_list_and_no_slots(self):
        facts = dict(characterLevel=21, feats=[], spellcastingLevels={'sorcerer': 21}, abilityScores={'cha': 24})
        pick, _ = apply_epic_spell_pick(self.core, {}, dict(featId='spell-knowledge', choices=dict(
            castingClassId='sorcerer', spells=[dict(spellId='animal-messenger'), dict(spellId='calm-emotions')])), facts)
        base = feat_slot_budget(self.core, 'sorcerer', 21, 24)
        self.assertEqual(feat_slot_budget(self.core, 'sorcerer', 21, 24, feat_choices=[pick]), base)
        plan = plan_cast(self.core, 'sorcerer', 'animal-messenger', 24, feat_choices=[pick])
        ledger = new_slots('sorcerer', base)
        with self.assertRaisesRegex(ValueError, 'not prepared, known'):
            spend_slot(ledger, 'regular:2:0', plan, known_spell_ids=())
        slots = spend_slot(ledger, 'regular:2:0', plan, known_spell_ids=epic_known_levels([pick], 'sorcerer'))
        self.assertTrue(slots['slots']['regular:2:0']['expended'])

    def test_multiclass_pick_depends_on_receiving_track_not_new_class(self):
        actor = dict(classChoices=['bard'] * 17 + ['wizard'] * 3, xp=190000,
                     abilityScores=dict(int=16, cha=16, con=12), maxHp=100)
        choices = dict(hitDieRoll=3, abilityIncreases={}, skillRanks={}, featChoices=[dict(
            featId='spell-knowledge', choices=dict(castingClassId='bard',
            spells=[dict(spellId='animate-objects'), dict(spellId='calm-emotions')]))])
        result = record_level_choices(self.core, actor, 'elf', class_id='wizard', xp_award=20000, choices=choices)
        self.assertEqual(epic_known_levels(result['featChoices'], 'bard'), {'animate-objects': 6, 'calm-emotions': 2})
        self.assertEqual(result['spellbooksById'], {})

        actor['classChoices'] = ['wizard'] * 20
        actor['abilityScores']['int'] = 24
        choices['featChoices'][0]['choices']['castingClassId'] = 'wizard'
        with self.assertRaisesRegex(ValueError, 'spellbook capacity'):
            record_level_choices(self.core, actor, 'elf', class_id='fighter', xp_award=20000, choices=choices)

    def test_knowledge_caps_choices_at_current_track_level(self):
        facts = dict(characterLevel=21, feats=[], classLevels={'bard': 2},
                     spellcastingLevels={'bard': 2}, abilityScores={'cha': 12})
        spells = [dict(spellId='magic-missile'), dict(spellId='shield')]
        pick = dict(featId='spell-knowledge', choices=dict(castingClassId='bard', spells=spells))
        granted, _ = apply_epic_spell_pick(self.core, {}, pick, facts)
        self.assertEqual(epic_known_levels([granted], 'bard'), {'magic-missile': 1, 'shield': 1})
        spells[1] = dict(spellId='fireball')
        with self.assertRaisesRegex(ValueError, 'eligible arcane list and spell level'):
            apply_epic_spell_pick(self.core, {}, pick, facts)
        with self.assertRaisesRegex(ValueError, 'at least one spell'):
            apply_epic_spell_pick(self.core, {}, pick, dict(facts, abilityScores={'cha': 9}))

    def test_cached_plan_requires_active_spell_knowledge_after_loss(self):
        from tools.drain_history import apply_permanent_level_loss, projected_level_grants, restore_character_drain
        actor = dict(classChoices=['sorcerer'] * 2 + ['fighter'] * 18, xp=190000, maxHp=100,
                     abilityScores=dict(cha=16, int=12, con=12))
        advanced = record_level_choices(self.core, actor, 'elf', class_id='fighter', xp_award=20000,
            choices=dict(hitDieRoll=5, abilityIncreases={}, skillRanks={}, featChoices=[dict(
                featId='spell-knowledge', choices=dict(castingClassId='sorcerer', spells=[
                    dict(spellId='cure-light-wounds'), dict(spellId='confusion-lesser')]))]))
        plan = plan_cast(self.core, 'sorcerer', 'cure-light-wounds', 16, feat_choices=advanced['featChoices'])
        slots = new_slots('sorcerer', {('regular', 1): 1})
        lost = fail_drain(self.core, advanced, 'loss')
        known = projected_level_grants(self.core, lost)['knownSpellIdsByClassId']
        with self.assertRaisesRegex(ValueError, 'not prepared, known'):
            spend_slot(slots, 'regular:1:0', plan, known_spell_ids=known.get('sorcerer', ()))
        restored = restore_character_drain(self.core, lost, 'restoration', 86401, 7)
        known = projected_level_grants(self.core, restored)['knownSpellIdsByClassId']
        self.assertTrue(spend_slot(slots, 'regular:1:0', plan,
                                  known_spell_ids=known['sorcerer'])['slots']['regular:1:0']['expended'])
