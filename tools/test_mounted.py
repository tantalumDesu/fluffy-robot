import json
import unittest

from tools.derived_stats import derive_sheet
from tools.level_history import replay_level_history
from tools.mounted import acquisition_training, project_mount
from tools.organize_core import PATH


class MountedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = json.loads(PATH.read_bytes())
        cls.horse = cls.core['companions']['creaturesById']['beasts-of-burden:horse-light']

    def test_all_barding_prices_fit_and_light_load_saddlebags(self):
        core = self.core
        mounted = core['mechanics']['mountedCombat']
        self.assertEqual(len(mounted['bardingById']), 24)
        plate = mounted['bardingById']['barding:large:full-plate']
        self.assertEqual((plate['priceCp'], plate['weightLb']), (600000, 100))
        def project(**changes):
            args = dict(rider_size_id='medium', rider_weight_lb=100, rider_inventory_lb=20,
                        saddle={'itemId': 'gear:saddle-military', 'sizeId': 'large'},
                        barding_id=plate['id'], saddlebags_payload_lb=150, charging=True, weapon_id='weapon:lance')
            return project_mount(core, self.horse, **(args | changes))
        sheet = project()
        self.assertEqual((sheet['mountedLoadLb'], sheet['landSpeedFt'], sheet['runMultiplier']), (408, 40, 3))
        self.assertEqual((sheet['stayMountedRideCircumstance'], sheet['unconsciousStayPercent']), (2, 75))
        self.assertTrue(sheet['flightBlocked'])
        self.assertEqual(sheet['lanceChargeMultiplier'], 2)
        self.assertEqual(sheet['controlInBattleDc'], 20)
        self.assertEqual(project(saddlebags_payload_lb=151)['status'], 'blocked')
        self.assertEqual(project(other_cargo_lb=1)['status'], 'blocked')
        self.assertEqual(project(rider_size_id='large')['status'], 'blocked')
        bare = project(saddle=None, suitability='ill-suited')
        self.assertEqual(bare['ridePenalties'], {'bareback': -5, 'illSuited': -5})
        self.assertEqual(bare['stayMountedRideCircumstance'], 0)

    def test_riding_uses_one_ranger_companion_sheet(self):
        core = self.core
        history = replay_level_history(core, ['ranger'] * 6)
        link = dict(instanceId='steed', definitionId='animal-companions:horse-light', acquiredByClassId='ranger',
                    bonusHitDieRolls=[4, 5], training={'purposeId': 'combat-riding'})
        sheet = derive_sheet(core, history, 'human', dict(str=14, dex=12, con=12, int=10, wis=14, cha=10),
                             companion_links=[link], skill_ranks={'ride': 2},
                             mount_link=dict(instanceId='steed', rider_weight_lb=130,
                                             saddle={'itemId': 'gear:saddle-riding', 'sizeId': 'large'}))
        self.assertEqual(len(sheet['companions']), 1)
        self.assertEqual(sheet['companions'][0]['effectiveMasterLevel'], 3)
        self.assertEqual(sheet['companions'][0]['bonusHitDice'], 2)
        self.assertEqual(sheet['mounted']['instanceId'], 'steed')
        self.assertIsNone(sheet['mounted']['controlInBattleDc'])
        self.assertEqual(sheet['mounted']['ridePenalty'], 0)

    def test_acquisition_seeds_training_not_species(self):
        items = self.core['inventory']['itemsById']
        self.assertEqual(items['gear:warpony']['trainingPurposeId'], 'combat-riding')
        self.assertEqual(acquisition_training(self.core, self.horse)['purposeId'], 'riding')
        creatures = self.core['companions']['creaturesById']
        self.assertIsNone(acquisition_training(self.core, creatures['animal-companions:horse-light'])['purposeId'])
        self.assertEqual(acquisition_training(self.core, creatures['animal-companions:dog-riding'])['purposeId'], 'combat-riding')

    def test_default_saddle_size_tracks_current_creature_size(self):
        args = dict(creature_sheet={'sizeId': 'huge'}, rider_size_id='medium', rider_weight_lb=120)
        large = project_mount(self.core, self.horse, saddle={'itemId': 'gear:saddle-riding', 'sizeId': 'large'}, **args)
        huge = project_mount(self.core, self.horse, saddle={'itemId': 'gear:saddle-riding', 'sizeId': 'huge'}, **args)
        self.assertEqual((large['ridePenalties']['bareback'], huge['ridePenalties']['bareback']), (-5, 0))

    def test_mounted_and_vehicle_load_read_same_creature_limits(self):
        from copy import deepcopy
        from tools.vehicle_load import evaluate_vehicle_load

        core = deepcopy(self.core)
        horse = core['companions']['creaturesById'][self.horse['id']]
        horse['carryingCapacity']['heavyLb'] = 451
        mount = project_mount(core, horse, rider_size_id='medium', rider_weight_lb=451)
        vehicle = evaluate_vehicle_load(core, 'gear:wagon', {'horse': 'horse-light'})
        self.assertEqual(mount['capacityLb']['heavyLb'], 451)
        self.assertEqual(vehicle['pullerCapacityLb']['horse'], 2255)

    def test_war_mount_acquisition_separates_purchase_from_special_mount(self):
        from tools.companion_sheet import project_creature

        core = self.core
        history = replay_level_history(core, ['paladin'] * 8)
        link = dict(instanceId='mount', definitionId='war-mounts:warhorse-heavy')
        ordinary = project_creature(core, history, link)
        self.assertEqual((ordinary['role'], ordinary['maxHp'], ordinary['landSpeedFt']), ('ordinary-mount', 30, 50))
        self.assertEqual(ordinary['training']['purposeId'], 'combat-riding')
        projected = project_creature(core, history, dict(link, acquiredByClassId='paladin', bonusHitDieRolls=[4] * 4))
        self.assertEqual((projected['role'], projected['actualHitDice'], projected['maxHp']), ('special-mount', 8, 58))
        self.assertEqual((projected['abilityScores']['str'], projected['landSpeedFt'], projected['armorClass']['normal']),
                         (20, 60, 20))
        self.assertEqual(projected['naturalWeapons'][0]['damageText'], '1d6+5')
        mounted = project_mount(core, core['companions']['creaturesById'][link['definitionId']],
                                creature_sheet=projected, rider_size_id='medium', rider_weight_lb=140)
        self.assertIsNone(mounted['controlInBattleDc'])
        self.assertEqual(mounted['fightAlongsideMountRideDc'], 10)

    def test_unusual_mounts_preserve_flight_training_and_unknowns(self):
        from tools.animal_training import plan_training, training_status
        from tools.companion_sheet import project_creature

        core = self.core
        catalogue = core['companions']['creaturesById']
        griffon = catalogue['unusual-mounts:griffon']
        self.assertEqual(griffon['flight'], {'speedFt': 50, 'maneuverability': 'average'})
        self.assertEqual(griffon['carryingCapacity']['lightLb'], 300)
        self.assertNotIn('dragLb', griffon['carryingCapacity'])
        self.assertNotIn('flight', catalogue['unusual-mounts:giant-wasp'])
        self.assertIsNone(catalogue['unusual-mounts:giant-wasp']['abilityScores']['int'])
        self.assertEqual(catalogue['unusual-mounts:eagle-giant']['mountProfile']['saddleFamily'], 'exotic')
        args = dict(rider_size_id='medium', rider_weight_lb=140)
        self.assertEqual(project_mount(core, griffon, **args)['status'], 'blocked')
        saddle = dict(itemId='gear:saddle-exotic-riding', sizeId='large')
        self.assertEqual(project_mount(core, griffon, saddle=saddle, **args)['flightStatus'], 'confirm-load-and-flight')
        self.assertTrue(project_mount(core, griffon, saddle=saddle, barding_id='barding:large:hide', **args)['flightBlocked'])
        training = core['skills']['animalTraining']
        state = acquisition_training(core, griffon)
        params = dict(kind='purpose', choice_id='combat-riding', handler_ranks=1, purpose_eligible=True)
        with self.assertRaisesRegex(ValueError, 'friendly'):
            plan_training(training, griffon, state, **params)
        plan = plan_training(training, griffon, state, friendly_confirmed=True, **params)
        self.assertEqual((plan['dc'], plan['totalHours']), (25, 126))
        trained = training_status(plan, 126, check_total=25)['trainingState']
        self.assertIsNone(project_mount(core, griffon, training=trained, saddle=saddle, **args)['controlInBattleDc'])
        sheet = project_creature(core, {}, dict(instanceId='griffon', definitionId=griffon['id'], confirmedPounce=True))
        self.assertEqual((sheet['naturalWeapons'][-1]['count'], sheet['naturalWeapons'][-1]['damageDice']), (2, '1d6'))

    def test_large_spider_is_an_unconfirmed_mount_candidate(self):
        from tools.companion_sheet import project_creature

        key = 'unusual-mounts:monstrous-spider-large'
        base = self.core['companions']['creaturesById'][key]
        sheet = project_creature(self.core, {}, dict(instanceId='spider', definitionId=key))
        self.assertEqual((sheet['sizeId'], sheet['landSpeedFt'], sheet['maxHp']), ('large', 30, 22))
        self.assertEqual(sheet['naturalWeapons'][0]['naturalAttackId'], 'bite')
        self.assertEqual(sheet['mountProfile']['suitability'], 'needs-review')
        self.assertEqual(sheet['mountProfile']['saddleFamily'], 'exotic')
        self.assertIsNone(sheet['training']['purposeId'])
        self.assertIsNone(sheet['carryingCapacity'])
        self.assertEqual(sheet['climbSpeedFt'], 20)
        projected = project_mount(self.core, base, creature_sheet=sheet, rider_size_id='medium', rider_weight_lb=140)
        self.assertEqual(projected['mountedClimbing']['stayMountedRideDc'], 5)
        self.assertEqual(projected['mountedClimbing']['climbSpeedFt'], 20)
        self.assertEqual(projected['status'], 'blocked')
        wrong = project_mount(self.core, base, rider_size_id='medium', rider_weight_lb=140,
                              saddle=dict(itemId='gear:saddle-riding', sizeId='large'),
                              saddle_fit=dict(saddleFamily='standard', saddleSizeId='large'))
        self.assertEqual(wrong['status'], 'blocked')
        fitted = project_mount(self.core, base, rider_size_id='medium', rider_weight_lb=140,
                               saddle=dict(itemId='gear:saddle-exotic-riding', sizeId='large'))
        self.assertEqual(fitted['status'], 'needs-review')

    def test_companion_catalogue_mounted_climbing(self):
        catalogue = self.core['companions']['creaturesById']
        for creature, speed in (('ape-dire', 15), ('snake-giant-constrictor', 20), ('weasel-dire', None)):
            with self.subTest(creature=creature):
                base = catalogue['alternative-animal-companions:' + creature]
                mounted = project_mount(self.core, base, rider_size_id='small', rider_weight_lb=40)
                if speed is None:
                    self.assertIsNone(mounted['mountedClimbing'])
                else:
                    self.assertEqual(mounted['mountedClimbing']['climbSpeedFt'], speed)
                    self.assertEqual(mounted['mountedClimbing']['stayMountedRideDc'], 5)
        self.assertEqual(catalogue['alternative-animal-companions:snake-giant-constrictor']['swimSpeedFt'], 20)

    def test_existing_mounts_use_base_sheets_without_class_packages(self):
        from tools.companion_sheet import project_creature

        core = self.core
        for key in ('worg', 'howler', 'hippogriff', 'alternative-animal-companions:ape-dire'):
            with self.subTest(key=key):
                sheet = project_creature(core, {}, dict(instanceId='mount', definitionId=key, acquisition='ordinary'))
                self.assertEqual(sheet['role'], 'ordinary-mount')
                self.assertGreater(sheet['maxHp'], 0)
                self.assertNotIn('effectiveMasterLevel', sheet)
        options = core['companions']['improvedFamiliarOptionsById']
        self.assertEqual(options['hippogriff']['combatRidingTraining']['dc'], 25)
        self.assertFalse(options['hippogriff']['combatRidingTraining']['requiresFriendly'])
        self.assertTrue(options['howler']['combatRidingTraining']['requiresFriendly'])

    def test_paladin_alternate_mounts_use_existing_definitions(self):
        from tools.companion_sheet import project_creature

        core = self.core
        history = replay_level_history(core, ['paladin'] * 8)
        for key, speed in (('animal-companions:dog-riding', 'landSpeedFt'),
                           ('alternative-animal-companions:shark-large', 'swimSpeedFt')):
            link = dict(instanceId='mount', definitionId=key, acquiredByClassId='paladin', bonusHitDieRolls=[4] * 4)
            with self.assertRaisesRegex(ValueError, 'nonstandard'):
                project_creature(core, history, link)
            special = project_creature(core, history, dict(link, dmConfirmedSpecialMount=True))
            ordinary = project_creature(core, {}, dict(instanceId='mount', definitionId=key, acquisition='ordinary'))
            self.assertEqual(special['training']['purposeId'], 'combat-riding')
            if key.endswith('shark-large'):
                self.assertIsNone(ordinary['training']['purposeId'])
                trained = project_creature(core, history, dict(link, dmConfirmedSpecialMount=True,
                    training=dict(purposeId=None, learnedTrickIds=['attack-all'], bonusTrickIds=['guard'])))
                self.assertEqual(trained['training']['purposeId'], 'combat-riding')
                self.assertIn('attack-all', trained['training']['learnedTrickIds'])
                self.assertNotIn('attack', trained['training']['learnedTrickIds'])
                self.assertEqual(trained['training']['bonusTrickIds'], ['guard'])
            self.assertEqual(special[speed], ordinary[speed] + 10)

    def test_draft_job_reuses_linked_creature(self):
        core = self.core
        history = replay_level_history(core, ['fighter'])
        vehicle = next(key for key, item in core['inventory']['itemsById'].items() if item.get('pulledVehicle'))
        kwargs = dict(companion_links=[dict(instanceId='horse', definitionId='beasts-of-burden:horse-light')],
                      draft_links=[dict(instanceId='cart', vehicleItemId=vehicle, pullerInstanceIds=['horse'])])
        scores = dict(str=14, dex=12, con=12, int=10, wis=14, cha=10)
        sheet = derive_sheet(core, history, 'human', scores, **kwargs)
        self.assertEqual(len(sheet['companions']), 1)
        self.assertIn('horse', sheet['draftByInstanceId']['cart']['workCommandsByInstanceId'])
        with self.assertRaisesRegex(ValueError, 'Simultaneous'):
            derive_sheet(core, history, 'human', scores, **kwargs,
                         mount_link=dict(instanceId='horse', rider_weight_lb=140))
