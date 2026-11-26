"""Project linked companion actors without mutating their base stat blocks."""
import re
from fractions import Fraction


FIELDS = {'Hit Dice', 'Initiative', 'Speed', 'Armor Class', 'Base Attack / Grapple',
          'Attack', 'Full Attack', 'STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA', 'Fort / Ref / Will',
          'Challenge Rating', 'Alignment', 'Organization', 'Treasure', 'Environment',
          'Level Adjustment', 'Special Abilities', 'Skills', 'Feats', 'Description', 'Combat'}


def stat_block(text):
    fields = {}
    current = None
    for line in text.splitlines():
        if line.strip() in FIELDS:
            current = line.strip()
            fields[current] = []
        elif current is not None:
            fields[current].append(line)
    return {key: '\n'.join(value).strip() for key, value in fields.items()}


def ability_mod(score):
    return (score - 10) // 2 if score is not None else 0


def project_companion(core, history, link, *, master_max_hp=None, master_skill_ranks=None):
    """Build a display-ready source block with a separate layer of current numbers."""
    catalog = core['companions']
    key = link['definitionId']
    improved = catalog['improvedFamiliarOptionsById'].get(key)
    base = improved or catalog['creaturesById'][key]
    role = 'familiar' if improved else base['role']
    if role not in ('familiar', 'animal-companion'):
        raise ValueError('Only familiar or animal-companion definitions can advance')
    familiar = role == 'familiar'
    class_id = 'wizard' if familiar else 'druid'
    master_level = history.get('classLevels', {}).get(class_id, 0) + link.get('otherEligibleClassLevels', 0)
    adjustment = base.get('effectiveLevelAdjustment', 0)
    effective = master_level + adjustment
    if effective < 1 or master_level < base.get('minimumMasterLevel', 1):
        raise ValueError(f'{base["name"]} does not meet the master level requirement')
    rows = catalog['familiarAdvancement' if familiar else 'animalCompanionAdvancement']
    row = next(r for r in rows if r['minEffectiveLevel'] <= min(effective, 20) <= r['maxEffectiveLevel'])
    fields = stat_block(base['statBlockText'])
    review = []
    scores = {stat.lower(): int(fields[stat]) if fields.get(stat, '').isdigit() else None
              for stat in ('STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA')}
    old = {stat: ability_mod(score) for stat, score in scores.items()}
    armor = row['naturalArmorAdjustment']
    special = [part for r in rows if r['minEffectiveLevel'] <= effective
               for part in r['special'].split(', ') if part.strip() not in ('', '—', '-')]
    combat = history['classBaseCombat']
    hd_match = re.match(r'([0-9/¼½⅓⅔¾]+)\s*d\d+', fields.get('Hit Dice', ''), re.I)
    hd = Fraction(hd_match[1].translate(str.maketrans({'¼': '1/4', '½': '1/2', '⅓': '1/3', '⅔': '2/3', '¾': '3/4'}))) if hd_match else None
    hp_match = re.search(r'\((\d+)\s*hp\)', fields.get('Hit Dice', ''), re.I)
    base_hp = int(hp_match[1]) if hp_match else None
    result = dict(instanceId=link['instanceId'], definitionId=key, name=base['name'], role=role,
                  effectiveMasterLevel=effective, statBlockText=base['statBlockText'], baseFields=fields,
                  source=base.get('statBlockSource', base['source']), advancementSource=row['source'],
                  excludedAbilityIds=base.get('excludedAbilityIds', []), specialAbilities=special, needsReview=review)
    if familiar:
        epic = max(0, (effective - 19) // 2) if effective > 20 else 0
        armor += epic
        scores['int'] = row['intelligence'] + epic
        if improved:
            special[:] = [name for name in special if name != 'Speak with animals of its kind']
        result.update(maxHp=None if master_max_hp is None else master_max_hp // 2,
                      actualHitDice=str(hd) if hd is not None else None,
                      effectiveHitDice=str(max(hd, history['characterLevel'])) if hd is not None else None,
                      baseAttackBonus=combat['bab'] + (history.get('epicCharacterBonuses') or {}).get('attackBonus', 0),
                      spellResistance=effective + 5 if effective >= 11 else None,
                      familiarSpellChoices=1 + (effective - 21) // 10 if effective >= 21 else 0,
                      creatureType='magical beast' if re.search(r'^\w+ Animal\b', base['statBlockText'], re.M)
                      else 'retain base type')
        if master_max_hp is None:
            review.append('Supply master maximum HP excluding temporary HP.')
        if master_skill_ranks is not None:
            result['masterSkillRanks'] = dict(master_skill_ranks)
        review.append('Compare master and familiar skill ranks; listed base skills are not rank allocations.')
        if improved:
            review.append('Confirm the improved familiar’s base save bonuses when they differ from the standard familiar defaults.')
        base_saves = link.get('baseSaveBonuses', dict(fort=2, ref=2, will=0))
        result['saves'] = {save: max(base_saves[save], combat[save]) + ability_mod(scores[ability])
                           for save, ability in (('fort', 'con'), ('ref', 'dex'), ('will', 'wis'))}
    else:
        epic = max(0, (effective - 20) // 3)
        bonus_hd = row['bonusHitDice'] + 2 * epic
        for stat in ('str', 'dex'):
            if scores[stat] is not None:
                scores[stat] += row['strengthDexterityAdjustment'] + epic
        total_hd = hd + bonus_hd if hd is not None else None
        hp_rolls = link.get('bonusHitDieRolls', ())
        if any(type(roll) is not int or not 1 <= roll <= 8 for roll in hp_rolls):
            raise ValueError('Companion bonus Hit Die rolls must be integers from 1 to 8')
        if bonus_hd > len(hp_rolls):
            review.append('Record remaining bonus d8 rolls and choose skill ranks and feats for the added Hit Dice.')
        result.update(actualHitDice=str(total_hd) if total_hd is not None else None,
                      bonusHitDice=bonus_hd, bonusTricks=row['bonusTricks'] + epic,
                      maxHp=base_hp + sum(max(1, n + old['con']) for n in hp_rolls[:bonus_hd])
                      if base_hp is not None and len(hp_rolls) >= bonus_hd else None)
        if total_hd is not None:
            n = int(total_hd)
            result['baseAttackBonus'] = 3 * n // 4
            result['saves'] = dict(fort=2 + n // 2 + old['con'], ref=2 + n // 2 + ability_mod(scores['dex']),
                                   will=n // 3 + old['wis'])
        if bonus_hd and len(hp_rolls) >= bonus_hd:
            review.append('Choose any new skill ranks and feats from bonus Hit Dice.')
        if 'Multiattack' in special:
            review.append('Apply Multiattack if eligible; otherwise confirm the second primary attack at −5.')
    dex_delta = ability_mod(scores['dex']) - old['dex']
    ac = re.fullmatch(r'(\d+),\s*touch\s*(\d+),\s*flat-footed\s*(\d+)', fields.get('Armor Class', ''), re.I)
    if ac:
        normal, touch, flat = map(int, ac.groups())
        result['armorClass'] = dict(normal=normal + armor + dex_delta, touch=touch + dex_delta,
                                   flatFooted=flat + armor + min(0, ability_mod(scores['dex'])) - min(0, old['dex']))
    else:
        review.append('Apply the natural armor and Dexterity adjustments to the source AC.')
    if re.fullmatch(r'[+−–-]?\d+', fields.get('Initiative', '')):
        result['initiative'] = int(fields['Initiative'].replace('−', '-').replace('–', '-')) + dex_delta
    bab_grapple = re.fullmatch(r'([+−–-]?\d+)\s*/\s*([+−–-]?\d+)', fields.get('Base Attack / Grapple', ''))
    if bab_grapple and 'baseAttackBonus' in result:
        base_bab, grapple = (int(value.replace('−', '-').replace('–', '-')) for value in bab_grapple.groups())
        bab_delta = result['baseAttackBonus'] - base_bab
        strength_delta = ability_mod(scores['str']) - old['str']
        result['grappleBonus'] = grapple + bab_delta + strength_delta
        finesse = 'weapon finesse' in fields.get('Feats', '').casefold()

        def update_attack(match):
            raw, mode = match.groups()
            value = int(raw.replace('−', '-').replace('–', '-'))
            if mode.lower() == 'ranged':
                adjustment = dex_delta
            elif familiar:
                adjustment = max(0, old['dex'] - old['str']) if not finesse else 0
            else:
                adjustment = dex_delta if finesse else strength_delta
            return f'{value + bab_delta + adjustment:+d} {mode}'

        result['attackRoutines'] = {field: re.sub(r'([+−–-]\d+)\s+(melee|ranged)\b', update_attack,
                                                  fields[field], flags=re.I)
                                    for field in ('Attack', 'Full Attack') if field in fields}
    result.update(abilityScores=scores, naturalArmorAdjustment=armor)
    review.append('Confirm damage adjustments, skill choices, and special abilities at the table; source attack damage dice and bonuses are retained.')
    return result


def familiar_loss_catalog(lines, source):
    result = {}
    for class_id in ('wizard', 'sorcerer'):
        file = class_id.upper() + '.txt'
        line, text = next((i, row) for i, row in enumerate(lines(file), 1)
                          if row.startswith('If the familiar dies or is dismissed'))
        result[class_id] = dict(source=source(file, line=line), description=text,
                                triggers=['death', 'dismissal'], fortitudeDc=15,
                                xpPerClassLevelOnFailure=200, xpPerClassLevelOnSuccess=100,
                                minimumXp=0, replacementWait={'years': 1, 'days': 1},
                                raisedFamiliarLosesLevelOrConstitution=False)
    return result


def resolve_familiar_loss(core, *, class_id, class_level, current_xp, fortitude_save_total, event):
    """Calculate XP loss after the table confirms the loss and adjudicates the save."""
    rule = core['companions']['familiarLossByClassId'][class_id]
    if event not in rule['triggers']:
        raise ValueError('Expected familiar death or dismissal')
    if (type(class_level) is not int or class_level < 1 or type(current_xp) is not int
            or current_xp < 0 or type(fortitude_save_total) is not int):
        raise ValueError('Supply a positive class level, nonnegative XP and an integer save total')
    passed = fortitude_save_total >= rule['fortitudeDc']
    rate = rule['xpPerClassLevelOnSuccess' if passed else 'xpPerClassLevelOnFailure']
    xp_after = max(rule['minimumXp'], current_xp - rate * class_level)
    return dict(event=event, saveSucceeded=passed, xpLost=current_xp - xp_after, xpAfter=xp_after,
                replacementWait=dict(rule['replacementWait']), description=rule['description'])
