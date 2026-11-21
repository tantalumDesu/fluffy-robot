"""Evaluate pulled vehicle loads against the assigned team's capacity."""
from decimal import Decimal, InvalidOperation


def _nonnegative(value, label):
    if not isinstance(value, (int, float, Decimal)) or isinstance(value, bool):
        raise ValueError(f'{label} must be a known nonnegative number')
    try:
        value = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f'Invalid {label}') from exc
    if not value.is_finite() or value < 0:
        raise ValueError(f'{label} must be a known nonnegative number')
    return value


def evaluate_vehicle_load(inventory, vehicle_item_id, pullers_by_actor_id, *, passenger_weight_lb=0,
                          cargo_weight_lb=0, terrain_multiplier=None):
    """Resolve one vehicle instance; mapping values are pack profile IDs, not item IDs.

    The caller aggregates actual passenger and cargo weights and checks that no
    actor is assigned to two vehicles. Unknown weights/capacities fail closed.
    Results use Decimal pounds, so fractions cannot turn a boundary into overload.
    """
    vehicle = inventory['itemsById'][vehicle_item_id]
    if 'pulledVehicle' not in vehicle:
        raise ValueError(f'{vehicle_item_id} is not a pulled vehicle')
    rule = inventory['pulledVehicleRules']
    factor = _nonnegative(rule['defaultTerrainMultiplier'] if terrain_multiplier is None else terrain_multiplier,
                          'Terrain multiplier')
    if factor > 1:
        raise ValueError('Terrain multiplier cannot exceed 1')
    if not pullers_by_actor_id:
        raise ValueError('Assign at least one animal to pull this vehicle')
    contributions = {}
    for actor_id, profile_id in pullers_by_actor_id.items():
        profile = inventory['packAnimalsById'][profile_id]
        heavy = _nonnegative(profile.get('carryingCapacity', {}).get('heavyLb'), 'Heavy-load capacity')
        contributions[actor_id] = heavy * rule['heavyLoadMultiplier']
    capacity = sum(contributions.values()) * factor
    empty = _nonnegative(vehicle.get('weightLb'), 'Empty vehicle weight')
    passengers = _nonnegative(passenger_weight_lb, 'Passenger weight')
    cargo = _nonnegative(cargo_weight_lb, 'Cargo weight')
    payload = passengers + cargo
    max_payload = max(Decimal(0), capacity - empty)
    gross_limit = capacity
    rated = vehicle['pulledVehicle'].get('maxPayloadLb')
    if rated is not None:
        rated = _nonnegative(rated, 'Rated payload')
        max_payload = min(max_payload, rated)
        gross_limit = min(gross_limit, empty + rated)
    total = empty + payload
    return dict(pullerCapacityLb=contributions, pullingCapacityLb=capacity, totalWeightLb=total,
                maxPayloadLb=max_payload, maxCargoLb=max(Decimal(0), max_payload - passengers),
                remainingCargoLb=max(Decimal(0), gross_limit - total),
                overloadLb=max(Decimal(0), total - gross_limit), canPull=total <= gross_limit)


def validate_vehicle_assignments(pullers_by_vehicle_id):
    """Reject simultaneous assignment of the same actor to multiple vehicles."""
    assigned = {}
    for vehicle_id, pullers in pullers_by_vehicle_id.items():
        for actor_id in pullers:
            if actor_id in assigned:
                raise ValueError(f'Animal {actor_id!r} is assigned to both {assigned[actor_id]!r} and {vehicle_id!r}')
            assigned[actor_id] = vehicle_id
