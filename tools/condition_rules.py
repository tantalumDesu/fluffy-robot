"""Typed condition rules transcribed from CONDITIONS.txt.

Sheet modifiers/flags are executable; event operations need an encounter consumer.
"""


def condition_policies(core):
    """Index canonical condition records without serializing a second copy."""
    return {record['id']: record['mechanics'] for record in core['effects']['conditions']}


def catalog(lines):
    result = {}

    def add(key, flags=(), mods=(), **operations):
        heading = key.replace('-', ' ').casefold() if key != 'flat-footed' else key
        line = next(i for i, text in enumerate(lines, 1) if text.split(':', 1)[0].casefold() == heading)
        result[key] = dict(flags=list(flags), modifiers=[
            dict(id=f'condition:{key}:{i}', operation='modifier', statId=stat, amount=amount,
                 bonusType=None, stacking='once-per-effect', **({'requires': requires[0]} if requires else {}))
            for i, (stat, amount, *requires) in enumerate(mods)], operations=operations,
            source={'file': 'CONDITIONS.txt', 'line': line})

    zero = dict(str=['prone', 'helpless'], dex=['paralyzed'], con=['dead'],
                int=['unconscious'], wis=['unconscious'], cha=['unconscious'])
    add('ability-damaged', scoreLoss={'ledger': 'ability-damage', 'zeroScoreConditions': zero,
                                     'defaultRecovery': {'points': 1, 'unit': 'day', 'sourceMayOverride': True}})
    add('ability-drained', scoreLoss={'ledger': 'ability-drain', 'zeroScoreConditions': zero, 'recovery': 'magic-only'})
    add('blinded', ['denied-dex-to-ac', 'half-speed', 'no-vision'],
        [('ac', -2), ('skill:search', -4), ('skill', -4, {'blindnessPhysicalSkillPenalty': True})],
        automaticFailure={'requiresSense': 'vision'}, opponentConcealment={'missChancePercent': 50},
        adaptation={'dmConfirmed': True, 'numericDivisor': 2, 'listenStillFails': True})
    add('blown-away', forcedMovement={'ground': {'distanceDice': '1d4', 'feetPerUnit': 10,
        'nonlethalDicePerUnit': '1d4', 'applyConditionId': 'knocked-down'},
        'flying': {'distanceDice': '2d6', 'feetPerUnit': 10, 'nonlethalDice': '2d6', 'direction': 'backward'}})
    add('checked', forcedMovement={'ground': {'stopForwardMotion': True}, 'flying': {'backwardDistanceFrom': 'source'}})
    add('confused', behavior={'trigger': 'start-turn', 'dice': '1d100', 'outcomes': [
        [1, 10, 'attack-or-close-with-caster'], [11, 20, 'act-normally'], [21, 50, 'babble'],
        [51, 70, 'flee-caster-at-top-speed'], [71, 100, 'attack-nearest-creature']],
        'familiarCountsAsSelf': True, 'fallback': 'babble', 'ifAttackedNextTurn': 'attack-attacker',
        'opportunityAttacks': 'current-target-only'})
    add('cowering', ['no-actions', 'denied-dex-to-ac'], [('ac', -2)])
    add('dazed', ['no-actions'], typicalDuration={'amount': 1, 'unit': 'round'})
    add('dazzled', mods=[(s, -1) for s in ('attack', 'skill:search', 'skill:spot')])
    add('dead', ['no-actions'], triggers={'hpAtMost': -10, 'constitutionEquals': 0, 'instantDeath': True},
        recovery={'normalHealing': False, 'magicalHealing': False, 'revival': 'source-defined'},
        body={'soulDeparts': True, 'decaysUnlessPreserved': True})
    add('deafened', ['no-hearing'], [('initiative', -4)], automaticFailure={'skillId': 'listen'},
        spellFailure={'component': 'verbal', 'chancePercent': 20}, adaptation={'dmConfirmed': True, 'numericDivisor': 2, 'listenStillFails': True})
    single = {'maximum': 1, 'allowed': ['move', 'standard'], 'fullRound': False}
    add('disabled', ['half-speed', 'single-move-or-standard'], actionBudget=single,
        strenuousAction={'trigger': 'action-completed', 'hpDamage': 1, 'standardIsStrenuous': True,
                         'otherActions': 'dm-determines-strenuousness'},
        unaidedRecovery={'unit': 'day', 'successPercent': 10, 'success': 'begin-natural-healing', 'failureHpLoss': 1},
        aidedRecovery='natural-healing')
    add('dying', ['no-actions'], implies=['unconscious'], hpRange=[-9, -1],
        stabilization={'trigger': 'end-round', 'chancePercent': 10, 'successConditionId': 'stable', 'failureHpLoss': 1})
    add('energy-drained', derivedFrom={'path': '/mechanics/negativeLevels', 'state': 'activeNegativeLevelCount'})
    add('entangled', ['half-speed', 'no-run', 'no-charge'], [('attack', -2), ('ability:dex', -4)],
        movementConstraint={'immobileIf': ['anchored', 'opposing-tether']},
        castingCheck={'skillId': 'concentration', 'dcBase': 15, 'add': 'spell-level', 'failure': 'lose-spell'})
    add('exhausted', ['half-speed', 'no-run', 'no-charge'], [('ability:str', -6), ('ability:dex', -6)],
        stateChangeId='fatigue', supersedes=['fatigued'])
    add('fascinated', ['attention-only'], [('skill', -4, {'reactionCheck': True})],
        endTriggers={'potential-threat': 'repeat-save', 'obvious-threat': 'end', 'ally-standard-action': 'end'})
    add('fatigued', ['no-run', 'no-charge'], [('ability:str', -2), ('ability:dex', -2)], stateChangeId='fatigue')
    add('flat-footed', ['denied-dex-to-ac', 'no-opportunity-attacks'], endTrigger='first-action-in-combat')
    fear = [(stat, -2) for stat in ('attack', 'save', 'skill', 'ability-check')]
    add('frightened', ['must-flee-if-possible'], fear, stateChangeId='fear',
        flight={'fightIfBlocked': True, 'mustUseAbilitiesIfOnlyEscape': True}, supersedes=['shaken'])
    add('grappling', ['does-not-threaten'], defense={'denyDexAgainst': 'outside-grapple'}, actionRules='grapple')
    add('helpless', mods=[('ac', -4, {'incomingAttackKind': 'melee'})], effectiveScores={'dex': 0},
        enablesSneakAttack=True, coupDeGrace={'action': 'full-round', 'provokes': True,
        'weapons': ['melee', 'bow', 'crossbow'], 'adjacentForRanged': True, 'automaticHit': True,
        'automaticCritical': True, 'sneakAttackApplies': True, 'save': 'fortitude', 'dcBase': 10,
        'add': 'damage-dealt', 'failure': 'dead', 'skipCriticalAndSaveIfImmuneToCriticals': True})
    add('incorporeal', allowedDamageSources=['incorporeal-creature', 'magic-weapon-plus-one-or-better',
        'spell', 'spell-like', 'supernatural'], additionalRules='incorporeality')
    add('invisible', ['visually-undetectable'], [('attack', 2, {'opponentSighted': True})],
        targetDefense={'denyDexterityBonus': True}, additionalRules='invisibility')
    add('knocked-down', forcedMovement={'ground': {'applyConditionId': 'prone'},
                                       'flying': {'distanceDice': '1d6', 'feetPerUnit': 10, 'direction': 'backward'}})
    add('nauseated', ['single-move-only'], actionBudget={'maximum': 1, 'allowed': ['move']},
        prohibitedActions=['attack', 'cast', 'concentrate', 'requires-attention'])
    add('panicked', ['drop-held', 'flee-only'], [m for m in fear if m[0] != 'attack'], stateChangeId='fear',
        flight={'topSpeed': True, 'randomPath': True, 'avoidOtherDangers': True, 'ifCornered': 'cowering',
                'typicalCorneredAction': 'total-defense', 'mustUseAbilitiesIfOnlyEscape': True}, supersedes=['frightened', 'shaken'])
    add('paralyzed', ['immobile', 'mental-actions-only'], implies=['helpless'], effectiveScores={'str': 0, 'dex': 0},
        hazards={'wingedFlight': 'fall', 'swimming': 'cannot-swim'}, occupiedSquareMovementCost=2)
    add('petrified', ['no-actions'], implies=['unconscious'], restoration={'intactOrReassembled': 'unharmed',
        'missingParts': ['permanent-hp-loss', 'debilitation']})
    add('pinned', ['immobile'], implies=['grappling'], actionRules='pinned-in-grapple', grantsHelpless=False)
    add('prone', mods=[('attack', -4, {'attackKind': 'melee'}), ('ac', 4, {'incomingAttackKind': 'ranged'}),
        ('ac', -4, {'incomingAttackKind': 'melee'})], prohibitedWeaponUse={'kind': 'ranged', 'exceptWeaponIds': ['weapon:crossbow-light', 'weapon:crossbow-heavy',
            'weapon:crossbow-hand', 'weapon:crossbow-repeating-light', 'weapon:crossbow-repeating-heavy',
            'weapon:dart', 'weapon:shuriken-5']},
        stand={'action': 'move', 'provokes': True})
    add('shaken', mods=fear, stateChangeId='fear')
    add('sickened', mods=fear + [('damage', -2, {'damageKind': 'weapon'})])
    add('stable', ['no-actions'], implies=['unconscious'], supersedes=['dying'],
        wakeCheck={'unit': 'hour', 'chancePercent': 10, 'successConditionId': 'disabled', 'unaidedFailureHpLoss': 1})
    add('staggered', ['single-move-or-standard'], actionBudget=single,
        comparison={'whenEqual': 'staggered', 'whenNonlethalHigher': 'unconscious', 'whenNonlethalLower': 'clear'})
    add('stunned', ['no-actions', 'drop-held', 'denied-dex-to-ac'], [('ac', -2)])
    add('turned', ['flee-only'], flight={'topSpeed': True, 'ifBlocked': 'cowering'}, duration={'amount': 10, 'unit': 'round'})
    add('unconscious', ['no-actions'], implies=['helpless'], triggers={'hpRange': [-9, -1], 'nonlethalExceedsHp': True})
    return result
