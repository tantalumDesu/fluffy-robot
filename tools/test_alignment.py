import json
import unittest

from tools.alignment import (aligned_burst_plan, class_alignment_status, evaluate_alignment_change,
                             source_alignment_context)
from tools.level_history import advance_level_history, replay_level_history
from tools.organize_core import PATH
from tools.sheet_effects import modifier_total
from tools.spellcasting import plan_cast


class AlignmentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = json.loads(PATH.read_bytes())

    def test_class_entry_and_persistent_fall(self):
        core = self.core
        self.assertEqual(class_alignment_status(core, 'cleric', 'NG', deity_alignment='LG'), 'eligible')
        self.assertEqual(class_alignment_status(core, 'cleric', 'N', deity_alignment='LN'), 'ineligible')
        self.assertEqual(class_alignment_status(core, 'cleric', 'NG'), 'needs-review')
        state = evaluate_alignment_change(core, ['paladin', 'monk', 'druid'], 'CG')
        self.assertEqual(state['fallenClassIds'], ['druid', 'paladin'])
        self.assertEqual(state['classes']['monk'], {'advancement': 'ineligible', 'features': 'retain-features'})
        self.assertEqual(state['classes']['paladin']['features'], 'retain-proficiencies-only')
        regained = evaluate_alignment_change(core, ['paladin'], 'LG', fallen=['paladin'])
        self.assertEqual(regained['classes']['paladin']['advancement'], 'atonement-required')
        self.assertEqual(evaluate_alignment_change(core, ['paladin'], 'LG', fallen=['paladin'], atoned=['paladin'])
                         ['classes']['paladin']['advancement'], 'eligible')
        self.assertEqual(evaluate_alignment_change(core, ['barbarian'], 'LG')['classes']['barbarian']['features'],
                         'lose-rage-only')

    def test_history_checks_alignment_at_selection_only(self):
        core = self.core
        history = {1: {'alignmentId': 'LG'}}
        with self.assertRaisesRegex(ValueError, 'ineligible'):
            replay_level_history(core, ['paladin'], alignment_by_level={1: {'alignmentId': 'NG'}})
        with self.assertRaisesRegex(ValueError, 'atonement-required'):
            advance_level_history(core, ['paladin'], 0, 1000, class_id='paladin', alignment_by_level=history,
                                  current_alignment={'alignmentId': 'LG', 'fallenClassIds': ['paladin']})
        build = advance_level_history(core, ['paladin'], 0, 1000, class_id='fighter', alignment_by_level=history,
                                      current_alignment={'alignmentId': 'CG'})
        self.assertEqual([e['alignmentAtSelection']['alignmentId'] for e in build['entries']], ['LG', 'CG'])

    def test_alignment_affects_spells(self):
        core = self.core
        spells = core['effects']['spellEffectsBySpellId']
        active = [(entry, {}) for entry in spells['protection-from-evil']]
        self.assertEqual(modifier_total('ac', active, source_alignment_context(core, 'LE')), 2)
        self.assertEqual(modifier_total('ac', active, source_alignment_context(core, 'LN')), 0)
        with self.assertRaisesRegex(ValueError, 'ineligible'):
            plan_cast(core, 'cleric', 'protection-from-evil', 16, alignment_id='NE')
        with self.assertRaisesRegex(ValueError, 'needs-review'):
            plan_cast(core, 'cleric', 'protection-from-evil', 16, alignment_id='NG')
        self.assertEqual(plan_cast(core, 'cleric', 'protection-from-evil', 16, alignment_id='NG', deity_known=True)
                         ['requiredSlotLevel'], 1)
        evil = aligned_burst_plan(core, 'holy-smite', 'LE', 12, target_is_outsider=True, will_saved=False)
        self.assertEqual((evil['diceCount'], evil['dieSides'], evil['condition']['conditionId']), (10, 6, 'blinded'))
        neutral = aligned_burst_plan(core, 'holy-smite', 'LN', 12, target_is_outsider=True, will_saved=True)
        self.assertEqual((neutral['diceCount'], neutral['dieSides'], neutral['damageDivisor'], neutral['condition']),
                         (5, 8, 4, None))
        self.assertEqual(aligned_burst_plan(core, 'unholy-blight', 'LE', 10, target_is_outsider=False,
                                           will_saved=False)['diceCount'], 0)

    def test_ethos_prestige_classes_lose_and_regain_features(self):
        core = self.core
        for class_id, allowed in [('assassin', 'NE'), ('blackguard', 'LE'), ('dwarven-defender', 'LN')]:
            fallen = evaluate_alignment_change(core, [class_id], 'CG')
            self.assertEqual(fallen['classes'][class_id], {'advancement': 'ineligible', 'features': 'suppress-class-abilities'})
            self.assertEqual(fallen['fallenClassIds'], [])
            restored = evaluate_alignment_change(core, [class_id], allowed, fallen=fallen['fallenClassIds'])
            self.assertEqual(restored['classes'][class_id], {'advancement': 'eligible', 'features': 'retain-features'})
            history = replay_level_history(core, [class_id, 'fighter', class_id], alignment_by_level={
                1: {'alignmentId': allowed}, 2: {'alignmentId': 'CG'}, 3: {'alignmentId': allowed}})
            self.assertEqual(history['classLevels'][class_id], 2)
        self.assertEqual(evaluate_alignment_change(core, ['arcane-trickster'], 'LG')['classes']['arcane-trickster']['features'],
                         'needs-review')

    def test_weapon_alignment_is_a_property_not_a_wielder_tag(self):
        from tools.alignment import weapon_alignment_tags
        self.assertEqual({key: weapon_alignment_tags(self.core, [key]) for key in
                          ('holy', 'unholy', 'axiomatic', 'anarchic')},
                         {'holy': {'good'}, 'unholy': {'evil'}, 'axiomatic': {'law'}, 'anarchic': {'chaos'}})
