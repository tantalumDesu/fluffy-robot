"""Typed transcriptions for sheet creation and advancement; not a rules evaluator."""


def progression_rules(lines, copper):
    xp = 'EXPERIENCE AND LEVELS.txt'
    mc = 'MULTICLASS CHARACTERS.txt'
    core = 'RULES.txt'

    def rule(id_, file, anchor, kind, **parameters):
        line = next(i for i, text in enumerate(lines(file), 1) if text.startswith(anchor))
        return dict(id=id_, name=id_.replace('-', ' ').title(), category='progression',
                    status='structured', source={'file': file, 'line': line, 'headingOrLead': anchor},
                    mechanic={'kind': kind, **parameters})

    def at_creation(id_, anchor, kind, **parameters):
        return rule(id_, core, anchor, kind, **parameters)

    def wealth():
        records = {}
        for class_id in ('barbarian', 'bard', 'cleric', 'druid', 'fighter', 'monk',
                         'paladin', 'ranger', 'rogue', 'sorcerer', 'wizard'):
            file = class_id.upper() + '.txt'
            line, text = next((i, text) for i, text in enumerate(lines(file), 1)
                              if text.startswith('Starting Wealth: '))
            roll, average = text.removeprefix('Starting Wealth: ').split(' (average ')
            avg_cp = copper(average.split(')', 1)[0])
            if not roll.endswith(' gp') or avg_cp is None:
                raise ValueError(f'Invalid starting wealth in {file}')
            records[class_id] = {'roll': roll.removesuffix(' gp'), 'averageCp': avg_cp,
                                 'source': {'file': file, 'line': line}}
        return records

    return [
        at_creation('ability-score-generation', '1. Ability Score Generation', 'ability-generation',
                    methodsById={
                        'point-buy': {'budget': 28, 'baseScore': 8,
                                      'costByScore': dict(zip(map(str, range(8, 19)), (0, 1, 2, 3, 4, 5, 6, 8, 10, 13, 16)))},
                        'elite-array': {'scores': [15, 14, 13, 12, 10, 8]},
                        'roll': {'diceCount': 4, 'dieSides': 6, 'dropLowest': 1, 'repeat': 6},
                    }, minimumIntelligenceAfterRacialAdjustment=3),
        at_creation('starting-wealth-by-class', '7. Starting Wealth', 'starting-wealth',
                    characterLevel=1, byClassId=wealth()),
        rule('character-advancement', xp, 'Advancing a Level:', 'experience-track',
             thresholdFormula={'kind': 'triangular-xp', 'multiplier': 500, 'minimumCharacterLevel': 1},
             levelBasis='character-level',
             thresholdSource={'file': core, 'headingOrLead': '2. Character Advancement'},
             maxLevelsPerAdventureAward=1, surplusPolicy='cap-at-one-xp-below-following-level',
             trainingAdjustments='dm-adjudication'),
        rule('level-up-sequence', xp, 'LEVEL ADVANCEMENT', 'ordered-steps',
             steps=['choose-class', 'base-attack-bonus', 'base-saves', 'ability-increase', 'hit-points',
                    'skill-points', 'feats', 'spells', 'class-features']),
        rule('ability-increases-and-feats', xp, '4. Ability Score:', 'character-level-benefits',
             levelBasis='character-level',
             abilityIncreases={'everyLevels': 4, 'amount': 1},
             generalFeats={'atFirstLevel': 1, 'everyLevels': 3, 'amount': 1},
             featPrerequisitesRequired=True),
        rule('hit-points', xp, '5. Hit Points:', 'hit-points-per-level',
             firstCharacterLevelDie='maximum', laterCharacterLevelDie='roll',
             dieFrom='class-advanced', minimumGainAfterConModifier=1,
             conModifierIncreaseAppliesToPreviousLevels=True,
             firstLevelSource={'file': core, 'headingOrLead': '3. Hit Points'}),
        rule('skill-points-and-ranks', xp, '6. Skill Points:', 'skill-purchase',
             pointBudgetClass='class-advanced', minPointsBeforeFirstLevelMultiplier=1,
             creationSource={'file': core, 'headingOrLead': '4. Skill Points & Starting Languages'},
             firstCharacterLevelMultiplier=4, racialSkillPointBonuses='apply-after-multiplier', classRanksPerPoint=1, crossClassRanksPerPoint=0.5,
             purchaseClassSkillScope='class-advanced', capClassSkillScope='any-class-taken',
             classRankCapLevelOffset=3, crossClassCapMultiplier=0.5, roundRanks=False,
             intelligenceForBudget='current-permanent', recalculatePriorPoints=False,
             startingBonusLanguages={'minimum': 0, 'countFrom': 'intelligence-modifier', 'choicesFrom': 'race'}),
        rule('multiclassing-progression', mc, 'CLASS AND LEVEL FEATURES', 'class-level-aggregation',
             levelSelection='one-class-per-level', startingBenefits='first-character-level-only',
             levelHistory={'persist': 'ordered-class-ids', 'classLevel': 'count-of-selected-class-through-entry',
                           'characterLevel': 'racial-hit-dice-plus-total-class-levels',
                           'effectiveCharacterLevel': 'character-level-plus-level-adjustment',
                           'progressionRow': 'selected-class-at-current-class-level',
                           'epicExtensions': 'continue-base-class-id'},
             baseAttackAndSaves='sum-final-progression-row-per-class', iterativeAttackThresholds=[6, 11, 16],
             iterativeAttackBonusStep=-5, spellcasting='track-by-casting-class',
             prestigeCasting='use-class-specific-advancement',
             classFeatures='retain-all-applicable-features-and-restrictions',
             laterBarbarianLevelGrantsIlliteracy=False, epicUsesSeparateRules=True),
        rule('multiclass-feature-stacking', mc, 'In the special case of turning undead', 'feature-stacking',
             turning={'classIds': ['cleric', 'paladin'], 'minimumPaladinLevel': 4, 'paladinLevelAdjustment': -3},
             uncannyDodge={'classIds': ['barbarian', 'rogue'], 'upgradeOnSecondGrant': 'improved-uncanny-dodge',
                           'sumLevelsForFlanking': True},
             familiar={'classIds': ['sorcerer', 'wizard'], 'effectiveLevel': 'sum-class-levels'}),
        rule('multiclass-xp-penalty', mc, 'XP FOR MULTICLASS CHARACTERS', 'xp-award-penalty',
             requiredOptionId='multiclass-xp-penalty', minimumLevelGap=2, percentPerClass=20,
             compareWith='highest-non-exempt-class', excludeFavoredClass=True, excludePrestigeClasses=True,
             favoredClassFrom='race', highestClassFavoredRaceIds=['human', 'half-elf'],
             prestigeExemptionSource={'file': mc, 'headingOrLead': 'Optional XP Penalty:'}),
    ]


def spell_swap_rules(lines, classes):
    """Keep explicit examples separate from schedules derived from 'and so on'."""
    by_id = {record['id']: record for record in classes}
    for class_id, file, stated, interval in (
        ('bard', 'BARD.txt', [5, 8, 11], 3),
        ('sorcerer', 'SORCERER.txt', [4, 6, 8], 2),
        ('assassin', 'Prestige Class ASSASSIN.txt', [6, 8, 10], 2),
    ):
        line, prose = next((i, text) for i, text in enumerate(lines(file), 1)
                           if 'can choose to learn a new spell in place' in text)
        maximum = max(row['level'] for row in by_id[class_id]['progression'])
        derived = (list(range(stated[-1] + interval, maximum + 1, interval))
                   if 'and so on' in prose else [])
        parameters = dict(statedEligibleLevels=stated, derivedEligibleLevels=derived,
                          swapsPerEligibleLevel=1, newSpellLevel='same-as-replaced-spell',
                          minLevelsBelowHighestCastable=2, timing='when-gaining-new-spells-known-for-the-level')
        if derived:
            parameters['derivedFrom'] = 'and so on; limited to the available class progression'
        yield dict(id=class_id + '-spell-swap', name=by_id[class_id]['name'] + ' Spell Swap',
                   category='class-mechanic', status='structured', appliesTo={'classIds': [class_id]},
                   source={'file': file, 'line': line, 'excerpt': prose},
                   mechanic={'type': 'scheduled-spell-swap', 'parameters': parameters})


def continuity_rules(lines):
    for class_id in ('monk', 'paladin'):
        file = class_id.upper() + '.txt'
        line, text = next((i, text) for i, text in enumerate(lines(file), 1)
                          if 'may never again raise her ' + class_id + ' level' in text)
        yield dict(id=class_id + '-continuous-levels', name=class_id.title() + ' Level Continuity',
                   category='class-mechanic', status='structured',
                   source={'file': file, 'line': line, 'excerpt': text}, appliesTo={'classIds': [class_id]},
                   mechanic={'type': 'level-sequence-constraint',
                             'parameters': {'classId': class_id, 'constraint': 'cannot-return-after-advancing-another-class'}})
