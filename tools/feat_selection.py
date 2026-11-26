"""Extract feat requirements and validate selections against a level-time snapshot."""
import re


CHOICES = {
    **dict.fromkeys(('exotic-weapon-proficiency', 'martial-weapon-proficiency', 'greater-weapon-focus',
                     'greater-weapon-specialization', 'improved-critical', 'rapid-reload',
                     'weapon-focus', 'weapon-specialization', 'overwhelming-critical'), 'weaponId'),
    'improved-natural-attack': 'naturalAttackId', 'skill-focus': 'skillId',
    'spell-focus': 'schoolId', 'greater-spell-focus': 'schoolId', 'familiar-spell': 'spellId',
}
# These choices have constraints beyond simply supplying an ID.
CHOICE_REVIEW = {'exotic-weapon-proficiency', 'martial-weapon-proficiency', 'improved-critical',
                 'rapid-reload', 'improved-natural-attack', 'overwhelming-critical', 'familiar-spell'}


def _field(text, label):
    match = re.search(rf'^{label}\s*:\s*(.*?)(?=^[A-Z][\w ]*\s*:|\Z)', text, re.M | re.S)
    return match[1].strip() if match else ''


def _clause(text, feat_names):
    normalized = text.casefold()
    for pattern, kind in (
        (r'(str|dex|con|int|wis|cha) (\d+)', 'ability'),
        (r'(base attack bonus) \+(\d+)', 'baseAttackBonus'),
        (r'(caster|character|fighter|wizard) level (\d+)(?:st|nd|rd|th)?', 'level'),
        (r'(ride|spellcraft|intimidate|perform \(any one\)) (\d+) ranks?', 'skillRanks'),
        (r'(sneak attack) \+(\d+)d6', 'sneakAttackDice'),
        (r'(rage) (\d+)/day', 'rageUsesPerDay'),
    ):
        if match := re.fullmatch(pattern, normalized):
            return dict(kind=kind, key=match[1].replace(' (any one)', ''), minimum=int(match[2]))
    if normalized == 'familiar':
        return dict(kind='hasFamiliar')
    if normalized in ('proficiency with selected weapon', 'proficient with weapon',
                      'weapon proficiency (crossbow type chosen)'):
        return dict(kind='weaponProficiency', choiceKey='weaponId')
    for suffix in (' with selected weapon', ' (chosen weapon)'):
        if normalized.endswith(suffix) and normalized[:-len(suffix)] in feat_names:
            return dict(kind='feat', featId=feat_names[normalized[:-len(suffix)]], choiceKey='weaponId')
    if normalized == 'spell focus (conjuration)':
        return dict(kind='feat', featId='spell-focus', choiceKey='schoolId', choiceValue='conjuration')
    if normalized in feat_names:
        return dict(kind='feat', featId=feat_names[normalized])
    known_features = {'ability to turn or rebuke creatures': 'turn-or-rebuke-creatures',
                      'ability to turn or rebuke undead': 'turn-or-rebuke-undead',
                      'wild shape ability': 'wild-shape', 'bardic music class feature': 'bardic-music',
                      'smite ability (from class feature or domain granted power)': 'smite',
                      'ability to wild shape into an elemental': 'elemental-wild-shape',
                      'natural weapon': 'natural-weapon'}
    if normalized in known_features:
        return dict(kind='feature', key=known_features[normalized])
    if normalized == 'five or more favored enemies':
        return dict(kind='favoredEnemyCount', minimum=5)
    if normalized == 'four metamagic feats':
        return dict(kind='metamagicFeatCount', minimum=4)
    return dict(kind='manual', text=text)


def encode_feats(feats, maximum_casting_rows):
    casting_options = [dict(classId=class_id, tradition=tradition, ability=ability,
                            minimumSpellcastingLevel=int(level), minimumAbilityScore=int(score),
                            source={'file': 'EPIC FEATS.txt', 'line': line})
                       for line, (class_id, tradition, ability, level, score) in maximum_casting_rows]
    names = {record['name'].casefold(): key for key, record in feats.items()}
    for key, record in feats.items():
        text = record['text']
        raw = _field(text, r'Prerequisites?')
        requirements = [_clause(clause.strip(), names) for clause in raw.rstrip('.').split(',') if clause.strip()]
        if key == 'exotic-weapon-proficiency':
            requirements = [dict(kind='baseAttackBonus', minimum=1),
                            dict(kind='ability', key='str', minimum=13,
                                 whenWeaponIds=['weapon:sword-bastard', 'weapon:waraxe-dwarven'])]
        if key in ('improved-spell-capacity', 'spell-knowledge'):
            requirements = [dict(kind='maximumNormalSpellcasting', anyOf=[option for option in casting_options
                            if key == 'improved-spell-capacity' or option['tradition'] == 'arcane'])]
        if key == 'improved-familiar':
            requirements = [dict(kind='familiarAcquisitionAbility')]
        if key == 'greater-spell-focus':
            requirements = [dict(kind='feat', featId='spell-focus', choiceKey='schoolId')]
        repeat_evidence = next((line for line in text.splitlines() if re.search(
            r'(?:\b(?:gain|take|taken|select)\b[^.]*?\bmultiple times\b)', line, re.I)), None)
        distinct = bool(repeat_evidence and re.search(r'\b(?:new|different)\b', repeat_evidence, re.I)
                        and key != 'familiar-spell')
        # The grant sentence and the target constraint can be on separate lines.
        if repeat_evidence and key in CHOICES and key != 'familiar-spell':
            distinct = True
        stack = bool(repeat_evidence and re.search(r'\beffects stack\b', repeat_evidence, re.I))
        if key == 'familiar-spell':
            stack = True  # additional daily uses of the same chosen spell
        record['benefitText'] = _field(text, r'Benefits?')
        record['prerequisites'] = {'text': raw, 'allOf': requirements}
        record['selection'] = dict(repeatable=bool(repeat_evidence), maxTakes=None if repeat_evidence else 1,
                                   stacksWithSelf=stack if not repeat_evidence or stack or distinct else None,
                                   distinctChoice=distinct, choiceKey=CHOICES.get(key), evidence=repeat_evidence,
                                   choiceNeedsReview=key in CHOICE_REVIEW)
    return feats


def check_feat_selection(feats, feat_id, snapshot, *, choices=None, monk_bonus_slot=None):
    """Check a single choice against facts available immediately before it is taken.

    Pass an explicit empty collection when a fact is known absent. Absent snapshot
    fields are unknown; unsupported clauses cannot silently pass.
    """
    feat = feats[feat_id]
    selection = feat['selection']
    choices = choices or {}
    owned = snapshot.get('feats')
    failed, review = [], []

    def check(value, label):
        if value is None:
            review.append(label)
        elif not value:
            failed.append(label)

    def owns(key, choice_key=None, choice_value=None):
        if owned is None:
            return None
        return any(entry['featId'] == key and (choice_key is None or
                   entry.get('choices', {}).get(choice_key) == choice_value) for entry in owned)

    choice_key = selection['choiceKey']
    choice_value = choices.get(choice_key) if choice_key else None
    if choice_key:
        check(isinstance(choice_value, str) and bool(choice_value.strip()), 'Choose ' + choice_key)
        options = snapshot.get('validChoiceIdsByKey', {}).get(choice_key)
        if choice_value and options is not None:
            check(choice_value in options, 'Choice is not in the eligible catalog')
        elif choice_value and not selection['choiceNeedsReview']:
            check(None, 'Verify the selected ' + choice_key)
    if not selection['repeatable'] or selection['distinctChoice']:
        existing = owns(feat_id, choice_key if selection['distinctChoice'] else None, choice_value)
        check(None if existing is None else not existing, 'Feat already possessed for this selection')
    if selection['choiceNeedsReview']:
        verified = snapshot.get('eligibleChoiceIdsByFeat', {}).get(feat_id)
        check(None if not choice_key or verified is None or not choice_value else choice_value in verified,
              'Verify feat-specific selection restrictions against the benefit text')
    requirements = list(feat['prerequisites']['allOf'])
    if monk_bonus_slot is not None:
        allowed = {1: {'improved-grapple', 'stunning-fist'}, 2: {'combat-reflexes', 'deflect-arrows'},
                   6: {'improved-disarm', 'improved-trip'}}
        level = snapshot.get('classLevels', {}).get('monk')
        if feat_id not in allowed.get(monk_bonus_slot, ()):
            check(False, 'Feat is not offered in this Monk bonus slot')
        elif level is None:
            check(None, 'Verify Monk level for the bonus slot')
        elif level != monk_bonus_slot:
            check(False, 'Monk bonus slot does not match the selection-time class level')
        else:
            requirements = []
    if feat['epic']:
        requirements.append(dict(kind='level', key='character', minimum=21))
    for req in requirements:
        kind, key = req['kind'], req.get('key')
        if kind == 'maximumNormalSpellcasting':
            levels = snapshot.get('spellcastingLevels')
            scores = snapshot.get('abilityScores', {})
            selected_class = choices.get('castingClassId') if feat_id == 'improved-spell-capacity' else None
            outcomes = []
            for option in req['anyOf']:
                class_id = option['classId']
                if selected_class is not None and class_id != selected_class:
                    continue
                level = levels.get(class_id, 0) if levels is not None else None
                score = scores.get(option['ability'])
                if ((level is not None and level < option['minimumSpellcastingLevel']) or
                        (score is not None and score < option['minimumAbilityScore'])):
                    outcomes.append(False)
                elif level is None or score is None:
                    outcomes.append(None)
                else:
                    outcomes.append(True)
            check(True if True in outcomes else None if None in outcomes else False,
                  'Ability to cast the maximum normal spell level for a qualifying class')
            continue
        if kind == 'familiarAcquisitionAbility':
            value = snapshot.get('hasFamiliarAcquisitionAbility')
            check(value if type(value) is bool else None, 'Ability to acquire a familiar')
            continue
        if kind == 'hasFamiliar':
            value = snapshot.get('hasFamiliar')
            check(value if type(value) is bool else None, 'Has a familiar')
            continue
        if kind == 'manual':
            check(None, req['text'])
            continue
        if req.get('whenWeaponIds') and choices.get('weaponId') not in req['whenWeaponIds']:
            continue
        if kind == 'feat':
            matching = req.get('choiceKey')
            value = req.get('choiceValue', choices.get(matching))
            check(owns(req['featId'], matching, value) if not matching or value else None, req['featId'])
            continue
        if kind in ('weaponProficiency', 'feature'):
            values = snapshot.get('weaponProficiencies' if kind == 'weaponProficiency' else 'features')
            expected = choices.get('weaponId') if kind == 'weaponProficiency' else key
            check(None if values is None or expected is None else expected in values, kind + ': ' + str(expected))
            continue
        if kind == 'ability':
            value = snapshot.get('abilityScores', {}).get(key)
        elif kind == 'skillRanks':
            value = snapshot.get('skillRanks', {}).get(key)
        elif kind == 'level':
            value = (snapshot.get(key + 'Level') if key in ('caster', 'character') else
                     snapshot.get('classLevels', {}).get(key))
        elif kind == 'metamagicFeatCount' and owned is not None:
            value = len({entry['featId'] for entry in owned if entry['featId'] in feats
                         and feats[entry['featId']]['category'].casefold() == 'metamagic'})
        else:
            value = snapshot.get(kind)
        check(None if value is None else value >= req['minimum'], f'{key or kind} ≥ {req["minimum"]}')
    return {'status': 'ineligible' if failed else 'needs-review' if review else 'eligible',
            'failed': failed, 'needsReview': review}
