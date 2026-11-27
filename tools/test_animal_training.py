import copy
import json
import unittest

from tools.animal_training import plan_training, training_choices, training_status, work_command
from tools.organize_core import PATH
from tools.mounted import acquisition_training


class AnimalTrainingTest(unittest.TestCase):
    def setUp(self):
        core = json.loads(PATH.read_bytes())
        self.rules = core['skills']['animalTraining']
        self.pony = core['companions']['creaturesById']['beasts-of-burden:pony']
        self.assertEqual(acquisition_training(core, self.pony)['purposeId'], 'riding')
        self.state = dict(purposeId=None, learnedTrickIds=[], bonusTrickIds=[])

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
        self.assertNotIn('combatTrained', self.pony)
        self.assertEqual(self.pony['attacks'], [])

    def test_constraints(self):
        with self.assertRaises(ValueError):
            self.plan('trick', 'work', handler_ranks=0)
        with self.assertRaises(ValueError):
            self.plan('trick', 'track', has_scent=False)
        self.assertEqual(self.plan('trick', 'track', has_scent=True)['dc'], 20)
        with self.assertRaises(ValueError):
            self.plan('purpose', 'riding')
        state = dict(self.state, learnedTrickIds=['attack', 'come', 'heel', 'stay', 'fetch', 'work'])
        with self.assertRaises(ValueError):
            self.plan('trick', 'attack-all', state)

    def test_choices_explain_prerequisites_without_assigning_training(self):
        original = copy.deepcopy(self.state)
        choices = training_choices(self.rules, self.pony, self.state, handler_ranks=1, has_scent=False,
                                   purpose_suitability={'riding': True, 'heavy-labor': False})
        tricks, purposes = choices['tricksById'], choices['purposesById']
        self.assertEqual(tricks['track']['reasonId'], 'requires-scent')
        self.assertEqual(purposes['hunting']['status'], 'blocked')
        self.assertEqual(purposes['heavy-labor']['status'], 'blocked')
        self.assertEqual(purposes['guarding']['status'], 'needs-review')
        self.assertEqual(purposes['riding']['status'], 'available')
        plan = self.plan('purpose', 'riding', purpose_eligible=True)
        self.assertEqual(purposes['riding']['totalHours'], plan['totalHours'])
        self.assertEqual(self.state, original)

    def test_choices_keep_known_tricks_and_report_riding_upgrade(self):
        state = dict(self.state, purposeId='riding', learnedTrickIds=['come', 'heel', 'stay'], bonusTrickIds=['fetch'])
        choices = training_choices(self.rules, self.pony, state, handler_ranks=1,
                                   purpose_suitability={'combat-riding': True})
        self.assertEqual(choices['tricksById']['fetch']['status'], 'known')
        self.assertEqual(choices['purposesById']['riding']['status'], 'known')
        self.assertEqual(choices['purposesById']['combat-riding']['totalHours'], 63)
        self.assertEqual(choices['purposesById']['fighting']['reasonId'], 'existing-purpose')
        exotic = dict(self.pony, creatureType='magical beast')
        self.assertEqual(training_choices(self.rules, exotic, state, handler_ranks=1)['tricksById']['work']['dc'], 20)

    def test_sheet_training_choices_and_source_specific_training(self):
        from tools.companion_sheet import project_creature
        core = json.loads(PATH.read_bytes())
        link = dict(instanceId='mount', definitionId='unusual-mounts:griffon',
                    trainingContext=dict(handler_ranks=2, purpose_suitability={'combat-riding': True}))
        subject = project_creature(core, {}, link)
        self.assertEqual(subject['trainingChoices']['purposesById']['combat-riding']['reasonId'], 'friendliness')
        link['trainingContext']['friendly_confirmed'] = True
        subject = project_creature(core, {}, link)
        choice = subject['trainingChoices']['purposesById']['combat-riding']
        self.assertEqual((choice['status'], choice['dc'], choice['totalHours']), ('available', 25, 126))
        self.assertIsNone(subject['training']['purposeId'])
