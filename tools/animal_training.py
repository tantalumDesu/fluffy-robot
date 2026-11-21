"""Handle Animal rules and per-animal training state (does not modify stat blocks)."""
import re


def training_rules(lines):
    text = lines('SKILLS.txt')
    start = next(i for i, line in enumerate(text) if line.startswith('Teach an Animal a Trick:'))
    end = next(i for i in range(start, len(text)) if text[i].startswith('Rear a Wild Animal:'))
    tricks, purposes = {}, {}
    for offset in range(start, end):
        if not (match := re.fullmatch(r'([\w ]+) \(DC (\d+)\): (.+)', text[offset])):
            continue
        name, dc, prose = match.groups()
        key = name.lower().replace(' ', '-')
        record = dict(dc=int(dc), source={'file': 'SKILLS.txt', 'line': offset + 1})
        if package := re.search(r'knows the tricks (.+?)\. Training .*? takes (\w+) weeks\.', prose):
            record['tricks'] = re.findall(r'\b(?!and\b)\w+', package[1])
            record['weeks'] = {'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6}[package[2]]
            purposes[key] = record
        else:
            tricks[key] = dict(record, weeks=1, slots=1)
    tricks['track']['requiresScent'] = True
    tricks['attack-all'] = dict(tricks['attack'], slots=2, replaces='attack')
    purposes['combat-riding']['upgradeFromRiding'] = {'weeks': 3, 'replacesLearnedTricks': True}
    return dict(skillId='handle-animal', tricksById=tricks, purposesById=purposes,
                normalTrickSlotsByInt={'1': 3, '2': 6}, hoursPerDay=3, daysPerWeek=7,
                checkAtFraction=0.5, handleDc=10, pushDc=25, injuredDcIncrease=2,
                source={'file': 'SKILLS.txt', 'line': start + 1})


def known_tricks(state):
    result = set(state.get('learnedTrickIds', ())) | set(state.get('bonusTrickIds', ()))
    if 'attack-all' in result:
        result.add('attack')
    return result


def plan_training(rules, creature, state, *, kind, choice_id, handler_ranks, has_scent=False,
                  purpose_eligible=False):
    """Plan training; caller confirms species/physical suitability for a purpose."""
    if handler_ranks <= 0:
        raise ValueError('Training requires ranks in Handle Animal')
    limit = rules['normalTrickSlotsByInt'].get(str(creature['abilityScores']['int']))
    if limit is None:
        raise ValueError('No supported trick capacity for this animal')
    learned = set(state.get('learnedTrickIds', ()))
    purpose = state.get('purposeId')
    if kind == 'trick':
        record = rules['tricksById'][choice_id]
        if choice_id in known_tricks(state):
            raise ValueError('Animal already knows the trick')
        learned.discard(record.get('replaces'))
        learned.add(choice_id)
        tricks_to_check = {choice_id}
    elif kind == 'purpose':
        record = rules['purposesById'][choice_id]
        if not purpose_eligible:
            raise ValueError('Confirm animal is physically suitable for this purpose')
        upgrade = purpose == 'riding' and choice_id == 'combat-riding'
        if purpose and not upgrade:
            raise ValueError('Animal already has a general purpose')
        tricks_to_check = set(record['tricks'])
        if upgrade:
            record = dict(record, **record['upgradeFromRiding'])
            learned = set()
        learned.update(tricks_to_check)
        if 'attack-all' in learned:
            learned.discard('attack')
        purpose = choice_id
    else:
        raise ValueError('Training kind must be trick or purpose')
    if not has_scent and any(rules['tricksById'][trick].get('requiresScent') for trick in tricks_to_check):
        raise ValueError('Track requires scent')
    if sum(rules['tricksById'][trick]['slots'] for trick in learned) > limit:
        raise ValueError('Training would exceed the normal trick limit')
    hours = record['weeks'] * rules['daysPerWeek'] * rules['hoursPerDay']
    return dict(dc=record['dc'], checkAtHours=hours * rules['checkAtFraction'], totalHours=hours,
                workTiming={'unit': 'hour', 'amount': hours, 'hoursPerDay': rules['hoursPerDay'],
                            'checkAtFraction': rules['checkAtFraction']},
                resultingState=dict(state, purposeId=purpose, learnedTrickIds=sorted(learned)))


def training_status(plan, hours_worked, *, check_total=None, interrupted=False):
    """Return state only after the midpoint check and remaining work succeed."""
    if interrupted:
        return {'status': 'failed'}
    if hours_worked < plan['checkAtHours']:
        if check_total is not None:
            raise ValueError('Handle Animal check is not due yet')
        return {'status': 'working'}
    if check_total is None:
        return {'status': 'check-due', 'dc': plan['dc']}
    if check_total < plan['dc']:
        return {'status': 'failed'}
    if hours_worked < plan['totalHours']:
        return {'status': 'working'}
    return {'status': 'complete', 'trainingState': plan['resultingState']}


def work_command(rules, state, *, injured=False):
    """For a physically capable draft animal; separate from weight checks."""
    trained = 'work' in known_tricks(state)
    return dict(action='move' if trained else 'full-round',
                dc=rules['handleDc' if trained else 'pushDc'] + (rules['injuredDcIncrease'] if injured else 0))
