"""Source-linked cure rules and reversible, independently tracked condition instances."""
from copy import deepcopy


def catalog():
    heal = ['blinded', 'confused', 'dazed', 'dazzled', 'deafened', 'exhausted', 'fatigued',
            'nauseated', 'sickened', 'stunned']
    rules = {
        'remove-blindness-deafness': ('Remove Blindness/Deafness', dict(operation='remove',
            conditionIds=['blinded', 'deafened'], chooseOne=True, excludes=['missing-organ'])),
        'remove-paralysis': ('Remove Paralysis', dict(operation='remove-or-repeat-save', conditionIds=['paralyzed'],
            requiresTemporarySource=True, repeatSaveResistanceBonusByTargetCount={'2': 4, '3': 2, '4': 2})),
        'remove-fear': ('Remove Fear', dict(operation='suppress', conditionIds=['shaken', 'frightened', 'panicked', 'cowering'],
            requiresFearSource=True, durationSeconds=600, dispelsSourceSpellId='cause-fear')),
        'calm-emotions': ('Calm Emotions', dict(operation='calm', conditionIds=['confused', 'shaken', 'frightened', 'panicked', 'cowering'],
            fearSuppressionDuration='confirmed-cast-duration', endsOnAggressionOrDamage=True)),
        'break-enchantment': ('Break Enchantment', dict(operation='break-source', conditionIds=[], matchBySource=True,
            sourceKinds=['enchantment', 'transmutation', 'curse'], casterLevelCheckCap=15,
            dcBase=11, cursedItemDc=25, nondispellableSpellMaxLevel=5)),
        'remove-curse': ('Remove Curse', dict(operation='remove-source-curse', conditionIds=[], matchBySource=True,
            mayRequireMinimumCasterLevel=True, doesNotCleanseCursedEquipment=True)),
        'stone-to-flesh': ('Stone to Flesh', dict(operation='remove', conditionIds=['petrified'],
            survivalSave={'type': 'fortitude', 'dc': 15}, onFailedSurvival='dead')),
        'heal': ('Heal', dict(operation='remove', conditionIds=heal, clearsLedger='abilityDamage', excludesTargetKinds=['undead'])),
        'heal-mass': ('Heal, Mass', dict(operation='remove', conditionIds=heal, clearsLedger='abilityDamage', excludesTargetKinds=['undead'])),
        'heal-mount': ('Heal Mount', dict(operation='remove', conditionIds=heal, clearsLedger='abilityDamage',
                                         requiresSpecialMount=True, excludesTargetKinds=['undead'])),
        'restoration-lesser': ('Restoration, Lesser', dict(operation='reduce-fatigue', conditionIds=['fatigued', 'exhausted'],
            onExhausted='fatigued', abilityDamageDice='1d4', abilityCount=1, alternative='dispel-magical-ability-penalty')),
        'restoration': ('Restoration', dict(operation='remove', conditionIds=['fatigued', 'exhausted'],
            clearsLedger='abilityDamage', abilityDrainCount=1, negativeLevelOperationId='restoration')),
        'restoration-greater': ('Restoration, Greater', dict(operation='remove', conditionIds=['fatigued', 'exhausted', 'confused'],
            clearsLedger='abilityDamage', clearAbilityDrain=True, negativeLevelOperationId='restoration-greater',
            dispelsMagicalAbilityPenalties=True)),
    }
    return {key: dict(rule, source={'file': 'SPELLBOOK.txt', 'heading': title}) for key, (title, rule) in rules.items()}


def active_condition_ids(instances, now):
    return sorted({i['conditionId'] for i in instances if now < i.get('expiresAtSeconds', float('inf'))
                   and now >= i.get('suppressedUntilSeconds', 0)})


def apply_condition_cure(core, spell_id, instances, now, *, resolved, target_kind='living', special_mount=False,
                         condition_id=None, target_count=1, save_totals=None, survival_total=None, suppression_until=None,
                         eligible_source_ids=()):
    """Resolve one target's confirmed cure; save_totals are per-instance totals including bonuses."""
    rule = core['effects']['conditionCuresBySpellId'][spell_id]
    result = deepcopy(list(instances))
    if (not resolved or target_kind in rule.get('excludesTargetKinds', ()) or
            rule.get('requiresSpecialMount') and not special_mount):
        return result
    ids = rule['conditionIds']
    if rule.get('chooseOne'):
        if condition_id not in ids:
            raise ValueError('Choose one condition to cure')
        ids = [condition_id]
    operation = rule['operation']
    if operation == 'remove-or-repeat-save' and (type(target_count) is not int or not 1 <= target_count <= 4):
        raise ValueError('Remove Paralysis targets one to four creatures')
    output = []
    exhaustion_reduced = False
    for entry in result:
        if (entry.get('sourceId') not in eligible_source_ids if rule.get('matchBySource') else
                entry['conditionId'] not in ids) or now >= entry.get('expiresAtSeconds', float('inf')):
            output.append(entry)
            continue
        if (entry.get('cause') in rule.get('excludes', ()) or
                rule.get('requiresFearSource') and entry.get('effectFamily') != 'fear' or
                rule.get('requiresTemporarySource') and not entry.get('temporary')):
            output.append(entry)
            continue
        if operation == 'calm' and entry['conditionId'] != 'confused':
            if entry.get('effectFamily') == 'fear':
                if type(suppression_until) is not int or suppression_until <= now:
                    raise ValueError('Supply the confirmed Calm Emotions expiry')
                entry['suppressedUntilSeconds'] = max(entry.get('suppressedUntilSeconds', 0), suppression_until)
            output.append(entry)
            continue
        if operation == 'suppress' and entry.get('sourceSpellId') != rule['dispelsSourceSpellId']:
            entry['suppressedUntilSeconds'] = max(entry.get('suppressedUntilSeconds', 0), now + rule['durationSeconds'])
            output.append(entry)
        elif operation == 'remove-or-repeat-save' and target_count > 1:
            total = (save_totals or {}).get(entry['id'])
            if type(total) is not int or type(entry.get('saveDc')) is not int:
                raise ValueError('Supply repeat save total and original DC')
            if total < entry['saveDc']:
                output.append(entry)
        elif rule.get('survivalSave'):
            if type(survival_total) is not int:
                raise ValueError('Supply the Stone to Flesh survival save total')
            if survival_total < rule['survivalSave']['dc']:
                output.append(dict(id=entry['id'], conditionId='dead', sourceSpellId=spell_id))
        elif operation == 'reduce-fatigue' and entry['conditionId'] == 'exhausted':
            exhaustion_reduced = True
    if exhaustion_reduced:
        output.append(dict(id=f'{spell_id}:{now}:fatigue', conditionId='fatigued', sourceSpellId=spell_id))
    return output


def cure_actor(core, actor, spell_id, now, *, resolved, target_kind='living', special_mount=False,
               ability=None, damage_healed=None, caster_level=None, **condition_facts):
    """Apply a confirmed cure to overlays; base scores, XP and class choices remain intact.

    Ability ledgers map ability abbreviations to points lost. The caller supplies
    Lesser Restoration's d4 result if choosing its ability-damage option.
    """
    rule = core['effects']['conditionCuresBySpellId'][spell_id]
    result = deepcopy(actor)
    if (not resolved or target_kind in rule.get('excludesTargetKinds', ()) or
            rule.get('requiresSpecialMount') and not special_mount):
        return result
    instances = result.get('conditionOverrides', [])
    result['conditionOverrides'] = apply_condition_cure(core, spell_id, instances, now, resolved=True,
        target_kind=target_kind, special_mount=special_mount, **condition_facts)
    if rule.get('clearsLedger'):
        result[rule['clearsLedger']] = {}
    if rule.get('clearAbilityDrain'):
        result['abilityDrain'] = {}
    elif rule.get('abilityDrainCount'):
        drain = result.get('abilityDrain', {})
        options = [key for key, value in drain.items() if value > 0]
        if options:
            chosen = ability if ability is not None else options[0] if len(options) == 1 else None
            if chosen not in options:
                raise ValueError('Choose one drained ability to restore')
            drain.pop(chosen)
    if damage_healed is not None:
        if not rule.get('abilityDamageDice') or type(damage_healed) is not int or not 1 <= damage_healed <= 4:
            raise ValueError('Supply the Lesser Restoration d4 result')
        damage = result.get('abilityDamage', {})
        if ability not in damage:
            raise ValueError('Choose a damaged ability')
        damage[ability] = max(0, damage[ability] - damage_healed)
        if not damage[ability]:
            damage.pop(ability)
    if rule.get('negativeLevelOperationId'):
        from .drain_history import restore_character_drain
        result = restore_character_drain(core, result, spell_id, now, caster_level)
    return result
