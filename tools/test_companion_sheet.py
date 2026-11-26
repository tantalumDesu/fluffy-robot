import json
import unittest

from tools.companion_sheet import project_companion
from tools.derived_stats import derive_sheet
from tools.level_history import replay_level_history
from tools.organize_core import PATH


class CompanionSheetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = json.loads(PATH.read_bytes())

    def test_wizard_familiar_on_sheet_and_master_hp(self):
        history = replay_level_history(self.core, ['wizard'] * 7 + ['fighter'])
        result = derive_sheet(self.core, history, 'human', dict(str=10, dex=10, con=10, int=16, wis=10, cha=10),
                              companion_links=[dict(instanceId='bat', definitionId='familiars:bat')], master_max_hp=31)
        bat = result['companions'][0]
        self.assertEqual((bat['effectiveMasterLevel'], bat['maxHp'], bat['effectiveHitDice']), (7, 15, '8'))
        self.assertEqual(bat['baseAttackBonus'], history['classBaseCombat']['bab'])
        self.assertEqual(bat['abilityScores']['int'], 9)
        self.assertEqual(bat['armorClass']['normal'], 20)
        self.assertIn('Blindsense', bat['statBlockText'])
        self.assertIn('Speak with animals of its kind', bat['specialAbilities'])

    def test_druid_advances_companion_and_preserves_base(self):
        link = dict(instanceId='wolf', definitionId='animal-companions:wolf', bonusHitDieRolls=[4, 5])
        one = project_companion(self.core, replay_level_history(self.core, ['druid']), link)
        three = project_companion(self.core, replay_level_history(self.core, ['druid'] * 3), link)
        self.assertEqual(three['bonusHitDice'], 2)
        self.assertEqual(three['baseAttackBonus'], 3)
        self.assertEqual(three['abilityScores']['str'], one['abilityScores']['str'] + 1)
        self.assertGreater(three['maxHp'], one['maxHp'])
        self.assertEqual(three['statBlockText'], one['statBlockText'])
        self.assertIn('Evasion', three['specialAbilities'])

    def test_improved_familiar_does_not_gain_speak_with_kind(self):
        history = replay_level_history(self.core, ['wizard'] * 7)
        v = project_companion(self.core, history, dict(instanceId='v', definitionId='vargouille-without-kiss'))
        self.assertEqual(v['excludedAbilityIds'], ['kiss'])
        self.assertNotIn('Speak with animals of its kind', v['specialAbilities'])

    def test_familiar_dismissal_xp_and_replacement_wait(self):
        from tools.companion_sheet import resolve_familiar_loss
        facts = dict(class_id='wizard', class_level=5, current_xp=1500, event='dismissal')
        failed = resolve_familiar_loss(self.core, fortitude_save_total=14, **facts)
        passed = resolve_familiar_loss(self.core, fortitude_save_total=15, **facts)
        self.assertEqual((failed['xpLost'], failed['xpAfter']), (1000, 500))
        self.assertEqual((passed['xpLost'], passed['xpAfter']), (500, 1000))
        self.assertEqual(passed['replacementWait'], {'years': 1, 'days': 1})
        self.assertEqual(resolve_familiar_loss(self.core, class_id='wizard', class_level=5,
                         current_xp=100, fortitude_save_total=14, event='death')['xpAfter'], 0)
