"""Replay one class choice and select one progression row per character level."""
from .alignment import class_alignment_status
from .character_advancement import _integer, apply_xp_award, character_level_grants, level_for_xp


def _rules(core):
    rules = {rule['id']: rule['mechanic'] for rule in core['mechanics']['rules']
             if rule['id'] in ('character-advancement', 'ability-increases-and-feats')}
    return rules['character-advancement'], rules['ability-increases-and-feats']


def replay_level_history(core, class_choices, *, racial_hit_dice=0, level_adjustment=0, xp=None, alignment_by_level=None):
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
    continuous = {rule['mechanic']['parameters']['classId'] for rule in core['mechanics']['rules']
                  if rule['mechanic'].get('type') == 'level-sequence-constraint'
                  and rule['mechanic']['parameters']['constraint'] == 'cannot-return-after-advancing-another-class'}
    counts, entries = {}, []
    pre_epic_rows = {}
    alignment_by_level = dict(alignment_by_level or {})
    for character_level, class_id in enumerate(class_choices, racial_hit_dice + 1):
        if not isinstance(class_id, str) or class_id not in classes:
            raise ValueError(f'Unknown class choice at character level {character_level}: {class_id!r}')
        base = classes[class_id]
        facts = alignment_by_level.pop(character_level, None)
        if facts is not None:
            status = class_alignment_status(core, class_id, facts['alignmentId'],
                                            deity_alignment=facts.get('deityAlignmentId'),
                                            deity_known=facts.get('deityKnown', False),
                                            fallen=facts.get('fallenClassIds', ()))
            if status != 'eligible':
                raise ValueError(f'{class_id} alignment at character level {character_level}: {status}')
        if base['type'] == 'epic':
            raise ValueError(f'Choose {base["extends"]!r}; epic progression is a continuation, not a separate class')
        if class_id in continuous and class_id in counts and entries[-1]['classId'] != class_id:
            raise ValueError(f'Cannot return to {class_id} after advancing another class')
        class_level = counts.get(class_id, 0) + 1
        progression_class = base
        rows = [row for row in base['progression'] if row['level'] == class_level]
        if not rows and class_id in extensions and character_level >= 21:
            progression_class = extensions[class_id]
            rows = [row for row in progression_class['progression'] if row['level'] == class_level]
        if len(rows) != 1:
            raise ValueError(f'Expected one progression row for {class_id} level {class_level}; found {len(rows)}')
        counts[class_id] = class_level
        if character_level <= 20:
            pre_epic_rows[class_id] = rows[0]
        entries.append(dict(characterLevel=character_level, classId=class_id, classLevel=class_level,
                            progressionClassId=progression_class['id'], progressionRow=rows[0],
                            firstCharacterLevel=character_level == 1,
                            **({'alignmentAtSelection': dict(facts)} if facts is not None else {}),
                            **character_level_grants(character_level, benefits)))
    if alignment_by_level:
        raise ValueError('Alignment facts supplied for an unrecorded class level')
    character_level = racial_hit_dice + len(entries)
    effective_level = character_level + level_adjustment
    if xp is not None and level_for_xp(xp, track) != effective_level:
        raise ValueError('XP does not match the effective level of the recorded history')
    epic_rows = core['mechanics']['lookups']['epicSaveAndAttackBonuses']['rows']
    epic_bonuses = next((row.copy() for row in epic_rows if row['level'] == character_level), None)
    class_base = {key: sum(row[key] for row in pre_epic_rows.values()) for key in ('bab', 'fort', 'ref', 'will')}
    return dict(characterLevel=character_level, effectiveCharacterLevel=effective_level,
                classBaseCombat=class_base, epicCharacterBonuses=epic_bonuses,
                racialHitDice=racial_hit_dice, levelAdjustment=level_adjustment,
                classLevels=counts, entries=entries)


def advance_level_history(core, class_choices, xp, award, *, class_id=None, racial_hit_dice=0, level_adjustment=0, alignment_by_level=None, current_alignment=None):
    """Apply XP and, if a level was earned, commit exactly one class choice together.

    The award is already adjusted (for example by any enabled XP penalty).
    The caller supplies historical and current alignment facts and other prerequisites.
    """
    build = replay_level_history(core, class_choices, racial_hit_dice=racial_hit_dice,
                                 level_adjustment=level_adjustment, xp=xp, alignment_by_level=alignment_by_level)
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
        facts = dict(alignment_by_level or {})
        if current_alignment is not None:
            facts[build['characterLevel'] + 1] = current_alignment
        build = replay_level_history(core, choices, racial_hit_dice=racial_hit_dice,
                                     level_adjustment=level_adjustment, xp=result['xp'], alignment_by_level=facts)
    return dict(xp=result['xp'], discardedXp=result['discardedXp'], classChoices=choices, **build)
