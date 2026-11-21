import json
import unittest

from tools.animal_training import plan_training, training_status, work_command
from tools.organize_core import PATH


class AnimalTrainingTest(unittest.TestCase):
    def setUp(self):
        core = json.loads(PATH.read_bytes())
        self.rules = core['skills']['animalTraining']
        self.pony = core['companions']['creaturesById']['beasts-of-burden:pony']
        self.state = core['inventory']['packAnimalsById']['pony']['initialTraining']

    def plan(self, kind, choice_id, state=None, **kwargs):
        return plan_training(self.rules, self.pony, self.state if state is None else state,
                             kind=kind, choice_id=choice_id, **dict({'handler_ranks': 1}, **kwargs))

    def test_heavy_labor_unlocks_handling_work_after_completion(self):
        self.assertEqual(work_command(self.rules, self.state), {'action': 'full-round', 'dc': 25})
        plan = self.plan('purpose', 'heavy-labor', purpose_eligible=True)
        self.assertEqual((plan['totalHours'], plan['checkAtHours']), (42, 21))
        self.assertEqual(training_status(plan, 21), {'status': 'check-due', 'dc': 15})
        self.assertEqual(training_status(plan, 21, check_total=14), {'status': 'failed'})
        self.assertEqual(training_status(plan, 21, check_total=15), {'status': 'working'})
        self.assertEqual(training_status(plan, 42, check_total=15, interrupted=True), {'status': 'failed'})
        learned = training_status(plan, 42, check_total=15)['trainingState']
        self.assertEqual(learned['learnedTrickIds'], ['come', 'work'])
        self.assertEqual(work_command(self.rules, learned, injured=True), {'action': 'move', 'dc': 12})
        self.assertEqual(self.state['learnedTrickIds'], [])

    def test_combat_riding_upgrade_replaces_normal_tricks_not_stats(self):
        state = dict(self.state, purposeId='riding', learnedTrickIds=['come', 'heel', 'stay', 'work'],
                     bonusTrickIds=['fetch'])
        plan = self.plan('purpose', 'combat-riding', state, purpose_eligible=True)
        self.assertEqual((plan['totalHours'], plan['dc']), (63, 20))
        self.assertNotIn('work', plan['resultingState']['learnedTrickIds'])
        self.assertEqual(plan['resultingState']['bonusTrickIds'], ['fetch'])
        self.assertFalse(self.pony['combatTrained'])
        self.assertEqual(self.pony['attacks'], [])

    def test_constraints(self):
        with self.assertRaises(ValueError):
            self.plan('trick', 'work', handler_ranks=0)
        with self.assertRaises(ValueError):
            self.plan('trick', 'track')
        self.assertEqual(self.plan('trick', 'track', has_scent=True)['dc'], 20)
        with self.assertRaises(ValueError):
            self.plan('purpose', 'riding')
        state = dict(self.state, learnedTrickIds=['attack', 'come', 'heel', 'stay', 'fetch', 'work'])
        with self.assertRaises(ValueError):
            self.plan('trick', 'attack-all', state)
