import json
import unittest

from tools.game_time import end_turn, new_encounter, start_next_turn
from tools.mounted import project_mount
from tools.mounted_encounter import (control_mount, mount_or_dismount, mounted_attack_context,
                                     move_mounted, resolve_mount_fall, spend_mounted_attack)
from tools.organize_core import PATH


class MountedEncounterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = json.loads(PATH.read_bytes())

    def projection(self, definition, **kwargs):
        base = self.core['companions']['creaturesById'][definition]
        return dict(instanceId='mount', **project_mount(self.core, base, rider_size_id='medium',
                                                         rider_weight_lb=100, **kwargs))

    def mount(self, projection, **kwargs):
        encounter, _ = start_next_turn(new_encounter(['rider', 'mount', 'enemy']))
        return mount_or_dismount(self.core, encounter, 'rider', projection, position_confirmed=True, **kwargs)

    def test_fast_mount_charge_and_lance_require_active_pair(self):
        mount = self.projection('war-mounts:warhorse-heavy')
        state = self.mount(mount, fast=True, ride_total=20)
        self.assertEqual(state['mountedByRiderId'], {'rider': 'mount'})
        self.assertEqual(state['actions']['move'], 1)
        self.assertEqual(self.mount(mount, fast=True, ride_total=19)['actions']['move'], 0)
        state = move_mounted(state, 'rider', mount, distance_ft=65, pace='charge', path_confirmed=True)
        self.assertEqual(state['actions']['move'], 1)
        with self.assertRaisesRegex(ValueError, 'budget'):
            move_mounted(state, 'rider', mount, distance_ft=5, path_confirmed=True)
        with self.assertRaisesRegex(ValueError, 'full attack'):
            spend_mounted_attack(self.core, state, 'rider', mount, full_attack=True)
        attacked, context = spend_mounted_attack(self.core, state, 'rider', mount,
                                                   weapon_id='weapon:lance', charge_endpoint_confirmed=True)
        self.assertEqual((context['lanceDamageMultiplier'], context['meleeAttackBonus'],
                          context['armorClassAdjustment']), (2, 2, -2))
        self.assertEqual(attacked['actions']['standard'], 0)
        next_turn, _ = start_next_turn(end_turn(attacked)[0])
        self.assertEqual(next_turn['order'][next_turn['index']], 'enemy')
        released, fall = resolve_mount_fall(self.core, state, 'rider', mount, ride_total=14)
        self.assertEqual(fall['fallDamageDice'], '1d6')
        with self.assertRaisesRegex(ValueError, 'active mount'):
            mounted_attack_context(self.core, released, 'rider', mount)

    def test_combat_control_and_normal_dismount(self):
        mount = self.projection('beasts-of-burden:horse-light')
        state = self.mount(mount, fast=True, ride_total=20)
        with self.assertRaisesRegex(ValueError, 'control'):
            move_mounted(state, 'rider', mount, distance_ft=5, path_confirmed=True)
        failed = control_mount(state, 'rider', mount, ride_total=19)
        self.assertTrue(failed['actions']['blocked'])
        self.assertEqual((failed['actions']['move'], failed['actions']['standard']), (0, 0))
        controlled = control_mount(state, 'rider', mount, ride_total=20)
        moved = move_mounted(controlled, 'rider', mount, distance_ft=60, pace='double-move', path_confirmed=True)
        context = mounted_attack_context(self.core, moved, 'rider', mount, ranged=True)
        self.assertEqual(context['rangedAttackPenalty'], -4)
        self.assertTrue(context['rangedAttackAtHalfMovement'])
        released = mount_or_dismount(self.core, state, 'rider', mount, dismount=True, position_confirmed=True)
        self.assertEqual(released['mountedByRiderId'], {})
        self.assertEqual(released['actions']['move'], 0)

    def test_climb_failed_ride_removes_rider_but_does_not_invent_damage(self):
        mount = self.projection('unusual-mounts:monstrous-spider-large', suitability='suitable',
                                saddle=dict(itemId='gear:saddle-exotic-riding', sizeId='large'),
                                training=dict(purposeId='riding'), locomotion='quadruped')
        state = self.mount(mount)
        moved = move_mounted(state, 'rider', mount, mode='climb', distance_ft=20, in_combat=False,
                             ride_total=5, path_confirmed=True)
        self.assertEqual(moved['mountedByRiderId'], {'rider': 'mount'})
        fallen = move_mounted(state, 'rider', mount, mode='climb', distance_ft=20, in_combat=False,
                              ride_total=4, path_confirmed=True)
        self.assertEqual(fallen['mountedByRiderId'], {})
        self.assertTrue(fallen['mountMovementByInstanceId']['mount']['lostSeat'])
        self.assertIsNone(fallen['mountMovementByInstanceId']['mount']['distanceFt'])
