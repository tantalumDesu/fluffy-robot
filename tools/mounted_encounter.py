"""Confirmed mounted actions using the encounter action budget and existing mount sheet."""
from copy import deepcopy
from math import isfinite

from .game_time import spend_action


def _turn(encounter, rider):
    if (encounter['phase'] not in ('start', 'acting') or
            encounter['order'][encounter['index']] != rider):
        raise ValueError('It is not the rider’s action phase')


def _check(total):
    if type(total) is not int:
        raise ValueError('Supply the resolved check total, including modifiers')
    return total


def _pair(encounter, rider, projection):
    mount = encounter.get('mountedByRiderId', {}).get(rider)
    if mount is None or projection.get('instanceId') != mount:
        raise ValueError('Projection must match the rider’s active mount')
    return mount


def _ready(projection):
    if projection.get('status') != 'ready':
        raise ValueError('Resolve blocked or unconfirmed mount requirements first')


def mount_or_dismount(core, encounter, rider, projection, *, dismount=False,
                      fast=False, ride_total=None, position_confirmed=False):
    """Commit one mount/dismount; the table confirms adjacency or landing space."""
    _turn(encounter, rider)
    if not position_confirmed:
        raise ValueError('Confirm reach to the mount or an available dismount space')
    links = encounter.get('mountedByRiderId', {})
    mount = projection['instanceId']
    if dismount:
        _pair(encounter, rider, projection)
    else:
        _ready(projection)
        if rider in links or rider in links.values() or mount == rider or mount in links or mount in links.values():
            raise ValueError('A rider or mount already has an active mounted assignment')
    action = 'move'
    if fast:
        if projection.get('mountSizeSteps') != 1 or not encounter['actions'].get('move'):
            raise ValueError('Fast mount or dismount requires a mount one size larger and an available move action')
        if _check(ride_total) >= core['mechanics']['mountedCombat']['encounterActions']['fastMountDc']:
            action = 'free'
    result = spend_action(encounter, action)
    links = result.setdefault('mountedByRiderId', {})
    if dismount:
        del links[rider]
    else:
        links[rider] = mount
    return result


def control_mount(encounter, rider, projection, *, ride_total):
    """Resolve the round's combat control check; failure consumes the rest of the turn."""
    _turn(encounter, rider)
    _pair(encounter, rider, projection)
    _ready(projection)
    dc = projection['controlInBattleDc']
    if dc is None:
        raise ValueError('This mount does not require the combat control check')
    prior = encounter.get('mountControlByRiderId', {}).get(rider, {})
    if prior.get('round') == encounter['round']:
        raise ValueError('Combat control has already been resolved this round')
    passed = _check(ride_total) >= dc
    result = spend_action(encounter, 'move')
    if not passed:
        result['actions'].update(standard=0, move=0, blocked=True)
    result.setdefault('mountControlByRiderId', {})[rider] = dict(
        round=result['round'], mountId=projection['instanceId'], passed=passed)
    return result


def _controlled(encounter, rider, projection, in_combat):
    if in_combat and projection['controlInBattleDc'] is not None:
        check = encounter.get('mountControlByRiderId', {}).get(rider, {})
        if (check.get('round') != encounter['round'] or check.get('mountId') != projection['instanceId']
                or not check.get('passed')):
            raise ValueError('Resolve the mount’s combat control check first')


def move_mounted(encounter, rider, projection, *, distance_ft, mode='land', pace='move',
                 in_combat=True, path_confirmed=False, ride_total=None):
    """Commit a confirmed movement sequence on the mount's budget, not the rider's.

    The table confirms path, mount readiness to act, and charge/run legality.
    A double move is declared as one sequence; no map position is inferred.
    """
    _turn(encounter, rider)
    mount = _pair(encounter, rider, projection)
    _ready(projection)
    _controlled(encounter, rider, projection, in_combat)
    if not path_confirmed:
        raise ValueError('Confirm the path and mount’s ability to take this action')
    if encounter['actions'].get('blocked') or rider in encounter['pending']:
        raise ValueError('The rider cannot direct the mount')
    if type(distance_ft) not in (int, float) or not isfinite(distance_ft) or distance_ft <= 0:
        raise ValueError('Supply a positive movement distance')
    if pace not in ('move', 'double-move', 'run', 'charge') or mode not in ('land', 'climb', 'swim', 'fly'):
        raise ValueError('Unknown movement mode or pace')
    if pace in ('run', 'charge') and mode != 'land':
        raise ValueError('Non-land runs or charges are not resolved by this helper')
    climbing = projection.get('mountedClimbing') or {}
    flight = projection.get('flight') or {}
    speed = {'land': projection.get('landSpeedFt'), 'climb': climbing.get('climbSpeedFt'),
             'swim': projection.get('swimSpeedFt'), 'fly': flight.get('speedFt')}[mode]
    if not speed or mode == 'fly' and projection.get('flightBlocked'):
        raise ValueError('This movement mode is unavailable')
    if encounter['round'] == 0 and pace != 'move':
        raise ValueError('Only a single mounted move is supported in a surprise round')
    actions = 1 if pace == 'move' else 2
    usage = encounter.get('mountMovementByInstanceId', {}).get(mount, {})
    if (mount in encounter.get('actedActorIdsThisRound', ()) and
            (usage.get('round') != encounter['round'] or not usage)):
        raise ValueError('The mount already had its own turn this round')
    used = usage.get('actions', 0) if usage.get('round') == encounter['round'] else 0
    if used + actions > (1 if encounter['round'] == 0 else 2):
        raise ValueError('The mount has spent its movement action budget')
    multiplier = {'move': 1, 'double-move': 2, 'charge': 2, 'run': projection['runMultiplier']}[pace]
    if distance_ft > speed * multiplier or pace == 'charge' and distance_ft < 10:
        raise ValueError('Distance is outside the selected mounted movement allowance')
    stays = mode != 'climb' or _check(ride_total) >= climbing['stayMountedRideDc']
    result = deepcopy(encounter)
    total = (usage.get('distanceFt', 0) if used else 0) + distance_ft if stays else None
    result.setdefault('mountMovementByInstanceId', {})[mount] = dict(
        round=result['round'], riderId=rider, actions=used + actions, distanceFt=total,
        pace='double-move' if used else pace, mode=mode, lostSeat=not stays)
    if not stays:
        del result['mountedByRiderId'][rider]
        result['mountMovementByInstanceId'][mount]['needsReview'] = 'Confirm fall position, distance travelled, and damage'
    return result


def mounted_attack_context(core, encounter, rider, projection, *, weapon_id=None, ranged=False,
                           charge_endpoint_confirmed=False, smaller_target_on_foot=False):
    """Return supported mounted attack modifiers; does not make or spend an attack."""
    _turn(encounter, rider)
    mount = _pair(encounter, rider, projection)
    _ready(projection)
    _controlled(encounter, rider, projection, True)
    move = encounter.get('mountMovementByInstanceId', {}).get(mount, {})
    if move.get('round') != encounter['round'] or move.get('riderId') != rider:
        move = {}
    rules = core['mechanics']['mountedCombat']
    attack = rules['encounterActions']
    charged = move.get('pace') == 'charge'
    endpoint = charged and charge_endpoint_confirmed and not ranged
    pace = move.get('pace')
    return dict(mountId=mount, fullAttackAllowed=ranged or (move.get('distanceFt') or 0) <= 5,
                meleeAttackBonus=0 if ranged else (attack['higherGroundBonus'] if smaller_target_on_foot else 0)
                + (attack['chargeAttackBonus'] if endpoint else 0),
                armorClassAdjustment=attack['chargeArmorAdjustment'] if charged else 0,
                rangedAttackPenalty=attack['rangedPenaltyByPace'].get(pace, 0) if ranged else 0,
                rangedAttackAtHalfMovement=ranged and pace in attack['rangedPenaltyByPace'],
                lanceDamageMultiplier=rules['lanceChargeMultiplier'] if endpoint and weapon_id == 'weapon:lance' else 1)


def resolve_mount_fall(core, encounter, rider, projection, *, ride_total):
    """Dismount after a confirmed fall, reporting rather than rolling/applying damage."""
    _pair(encounter, rider, projection)
    dc = core['mechanics']['mountedCombat']['encounterActions']['softFallDc']
    damage = None if _check(ride_total) >= dc else '1d6'
    result = deepcopy(encounter)
    del result['mountedByRiderId'][rider]
    return result, dict(fallDamageDice=damage)


def spend_mounted_attack(core, encounter, rider, projection, *, full_attack=False,
                         mount_attacking=False, fight_ride_total=None, **attack_facts):
    """Spend the rider's attack action and return modifiers for external hit resolution."""
    context = mounted_attack_context(core, encounter, rider, projection, **attack_facts)
    if full_attack and not context['fullAttackAllowed']:
        raise ValueError('The mount moved too far for a melee full attack')
    if mount_attacking:
        dc = projection['fightAlongsideMountRideDc']
        if dc is None or _check(fight_ride_total) < dc:
            raise ValueError('Cannot attack alongside the mount without a successful Ride check')
    result = spend_action(encounter, 'full-round' if full_attack else 'standard')
    return result, context
