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
                normalTrickSlotsByInt={'1': 3, '2': 6}, nonAnimalTrainingDcIncrease=5, hoursPerDay=3, daysPerWeek=7,
                checkAtFraction=0.5, handleDc=10, pushDc=25, injuredDcIncrease=2,
                source={'file': 'SKILLS.txt', 'line': start + 1})


def known_tricks(state):
    result = set(state.get('learnedTrickIds', ())) | set(state.get('bonusTrickIds', ()))
    if 'attack-all' in result:
        result.add('attack')
    return result


class TrainingIneligible(ValueError):
    def __init__(self, code, message, status='blocked'):
        super().__init__(message)
        self.code = code
        self.status = status


def _listed_scent(creature):
    text = creature.get('statBlockText') or creature.get('raw', '')
    return True if re.search(r'^\s*Scent\s*$', text, re.I | re.M) else None


def training_choices(rules, creature, state, *, handler_ranks, has_scent=None,
                     purpose_suitability=None, friendly_confirmed=None):
    """List training choices using the same prerequisites as the plan builder.

    Suitability is keyed by purpose ID. True/False confirms or rules out a
    purpose; a missing entry leaves physical suitability for adjudication.
    """
    suitability = purpose_suitability or {}
    known = known_tricks(state)
    result = {'tricksById': {}, 'purposesById': {}}
    for kind, key in (('trick', 'tricksById'), ('purpose', 'purposesById')):
        for choice_id, record in rules[key].items():
            entry = dict(source=record['source'])
            if (kind == 'trick' and choice_id in known or
                    kind == 'purpose' and choice_id == state.get('purposeId')):
                entry.update(status='known')
            else:
                try:
                    plan = plan_training(rules, creature, state, kind=kind, choice_id=choice_id,
                                         handler_ranks=handler_ranks, has_scent=has_scent,
                                         purpose_eligible=suitability.get(choice_id),
                                         friendly_confirmed=friendly_confirmed)
                except TrainingIneligible as exc:
                    entry.update(status=exc.status, reasonId=exc.code, reason=str(exc))
                else:
                    after = known_tricks(plan['resultingState'])
                    entry.update(status='available', dc=plan['dc'], totalHours=plan['totalHours'],
                                 checkAtHours=plan['checkAtHours'],
                                 gainsTrickIds=sorted(after - known), losesTrickIds=sorted(known - after))
            result[key][choice_id] = entry
    return result


def plan_training(rules, creature, state, *, kind, choice_id, handler_ranks, has_scent=None,
                  purpose_eligible=None, friendly_confirmed=None):
    """Plan training; caller confirms species/physical suitability for a purpose."""
    if handler_ranks <= 0:
        raise TrainingIneligible('handler-ranks', 'Training requires ranks in Handle Animal')
    if kind == 'purpose' and choice_id == 'combat-riding' and (special := creature.get('combatRidingTraining')):
        if state.get('purposeId') == 'combat-riding':
            raise TrainingIneligible('already-known', 'Creature is already trained for combat riding')
        if state.get('purposeId') not in (None, 'riding'):
            raise TrainingIneligible('existing-purpose', 'Creature already has a general purpose')
        if special['requiresFriendly'] and friendly_confirmed is not True:
            raise TrainingIneligible('friendliness', 'Confirm the mount is friendly before starting training',
                                     'blocked' if friendly_confirmed is False else 'needs-review')
        if purpose_eligible is not True:
            raise TrainingIneligible('purpose-suitability', 'Confirm the mount is physically suitable',
                                     'blocked' if purpose_eligible is False else 'needs-review')
        hours = special['weeks'] * rules['daysPerWeek'] * rules['hoursPerDay']
        return dict(dc=special['dc'], checkAtHours=hours * rules['checkAtFraction'], totalHours=hours,
                    workTiming={'unit': 'hour', 'amount': hours, 'hoursPerDay': rules['hoursPerDay'],
                                'checkAtFraction': rules['checkAtFraction']},
                    resultingState=dict(state, purposeId='combat-riding'))
    limit = rules['normalTrickSlotsByInt'].get(str(creature['abilityScores']['int']))
    if limit is None:
        raise TrainingIneligible('unsupported-intelligence', 'No supported trick capacity for this creature')
    learned = set(state.get('learnedTrickIds', ()))
    purpose = state.get('purposeId')
    if kind == 'trick':
        record = rules['tricksById'][choice_id]
        if choice_id in known_tricks(state):
            raise TrainingIneligible('already-known', 'Creature already knows the trick')
        learned.discard(record.get('replaces'))
        learned.add(choice_id)
        tricks_to_check = {choice_id}
    elif kind == 'purpose':
        record = rules['purposesById'][choice_id]
        upgrade = purpose == 'riding' and choice_id == 'combat-riding'
        if purpose and not upgrade:
            raise TrainingIneligible('existing-purpose', 'Creature already has a general purpose')
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
    if any(rules['tricksById'][trick].get('requiresScent') for trick in tricks_to_check):
        scent = _listed_scent(creature) if has_scent is None else has_scent
        if scent is not True:
            raise TrainingIneligible('requires-scent', 'Track requires scent',
                                     'blocked' if scent is False else 'needs-review')
    if sum(rules['tricksById'][trick]['slots'] for trick in learned) > limit:
        raise TrainingIneligible('trick-capacity', 'Training would exceed the normal trick limit')
    if kind == 'purpose' and purpose_eligible is not True:
        raise TrainingIneligible('purpose-suitability', 'Confirm creature is physically suitable for this purpose',
                                 'blocked' if purpose_eligible is False else 'needs-review')
    classification = creature.get('classification') or ''
    creature_type = creature.get('creatureType')
    non_animal = (creature_type.lower() != 'animal' if creature_type else
                  bool(classification and not re.match(r'^\w+ Animal\b', classification, re.I)))
    dc = record['dc'] + (rules['nonAnimalTrainingDcIncrease'] if non_animal else 0)
    hours = record['weeks'] * rules['daysPerWeek'] * rules['hoursPerDay']
    return dict(dc=dc, checkAtHours=hours * rules['checkAtFraction'], totalHours=hours,
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
