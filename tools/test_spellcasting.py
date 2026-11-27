import json
import unittest

from tools.effect_state import apply_spell
from tools.level_history import replay_level_history
from tools.organize_core import PATH
from tools.spellbooks import learn_wizard_spells, new_spellbook
from tools.spellcasting import (new_slots, numeric_spell_result, plan_cast, prepare_spell, slot_budget,
                                spellcasting_levels, spend_slot)


class SpellcastingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = json.loads(PATH.read_bytes())

    def plan(self, class_id, spell, ability, *feats, **kwargs):
        owned = feats + tuple(kwargs.pop('extra_feats', ()))
        return plan_cast(self.core, class_id, spell, ability, owned_feats=owned, metamagic=feats, **kwargs)

    def test_budget_bonus_only_locked_and_domain(self):
        self.assertNotIn(('regular', 1), slot_budget(self.core, 'assassin', 1, 11))
        self.assertEqual(slot_budget(self.core, 'assassin', 1, 12)['regular', 1], 1)
        cleric = slot_budget(self.core, 'cleric', 1, 20)
        self.assertEqual(cleric['domain', 1], 1)
        self.assertEqual(cleric['regular', 1], 3)
        self.assertNotIn(('regular', 2), cleric)
        self.assertEqual(slot_budget(self.core, 'wizard', 20, 20, extra_slots={10: 1})['regular', 10], 1)
        self.assertEqual(slot_budget(self.core, 'wizard', 21, 30, extra_slots={10: 1})['regular', 10], 2)
        self.assertEqual(slot_budget(self.core, 'wizard', 21, 20), slot_budget(self.core, 'wizard', 20, 20))
        self.assertEqual(spellcasting_levels(self.core, replay_level_history(self.core, ['wizard'] * 21)), {'wizard': 21})

    def test_prepared_slot_and_extend_effect(self):
        plan = self.plan('wizard', 'mage-armor', 16, 'extend-spell')
        self.assertEqual((plan['requiredSlotLevel'], plan['saveDc']), (2, 14))
        state = new_slots('wizard', slot_budget(self.core, 'wizard', 3, 16))
        prepared = prepare_spell(state, 'regular:2:0', plan, accessible_spell_ids={'mage-armor'},
                                 accessible_spellbooks=[learn_wizard_spells(self.core, new_spellbook(self.core, 'book'), ['mage-armor'])])
        self.assertIsNone(state['slots']['regular:2:0']['preparation'])
        with self.assertRaises(ValueError):
            spend_slot(prepared, 'regular:2:0', self.plan('wizard', 'mage-armor', 16))
        spent = spend_slot(prepared, 'regular:2:0', plan)
        self.assertTrue(spent['slots']['regular:2:0']['expended'])
        with self.assertRaises(ValueError):
            spend_slot(spent, 'regular:2:0', plan)
        active, = apply_spell([], self.core['effects']['spellEffectsBySpellId'], 'mage-armor', 3, 0,
                              lambda sides: sides, cast_plan=plan)
        self.assertEqual(active['expiresAtRound'], 3600)

    def test_heighten_improved_and_random_effects(self):
        plan = self.plan('wizard', 'fireball', 20, 'heighten-spell', 'empower-spell', 'maximize-spell',
                         heighten_to=4, extra_feats=['improved-metamagic'] * 2)
        self.assertEqual((plan['effectiveSpellLevel'], plan['requiredSlotLevel'], plan['saveDc']), (4, 6, 19))
        self.assertEqual(numeric_spell_result(plan, 21, 36), 46)
        shape = self.plan('wizard', 'fireball', 20, 'enlarge-spell', 'widen-spell', 'still-spell', 'silent-spell')
        self.assertEqual(shape['transforms']['rangeMultiplier'], 2)
        self.assertEqual(shape['transforms']['areaDimensionMultiplier'], 2)
        self.assertNotIn('V', shape['components'])
        self.assertNotIn('S', shape['components'])

    def test_spontaneous_and_quicken(self):
        plan = self.plan('sorcerer', 'mage-armor', 16, 'extend-spell')
        self.assertEqual(plan['castingTime'], 'full-round action')
        state = new_slots('sorcerer', slot_budget(self.core, 'sorcerer', 4, 16))
        with self.assertRaises(ValueError):
            spend_slot(state, 'regular:2:0', plan)
        self.assertTrue(spend_slot(state, 'regular:2:0', plan, known_spell_ids=['mage-armor'])['slots']['regular:2:0']['expended'])
        with self.assertRaises(ValueError):
            self.plan('sorcerer', 'mage-armor', 16, 'quicken-spell')
        self.assertEqual(self.plan('wizard', 'mage-armor', 20, 'quicken-spell')['castingTime'], 'free action')
        with self.assertRaises(ValueError):
            self.plan('wizard', 'mage-armor', 20, 'quicken-spell', quickened_this_round=True)

    def test_conversion_cannot_use_domain_slot(self):
        state = new_slots('cleric', slot_budget(self.core, 'cleric', 1, 14))
        domain = self.plan('cleric', 'bless', 14, domain_spell_levels={'bless': 1})
        regular = self.plan('cleric', 'bless', 14)
        for slot, plan in [('domain:1:0', domain), ('regular:1:0', regular)]:
            state = prepare_spell(state, slot, plan, accessible_spell_ids={'bless'})
        cure = self.plan('cleric', 'cure-light-wounds', 14, conversion=True)
        with self.assertRaises(ValueError):
            spend_slot(state, 'domain:1:0', cure, authorized_conversion_spell_ids={'cure-light-wounds'})
        self.assertTrue(spend_slot(state, 'regular:1:0', cure, authorized_conversion_spell_ids={'cure-light-wounds'})
                        ['slots']['regular:1:0']['expended'])

    def test_prestige_tracks_remain_separate(self):
        history = replay_level_history(self.core, ['wizard'] * 3 + ['cleric'] * 3 + ['mystic-theurge'])
        self.assertEqual(spellcasting_levels(self.core, history, {7: ['wizard', 'cleric']}), {'wizard': 4, 'cleric': 4})
        with self.assertRaises(ValueError):
            spellcasting_levels(self.core, history, {7: ['cleric', 'wizard']})

    def test_armor_spell_failure_uses_casting_track_and_final_components(self):
        from tools.spellcasting import resolve_armor_spell_failure

        gear = ['armor:leather', 'armor:shield-light-steel']
        wizard = self.plan('wizard', 'mage-armor', 16, worn_armor_and_shields=gear)
        chance = wizard['armorSpellFailure']['percent']
        self.assertEqual(chance, 15)
        self.assertIsNone(resolve_armor_spell_failure(wizard, chance)['spellToApply'])
        self.assertEqual(resolve_armor_spell_failure(wizard, chance + 1)['spellToApply'], wizard)
        still = self.plan('wizard', 'mage-armor', 16, 'still-spell', worn_armor_and_shields=gear)
        self.assertEqual(still['armorSpellFailure']['percent'], 0)
        bard = self.plan('bard', 'cure-light-wounds', 16, worn_armor_and_shields=gear)
        cleric = self.plan('cleric', 'cure-light-wounds', 16, worn_armor_and_shields=gear)
        self.assertEqual(bard['armorSpellFailure']['percent'], 5)
        self.assertEqual(cleric['armorSpellFailure']['percent'], 0)

    def test_spell_focus_stacks_only_for_same_school_across_distinct_feats(self):
        from tools.feat_selection import check_spell_focus_selection
        picks = [dict(featId=feat, choices={'schoolId': school}) for feat, school in (
            ('spell-focus', 'evocation'), ('spell-focus', 'evocation'), ('greater-spell-focus', 'evocation'))]
        facts = {'feats': picks[:1]}
        self.assertEqual(check_spell_focus_selection(self.core, facts, 'greater-spell-focus', 'evocation')['status'], 'eligible')
        self.assertEqual(check_spell_focus_selection(self.core, facts, 'greater-spell-focus', 'illusion')['status'], 'ineligible')
        self.assertEqual(check_spell_focus_selection(self.core, facts, 'spell-focus', 'universal')['status'], 'ineligible')
        self.assertEqual(self.plan('wizard', 'fireball', 16, feat_choices=picks)['saveDc'], 18)
        self.assertEqual(self.plan('wizard', 'grease', 16, feat_choices=picks)['saveDc'], 14)

    def test_spell_penetration_is_not_spell_focus(self):
        picks = [dict(featId=key) for key in ('spell-penetration', 'greater-spell-penetration')]
        fireball = self.plan('wizard', 'fireball', 16, feat_choices=picks)
        self.assertEqual(fireball['spellResistanceCheckBonus'], 4)
        self.assertEqual(fireball['saveDc'], 16)
        self.assertEqual(self.plan('wizard', 'grease', 16, feat_choices=picks)['spellResistanceCheckBonus'], 0)

    def test_component_access_and_conditions_after_metamagic(self):
        from tools.spell_components import resolve_component_cast
        empty = self.plan('wizard', 'fireball', 16, component_context={})
        self.assertIn('equipped-component-pouch-required', empty['componentCheck']['blockedReasons'])
        eschew = self.plan('wizard', 'fireball', 16, extra_feats=('eschew-materials',), component_context={})
        self.assertEqual(eschew['componentCheck']['status'], 'ready')
        ready = self.plan('wizard', 'fireball', 16, component_context={'equippedItemIds': ['gear:spell-component-pouch']})
        self.assertEqual(ready['componentCheck']['status'], 'ready')
        priced = self.plan('wizard', 'identify', 16, extra_feats=('eschew-materials',), component_context={})
        self.assertIn('priced-material-unavailable', priced['componentCheck']['blockedReasons'])
        focused = self.plan('wizard', 'chain-lightning', 18, component_context={'accessibleItemIds': ['gear:spell-component-pouch']})
        self.assertEqual(focused['componentCheck']['status'], 'ready')
        context = dict(activeSpellIds=['silence'], conditionIds=['deafened'])
        blocked = self.plan('wizard', 'magic-missile', 16, component_context=context)
        self.assertIn('verbal-blocked-by-silence', blocked['componentCheck']['blockedReasons'])
        silent = self.plan('wizard', 'magic-missile', 16, 'silent-spell', component_context=context)
        self.assertEqual(silent['componentCheck']['failureChancePercent'], 0)
        self.assertEqual(silent['componentCheck']['status'], 'ready')
        deafened = self.plan('wizard', 'magic-missile', 16, component_context={'conditionIds': ['deafened', 'entangled']})
        self.assertEqual(deafened['componentCheck']['concentrationDc'], 16)
        self.assertTrue(resolve_component_cast(deafened, percentile_roll=20, concentration_total=16)['failed'])
        self.assertFalse(resolve_component_cast(deafened, percentile_roll=21, concentration_total=16)['failed'])

    def test_divine_focus_and_cleric_weapon_choice(self):
        from tools.spell_components import choose_cleric_holy_weapon
        symbol = self.plan('cleric', 'bless', 16, component_context={'accessibleItemIds': ['gear:holy-symbol-wooden']})
        self.assertEqual(symbol['componentCheck']['status'], 'ready')
        weapon = choose_cleric_holy_weapon(self.core, 'weapon:longsword', cleric_class_level=1,
                                            deity_weapon_id='weapon:longsword')
        self.assertEqual(self.plan('cleric', 'bless', 16, component_context={'holyWeaponId': weapon,
                         'equippedItemIds': [weapon]})['componentCheck']['status'], 'ready')
        with self.assertRaisesRegex(ValueError, 'first Cleric'):
            choose_cleric_holy_weapon(self.core, weapon, cleric_class_level=2, deity_weapon_id=weapon)
        for key in ('gear:holly', 'gear:mistletoe'):
            item = self.core['inventory']['itemsById'][key]
            self.assertEqual((item['priceCp'], item['weightLb']), (0, 0))

    def test_casting_pool_boundaries_and_component_block_at_spend(self):
        with self.assertRaisesRegex(ValueError, 'domain casting pool'):
            self.plan('wizard', 'cure-light-wounds', 16, domain_spell_levels={'cure-light-wounds': 1})
        with self.assertRaisesRegex(ValueError, 'domain casting pool'):
            self.plan('cleric', 'bless', 16, domain_spell_levels={'bless': 2})
        for class_id, spell_id in [('cleric', 'bless'), ('druid', 'entangle')]:
            with self.assertRaisesRegex(ValueError, 'conversion choices'):
                self.plan(class_id, spell_id, 16, conversion=True)
        plan = self.plan('sorcerer', 'magic-missile', 16, component_context={'silenced': True})
        slots = new_slots('sorcerer', {('regular', 1): 1})
        with self.assertRaisesRegex(ValueError, 'components unavailable'):
            spend_slot(slots, 'regular:1:0', plan, known_spell_ids={'magic-missile'})
        self.assertFalse(slots['slots']['regular:1:0']['expended'])

    def test_divine_conversion_and_arcane_spontaneous_remain_distinct(self):
        druid = self.plan('druid', 'summon-natures-ally-i', 16, conversion=True)
        bard = self.plan('bard', 'cure-light-wounds', 16)
        self.assertEqual((druid['mode'], bard['mode']), ('conversion', 'spontaneous'))
        self.assertEqual(self.plan('paladin', 'bless', 16)['mode'], 'prepared')
        self.assertIn(('regular', 1), slot_budget(self.core, 'ranger', 4, 14))
        self.assertNotIn(('regular', 1), slot_budget(self.core, 'ranger', 3, 14))

    def test_generated_profiles_and_caster_levels(self):
        from tools.spellcasting import base_caster_level
        profiles = self.core['magic']['castingProfilesByClassId']
        self.assertEqual(profiles['cleric']['conversion']['familyBySpellId']['cure-light-wounds'], 'cure')
        self.assertEqual(base_caster_level(self.core, 'paladin', 3), 0)
        self.assertEqual(base_caster_level(self.core, 'ranger', 7, prestige_advancement=2), 5)
        self.assertEqual(self.plan('wizard', 'magic-missile', 16, class_level=3, prestige_advancement=1)['baseCasterLevel'], 4)
        recovery = self.core['magic']['spellRecoveryByClassId']
        self.assertEqual(recovery['adept']['restHours'], 0)
        self.assertFalse(recovery['blackguard']['scheduledDailyTime'])
        self.assertEqual(recovery['magewright']['restHours'], 8)
        self.assertEqual(recovery['assassin']['inheritedFromClassId'], 'bard')

    def test_cast_completion_requires_components_and_resolves_armor(self):
        from tools.spellcasting import resolve_cast_completion
        with self.assertRaisesRegex(ValueError, 'checked'):
            resolve_cast_completion(self.plan('wizard', 'magic-missile', 16))
        plan = self.plan('wizard', 'magic-missile', 16, component_context={}, worn_armor_and_shields=['armor:leather'])
        self.assertEqual(resolve_cast_completion(plan, armor_percentile=10)['failedBy'], 'armor-spell-failure')
        self.assertEqual(resolve_cast_completion(plan, armor_percentile=11)['spellToApply'], plan)

    def test_casting_injury_concentration_and_adapted_deafness(self):
        from tools.spellcasting import casting_injury_concentration_dc, resolve_cast_completion
        plan = self.plan('wizard', 'magic-missile', 16,
                         component_context={'conditionIds': ['deafened'], 'deafnessAdapted': True})
        self.assertEqual(plan['componentCheck']['failureChancePercent'], 10)
        dc = casting_injury_concentration_dc(self.core, plan, 7)
        self.assertEqual(dc, 18)
        self.assertEqual(casting_injury_concentration_dc(self.core, plan, 7, continuous=True), 14)
        self.assertIsNone(casting_injury_concentration_dc(self.core, plan, 7, continuous=True, source_ended=True))
        self.assertEqual(resolve_cast_completion(plan, component_percentile=11,
                         injury_checks=[(dc, 17)])['failedBy'], 'injury-concentration')
        self.assertIsNotNone(resolve_cast_completion(plan, component_percentile=11,
                             injury_checks=[(dc, 18)])['spellToApply'])

    def test_material_or_divine_focus_uses_casting_track(self):
        from tools.spell_components import effective_codes
        for spell in self.core['magic']['spells']:
            if 'M/DF' not in spell['components']['raw']:
                continue
            with self.subTest(spell=spell['id']):
                arcane = effective_codes(spell['componentProfile'], 'arcane')
                divine = effective_codes(spell['componentProfile'], 'divine')
                self.assertIn('M', arcane)
                self.assertNotIn('DF', arcane)
                self.assertIn('DF', divine)
                self.assertNotIn('M', divine)
                if 'F' in spell['componentProfile']['codes']:
                    self.assertIn('F', arcane)
                    self.assertIn('F', divine)
        wizard = self.plan('wizard', 'hold-monster', 16, component_context={})
        self.assertEqual(wizard['componentCheck']['blockedReasons'], ['equipped-component-pouch-required'])
        wizard = self.plan('wizard', 'hold-monster', 16, component_context={'equippedItemIds': ['gear:spell-component-pouch']})
        self.assertEqual(wizard['componentCheck']['status'], 'ready')
        cleric = self.plan('cleric', 'hold-monster', 16, domain_spell_levels={'hold-monster': 6},
                           component_context={'accessibleItemIds': ['gear:holy-symbol-wooden']})
        self.assertEqual(cleric['componentCheck']['status'], 'ready')
        self.assertEqual(set(cleric['components']), {'V', 'S', 'DF'})
