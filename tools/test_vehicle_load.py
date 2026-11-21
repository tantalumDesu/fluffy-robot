import json
import unittest
from copy import deepcopy
from decimal import Decimal

from tools.organize_core import PATH
from tools.vehicle_load import evaluate_vehicle_load, validate_vehicle_assignments


class VehicleLoadTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = json.loads(PATH.read_bytes())['inventory']

    def test_mule_wagon_payload(self):
        result = evaluate_vehicle_load(self.inventory, 'gear:wagon', {'mule-1': 'mule'},
                                       passenger_weight_lb=350, cargo_weight_lb=2700)
        self.assertEqual(result['pullingCapacityLb'], 3450)
        self.assertEqual(result['totalWeightLb'], 3450)
        self.assertEqual(result['maxCargoLb'], 2700)
        self.assertEqual(result['remainingCargoLb'], 0)
        self.assertTrue(result['canPull'])

    def test_team_and_terrain(self):
        result = evaluate_vehicle_load(self.inventory, 'gear:wagon', {'mule-1': 'mule', 'mule-2': 'mule'},
                                       passenger_weight_lb=350, cargo_weight_lb=3000, terrain_multiplier=0.5)
        self.assertEqual(result['pullingCapacityLb'], 3450)
        self.assertEqual(result['overloadLb'], 300)
        self.assertFalse(result['canPull'])

    def test_rated_payload_and_decimal_boundary(self):
        inventory = deepcopy(self.inventory)
        inventory['itemsById']['gear:wagon']['pulledVehicle']['maxPayloadLb'] = 0.3
        args = inventory, 'gear:wagon', {'ox-1': 'ox'}
        self.assertTrue(evaluate_vehicle_load(*args, passenger_weight_lb=0.1, cargo_weight_lb=0.2)['canPull'])
        overloaded = evaluate_vehicle_load(*args, passenger_weight_lb=0.4)
        self.assertEqual(overloaded['overloadLb'], Decimal('0.1'))

    def test_unknown_and_invalid_inputs(self):
        for vehicle, team, kwargs in [
            ('gear:wagon', {}, {}), ('gear:rowboat', {'ox-1': 'ox'}, {}),
            ('gear:wagon', {'ox-1': 'ox'}, {'cargo_weight_lb': None}),
            ('gear:wagon', {'ox-1': 'ox'}, {'terrain_multiplier': 1.1}),
        ]:
            with self.subTest(vehicle=vehicle, team=team, kwargs=kwargs), self.assertRaises(ValueError):
                evaluate_vehicle_load(self.inventory, vehicle, team, **kwargs)
        with self.assertRaises(ValueError):
            validate_vehicle_assignments({'wagon-1': {'ox-1': 'ox'}, 'wagon-2': {'ox-1': 'ox'}})
        validate_vehicle_assignments({'wagon-1': {'ox-1': 'ox'}, 'wagon-2': {'ox-2': 'ox'}})
