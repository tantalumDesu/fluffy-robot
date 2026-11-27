"""Project linked companion actors without mutating their base stat blocks."""
import re

if __package__:
    from .natural_weapons import creature_roster, project as project_natural
else:
    from natural_weapons import creature_roster, project as project_natural
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


def project_paladin_mount(core, history, link, base, sheet, *, after_level_loss=False):
    """Apply the Paladin acquisition package to a sourced ordinary war mount."""
    level = history['classLevels'].get('paladin', 0)
    if level < 5:
        if not after_level_loss:
            raise ValueError('Special mount acquisition requires Paladin 5')
        return dict(sheet, advancementInactive=True, needsReview=['Confirm the mount relationship after level loss.'])
    if base['id'] not in ('war-mounts:warhorse-heavy', 'war-mounts:warpony') and not link.get('dmConfirmedSpecialMount'):
        raise ValueError('Confirm this nonstandard Paladin mount at the table')
    catalog = core['companions']
    rows = catalog['paladinMountAdvancement']
    row = next(r for r in rows if r['minEffectiveLevel'] <= min(level, 20) <= r['maxEffectiveLevel'])
    epic = catalog['paladinMountEpic']
    steps = max(0, (level - epic['afterLevel']) // epic['interval'])
    def grant(key):
        return row[key] + steps * epic[key]
    bonus_hd, armor = grant('bonusHitDice'), grant('naturalArmorAdjustment')
    base_hd = int(re.match(r'\d+', base['hitDiceText'])[0])
    hd = base_hd + bonus_hd
    rolls = link.get('bonusHitDieRolls', ())
    if any(type(roll) is not int or not 1 <= roll <= 8 for roll in rolls):
        raise ValueError('Special mount bonus Hit Die rolls must be integers from 1 to 8')
    scores = dict(base['abilityScores'], str=base['abilityScores']['str'] + grant('strengthAdjustment'),
                  int=grant('intelligence'))
    strength_delta = ability_mod(scores['str']) - ability_mod(base['abilityScores']['str'])
    bab = hd * 3 // 4
    bab_delta = bab - base['baseAttackBonus']
    combat = history['classBaseCombat']
    saves = {}
    for save, stat in (('fort', 'con'), ('ref', 'dex'), ('will', 'wis')):
        good = save != 'will'
        base_progression = 2 + base_hd // 2 if good else base_hd // 3
        progression = 2 + hd // 2 if good else hd // 3
        ability = ability_mod(scores[stat])
        misc = base['saves'][save] - base_progression - ability
        saves[save] = max(progression, combat[save]) + ability + misc
    natural = []
    for attack in base['naturalWeapons']:
        entry = dict(attack, attackBonus=attack['attackBonus'] + bab_delta + strength_delta)
        if attack['naturalAttackId'] == 'bite':
            delta = ability_mod(scores['str']) // 2 - ability_mod(base['abilityScores']['str']) // 2
        else:
            delta = strength_delta
        if match := re.fullmatch(r'(\d+d\d+)([+-]\d+)?', attack['damageText']):
            modifier = int(match[2] or 0) + delta
            entry['damageText'] = match[1] + (f'{modifier:+d}' if modifier else '')
        natural.append(entry)
    from .creature_size import carrying_limits
    aquatic = base['id'] == 'alternative-animal-companions:shark-large'
    capacity = None if aquatic else carrying_limits(core, scores['str'], base['sizeId'], 'quadruped')
    speed_increase = 10 if level >= 8 else 0
    movement = {'swimSpeedFt': base['swimSpeedFt'] + speed_increase} if aquatic else {
        'landSpeedFt': sheet['landSpeedFt'] + speed_increase}
    return dict(sheet, role='special-mount', creatureType='magical beast', acquiredByClassId='paladin',
                effectiveMasterLevel=level, abilityScores=scores, actualHitDice=hd, bonusHitDice=bonus_hd,
                maxHp=sheet['maxHp'] + sum(max(1, n + ability_mod(scores['con'])) for n in rolls[:bonus_hd])
                if len(rolls) >= bonus_hd else None,
                carryingCapacity={key: float(value) for key, value in capacity.items()} if capacity is not None else None,
                armorClass=dict(normal=sheet['armorClass']['normal'] + armor, touch=sheet['armorClass']['touch'],
                                flatFooted=sheet['armorClass']['flatFooted'] + armor),
                naturalArmorAdjustment=armor, baseAttackBonus=bab,
                grappleBonus=base['grappleBonus'] + bab_delta + strength_delta, saves=saves,
                **movement,
                naturalWeapons=project_natural(core, natural, link.get('featChoices', ())),
                spellResistance=level + 5 if level >= 15 else None,
                specialAbilities=[ability for tier in rows if tier['minEffectiveLevel'] <= level
                                  for ability in tier['special'].split(', ')], advancementSource=row['source'],
                needsReview=['Record bonus-HD skill and feat choices and adjudicate the mount’s special abilities.']
                + (['Record remaining bonus d8 HP rolls.'] if len(rolls) < bonus_hd else []))


def project_creature(core, history, link, **context):
    """Build one creature sheet from its acquisition definition, not its current job."""
    from .mounted import acquisition_training, training_seed

    catalog = core['companions']
    key = link['definitionId']
    base = catalog['creaturesById'].get(key) or catalog['improvedFamiliarOptionsById'][key]
    role = base.get('role', 'familiar')
    paladin = link.get('acquiredByClassId') == 'paladin'
    if paladin and not (key.startswith('war-mounts:') or key in (
            'animal-companions:dog-riding', 'alternative-animal-companions:shark-large')):
        raise ValueError('This alternative Paladin mount needs a typed special-mount profile')
    ordinary = paladin or role in ('pack-animal', 'ordinary-mount') or link.get('acquisition') == 'ordinary'
    if link.get('acquisition') == 'ordinary' and link.get('acquiredByClassId'):
        raise ValueError('An ordinary acquisition cannot also have a class package')
    if not ordinary:
        sheet = project_companion(core, history, link, **context)
    else:
        text = base.get('statBlockText') or base['raw']
        fields = stat_block(text)
        armor = re.match(r'(\d+), touch (\d+), flat-footed (\d+)', fields.get('Armor Class', ''))
        sheet = {field: base[field] for field in ('abilityScores', 'saves', 'landSpeedFt', 'initiative',
                                                  'baseAttackBonus', 'grappleBonus', 'naturalWeapons', 'flight') if field in base}
        hd_text = fields.get('Hit Dice', '')
        hp = re.search(r'\((\d+)\s*hp\)', hd_text, re.I)
        speed = re.match(r'(?:Land )?(\d+) ft', fields.get('Speed', ''), re.I)
        if speed:
            sheet.setdefault('landSpeedFt', int(speed[1]))
        if 'saves' not in sheet and (saves := re.fullmatch(r'([+-]?\d+)\s*/\s*([+-]?\d+)\s*/\s*([+-]?\d+)', fields.get('Fort / Ref / Will', ''))):
            sheet['saves'] = dict(zip(('fort', 'ref', 'will'), map(int, saves.groups())))
        if combat := re.fullmatch(r'([+-]?\d+)\s*/\s*([+-]?\d+)', fields.get('Base Attack / Grapple', '')):
            sheet.update(baseAttackBonus=int(combat[1]), grappleBonus=int(combat[2]))
        sheet.update(hitDiceText=hd_text, featNames=base.get('featNames', []),
                     instanceId=link['instanceId'], definitionId=key, name=base['name'],
                     role='pack-animal' if role == 'pack-animal' else 'ordinary-mount',
                     maxHp=base.get('hitPoints', int(hp[1]) if hp else None),
                     carryingCapacity=base.get('carryingCapacity'), baseFields=fields,
                     statBlockText=text, source=base.get('statBlockSource', base['source']))
        if armor:
            sheet['armorClass'] = dict(zip(('normal', 'touch', 'flatFooted'), map(int, armor.groups())))
    if paladin:
        sheet = project_paladin_mount(core, history, link, dict(base, **{field: sheet[field] for field in
                                       ('hitDiceText', 'maxHp', 'baseAttackBonus', 'grappleBonus', 'saves')}), sheet,
                                      after_level_loss=context.get('after_level_loss', False))
    if 'pounceNaturalWeapons' in base and ordinary:
        if sheet['role'] == 'ordinary-mount':
            sheet['naturalWeapons'] = project_natural(core, base['naturalWeapons'], link.get('featChoices', ()))
        pounce = project_natural(core, base['pounceNaturalWeapons'], link.get('featChoices', ()))
        sheet['pounceNaturalWeapons'] = pounce
        if link.get('confirmedPounce'):
            sheet['naturalWeapons'] = [*sheet['naturalWeapons'], *pounce]
    for field in ('climbSpeedFt', 'swimSpeedFt'):
        if field in base:
            sheet.setdefault(field, base[field])
    sheet['training'] = link['training'] if 'training' in link else acquisition_training(
        core, base, purchase_item_id=link.get('purchaseItemId'))
    if sheet['role'] == 'special-mount':
        seed = training_seed(core['skills']['animalTraining'], catalog['paladinMountInitialTrainingPurposeId'])
        existing = sheet['training']
        learned = list(dict.fromkeys([*seed['learnedTrickIds'], *existing.get('learnedTrickIds', ())]))
        if 'attack-all' in learned and 'attack' in learned:
            learned.remove('attack')
        sheet['training'] = {**seed, **existing}
        sheet['training'].update(purposeId=seed['purposeId'], learnedTrickIds=learned)
    sheet['sizeId'] = base['sizeId']
    sheet['mountProfile'] = base.get('mountProfile', {'suitability': 'needs-review'})
    if 'trainingContext' in link:
        from .animal_training import training_choices

        training_context = dict(link['trainingContext'])
        subject = dict(base, abilityScores=sheet.get('abilityScores', base['abilityScores']))
        if 'creatureType' in sheet:
            subject['creatureType'] = sheet['creatureType']
        sheet['trainingChoices'] = training_choices(core['skills']['animalTraining'], subject,
                                                   sheet['training'], **training_context)
    return sheet


def project_companion(core, history, link, *, master_max_hp=None, master_skill_ranks=None, after_level_loss=False):
    """Build a display-ready source block with a separate layer of current numbers."""
    catalog = core['companions']
    key = link['definitionId']
    improved = catalog['improvedFamiliarOptionsById'].get(key)
    base = improved or catalog['creaturesById'][key]
    role = 'familiar' if improved else base['role']
    if role not in ('familiar', 'animal-companion'):
        raise ValueError('Only familiar or animal-companion definitions can advance')
    familiar = role == 'familiar'
    class_id = link.get('acquiredByClassId', 'wizard' if familiar else 'druid')
    if class_id not in (('wizard', 'sorcerer') if familiar else ('druid', 'ranger')):
        raise ValueError('Invalid acquisition class for this advancement package')
    levels = history.get('classLevels', {})
    raw_level = levels.get(class_id, 0)
    master_level = (raw_level // 2 if raw_level >= 4 else 0) if class_id == 'ranger' else raw_level
    master_level += link.get('otherEligibleClassLevels', 0)
    adjustment = base.get('effectiveLevelAdjustment', 0)
    effective = master_level + adjustment
    if effective < 1 or master_level < base.get('minimumMasterLevel', 1):
        if not after_level_loss:
            raise ValueError(f'{base["name"]} does not meet the master level requirement')
        if effective < 1:
            return dict(instanceId=link['instanceId'], definitionId=key, name=base['name'], role=role,
                        effectiveMasterLevel=0, advancementInactive=True, statBlockText=base['statBlockText'],
                        baseFields=stat_block(base['statBlockText']),
                        needsReview=['Confirm the companion relationship after losing the qualifying master level.'])
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
    result = dict(instanceId=link['instanceId'], definitionId=key, name=base['name'], role=role, acquiredByClassId=class_id,
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
    routine = result.get('attackRoutines', {}).get('Full Attack')
    roster = creature_roster('Full Attack\n' + routine) if routine else base.get('naturalWeapons', ())
    pounce = base.get('pounceNaturalWeapons', ())
    if pounce and 'Full Attack' in fields and 'baseAttackBonus' in result and bab_grapple:
        pounce = [dict(entry, attackBonus=int(update_attack(re.fullmatch(
            r'([+−–-]\d+) (melee)', f"{entry['attackBonus']:+d} melee")).split()[0])) for entry in pounce]
    result['pounceNaturalWeapons'] = project_natural(core, pounce, link.get('featChoices', ()))
    if link.get('confirmedPounce'):
        roster = [*roster, *pounce]
    result['naturalWeapons'] = project_natural(core, roster, link.get('featChoices', ()))
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
