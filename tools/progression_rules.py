"""Typed transcriptions for sheet creation and advancement; not a rules evaluator."""


def progression_rules(lines, table, copper):
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
        return {class_id: {'roll': roll.removesuffix(' gp'), 'averageCp': copper(average),
                           'source': {'file': core, 'line': line}}
                for line, (class_id, roll, average) in table(core, '7. Table: Starting Wealth at 1st Level (starting-wealth-by-class)')}

    return [
        at_creation('ability-score-generation', '1. Ability Score Generation', 'ability-generation',
                    methodsById={
                        'point-buy': {'budget': 28, 'baseScore': 8,
                                      'costByScore': dict(zip(map(str, range(8, 19)), (0, 1, 2, 3, 4, 5, 6, 8, 10, 13, 16)))},
                        'elite-array': {'scores': [15, 14, 13, 12, 10, 8]},
                        'roll': {'diceCount': 4, 'dieSides': 6, 'dropLowest': 1, 'repeat': 6},
                    }, minimumIntelligenceAfterRacialAdjustment=3),
        at_creation('starting-wealth-by-class', '7. Table: Starting Wealth', 'starting-wealth',
                    characterLevel=1, byClassId=wealth()),
        rule('character-advancement', xp, 'Advancing a Level:', 'experience-track',
             thresholds=[{'characterLevel': level, 'minimumXp': 500 * level * (level - 1)} for level in range(1, 21)],
             thresholdSource={'file': core, 'headingOrLead': '2. Character Advancement'},
             maxLevelsPerAdventureAward=1, surplusPolicy='cap-at-one-xp-below-following-level',
             trainingAdjustments='dm-adjudication', beyondTable='use-separate-epic-progression'),
        rule('level-up-sequence', xp, 'LEVEL ADVANCEMENT', 'ordered-steps',
             steps=['choose-class', 'base-attack-bonus', 'base-saves', 'ability-increase', 'hit-points',
                    'skill-points', 'feats', 'spells', 'class-features']),
        rule('ability-increases-and-feats', xp, '4. Ability Score:', 'character-level-benefits',
             abilityIncreaseLevels=[4, 8, 12, 16, 20], abilityIncreaseAmount=1,
             generalFeatLevels=[1, 3, 6, 9, 12, 15, 18], featPrerequisitesRequired=True,
             maxStructuredCharacterLevel=20),
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
             prestigeExemptionSource={'file': core, 'headingOrLead': 'MULTICLASSING RULES'}),
    ]
