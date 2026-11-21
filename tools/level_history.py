"""Replay one class choice and select one progression row per character level."""
from .character_advancement import _integer, apply_xp_award, character_level_grants, level_for_xp


def _rules(core):
    rules = {rule['id']: rule['mechanic'] for rule in core['mechanics']['rules']
             if rule['id'] in ('character-advancement', 'ability-increases-and-feats')}
    return rules['character-advancement'], rules['ability-increases-and-feats']


def replay_level_history(core, class_choices, *, racial_hit_dice=0, level_adjustment=0, xp=None):
    """Derive counts from ordered class IDs; optionally validate a committed XP total.

    Select rows, not bonuses: rows can contain cumulative values, and epic BAB
    and save bonuses use a separate character-level track.
    """
    _integer(racial_hit_dice, 0, 'Racial Hit Dice')
    _integer(level_adjustment, 0, 'Level adjustment')
    if not isinstance(class_choices, (list, tuple)):
        raise ValueError('Class choices must be an ordered list or tuple of class IDs')
    track, benefits = _rules(core)
    classes = {record['id']: record for record in core['progression']['classes']}
    extensions = {record['extends']: record for record in classes.values() if record['type'] == 'epic'}
    counts, entries = {}, []
    for character_level, class_id in enumerate(class_choices, racial_hit_dice + 1):
        if not isinstance(class_id, str) or class_id not in classes:
            raise ValueError(f'Unknown class choice at character level {character_level}: {class_id!r}')
        base = classes[class_id]
        if base['type'] == 'epic':
            raise ValueError(f'Choose {base["extends"]!r}; epic progression is a continuation, not a separate class')
        class_level = counts.get(class_id, 0) + 1
        progression_class = base
        rows = [row for row in base['progression'] if row['level'] == class_level]
        if not rows and class_id in extensions and character_level >= 21:
            progression_class = extensions[class_id]
            rows = [row for row in progression_class['progression'] if row['level'] == class_level]
        if len(rows) != 1:
            raise ValueError(f'Expected one progression row for {class_id} level {class_level}; found {len(rows)}')
        counts[class_id] = class_level
        entries.append(dict(characterLevel=character_level, classId=class_id, classLevel=class_level,
                            progressionClassId=progression_class['id'], progressionRow=rows[0],
                            firstCharacterLevel=character_level == 1,
                            **character_level_grants(character_level, benefits)))
    character_level = racial_hit_dice + len(entries)
    effective_level = character_level + level_adjustment
    if xp is not None and level_for_xp(xp, track) != effective_level:
        raise ValueError('XP does not match the effective level of the recorded history')
    return dict(characterLevel=character_level, effectiveCharacterLevel=effective_level,
                racialHitDice=racial_hit_dice, levelAdjustment=level_adjustment,
                classLevels=counts, entries=entries)


def advance_level_history(core, class_choices, xp, award, *, class_id=None, racial_hit_dice=0, level_adjustment=0):
    """Apply XP and, if a level was earned, commit exactly one class choice together.

    The award is already adjusted (for example by any enabled XP penalty).
    Prerequisites, continuity restrictions and other class choices are caller-owned.
    """
    build = replay_level_history(core, class_choices, racial_hit_dice=racial_hit_dice,
                                 level_adjustment=level_adjustment, xp=xp)
    if not build['characterLevel']:
        raise ValueError('Record the starting character before applying XP awards')
    track, benefits = _rules(core)
    # Resolve XP on the effective level track; derive grants from the actual
    # character level when replaying the committed class choice below.
    result = apply_xp_award(build['effectiveCharacterLevel'], xp, award, track, benefits)
    level_earned = result['characterLevel'] > build['effectiveCharacterLevel']
    if level_earned != (class_id is not None):
        raise ValueError('Choose exactly one class if and only if the award grants a level')
    choices = list(class_choices)
    if level_earned:
        choices.append(class_id)
        build = replay_level_history(core, choices, racial_hit_dice=racial_hit_dice,
                                     level_adjustment=level_adjustment, xp=result['xp'])
    return dict(xp=result['xp'], discardedXp=result['discardedXp'], classChoices=choices, **build)
