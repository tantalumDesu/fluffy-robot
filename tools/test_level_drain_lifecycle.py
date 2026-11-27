import json
import unittest

from tools.drain_history import (apply_permanent_level_loss, commit_negative_levels, projected_level_grants,
                                 resolve_character_drain_save, restore_character_drain)
from tools.level_choices import record_level_choices
from tools.negative_levels import create_drain_levels, minimum_restoration_caster_level
from tools.organize_core import PATH


def fail_drain(core, actor, event, *, hd=4, delay=0):
    levels = create_drain_levels(core['mechanics']['negativeLevels'], event, 1, 0,
                                 kind='creature', save_dc=15, attacker_hd=hd,
                                 )['levels']
    actor = commit_negative_levels(core, actor, levels, 0)
    return resolve_character_drain_save(core, actor, levels[0]['id'], 86400 + delay, 14)


class LevelDrainLifecycleTest(unittest.TestCase):
    def test_minimum_restoring_caster_level_and_irreversible_loss(self):
        core = json.loads(PATH.read_bytes())
        old_feat = {'featId': 'toughness'}
        actor = dict(classChoices=['fighter'] * 3, xp=3100, maxHp=20, featChoices=[old_feat],
                     abilityScores=dict(con=12, int=10), levelGrantsByLevel={'3': dict(
                         hpGain=6, abilityIncreases={}, skillRanks={}, featChoices=[old_feat])})
        lost = fail_drain(core, actor, 'source', hd=4, delay=100)
        failed = 86500
        record = lost['drainedLevels'][0]
        self.assertEqual(record['failedSaveAtSeconds'], failed)
        self.assertEqual(minimum_restoration_caster_level(core, 'restoration', record, failed + 86400), 1)
        self.assertEqual(minimum_restoration_caster_level(core, 'restoration', record, failed + 86401), 2)
        self.assertEqual(minimum_restoration_caster_level(core, 'restoration-greater', record, failed + 86401), 1)
        rejected = restore_character_drain(core, lost, 'restoration', failed + 86401, 1)
        self.assertEqual(rejected['drainedLevels'], lost['drainedLevels'])
        recovered = restore_character_drain(core, rejected, 'restoration', failed + 86401, 2)
        self.assertEqual(projected_level_grants(core, recovered)['featChoices'], [old_feat])
        expired = apply_permanent_level_loss(core, actor, 'raise', 0, cause='raise-dead')
        self.assertNotIn('3', expired['levelGrantsByLevel'])
        new_feat = {'featId': 'iron-will'}
        earned = record_level_choices(core, expired, 'elf', class_id='fighter', xp_award=1000,
                                      choices=dict(hitDieRoll=4, abilityIncreases={}, skillRanks={}, featChoices=[new_feat]))
        self.assertEqual(earned['featChoices'], [new_feat])
        self.assertNotIn('levelLossHistory', earned)
        death = apply_permanent_level_loss(core, actor, 'raise', 0, cause='raise-dead')
        after = restore_character_drain(core, death, 'restoration-greater', 1, 40)
        self.assertEqual(projected_level_grants(core, after)['featChoices'], [])

    def test_earned_level_consumes_only_one_loss_and_restoration_cannot_overlevel(self):
        from tools.drain_history import lost_level_recovery_options

        core = json.loads(PATH.read_bytes())
        feat = {'featId': 'toughness'}
        actor = dict(classChoices=['fighter'] * 4, xp=6200, maxHp=30, featChoices=[feat],
                     abilityScores=dict(str=15, con=12, int=10), levelGrantsByLevel={
                         '3': dict(hpGain=6, abilityIncreases={}, skillRanks={}, featChoices=[feat]),
                         '4': dict(hpGain=5, abilityIncreases={'str': 1}, skillRanks={}, featChoices=[])})
        actor = fail_drain(core, actor, 'first')
        actor = fail_drain(core, actor, 'second', delay=10)
        actor = record_level_choices(core, actor, 'elf', xp_award=1)
        self.assertEqual(len(actor['drainedLevels']), 2)
        choice = {'featId': 'iron-will'}
        actor = record_level_choices(core, actor, 'elf', class_id='fighter', xp_award=999,
                                      choices=dict(hitDieRoll=4, abilityIncreases={}, skillRanks={}, featChoices=[choice]))
        options = lost_level_recovery_options(core, actor, 86401)
        self.assertEqual([row['characterLevel'] for row in options], [4])
        self.assertEqual(options[0]['spells']['restoration']['minimumClericCasterLevel'], 7)
        self.assertEqual(options[0]['spells']['restoration-greater']['clericSpellLevel'], 7)
        self.assertEqual(projected_level_grants(core, actor)['featChoices'], [choice])
        restored = restore_character_drain(core, actor, 'restoration-greater', 86411, 13)
        view = projected_level_grants(core, restored)
        self.assertEqual(view['history']['characterLevel'], 4)
        self.assertEqual(view['featChoices'], [choice])
        self.assertEqual(view['abilityScores']['str'], 15)
        self.assertEqual(view['xp'], 6000)
        self.assertFalse(restored['drainedLevels'])

    def test_confirmed_greater_restoration_pays_caster_xp_only(self):
        from tools.drain_history import commit_restoration_cast

        core = json.loads(PATH.read_bytes())
        caster = dict(classChoices=['cleric'] * 13, xp=78900)
        target = dict(classChoices=['fighter'] * 3, xp=3100, maxHp=20,
                      abilityScores=dict(con=12), levelGrantsByLevel={
                          '3': dict(hpGain=5, abilityIncreases={}, skillRanks={}, featChoices=[])})
        lost = fail_drain(core, target, 'cost')
        result = commit_restoration_cast(core, caster, lost, 'restoration-greater', 86401, 13)
        self.assertEqual(result['caster']['xp'], 78400)
        self.assertEqual(caster['xp'], 78900)
        self.assertEqual(projected_level_grants(core, result['recipient'])['xp'], 3000)
        with self.assertRaisesRegex(ValueError, 'without losing a level'):
            commit_restoration_cast(core, dict(caster, xp=78000), lost, 'restoration-greater', 86401, 13)
