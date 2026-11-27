import json
import unittest
from pathlib import Path

from tools.derived_stats import derive_sheet
from tools.game_time import new_encounter, spend_action, start_next_turn


class DerivedSheetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = json.loads((Path(__file__).resolve().parents[1] / 'dnd-core.json').read_text())

    def sheet(self, race='human', **kwargs):
        return derive_sheet(self.core, dict(characterLevel=3, classBaseCombat=dict(bab=3, fort=3, ref=1, will=1)),
                            race, dict(str=14, dex=16, con=12, int=10, wis=10, cha=10), **kwargs)

    def test_load_and_armor(self):
        armor = dict(instanceId='armor', itemId='armor:leather')
        sheet = self.sheet(equipment=[armor], carried_weight_lb=150)
        self.assertEqual(sheet['loadBand'], 'heavy')
        self.assertEqual(sheet['landSpeedFt'], 20)
        self.assertEqual(sheet['armorCheckPenalty'], -6)
        self.assertEqual({key: sheet['ac'][key]['total'] for key in ('normal', 'touch', 'flatFooted')},
                         dict(normal=13, touch=11, flatFooted=12))
        self.assertEqual(self.sheet('dwarf', carried_weight_lb=150)['landSpeedFt'], 20)

    def test_stun_drops_opposed_weapon_and_blocks_turn(self):
        weapon = dict(instanceId='blade', itemId='weapon:longsword', proficient=True, held=True,
                      alignmentPropertyIds=['holy'])
        ready = self.sheet(equipment=[weapon], alignment_id='NE')
        stunned = self.sheet(equipment=[weapon], alignment_id='NE', condition_ids=['stunned'])
        self.assertEqual(ready['attacks'][0]['attackBonus'], 4)
        self.assertEqual(stunned['saves']['fort'], ready['saves']['fort'] + 1)
        self.assertEqual(stunned['droppedInstanceIds'], ['blade'])
        self.assertEqual(stunned['attacks'][0]['itemId'], 'weapon:unarmed-strike')
        self.assertEqual(stunned['ac']['normal']['total'], 8)
        turn, _ = start_next_turn(new_encounter(['actor']), condition_flags_by_actor={'actor': stunned['conditionFlags']})
        with self.assertRaisesRegex(ValueError, 'cannot take actions'):
            spend_action(turn, 'standard')

    def test_absent_constitution_is_not_zero_and_ignores_bonuses(self):
        history = dict(characterLevel=3, classBaseCombat=dict(bab=3, fort=3, ref=1, will=1))
        scores = dict(str=14, dex=16, con=None, int=10, wis=10, cha=10)
        effect = dict(id='test-con', operation='modifier', statId='ability:con', amount=4, stacking='sum')
        absent = derive_sheet(self.core, history, 'human', scores, active_effects=[(effect, {})])
        self.assertIsNone(absent['abilityScores']['con'])
        self.assertEqual(absent['abilityModifiers']['con'], 0)
        self.assertEqual(absent['saves']['fort'], 3)
        zero = derive_sheet(self.core, history, 'human', dict(scores, con=0))
        self.assertEqual(zero['abilityModifiers']['con'], -5)

    def test_all_named_conditions_have_structured_rules(self):
        conditions = self.core['effects']['conditions']
        rules = self.core['effects']['sheetConditionRulesById']
        self.assertEqual(len(conditions), 38)
        self.assertEqual({c['id']: c['mechanics'] for c in conditions}, rules)
        for rule in rules.values():
            self.assertTrue(any(rule[k] for k in ('flags', 'modifiers', 'operations')))

    def test_condition_modifiers_and_implications(self):
        sheet = self.sheet(condition_ids=['sickened', 'frightened', 'shaken', 'entangled'])
        self.assertEqual(sheet['abilityScores']['dex'], 12)
        self.assertEqual(sheet['saves']['fort'], 0)
        self.assertEqual(sheet['landSpeedFt'], 15)
        paralyzed = self.sheet(condition_ids=['paralyzed'])
        self.assertEqual(paralyzed['abilityScores']['str'], 0)
        self.assertEqual(paralyzed['abilityScores']['dex'], 0)
        self.assertEqual(paralyzed['landSpeedFt'], 0)
        self.assertFalse(paralyzed['attacks'][0]['canAct'])

    def test_limited_turn_budgets(self):
        for condition in ('staggered', 'disabled', 'nauseated'):
            flags = self.sheet(condition_ids=[condition])['conditionFlags']
            turn, _ = start_next_turn(new_encounter(['actor']), condition_flags_by_actor={'actor': flags})
            with self.assertRaises(ValueError):
                spend_action(turn, 'full-round')
            turn = spend_action(turn, 'move')
            with self.assertRaises(ValueError):
                spend_action(turn, 'move')

    def test_locked_gauntlet_projects_numbers_and_keeps_adjudication_text(self):
        gauntlet = dict(instanceId='g', itemId='armor:gauntlet-locked', hand='primary')
        blade = dict(instanceId='blade', itemId='weapon:longsword', held=True)
        plate = dict(instanceId='armor', itemId='armor:full-plate', fitted=True)
        open_sheet = self.sheet(equipment=[gauntlet])
        self.assertEqual(open_sheet['lockedGauntlets'][0]['effectiveWeightLb'], 5)
        self.assertTrue(open_sheet['attacks'][0]['allowsLethalViaGauntlet'])
        locked = dict(gauntlet, securedWeaponInstanceId='blade')
        sheet = self.sheet(equipment=[locked, blade, plate], carried_weight_lb=60)
        self.assertEqual(sheet['carriedWeightAdjustmentLb'], -5)
        self.assertEqual(sheet['attacks'][0]['disarmDefenseBonus'], 10)
        self.assertTrue(sheet['lockedGauntlets'][0]['handUnavailableForCastingOrSkills'])
        self.assertIn('full-round action', sheet['lockedGauntlets'][0]['adjudicationText'])
        stunned = self.sheet(equipment=[locked, blade], condition_ids=['stunned'])
        self.assertIn('adjudicate-drop-secured-weapon', stunned['needsReview'])
        self.assertFalse(stunned['attacks'][0]['canAct'])
        with self.assertRaises(ValueError):
            self.sheet(equipment=[locked])

    def test_prone_attack_profiles_and_defense(self):
        restriction = self.core['effects']['sheetConditionRulesById']['prone']['operations']['prohibitedWeaponUse']
        ids = [*restriction['exceptWeaponIds'], 'weapon:longbow', 'weapon:longsword']
        equipment = [dict(instanceId=id_, itemId=id_, proficient=True) for id_ in ids]
        upright = self.sheet(equipment=equipment)
        prone = self.sheet(equipment=equipment, condition_ids=['prone'], attack_context={'incomingAttackKind': 'ranged'})
        self.assertEqual([a['canAct'] for a in prone['attacks']], [True] * 7 + [False, True])
        for item_id in ('weapon:dart', 'weapon:shuriken-5'):
            with self.subTest(item_id=item_id):
                index = ids.index(item_id)
                self.assertEqual(prone['attacks'][index]['attackBonus'], upright['attacks'][index]['attackBonus'])
        self.assertEqual(prone['attacks'][-1]['attackBonus'], upright['attacks'][-1]['attackBonus'] - 4)
        self.assertEqual(prone['ac']['normal']['total'], upright['ac']['normal']['total'] + 4)
        melee = self.sheet(condition_ids=['prone'], attack_context={'incomingAttackKind': 'melee'})
        self.assertEqual(melee['ac']['normal']['total'], upright['ac']['normal']['total'] - 4)

    def test_sheet_damage_reduction_into_hp(self):
        from tools.injury import resolve_sheet_damage
        from tools.level_history import replay_level_history
        history = replay_level_history(self.core, ['barbarian'] * 7)
        defender = derive_sheet(self.core, history, 'human',
                                dict(str=14, dex=16, con=12, int=10, wis=10, cha=10),
                                damage_reduction_grants=[dict(sourceId='confirmed-ward', amount=5,
                                                              bypassAnyOf=[['good', 'slashing']])])
        self.assertEqual([r['amount'] for r in defender['damageReduction']], [1, 5])
        blade = dict(instanceId='blade', itemId='weapon:longsword', held=True, alignmentPropertyIds=['holy'])
        attack = self.sheet(equipment=[blade], alignment_id='LG')['attacks'][0]
        state = dict(hp=20, maxHp=20)
        first = resolve_sheet_damage(self.core, state, defender, attack=attack, weapon=4, round_id=1)
        self.assertEqual(first['weaponPrevented'], 1)
        self.assertEqual(first['state']['hp'], 17)
        second = resolve_sheet_damage(self.core, first['state'], defender, weapon=6, round_id=1)
        self.assertEqual(second['weaponPrevented'], 4)
        self.assertEqual(second['state']['hp'], 15)
        third = resolve_sheet_damage(self.core, second['state'], defender, weapon=6, round_id=2)
        self.assertEqual(third['weaponPrevented'], 5)

    def test_equipment_slots_two_weapon_feats_and_defense(self):
        sword = dict(instanceId='sword', itemId='weapon:longsword', hand='primary', proficient=True)
        dagger = dict(instanceId='dagger', itemId='weapon:dagger', hand='offhand', proficient=True)
        baseline = self.sheet(equipment=[sword, dagger])
        routine = baseline['twoWeaponRoutine']
        self.assertEqual((routine['mainHandPenalty'], routine['offHandPenalty']), (-4, -8))
        self.assertEqual(routine['mainHand']['instanceId'], 'sword')
        self.assertEqual(baseline['equipmentSlots']['bySlot']['grip-offhand'], 'dagger')
        feats = ['two-weapon-fighting', 'improved-two-weapon-fighting', 'greater-two-weapon-fighting', 'two-weapon-defense']
        trained = self.sheet(equipment=[sword, dagger], feat_ids=feats,
                             attack_context={'fightingDefensively': True})
        routine = trained['twoWeaponRoutine']
        self.assertEqual((routine['mainHandPenalty'], routine['offHandPenalty']), (-2, -2))
        self.assertEqual(routine['offHand']['attackBonuses'], [3, -2, -7])
        self.assertEqual(trained['ac']['normal']['total'], baseline['ac']['normal']['total'] + 2)
        self.assertEqual(trained['ac']['touch']['total'], baseline['ac']['touch']['total'])
        with self.assertRaisesRegex(ValueError, 'occupied'):
            self.sheet(equipment=[sword, dict(dagger, hand='primary')])
        with self.assertRaisesRegex(ValueError, 'ring-left'):
            self.sheet(equipment=[dict(sword, slotId='ring-left'), dict(dagger, slotId='ring-left')])

    def test_two_handed_double_weapon_and_shield_bash(self):
        staff = dict(instanceId='staff', itemId='weapon:quarterstaff', proficient=True)
        self.assertFalse(self.sheet(equipment=[dict(staff, hand='primary')])['attacks'][0]['canAct'])
        two_hands = self.sheet(equipment=[dict(staff, gripHands=['primary', 'offhand'])], double_weapon_instance_id='staff')
        self.assertTrue(two_hands['twoWeaponRoutine']['doubleWeapon'])
        shield = dict(instanceId='shield', itemId='armor:shield-light-steel', hand='offhand', proficient=True,
                      bashWeaponId='weapon:spiked-shield-light', additionIds=['armor:shield-spikes'])
        sword = dict(instanceId='sword', itemId='weapon:longsword', hand='primary', proficient=True)
        context = {'shieldBashUsedInstanceIds': ['shield']}
        no_feat = self.sheet(equipment=[sword, shield], attack_context=context)
        feat = self.sheet(equipment=[sword, shield], attack_context=context, feat_ids=['improved-shield-bash'])
        self.assertEqual(no_feat['twoWeaponRoutine']['offHand']['instanceId'], 'shield')
        self.assertEqual(no_feat['attacks'][1]['physicalDamage']['typeIds'], ['piercing'])
        self.assertEqual(feat['ac']['normal']['total'], no_feat['ac']['normal']['total'] + 1)

    def test_ranger_style_and_buckler(self):
        from tools.level_history import replay_level_history
        history = replay_level_history(self.core, ['ranger'] * 6)
        gear = [dict(instanceId='sword', itemId='weapon:longsword', hand='primary', proficient=True),
                dict(instanceId='dagger', itemId='weapon:dagger', hand='offhand', proficient=True),
                dict(instanceId='buckler', itemId='armor:buckler', hand='offhand')]
        scores = dict(str=14, dex=16, con=12, int=10, wis=10, cha=10)
        light = derive_sheet(self.core, history, 'human', scores, equipment=gear,
                             ranger_combat_style='two-weapon')
        heavy = derive_sheet(self.core, history, 'human', scores, equipment=gear + [
            dict(instanceId='plate', itemId='armor:full-plate', fitted=True)], ranger_combat_style='two-weapon')
        self.assertEqual(light['twoWeaponRoutine']['offHandPenalty'], -2)
        self.assertEqual(len(light['twoWeaponRoutine']['offHand']['attackBonuses']), 2)
        self.assertEqual(heavy['twoWeaponRoutine']['offHandPenalty'], -8)
        self.assertEqual(light['attacks'][1]['breakdown']['grip'], -1)
        used = derive_sheet(self.core, history, 'human', scores, equipment=gear,
                            attack_context={'bucklerArmUsedInstanceIds': ['buckler']})
        self.assertEqual(used['ac']['normal']['total'], light['ac']['normal']['total'] - 1)

    def test_familiar_spell_choices_and_repeated_grants(self):
        from tools.feat_selection import check_familiar_spell_selection
        known = {'chain-lightning': 6, 'magic-missile': 1, 'time-stop': 9, 'fireball': 3, 'identify': 1, 'wish': 8}
        picks = [dict(featId='familiar-spell', choices={'spellId': key})
                 for key in ('chain-lightning', 'magic-missile', 'magic-missile')]
        sheet = self.sheet(known_spell_levels=known, feat_choices=picks)
        self.assertEqual([o['spellId'] for o in sheet['familiarSpellChoices']['eligible']],
                         ['magic-missile', 'fireball', 'chain-lightning'])
        self.assertEqual([o['spellId'] for o in sheet['familiarSpellChoices']['needsReview']], ['identify'])
        self.assertEqual([o['label'] for o in sheet['familiarSpellGrants']],
                         ['Familiar Spell, Chain Lightning 1/day', 'Familiar Spell, Magic Missile 2/day'])
        facts = dict(feats=picks, characterLevel=21, hasFamiliar=True, abilityScores={'int': 25})
        self.assertEqual(check_familiar_spell_selection(self.core, facts, 'magic-missile',
                         known_spell_levels=known)['status'], 'eligible')
        self.assertEqual(check_familiar_spell_selection(self.core, facts, 'identify',
                         known_spell_levels=known, verified_material_cost_gp={'identify': 100})['status'], 'ineligible')

    def test_weapon_focus_choices_and_dynamic_ray_spells(self):
        from tools.feat_selection import check_weapon_focus_selection
        from tools.level_history import replay_level_history
        known = {'ray-of-frost': 0, 'magic-missile': 1}
        weapon = dict(instanceId='sword', itemId='weapon:longsword')
        picks = [dict(featId='weapon-focus', choices={'weaponId': id_}) for id_ in
                 ('weapon:longsword', 'weapon:grapple', 'weapon:ray', 'weapon:unarmed-strike')]
        history = replay_level_history(self.core, ['fighter', 'wizard'])
        scores = dict(str=14, dex=16, con=12, int=16, wis=10, cha=10)
        args = dict(equipment=[weapon], weapon_proficiencies=['weapon:longsword'], known_spell_levels=known)
        clean = derive_sheet(self.core, history, 'human', scores, **args)
        focused = derive_sheet(self.core, history, 'human', scores, feat_choices=picks, **args)
        self.assertEqual(focused['attacks'][0]['attackBonus'], clean['attacks'][0]['attackBonus'] + 1)
        self.assertEqual(focused['grappleBonus'], clean['grappleBonus'] + 1)
        self.assertEqual(focused['specialAttackModifiers']['weapon:unarmed-strike'], 1)
        self.assertEqual({o['weaponId'] for o in focused['weaponFocusChoices']},
                         {'weapon:longsword', 'weapon:grapple', 'weapon:ray', 'weapon:unarmed-strike'})
        self.assertIn('Weapon Focus, Ray', [o['label'] for o in focused['weaponFocusGrants']])
        later = derive_sheet(self.core, history, 'human', scores, feat_choices=picks,
                             **dict(args, known_spell_levels=dict(known, **{'scorching-ray': 2})))
        self.assertEqual({o['spellId'] for o in later['knownSpells'] if o.get('weaponFocusAttackBonus') == 1},
                         {'ray-of-frost', 'scorching-ray'})
        facts = dict(feats=[], weaponProficiencies=['weapon:longsword'], classLevels={'fighter': 1}, baseAttackBonus=1)
        self.assertEqual(check_weapon_focus_selection(self.core, facts, 'weapon:ray')['status'], 'ineligible')
        self.assertEqual(check_weapon_focus_selection(self.core, facts, 'weapon:dagger')['status'], 'ineligible')
        self.assertEqual(check_weapon_focus_selection(self.core, dict(facts, classLevels={'wizard': 1}),
                         'weapon:ray')['status'], 'eligible')

    def test_dependent_weapon_feats_use_exact_choice(self):
        from tools.feat_selection import check_weapon_focus_selection
        ray = {'weaponId': 'weapon:ray'}
        picks = [dict(featId=feat, choices=ray) for feat in (
            'weapon-focus', 'greater-weapon-focus', 'weapon-specialization', 'greater-weapon-specialization')]
        facts = dict(feats=picks[:1], classLevels={'fighter': 8, 'wizard': 1},
                     weaponProficiencies=['weapon:longsword'])
        for feat in ('greater-weapon-focus', 'weapon-specialization'):
            self.assertEqual(check_weapon_focus_selection(self.core, facts, 'weapon:ray', feat_id=feat)['status'], 'eligible')
            self.assertEqual(check_weapon_focus_selection(self.core, facts, 'weapon:longsword', feat_id=feat)['status'], 'ineligible')
        sheet = self.sheet(feat_choices=picks, known_spell_levels={'ray-of-frost': 0})
        self.assertEqual(sheet['knownSpells'][0]['weaponFocusAttackBonus'], 2)
        self.assertEqual(sheet['knownSpells'][0]['weaponSpecializationDamageBonus'], 4)

    def test_confirmed_feat_grants_reach_sheet(self):
        picks = [dict(featId=key, choices=choice) for key, choice in (
            ('martial-weapon-proficiency', {'weaponId': 'weapon:longsword'}),
            ('improved-critical', {'weaponId': 'weapon:longsword'}),
            ('skill-focus', {'skillId': 'jump'}), ('toughness', {}), ('toughness', {}),
            ('extra-turning', {}), ('extra-turning', {}), ('rapid-reload', {'weaponId': 'weapon:crossbow-light'}))]
        sheet = self.sheet(feat_choices=picks, skill_ranks={'jump': 0}, turning_pool_ids=['turn-undead'], equipment=[
            dict(instanceId='sword', itemId='weapon:longsword', keen=True),
            dict(instanceId='bow', itemId='weapon:crossbow-light')])
        self.assertEqual(sheet['skillTotals']['jump'], 5)
        self.assertEqual(sheet['featMaxHpBonus'], 6)
        self.assertEqual(sheet['extraTurningUsesByPool'], {'turn-undead': 8})
        self.assertEqual(sheet['attacks'][0]['nonproficiencyPenalty'], 0)
        self.assertEqual(sheet['attacks'][0]['criticalProfile'], {'threatMinimum': 17, 'multiplier': 2})
        self.assertEqual(sheet['attacks'][1]['reload'], {'action': 'free', 'provokes': True})

    def test_grip_and_familiar_spell_read_generated_rules(self):
        from copy import deepcopy
        from tools.equipment_slots import grip_adjustment
        from tools.familiar_spell import familiar_spell_choices
        core = deepcopy(self.core)
        weapon = core['inventory']['itemsById']['weapon:crossbow-heavy']
        self.assertEqual(grip_adjustment(weapon, {'effectiveCategory': 'Ranged Weapon'}, ('primary',)), (True, -4))
        weapon['gripProfile']['oneHandAttackPenalty'] = -3
        self.assertEqual(grip_adjustment(weapon, {'effectiveCategory': 'Ranged Weapon'}, ('primary',)), (True, -3))
        known = {'chain-lightning': 6}
        self.assertTrue(familiar_spell_choices(core, known)['eligible'])
        core['feats']['byId']['familiar-spell']['spellGrant']['maximumKnownSpellLevel'] = 5
        self.assertFalse(familiar_spell_choices(core, known)['eligible'])

    def test_deity_weapon_inherits_focus_only_for_selected_actor(self):
        blade = dict(instanceId='blade', itemId='weapon:longsword', proficient=True)
        item = self.core['inventory']['itemsById']
        self.assertEqual(item['gear:holly']['divineFocus']['kind'], 'nature')
        self.assertEqual(item['gear:holy-symbol-wooden']['divineFocus']['kind'], 'holy-symbol')
        self.assertNotIn('divineFocus', self.sheet(equipment=[blade])['attacks'][0])
        focus = self.sheet(equipment=[blade], holy_weapon_id='weapon:longsword')['attacks'][0]['divineFocus']
        self.assertEqual(focus, {'kind': 'holy-symbol', 'requiresEquipped': True, 'via': 'deity-weapon'})
        self.assertNotIn('divineFocus', item['weapon:longsword'])
