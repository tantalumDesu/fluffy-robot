import json
import unittest

from tools.effect_state import active_spells, apply_spell
from tools.game_time import (encounter_clock, end_turn, interrupt_cast, new_encounter, schedule_cast,
                             schedule_downtime_cast, seconds, spend_action, start_next_turn)
from tools.organize_core import PATH
from tools.spellcasting import (begin_encounter_cast, new_slots, plan_cast, prepare_spell, recover_slots,
                                slot_budget, spend_slot)


class TimingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = json.loads(PATH.read_bytes())

    def test_round_cast_completes_on_same_initiative_next_round(self):
        plan = plan_cast(self.core, 'wizard', 'summon-monster-i', 14)
        slots = new_slots('wizard', slot_budget(self.core, 'wizard', 1, 14))
        slot = 'regular:1:0'
        slots = prepare_spell(slots, slot, plan, accessible_spell_ids={'summon-monster-i'})
        encounter, _ = start_next_turn(new_encounter(['fast', 'caster', 'slow']))
        encounter, _ = start_next_turn(end_turn(encounter)[0])
        encounter, spent, completed = begin_encounter_cast(encounter, 'caster', slots, slot, plan)
        self.assertEqual(completed, [])
        self.assertTrue(spent['slots'][slot]['expended'])
        self.assertFalse(slots['slots'][slot]['expended'])
        for _ in range(2):
            encounter, completed = start_next_turn(end_turn(encounter)[0])
            self.assertEqual(completed, [])
        interrupted = interrupt_cast(encounter, 'caster')
        self.assertEqual(start_next_turn(end_turn(interrupted)[0])[1], [])
        encounter, completed = start_next_turn(end_turn(encounter)[0])
        self.assertEqual(completed, [plan])
        self.assertEqual(encounter['actions']['standard'], 1)

    def test_full_round_action_and_quicken(self):
        plan = plan_cast(self.core, 'sorcerer', 'mage-armor', 14,
                         owned_feats=['extend-spell'], metamagic=['extend-spell'])
        encounter, _ = start_next_turn(new_encounter(['caster']))
        spent, completed = schedule_cast(encounter, 'caster', plan)
        self.assertEqual(completed, [plan])
        with self.assertRaises(ValueError):
            spend_action(spent, 'move')
        quicken = plan_cast(self.core, 'wizard', 'mage-armor', 16,
                            owned_feats=['quicken-spell'], metamagic=['quicken-spell'])
        state, _ = schedule_cast(encounter, 'caster', quicken)
        self.assertEqual(state['actions']['standard'], 1)
        with self.assertRaises(ValueError):
            schedule_cast(state, 'caster', quicken)

    def test_surprise_expiry_and_downtime(self):
        encounter, _ = start_next_turn(new_encounter(['fast', 'caster'], surprise_actors=['caster']))
        self.assertEqual((encounter['round'], encounter['index']), (0, 1))
        with self.assertRaises(ValueError):
            spend_action(encounter, 'full-round')
        self.assertEqual(spend_action(encounter, 'move')['actions']['standard'], 0)
        effects = self.core['effects']['spellEffectsBySpellId']
        active = apply_spell([], effects, 'haste', 1, encounter_clock(encounter), lambda sides: 1)
        encounter, _ = start_next_turn(end_turn(encounter)[0])
        self.assertTrue(active_spells(active, encounter_clock(encounter)))
        encounter, _ = start_next_turn(end_turn(encounter)[0])
        self.assertFalse(active_spells(active, encounter_clock(encounter)))
        self.assertFalse(active_spells(active, {'gameSeconds': 6}))
        long_cast = {'timing': {'completion': 'elapsed', 'elapsed': {'unit': 'hour', 'amount': 1}}}
        self.assertEqual(schedule_downtime_cast(long_cast, 10)['completion']['gameSeconds'], 3610)
        self.assertEqual(seconds('day', 2), 172800)

    def test_recovery_distinguishes_rest_prep_and_recent_casting(self):
        plan = plan_cast(self.core, 'wizard', 'mage-armor', 14)
        slots = new_slots('wizard', slot_budget(self.core, 'wizard', 1, 14))
        for slot, cast_at in [('regular:1:0', 0), ('regular:1:1', 3599)]:
            slots = prepare_spell(slots, slot, plan, accessible_spell_ids={'mage-armor'})
            slots = spend_slot(slots, slot, plan, game_seconds=cast_at)
        kwargs = dict(start_seconds=28800, end_seconds=32400, verified_rest_seconds=28800)
        with self.assertRaises(ValueError):
            recover_slots(self.core, slots, **dict(kwargs, end_seconds=30000))
        recovered = recover_slots(self.core, slots, **kwargs)
        self.assertFalse(recovered['slots']['regular:1:0']['expended'])
        self.assertTrue(recovered['slots']['regular:1:1']['expended'])
        divine = new_slots('cleric', slot_budget(self.core, 'cleric', 1, 14))
        with self.assertRaises(ValueError):
            recover_slots(self.core, divine, start_seconds=0, end_seconds=3600, scheduled_second_of_day=1)
        self.assertEqual(recover_slots(self.core, divine, start_seconds=0, end_seconds=3600,
                                      scheduled_second_of_day=0)['lastRecovery']['day'], 0)
