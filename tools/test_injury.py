import json
from pathlib import Path
import unittest

from tools.injury import heal_injury, resolve_damage, stabilize_injury

CORE = json.loads((Path(__file__).resolve().parents[1] / 'dnd-core.json').read_text())


class InjuryTest(unittest.TestCase):
    def test_packet_and_recovery(self):
        state = dict(hp=6, maxHp=20, temporaryHp=3, nonlethal=0)
        hit = resolve_damage(CORE, state, weapon=12, round_id=1, energy={'fire': 9}, energy_resistance={'fire': 6},
                             damage_reduction=[{'amount': 8, 'bypassAnyOf': [['silver', 'magic']]}, {'amount': 4}],
                             bypass_tags=['silver', 'magic'])
        self.assertEqual((hit['weaponPrevented'], hit['temporaryHpAbsorbed']), (4, 3))
        self.assertEqual(hit['energyPrevented'], {'fire': 6})
        self.assertEqual(hit['conditionIds'], ['dying'])
        self.assertEqual(stabilize_injury(CORE, hit['state'], 15)['conditionIds'], ['stable'])
        self.assertEqual(heal_injury(CORE, hit['state'], 1, magical=True)['conditionIds'], ['stable'])
        self.assertEqual(heal_injury(CORE, hit['state'], 2)['conditionIds'], ['disabled'])
        self.assertEqual(heal_injury(CORE, hit['state'], 3)['conditionIds'], [])
        self.assertEqual(state['hp'], 6)

    def test_nonlethal_and_massive_damage(self):
        state = dict(hp=70, maxHp=70, temporaryHp=4, nonlethal=20)
        with self.assertRaisesRegex(ValueError, 'Fortitude'):
            resolve_damage(CORE, state, weapon=50)
        self.assertEqual(resolve_damage(CORE, state, weapon=50,
                                        massive_save_total=14)['conditionIds'], ['dead'])
        result = resolve_damage(CORE, state, weapon=54, nonlethal=True)
        self.assertEqual(result['conditionIds'], ['staggered'])
        self.assertEqual(heal_injury(CORE, result['state'], 1, magical=True)['conditionIds'], [])

    def test_round_defenses_are_shared_then_reset(self):
        state = dict(hp=30, maxHp=30)
        args = dict(weapon=4, energy={'fire': 8}, energy_resistance={'fire': 10}, damage_reduction=[{'amount': 5}])
        first = resolve_damage(CORE, state, round_id=1, **args)
        second = resolve_damage(CORE, first['state'], round_id=1, **args)
        self.assertEqual((first['applied'], second['applied']), (0, 9))
        self.assertEqual(second['energyPrevented']['fire'], 2)
        self.assertEqual(second['weaponPrevented'], 1)
        self.assertEqual(resolve_damage(CORE, second['state'], round_id=2, **args)['applied'], 0)

    def test_stabilization_at_round_end_only_once(self):
        from tools.injury import end_injury_round
        first = end_injury_round(CORE, dict(hp=-1), 1, stabilization_roll=11)
        self.assertEqual(first['state']['hp'], -2)
        self.assertEqual(end_injury_round(CORE, first['state'], 1), first)
        self.assertEqual(end_injury_round(CORE, first['state'], 2, stabilization_roll=10)['conditionIds'], ['stable'])

    def test_protection_from_energy_shares_pool_across_types_and_does_not_spend_resistance_first(self):
        from tools.injury import grant_energy_protection
        state = grant_energy_protection(CORE, dict(hp=30, maxHp=30), 1, 0)
        first = resolve_damage(CORE, state, energy={'fire': 8}, energy_resistance={'fire': 4}, round_id=1, now=1)
        self.assertEqual(first['state']['energyProtection']['remaining'], 4)
        self.assertEqual(first['energyPrevented']['fire'], 0)
        second = resolve_damage(CORE, first['state'], energy={'cold': 8}, now=2)
        self.assertEqual(second['wardPrevented'], {'cold': 4})
        self.assertEqual(second['applied'], 4)
        self.assertNotIn('energyProtection', second['state'])
        for kind in ('acid', 'cold', 'electricity', 'fire', 'sonic'):
            self.assertEqual(resolve_damage(CORE, state, energy={kind: 1}, now=1)['applied'], 0)
