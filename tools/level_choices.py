"""Validate and record concrete level-up choices with the XP transaction."""
from copy import deepcopy
from fractions import Fraction

from .drain_history import (discard_permanent_losses, effective_xp, forget_level_inscriptions,
                            materialize_active_levels, projected_history, reconcile_character_spell_ledgers,
                            restore_suppressed_suffix)
from .epic_spell_feats import CAPACITY, KNOWLEDGE, apply_epic_spell_pick
from .natural_weapons import FEAT as NATURAL_ATTACK_FEAT, form_roster, selection_ids
from .feat_selection import check_feat_selection
from .spell_advancement import active_known, record_casting_choices
from .level_history import advance_level_history, replay_level_history


def record_level_choices(core, character, race_id, *, class_id=None, xp_award=0, choices=None,
                         current_alignment=None, feat_snapshot=None):
    """Record first class level or award XP and commit the resulting level choices.

    Scores include racial adjustments. The caller confirms class-specific feat
    slots, prerequisites requiring table facts, and spell/class choices.
    """
    result = deepcopy(character)
    choices = deepcopy(choices)
    result = discard_permanent_losses(core, result)
    outstanding = sorted([*result.get('drainedLevels', ()), *result.get('permanentLosses', ())],
                         key=lambda loss: loss['characterLevel'])
    if outstanding:
        result = materialize_active_levels(core, result)
        if class_id is not None:
            forget_level_inscriptions(result, outstanding.pop(0))
    if 'drainXpOverride' in result:
        result['xp'] = effective_xp(result)
        del result['drainXpOverride']
    history_args = dict(racial_hit_dice=result.get('racialHitDice', 0),
                        level_adjustment=result.get('levelAdjustment', 0),
                        alignment_by_level={int(k): v for k, v in result.get('alignmentByLevel', {}).items()})
    prior = projected_history(core, result)
    if not result['classChoices']:
        if class_id is None or xp_award != 0:
            raise ValueError('Record the starting class before giving XP awards')
        if current_alignment is not None:
            history_args['alignment_by_level'][prior['characterLevel'] + 1] = current_alignment
        history = replay_level_history(core, [class_id], xp=result['xp'], **history_args)
    else:
        history = advance_level_history(core, result['classChoices'], result['xp'], xp_award,
                                        class_id=class_id, current_alignment=current_alignment, **history_args)
        result['xp'] = history['xp']
    if class_id is None:
        if choices is not None:
            raise ValueError('Choices are only recorded when a level is gained')
        return restore_suppressed_suffix(result, outstanding)
    required = {'hitDieRoll', 'abilityIncreases', 'skillRanks', 'featChoices'}
    if choices is None or not required <= choices.keys():
        raise ValueError('Record the Hit Die, ability, skill, and feat choices for this level')
    entry = history['entries'][-1]
    level = entry['characterLevel']
    cls = next(c for c in core['progression']['classes'] if c['id'] == class_id)
    race = next(r['effective'] for r in core['progression']['races'] if r['id'] == race_id)
    scores = result['abilityScores']
    prior_scores = dict(scores)
    old_con = (scores['con'] - 10) // 2
    increases = choices['abilityIncreases']
    if (any(key not in scores or scores[key] is None or type(n) is not int or n != 1 for key, n in increases.items())
            or sum(increases.values()) != entry['abilityScoreIncrease']):
        raise ValueError('Record exactly the ability increases granted at this level')
    for key, amount in increases.items():
        scores[key] += amount
    roll = choices['hitDieRoll']
    if type(roll) is not int or not 1 <= roll <= cls['hitDie'] or level == 1 and roll != cls['hitDie']:
        raise ValueError('Invalid Hit Die result; use the maximum at first character level')
    con = (scores['con'] - 10) // 2
    hp_gain = max(1, roll + con) + (level - 1) * (con - old_con)
    ranks = result.setdefault('skillRanks', {})
    ranks_gained = choices['skillRanks']
    class_skills = {skill['skillId'] for skill in cls['classSkills']}
    ever_class = {skill['skillId'] for c in core['progression']['classes'] if c['id'] in history['classLevels']
                  for skill in c['classSkills']} | class_skills
    valid_skills = {s['id'] for s in core['skills']['skills']}
    budget = max(1, cls['skillPoints']['base'] + (scores['int'] - 10) // 2)
    if level == 1:
        budget *= cls['skillPoints']['firstLevelMultiplier']
    budget += sum(grant['firstLevel' if level == 1 else 'perLevel'] for grant in race.get('bonusSkillPoints') or ())
    spent = 0
    for skill, raw in ranks_gained.items():
        gained = Fraction(str(raw))
        cost = gained * (1 if skill in class_skills else 2)
        total = Fraction(str(ranks.get(skill, 0))) + gained
        cap = Fraction(level + 3, 1 if skill in ever_class else 2)
        if skill not in valid_skills or gained <= 0 or cost.denominator != 1 or total > cap:
            raise ValueError(f'Invalid skill purchase: {skill}')
        spent += cost
        ranks[skill] = float(total) if total.denominator != 1 else int(total)
    if spent > budget:
        raise ValueError('Skill purchases exceed the level budget')
    targets, casting_levels, spell_changes = record_casting_choices(core, result, prior, history, choices, prior_scores=prior_scores)
    known = active_known(result, prior, result.get('featChoices', ()))
    for track, change in spell_changes.items():
        ids = set(known.get(track, ())) - set(change['removed'])
        known[track] = sorted(ids | change['learned'].keys())
    feats = result.setdefault('featChoices', [])
    picks = deepcopy(choices['featChoices'])
    racial = sum(grant['count'] for grant in race.get('bonusFeats') or () if grant.get('atLevel') == level)
    if sum(pick.get('source', 'general') == 'general' for pick in picks) != entry['generalFeatChoices']:
        raise ValueError('Record exactly the general feats granted at this level')
    if sum(pick.get('source') == 'racial' for pick in picks) != racial:
        raise ValueError('Record exactly the racial feat choices granted at this level')
    for pick in picks:
        if pick.get('source', 'general') not in ('general', 'racial', 'class'):
            raise ValueError('Unknown feat grant source')
        if pick.get('source') == 'class' and not pick.get('classGrantConfirmed'):
            raise ValueError('Confirm the class bonus feat grant and allowed choice')
        facts = dict(feat_snapshot or {}, feats=feats, characterLevel=level, classLevels=history['classLevels'],
                     abilityScores=scores, skillRanks=ranks, baseAttackBonus=history['classBaseCombat']['bab'])
        facts['spellcastingLevels'] = casting_levels
        if pick['featId'] == NATURAL_ATTACK_FEAT:
            facts['naturalAttackIds'] = selection_ids(race.get('naturalWeapons') or (),
                result.get('naturalAttacks', ()),
                *(form_roster(core, key, result.get('naturalFormsById')) for key in result.get('availableNaturalFormIds', ())))
        checked = check_feat_selection(core['feats']['byId'], pick['featId'], facts,
                                       choices=pick.get('choices'), monk_bonus_slot=pick.get('monkBonusSlot'))
        if checked['status'] == 'ineligible' or checked['status'] == 'needs-review' and not pick.get('dmConfirmation'):
            raise ValueError(f"Feat selection not confirmed: {pick['featId']}: {checked}")
        if pick['featId'] in (CAPACITY, KNOWLEDGE):
            if 'accessibleSpellbookIds' in choices:
                facts['accessibleSpellbookIds'] = choices['accessibleSpellbookIds']
            pick, result['spellbooksById'] = apply_epic_spell_pick(core, dict(result, knownSpellIdsByClassId=known), pick, facts)
        feats.append(pick)
        hp_gain += sum(effect['amount'] for effect in core['effects']['featEffectsByFeatId'].get(pick['featId'], ())
                       if effect.get('statId') == 'max-hp' and type(effect.get('amount')) is int)
    grants = dict(choices, classId=class_id, classLevel=entry['classLevel'], hpGain=hp_gain,
                  featChoices=feats[-len(picks):] if picks else [], skillRanks=dict(ranks_gained))
    grants.update(castingTargets=targets, knownSpellChanges=spell_changes)
    result.setdefault('levelGrantsByLevel', {})[str(level)] = grants
    result['maxHp'] = result.get('maxHp', 0) + hp_gain
    result['classChoices'] = [*result['classChoices'], class_id]
    if current_alignment is not None:
        result.setdefault('alignmentByLevel', {})[str(level)] = deepcopy(current_alignment)
    return reconcile_character_spell_ledgers(core, restore_suppressed_suffix(result, outstanding))
