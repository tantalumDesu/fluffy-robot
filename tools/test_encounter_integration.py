import unittest

from tools.test_state_changes import CORE
from tools.encounter_conditions import advance_turn, change_conditions, effective_conditions
from tools.game_time import new_encounter, spend_action
from tools.drain_history import commit_negative_levels, projected_history, resolve_character_drain_save, restore_character_drain
from tools.negative_levels import create_drain_levels
from tools.spellcasting import recover_spell_tracks


class EncounterIntegrationTest(unittest.TestCase):
    def test_midturn_override_does_not_refund_action(self):
        state, _ = advance_turn(CORE, new_encounter(['a']))
        state = spend_action(state, 'standard')
        state = change_conditions(CORE, state, 'a', add=['stunned'])
        with self.assertRaises(ValueError):
            spend_action(state, 'move')
        state = change_conditions(CORE, state, 'a', dm_override={'reason': 'Allow movement this turn', 'turnFlags': []})
        self.assertEqual(effective_conditions(state, 'a'), ['stunned'])
        with self.assertRaises(ValueError):
            spend_action(state, 'standard')
        state = spend_action(state, 'move')
        self.assertEqual(len(state['dmRulings']), 1)

    def test_rage_escalates_existing_fatigue(self):
        state = change_conditions(CORE, new_encounter(['a']), 'a', add=['fatigued'],
                                  machine='rage', event='rage-started')
        state = change_conditions(CORE, state, 'a', machine='rage', event='rage-ended', facts={'tirelessRage': False})
        self.assertEqual(effective_conditions(state, 'a'), ['exhausted'])

    def test_drain_save_and_restoration_keep_history(self):
        original = dict(classChoices=['fighter', 'wizard', 'fighter'], xp=3100,
                        levelGrantsByLevel={'3': dict(hpGain=5, abilityIncreases={}, skillRanks={}, featChoices=[])})
        levels = create_drain_levels(CORE['mechanics']['negativeLevels'], 'hit', 1, 0,
                                     kind='creature', save_dc=15)['levels']
        actor = commit_negative_levels(CORE, original, levels, 0)
        due = levels[0]['saveDueAtSeconds']
        actor = resolve_character_drain_save(CORE, actor, levels[0]['id'], due, 14)
        self.assertEqual(actor['drainXpOverride'], 2000)
        self.assertEqual(actor['xp'], original['xp'])
        self.assertEqual(projected_history(CORE, actor)['classLevels'], {'fighter': 1, 'wizard': 1})
        actor = restore_character_drain(CORE, actor, 'restoration', due, 7)
        self.assertEqual(actor['drainXpOverride'], 3000)
        self.assertEqual(actor['xp'], original['xp'])
        self.assertEqual(actor['classChoices'], original['classChoices'])
        self.assertEqual(projected_history(CORE, actor)['characterLevel'], 3)

    def test_recovery_requires_tie_choice_and_does_not_mutate_ledger(self):
        slot = dict(level=1, expended=False, preparation=None)
        ledgers = {'wizard': dict(classId='wizard', slots={'a': dict(slot), 'b': dict(slot)})}
        args = {'wizard': dict(start_seconds=28800, end_seconds=32400, verified_rest_seconds=28800)}
        levels = [dict(id='one', kind='energy-drain')]
        with self.assertRaisesRegex(ValueError, 'Choose'):
            recover_spell_tracks(CORE, ledgers, args, at_seconds=32400, negative_levels=levels)
        result = recover_spell_tracks(CORE, ledgers, args, at_seconds=32400, negative_levels=levels,
                                      choices=[('wizard', 'b')])
        self.assertEqual(result['wizard']['slots']['b']['negativeLevelLoss'], 'recovery')
        self.assertNotIn('negativeLevelLoss', ledgers['wizard']['slots']['b'])
