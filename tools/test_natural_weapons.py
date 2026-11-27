import json
import unittest

from tools.drain_history import derive_level_loss_sheet
from tools.level_choices import record_level_choices
from tools.natural_weapons import form_roster, project
from tools.organize_core import PATH


class NaturalWeaponsTest(unittest.TestCase):
    def test_one_claw_pick_across_forms(self):
        core = json.loads(PATH.read_bytes())
        bear = 'alternative-animal-companions:bear-black'
        tiger = 'alternative-animal-companions:tiger'
        actor = dict(classChoices=['fighter'] * 5, xp=10000, maxHp=30,
                     abilityScores=dict(str=16, dex=12, con=12, int=10, wis=10, cha=10),
                     availableNaturalFormIds=[bear, tiger])
        pick = dict(featId='improved-natural-attack', choices=dict(naturalAttackId='claw'))
        choices = dict(hitDieRoll=5, abilityIncreases={}, skillRanks={}, featChoices=[pick])
        actor = record_level_choices(core, actor, 'elf', class_id='fighter', xp_award=5000, choices=choices)
        for form, die in ((bear, '1d6'), (tiger, '2d6')):
            sheet = derive_level_loss_sheet(core, dict(actor, activeNaturalFormId=form), 'elf')
            claw, bite = sheet['naturalWeapons']
            self.assertEqual((claw['naturalAttackId'], claw['count'], claw['damageDice']), ('claw', 2, die))
            self.assertEqual(bite, form_roster(core, form)[1])
            self.assertEqual(sheet['improvedNaturalAttackChoices'], ['bite'])
        self.assertEqual(derive_level_loss_sheet(core, actor, 'elf')['naturalWeapons'], [])
        self.assertEqual(project(core, form_roster(core, bear), [pick, pick])[0]['damageDice'], '1d6')
