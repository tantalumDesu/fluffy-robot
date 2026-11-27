"""Per-class spell pools and metamagic cast planning; no targeting or rest automation."""
import re
from copy import deepcopy

if __package__:
    from .spell_components import check_components, effective_codes, resolve_component_cast
    from .spellbooks import pages_used, school_access, wizard_specialization
    from .feat_grants import feat_effects
    from .sheet_effects import modifier_total
    from .spell_focus import focus_bonus
    from .alignment import check_spell_alignment
    from .game_time import SECONDS, encounter_clock, schedule_cast
else:
    from spell_components import check_components, effective_codes, resolve_component_cast
    from spellbooks import pages_used, school_access, wizard_specialization
    from feat_grants import feat_effects
    from sheet_effects import modifier_total
    from spell_focus import focus_bonus
    from alignment import check_spell_alignment
    from game_time import SECONDS, encounter_clock, schedule_cast


METAMAGIC = {
    'empower-spell': (2, 'empower'), 'enlarge-spell': (1, 'double-range'),
    'extend-spell': (1, 'double-duration'), 'heighten-spell': (None, 'raise-effective-level'),
    'maximize-spell': (3, 'maximize'), 'quicken-spell': (4, 'quicken'),
    'silent-spell': (1, 'remove-verbal'), 'still-spell': (1, 'remove-somatic'),
    'widen-spell': (3, 'double-area'),
}


def metamagic_catalog(feats):
    result = {key: dict(slotIncrease=cost, operation=operation, source=feats[key]['source'])
              for key, (cost, operation) in METAMAGIC.items()}
    result['improved-metamagic'] = dict(operation='reduce-fixed-slot-increase', reductionPerTake=1,
                                       minimumIncrease=1, source=feats['improved-metamagic']['source'])
    return result


def feat_slot_budget(core, class_id, spellcasting_level, ability_score, *, feat_choices=(), specialization=None):
    """Daily budget from active feat picks (use projected picks after level loss)."""
    from .epic_spell_feats import epic_slot_grants
    return slot_budget(core, class_id, spellcasting_level, ability_score,
                       extra_slots=epic_slot_grants(feat_choices, class_id), specialization=specialization)


def slot_budget(core, class_id, spellcasting_level, ability_score, *, extra_slots=None, specialization=None):
    """Return castable daily slots by (pool, level), for one effective casting class.

    Supply the bonus-slot-eligible ability score (not transient spell boosts).
    Extra slots are caller-validated grants such as Improved Spell Capacity.
    """
    cls = next(c for c in core['progression']['classes'] if c['id'] == class_id)
    casting = cls.get('spellcasting', {})
    if casting.get('source') != 'own':
        raise ValueError('Choose a class with its own spellcasting track')
    cap = core['magic']['dailySlotRules']['epicBaseSlotCapsByClassId'].get(class_id)
    row_level = min(spellcasting_level, cap['level']) if cap else spellcasting_level
    if class_id in ('adept', 'magewright'):
        row_level = min(row_level, cls['progression'][-1]['level'])
    row = next((r for r in cls['progression'] if r['level'] == row_level), None)
    if row is None:
        raise ValueError('No slot progression row for this effective spellcasting level')
    result = {}
    mod = (ability_score - 10) // 2
    for pool, field in (('regular', 'spellsPerDay'), ('domain', 'domainSpellsPerDay')):
        for level, base in enumerate(row.get(field, ()), casting['minSpellLevel']):
            if base is None or ability_score < 10 + level:
                continue
            bonus = (1 + (mod - level) // 4) if pool == 'regular' and level > 0 and mod >= level else 0
            if base + bonus:
                result[pool, level] = base + bonus
    for level, quantity in (extra_slots or {}).items():
        if type(level) is not int or level < casting['minSpellLevel'] or type(quantity) is not int or quantity < 0:
            raise ValueError('Invalid extra slot grant')
        if quantity and ability_score >= 10 + level:
            # A newly unlocked spell level also receives its ability bonus once.
            bonus = (1 + (mod - level) // 4) if ('regular', level) not in result and 0 < level <= mod else 0
            result['regular', level] = result.get(('regular', level), 0) + quantity + bonus
    if class_id == 'wizard' and specialization:
        profile = wizard_specialization(core, specialization.get('specialtySchoolId'), specialization.get('prohibitedSchoolIds', ()))
        if profile['specialtySchoolId']:
            count = core['magic']['wizardSpellbook']['specialization']['extraSlotsPerSpellLevel']
            for level, base in enumerate(row.get('spellsPerDay', ()), casting['minSpellLevel']):
                if base is not None and ability_score >= 10 + level:
                    result['specialist', level] = count
    return result


def armor_spell_failure(core, class_id, casting_kind, components, worn_armor_and_shields):
    """Return a per-cast chance from confirmed worn/in-use item IDs."""
    items = core['inventory']['itemsById']
    contributions = []
    seen = set()
    applicable = casting_kind == 'arcane' and 'S' in components
    for item_id in worn_armor_and_shields:
        item = items[item_id]
        kind = item['kind']
        if kind not in ('armor', 'shield') or kind in seen:
            raise ValueError('Supply at most one worn armor and one in-use shield')
        seen.add(kind)
        bard_light = class_id == 'bard' and kind == 'armor' and item['category'].lower().split()[0] == 'light'
        percent = (item['arcaneSpellFailurePercent'] or 0) if applicable and not bard_light else 0
        contributions.append(dict(itemId=item_id, percent=percent))
    percent = min(100, sum(entry['percent'] for entry in contributions))
    return dict(percent=percent, contributions=contributions, requiresRuling=percent > 0,
                adjudicationText=('Roll d100. A result at or below the listed chance ruins the spell; '
                                  'the action and spell slot are not refunded. Do not apply spell effects until resolved.'))


def resolve_armor_spell_failure(plan, roll):
    """Adjudicate a completed cast using a player/DM-supplied percentile roll."""
    if type(roll) is not int or not 1 <= roll <= 100:
        raise ValueError('Arcane spell failure roll must be an integer from 1 to 100')
    chance = plan['armorSpellFailure']['percent']
    failed = roll <= chance
    return dict(roll=roll, percent=chance, failed=failed, spellToApply=None if failed else deepcopy(plan))


def plan_cast(core, class_id, spell_id, ability_score, *, owned_feats=(), metamagic=(), heighten_to=None,
              domain_spell_levels=None, conversion=False, random_numeric=None, quickened_this_round=False,
              alignment_id=None, deity_alignment=None, deity_known=False, worn_armor_and_shields=(), feat_choices=(), specialization=None, specialist_slot=False, component_context=None, class_level=None, prestige_advancement=0):
    """Validate spell membership and metamagic, returning a plan without spending a slot."""
    cls = next(c for c in core['progression']['classes'] if c['id'] == class_id)
    casting = cls.get('spellcasting', {})
    if casting.get('source') != 'own':
        raise ValueError('Choose an actual spellcasting track')
    profile = core['magic']['castingProfilesByClassId'][class_id]
    conversion_rule = profile.get('conversion')
    if conversion and not conversion_rule:
        raise ValueError('This class has no spontaneous conversion')
    spell = next(s for s in core['magic']['spells'] if s['id'] == spell_id)
    if domain_spell_levels is not None:
        level = domain_spell_levels.get(spell_id)
        if (not profile['allowsDomainSlots'] or type(level) is not int or
                not any(domain['level'] == level for domain in spell['domains'])):
            raise ValueError('Spell is not available at that level in a domain casting pool')
    family = conversion_rule['familyBySpellId'].get(spell_id) if conversion else None
    if conversion and not family:
        raise ValueError('Spell is outside this class’s spontaneous conversion choices')
    if class_id == 'wizard' and not school_access(core, spell, specialization):
        raise ValueError('Spell belongs to a prohibited Wizard school')
    if specialist_slot and (class_id != 'wizard' or domain_spell_levels is not None or
                            (specialization or {}).get('specialtySchoolId') != spell['schoolId']):
        raise ValueError('Specialist slots require a spell from the Wizard specialty school')
    alignment_status = check_spell_alignment(core, class_id, spell, alignment_id,
                                             deity_alignment=deity_alignment, deity_known=deity_known)
    if alignment_status != 'eligible':
        raise ValueError(f'Spell alignment: {alignment_status}')
    base = (domain_spell_levels.get(spell_id) if domain_spell_levels is not None else
            next((row['level'] for row in spell['lists'] if row['listId'] == profile['spellListId']), None))
    feat_choices = tuple(feat_choices)
    epic_level = None
    if domain_spell_levels is None and not conversion and feat_choices:
        from .epic_spell_feats import epic_known_levels
        epic_level = epic_known_levels(feat_choices, class_id).get(spell_id)
        if epic_level is not None:
            base = epic_level
    if base is None or (conversion and domain_spell_levels is not None):
        raise ValueError('Spell is not available in this pool')
    feats = tuple(sorted(metamagic))
    owned_feats = tuple(owned_feats)
    catalog = core['magic']['metamagicByFeatId']
    if len(set(feats)) != len(feats) or any(key not in METAMAGIC or key not in owned_feats for key in feats):
        raise ValueError('Metamagic must be owned and cannot be applied twice to one spell')
    effective = base
    if 'heighten-spell' in feats:
        if type(heighten_to) is not int or not base < heighten_to <= 9:
            raise ValueError('Heighten must raise the spell level, to at most 9')
        effective = heighten_to
    elif heighten_to is not None:
        raise ValueError('Heighten level requires Heighten Spell')
    if ability_score < 10 + effective:
        raise ValueError('Casting ability is too low for the effective spell level')
    spontaneous = profile['mode'] == 'spontaneous' or conversion
    component_tradition = 'divine' if domain_spell_levels is not None else profile['tradition']
    components = effective_codes(spell['componentProfile'], component_tradition)
    raw_time = spell['castingTime']['raw']
    time = raw_time
    timing = spell['timing']['casting'].copy()
    range_kind = (spell['range'].get('category') or '').casefold()
    duration = (spell['duration'].get('category') or '').casefold()
    area = spell['target'].get('area') or ''
    if random_numeric is None:
        random_numeric = bool(spell['mechanics'].get('diceRolls'))
    transforms = {}
    if 'quicken-spell' in feats:
        if spontaneous or quickened_this_round or raw_time.casefold() not in ('1 standard action', '1 round', '1 full-round action'):
            raise ValueError('This casting cannot be quickened')
        time = 'free action'
        timing.update(action='free', completion='current-turn')
        timing.pop('elapsed', None)
        timing.pop('continuous', None)
        transforms['provokes'] = False
    elif spontaneous and feats:
        time = 'full-round action' if raw_time.casefold() == '1 standard action' else {'base': raw_time, 'extraFullRoundActions': 1}
        if timing['action'] == 'standard' and timing['completion'] == 'current-turn':
            timing['action'] = 'full-round'
        else:
            timing['extraFullRoundActions'] = 1
    if 'silent-spell' in feats:
        if class_id == 'bard' or 'V' not in components:
            raise ValueError('Silent Spell cannot affect this casting')
        components.remove('V')
    if 'still-spell' in feats:
        if 'S' not in components:
            raise ValueError('Still Spell requires a somatic component')
        components.remove('S')
    if 'enlarge-spell' in feats:
        if range_kind not in ('close', 'medium', 'long'):
            raise ValueError('Enlarge requires close, medium, or long range')
        transforms['rangeMultiplier'] = 2
    if 'extend-spell' in feats:
        if not duration or re.search(r'concentration|instantaneous|permanent', spell['duration']['raw'], re.I):
            raise ValueError('Extend requires an eligible finite duration')
        transforms['durationMultiplier'] = 2
    if 'widen-spell' in feats:
        if not re.search(r'\b(burst|emanation|line|spread)\b', area, re.I):
            raise ValueError('Widen requires a burst, emanation, line, or spread area')
        transforms['areaDimensionMultiplier'] = 2
    empower, maximize = 'empower-spell' in feats, 'maximize-spell' in feats
    if empower or maximize:
        if not random_numeric:
            raise ValueError('Empower and Maximize require an eligible random numeric effect')
        transforms['variableNumericEffects'] = ('maximum-plus-half-normal-roll' if empower and maximize else
                                               'maximum' if maximize else 'normal-roll-plus-half')
    reduction = catalog['improved-metamagic']['reductionPerTake'] * owned_feats.count('improved-metamagic')
    minimum = catalog['improved-metamagic']['minimumIncrease']
    increase = sum(max(minimum, catalog[key]['slotIncrease'] - reduction)
                   for key in feats if catalog[key]['slotIncrease'] is not None)
    feat_choices = tuple(feat_choices)
    caster_level = None if class_level is None else base_caster_level(
        core, class_id, class_level, prestige_advancement=prestige_advancement)
    if caster_level == 0:
        raise ValueError('This class has not reached its first casting level')
    focus = focus_bonus(core, spell, feat_choices)
    penetration = modifier_total('spell-resistance-check', feat_effects(
        core, feat_choices, {'spell-penetration', 'greater-spell-penetration'}))
    if spell['spellResistance'].get('applies') is False:
        penetration = 0
    return dict(classId=class_id, spellId=spell_id, baseCasterLevel=caster_level,
                epicKnown=epic_level is not None,
                spellbookRules=core['magic']['wizardSpellbook'] if profile['requiresSpellbook'] else None,
                conversionFamily=family, conversionRequiresAuthorization=bool(conversion and conversion_rule['requiresFamilyAuthorization']),
                pool='specialist' if specialist_slot else 'domain' if domain_spell_levels is not None else 'regular',
                mode='conversion' if conversion else 'spontaneous' if spontaneous else 'prepared',
                baseSpellLevel=base, effectiveSpellLevel=effective, requiredSlotLevel=effective + increase,
                saveDc=10 + effective + (ability_score - 10) // 2 + focus, spellFocusSaveDcBonus=focus, spellResistanceCheckBonus=penetration, castingTime=time, timing=timing,
                metamagic=list(feats), components=components, transforms=transforms,
                componentCheck=check_components(core, spell, class_id, components, owned_feats, component_context, spell_level=effective),
                armorSpellFailure=armor_spell_failure(core, class_id, casting['kind'], components, worn_armor_and_shields))


def new_slots(class_id, budget):
    """Create a fresh mutable-state snapshot for one class; slot IDs are local to it."""
    return dict(classId=class_id, slots={f'{pool}:{level}:{index}':
                dict(pool=pool, level=level, expended=False, preparation=None)
                for (pool, level), count in sorted(budget.items()) for index in range(count)})


def _slot_for(state, slot_id, plan):
    if state['classId'] != plan['classId']:
        raise ValueError('Wrong casting class')
    slot = state['slots'][slot_id]
    if slot['expended'] or slot.get('negativeLevelLoss') or slot['pool'] != plan['pool'] or slot['level'] < plan['requiredSlotLevel']:
        raise ValueError('Slot unavailable, too low, or in the wrong pool')
    return slot


def _signature(plan):
    return [plan['spellId'], plan['effectiveSpellLevel'], list(plan['metamagic'])]


def prepare_spell(state, slot_id, plan, *, accessible_spell_ids, accessible_spellbooks=()):
    slot = _slot_for(state, slot_id, plan)
    if plan['mode'] != 'prepared' or slot['preparation'] is not None or (plan['spellId'] not in accessible_spell_ids
            and not plan.get('epicKnown', False)):
        raise ValueError('Cannot prepare this spell in this slot')
    if state['classId'] == 'wizard':
        rule = plan['spellbookRules']
        found = False
        for book in accessible_spellbooks:
            pages_used(book, rule)
            if (not book.get('lost') and not book.get('destroyed')
                    and plan['spellId'] not in book.get('damagedSpellIds', ())
                    and book['spellsById'].get(plan['spellId']) == plan['baseSpellLevel']):
                found = True
        if not found:
            raise ValueError('Wizard preparation requires the spell in an accessible spellbook')
    result = deepcopy(state)
    result['slots'][slot_id]['preparation'] = _signature(plan)
    return result


def spend_slot(state, slot_id, plan, *, known_spell_ids=(), authorized_conversion_spell_ids=(), game_seconds=None):
    if plan.get('componentCheck', {}).get('status') == 'blocked':
        raise ValueError('Casting components unavailable: ' + ', '.join(plan['componentCheck']['blockedReasons']))
    slot = _slot_for(state, slot_id, plan)
    if plan['mode'] == 'prepared':
        allowed = slot['preparation'] == _signature(plan)
    elif plan['mode'] == 'conversion':
        allowed = slot['preparation'] is not None and (not plan.get('conversionRequiresAuthorization', True) or plan['spellId'] in authorized_conversion_spell_ids)
    else:
        allowed = slot['preparation'] is None and (plan['spellId'] in known_spell_ids or plan.get('epicKnown', False))
    if not allowed:
        raise ValueError('Spell is not prepared, known, or available for conversion')
    result = deepcopy(state)
    result['slots'][slot_id]['expended'] = True
    if game_seconds is not None:
        if type(game_seconds) is not int or game_seconds < 0:
            raise ValueError('Expected a nonnegative cast timestamp')
        result['slots'][slot_id]['spentAtSeconds'] = game_seconds
    return result


def spellcasting_levels(core, history, advancement_choices=None):
    """Replay casting tracks; prestige targets are selected per character level.

    `advancement_choices[level]` is a list of target class IDs in the order of
    that progression row's `spellcastingAdvancement` entries.
    """
    classes = {c['id']: c for c in core['progression']['classes']}
    choices = dict(advancement_choices or {})
    levels = {}
    for entry in history['entries']:
        class_id, row = entry['classId'], entry['progressionRow']
        casting = classes[class_id].get('spellcasting', {})
        if casting.get('source') == 'own' and ('spellsPerDay' in row or class_id in levels):
            levels[class_id] = levels.get(class_id, 0) + 1
        advancement = row.get('spellcastingAdvancement', [])
        targets = choices.pop(entry['characterLevel'], [])
        if len(targets) != len(advancement) or len(set(targets)) != len(targets):
            raise ValueError(f'Choose each prestige casting target at character level {entry["characterLevel"]}')
        for kind, target in zip(advancement, targets):
            if target not in levels or (kind != 'any' and classes[target]['spellcasting']['kind'] != kind):
                raise ValueError(f'Invalid {kind} prestige casting target: {target}')
            levels[target] += 1
    if choices:
        raise ValueError('Casting targets supplied for a level not in the history')
    return levels


def numeric_spell_result(plan, normal_roll, maximum):
    """Transform one eligible numeric effect; never pass a save or opposed roll."""
    mode = plan['transforms'].get('variableNumericEffects')
    if mode == 'maximum-plus-half-normal-roll':
        return maximum + normal_roll // 2
    if mode == 'maximum':
        return maximum
    if mode == 'normal-roll-plus-half':
        return normal_roll + normal_roll // 2
    return normal_roll


def begin_encounter_cast(encounter, actor_id, spell_slots, slot_id, plan, **access):
    """Commit both action and slot, or neither. Interrupted casts keep the expenditure."""
    encounter_next, completed = schedule_cast(encounter, actor_id, plan)
    slots_next = spend_slot(spell_slots, slot_id, plan, game_seconds=encounter_clock(encounter)['gameSeconds'], **access)
    return encounter_next, slots_next, completed


def recover_slots(core, state, *, start_seconds, end_seconds, verified_rest_seconds=0,
                  scheduled_second_of_day=None):
    """Refresh a class's current ledger after eligible full preparation or focus.

    Caller verifies rest and preparation conditions. Uncast preparations remain;
    recovered slots are empty. Recent expenditures remain expended.
    """
    profile = core['magic']['spellRecoveryByClassId'].get(state['classId'])
    if profile is None:
        raise ValueError('This class has no automated recovery profile')
    if any(type(value) is not int or value < 0 for value in (start_seconds, end_seconds, verified_rest_seconds)):
        raise ValueError('Recovery times must be nonnegative integer seconds')
    if end_seconds - start_seconds < profile['preparationMinutes'] * SECONDS['minute']:
        raise ValueError('Preparation or focus is incomplete')
    if not profile['restHours'] * SECONDS['hour'] <= verified_rest_seconds <= start_seconds:
        raise ValueError('Insufficient or invalid verified rest')
    prior = state.get('lastRecovery')
    day = start_seconds // SECONDS['day']
    if prior and (start_seconds - verified_rest_seconds < prior['endSeconds'] or day == prior['day']):
        raise ValueError('Recovery overlaps a prior recovery or has already occurred this day')
    if profile['scheduledDailyTime']:
        if (type(scheduled_second_of_day) is not int or
                start_seconds % SECONDS['day'] != scheduled_second_of_day):
            raise ValueError('Preparation must begin at the chosen daily time')
    result = deepcopy(state)
    since = start_seconds - profile['recentUseHours'] * SECONDS['hour']
    for slot in result['slots'].values():
        slot.pop('negativeLevelId', None)
        if slot.pop('negativeLevelLoss', None) == 'immediate':
            slot['preparation'] = None
        if not slot['expended']:
            continue
        spent = slot.get('spentAtSeconds')
        if type(spent) is not int or not 0 <= spent <= start_seconds:
            raise ValueError('Expended slot needs a valid pre-recovery timestamp')
        if spent <= since:
            slot.update(expended=False, preparation=None)
            slot.pop('spentAtSeconds')
    result['lastRecovery'] = {'day': day, 'endSeconds': end_seconds}
    return result


def recover_spell_tracks(core, ledgers, recovery_by_class, *, negative_levels=(), choices=(), at_seconds):
    """Recover a batch of tracks, then apply one shared set of drain losses.

    Tracks recovering at different times must be submitted as separate batches.
    Equipment negative levels must be supplied from the current wielded state.
    """
    from .negative_levels import active_negative_levels, allocate_spell_losses

    if not recovery_by_class or any(args['end_seconds'] != at_seconds for args in recovery_by_class.values()):
        raise ValueError('Recovery batch must finish at one specified time')
    recovered = {key: recover_slots(core, ledgers[key], **args) for key, args in recovery_by_class.items()}
    blocked = allocate_spell_losses(core, recovered, active_negative_levels(negative_levels, at_seconds),
                                    choices, recovery=True)
    return {**deepcopy(ledgers), **blocked}


def base_caster_level(core, class_id, class_level, *, prestige_advancement=0):
    """Calculate the class baseline, separate from temporary caster-level modifiers."""
    if any(type(n) is not int or n < 0 for n in (class_level, prestige_advancement)):
        raise ValueError('Supply nonnegative class levels and prestige advancement')
    rule = core['magic']['castingProfilesByClassId'][class_id].get('casterLevel', {})
    if class_level < rule.get('minimumClassLevel', 1):
        return 0
    return class_level // rule.get('classLevelDivisor', 1) + prestige_advancement


def resolve_cast_completion(plan, *, component_percentile=None, concentration_total=None, armor_percentile=None,
                            injury_checks=()):
    """Return an applicable spell only after confirmed readiness and supplied rolls."""
    components = resolve_component_cast(plan, percentile_roll=component_percentile,
                                        concentration_total=concentration_total)
    if components['failed']:
        return dict(spellToApply=None, failedBy='components-or-concentration')
    for dc, total in injury_checks:
        if dc is None:
            continue
        if type(total) is not int:
            raise ValueError('Supply each injury Concentration check total')
        if total < dc:
            return dict(spellToApply=None, failedBy='injury-concentration')
    if plan['armorSpellFailure']['percent']:
        armor = resolve_armor_spell_failure(plan, armor_percentile)
        if armor['failed']:
            return dict(spellToApply=None, failedBy='armor-spell-failure')
    return dict(spellToApply=deepcopy(plan), failedBy=None)


def prepare_wizard_session(core, state, preparations, *, start_seconds, end_seconds,
                           verified_rest_seconds, accessible_spell_ids, accessible_spellbooks, refresh=False):
    """Prepare any number of Wizard spells after verified uninterrupted rest/study."""
    if state['classId'] != 'wizard':
        raise ValueError('Wizard preparation session requires a Wizard ledger')
    policy = core['magic']['spellRecoveryByClassId']['wizard']
    if (any(type(n) is not int or n < 0 for n in (start_seconds, end_seconds, verified_rest_seconds)) or
            not policy['restHours'] * SECONDS['hour'] <= verified_rest_seconds <= start_seconds or
            end_seconds - start_seconds < policy['preparationMinutes'] * SECONDS['minute']):
        raise ValueError('Wizard preparation requires uninterrupted rest and study')
    prior_end = max(state.get('lastPreparationEndSeconds', 0), state.get('lastRecovery', {}).get('endSeconds', 0))
    if start_seconds - verified_rest_seconds < prior_end:
        raise ValueError('Preparation overlaps an earlier session')
    result = (recover_slots(core, state, start_seconds=start_seconds, end_seconds=end_seconds,
                            verified_rest_seconds=verified_rest_seconds) if refresh else deepcopy(state))
    books = tuple(accessible_spellbooks)
    for slot_id, plan in preparations:
        result = prepare_spell(result, slot_id, plan, accessible_spell_ids=accessible_spell_ids, accessible_spellbooks=books)
    result['lastPreparationEndSeconds'] = end_seconds
    return result


def casting_injury_concentration_dc(core, plan, damage, *, continuous=False, source_ended=False):
    """One confirmed interruption, or the last tick of an ongoing continuous source."""
    if type(damage) is not int or damage < 0:
        raise ValueError('Damage must be a nonnegative integer')
    rule = core['magic']['castingInjury']
    if not damage or continuous and source_ended and rule['ignoreEndedContinuousSource']:
        return None
    counted = damage // rule['continuousDamageDivisor'] if continuous else damage
    return rule['baseDc'] + counted + plan['effectiveSpellLevel']
