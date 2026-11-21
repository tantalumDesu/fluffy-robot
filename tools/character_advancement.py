"""Evaluate character-level XP and grants without advancing any class."""
from math import isqrt


def _integer(value, minimum, label):
    if type(value) is not int or value < minimum:
        raise ValueError(f'{label} must be an integer >= {minimum}')
    return value


def minimum_xp(level, track):
    formula = track['thresholdFormula']
    level = _integer(level, formula['minimumCharacterLevel'], 'Character level')
    return formula['multiplier'] * level * (level - 1)


def level_for_xp(xp, track):
    """Return the highest threshold met, before any single-award cap."""
    xp = _integer(xp, 0, 'XP')
    units = xp // track['thresholdFormula']['multiplier']
    return (1 + isqrt(1 + 4 * units)) // 2


def character_level_grants(level, benefits):
    """Return new choices earned at this level, excluding class/racial bonuses."""
    level = _integer(level, 1, 'Character level')
    feats = benefits['generalFeats']
    abilities = benefits['abilityIncreases']
    return {
        'generalFeatChoices': feats['atFirstLevel'] if level == 1 else
                              feats['amount'] if level % feats['everyLevels'] == 0 else 0,
        'abilityScoreIncrease': abilities['amount'] if level % abilities['everyLevels'] == 0 else 0,
    }


def apply_xp_award(current_level, xp, award, track, benefits):
    """Resolve an already adjusted award against the applied character level."""
    xp = _integer(xp, 0, 'XP')
    award = _integer(award, 0, 'XP award')
    if level_for_xp(xp, track) != current_level or type(current_level) is not int:
        raise ValueError('Current XP and character level must agree before applying an award')
    raw_total = xp + award
    max_level = current_level + track['maxLevelsPerAdventureAward']
    retained = min(raw_total, minimum_xp(max_level + 1, track) - 1)
    attained = level_for_xp(retained, track)
    return dict(xp=retained, characterLevel=attained, discardedXp=raw_total - retained,
                grants=[dict(characterLevel=level, **character_level_grants(level, benefits))
                        for level in range(current_level + 1, attained + 1)])
