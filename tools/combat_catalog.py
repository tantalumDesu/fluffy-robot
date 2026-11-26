"""Source-backed shared rules; typed facts are not automatic effect grants."""
import re


def combat_rules(lines, source):
    index = {m[1]: m[2] for row in lines('RULES.txt')
             if (m := re.match(r'- `([^`]+)`: (.*)', row))}
    records = []

    def add(key, file, start, end=None, **facts):
        file += '.txt'
        rows = lines(file)
        def locate(prefix):
            return next(i for i, row in enumerate(rows) if row.startswith(prefix))
        first = locate(start)
        last = locate(end) if end else len(rows)
        if first >= last:
            raise ValueError(f'Invalid source span: {key}')
        records.append(dict(id=key, name=index[key].split(' (')[0].rstrip(';'), category='shared-rule',
                            status='structured' if facts else 'reference',
                            source=source(file, line=first + 1, endLine=last),
                            summary='\n'.join(rows[first:last]).strip(),
                            mechanic=facts, automaticApplication=False))

    f = 'INITIATIVE'
    add('initiative-order', f, 'Initiative Checks:', 'Flat-Footed:',
        formula='1d20 + initiativeModifier', order=['result-desc', 'modifier-desc', 'reroll-ties'])
    add('flat-footed', f, 'Flat-Footed:', 'Inaction:',
        conditionId='flat-footed', until='first-regular-turn')
    add('surprise-round', f, 'SURPRISE', actions=['standard', 'free'], requiresMixedAwareness=True)
    f = 'ATTACKS OF OPPORTUNITY'
    add('threatened-squares-and-reach', f, 'Threatened Squares:', 'Provoking an Attack')
    add('attacks-of-opportunity', f, 'Provoking an Attack', 'Combat Reflexes and', basePerRound=1)
    add('combat-reflexes-aoo', f, 'Combat Reflexes and', featId='combat-reflexes')
    f = 'SPECIAL INITIATIVE ACTIONS'
    add('delay-action', f, 'DELAY', 'READY')
    add('ready-action', f, 'READY', 'Distracting Spellcasters:', action='standard',
        allowedReadiedActions=['standard', 'move', 'free'])
    add('distract-spellcaster-readied', f, 'Distracting Spellcasters:', 'Readying to Counterspell:')
    add('counterspell-readied', f, 'Readying to Counterspell:', 'Readying a Weapon',
        identifySkillId='spellcraft', identifyDc='15 + spellLevel')
    add('ready-weapon-against-charge', f, 'Readying a Weapon', damageMultiplier=2)
    f = 'COMBAT STATISTICS'
    add('attack-roll-resolution', f, 'ATTACK ROLL', 'ATTACK BONUS', dieSides=20,
        target='armor-class', naturalOne='miss', naturalTwenty='hit-and-threat')
    add('attack-bonus-formulas', f, 'ATTACK BONUS', 'DAMAGE', formulas={
        'melee': ['baseAttackBonus', 'strengthModifier', 'sizeModifier', 'otherModifiers'],
        'ranged': ['baseAttackBonus', 'dexterityModifier', 'sizeModifier', 'rangePenalty', 'otherModifiers']})
    add('damage-rules', f, 'DAMAGE', 'ARMOR CLASS')
    add('armor-class-formula', f, 'ARMOR CLASS', 'HIT POINTS', base=10,
        terms=['armor', 'shield', 'cappedDexterity', 'size', 'naturalArmor', 'dodge', 'deflection', 'otherModifiers'],
        touchExcludes=['armor', 'shield', 'naturalArmor'])
    add('speed-and-movement-rates', f, 'SPEED', 'SAVING THROWS', doubleMove=2, run=4, heavyArmorRun=3)
    add('saving-throw-formulas', f, 'SAVING THROWS', dieSides=20,
        abilityBySave={'fort': 'con', 'ref': 'dex', 'will': 'wis'}, naturalOne='fail', naturalTwenty='succeed')
    f = 'COMBAT MODIFIERS'
    rows = lines(f + '.txt')
    def cells(row):
        return [cell.strip() for cell in row.split('\t')]
    def number(cell):
        return int(cell.replace('–', '-')) if re.fullmatch(r'[+–-]?\d+', cell) else None
    def modifiers(start, stop):
        return [dict(condition=label, melee=number(melee), ranged=number(ranged),
                     raw=[label, melee, ranged, *notes])
                for row in rows[start - 1:stop] if row.strip()
                for label, melee, ranged, *notes in [cells(row)]]
    add('combat-modifier-tables', f, 'FAVORABLE', 'TWO-WEAPON',
        attack=modifiers(7, 14), armorClass=modifiers(18, 30))
    add('two-weapon-fighting', f, 'TWO-WEAPON', 'COVER', penalties=[
        dict(offHandLight=bool(i % 2), hasFeat=i >= 2, mainHand=number(main), offHand=number(off))
        for i, (_, main, off) in enumerate(map(cells, rows[41:45]))])
    add('cover', f, 'COVER', 'CONCEALMENT', bonuses={
        'normal': {'ac': 4, 'reflex': 2}, 'soft': {'ac': 4, 'reflex': 0},
        'improved': {'ac': 8, 'reflex': 4, 'hide': 10}}, totalBlocksAttack=True)
    add('concealment', f, 'CONCEALMENT', 'FLANKING', missChancePercent={'normal': 20, 'total': 50}, stacks=False)
    add('flanking', f, 'FLANKING', 'HELPLESS DEFENDERS', meleeAttackBonus=2)
    add('helpless-and-coup-de-grace', f, 'HELPLESS DEFENDERS', meleeAcPenalty=-4, dexterityForAc=0,
        action='full-round', fortitudeDc='10 + damageDealt')
    f = 'INJURY AND DEATH'
    add('hit-point-thresholds', f, 'LOSS OF HIT POINTS', 'Massive Damage:', disabledAt=0, dyingFrom=-1, deadAtOrBelow=-10)
    add('massive-damage', f, 'Massive Damage:', 'DISABLED', threshold=50, fortitudeDc=15,
        rulesPath='/mechanics/injury')
    add('disabled-at-zero-hp', f, 'DISABLED', 'DYING', conditionId='disabled')
    add('dying-and-stability', f, 'DYING', 'HEALING', rulesPath='/mechanics/injury')
    add('natural-healing', f, 'HEALING', 'TEMPORARY HIT POINTS', rulesPath='/mechanics/injury')
    add('temporary-hit-points', f, 'TEMPORARY HIT POINTS', 'NONLETHAL DAMAGE', rulesPath='/mechanics/injury')
    add('nonlethal-damage', f, 'NONLETHAL DAMAGE', rulesPath='/mechanics/injury')
    add('alignment-taxonomy', 'ALIGNMENT', 'THE NINE ALIGNMENTS', rulesPath='/mechanics/alignmentsById')
    add('alignment-class-restrictions', 'RULES', '- `alignment-class-restrictions`', 'Typed shapes',
        rulesPath='/mechanics/alignmentConsequencesByClassId', classEligibilityPath='/progression/classes/*/alignments')
    add('modifier-definition', 'RULES', 'MODIFIERS', 'STACKING', bonusSign='positive', penaltySign='negative')
    add('modifier-stacking', 'RULES', 'STACKING', 'MODIFIER TYPES', nonstacking=['best-bonus', 'worst-penalty'],
        sameSource='dm-adjudication', sameTypeBonusExceptions=[])
    modifier_rows = lines('RULES.txt')
    first = modifier_rows.index('MODIFIER TYPES') + 1
    last = modifier_rows.index('<!-- stage-s49:end -->')
    headings = [(i, re.fullmatch(r'([A-Za-z ]+) (?:Bonus|Modifier)', row, re.I))
                for i, row in enumerate(modifier_rows[first:last], first)]
    headings = [(i, match) for i, match in headings if match]
    modifier_types = {}
    for position, (i, match) in enumerate(headings):
        end = headings[position + 1][0] if position + 1 < len(headings) else last
        key = match[1].strip().lower().replace(' ', '-')
        modifier_types[key] = dict(name=modifier_rows[i], description='\n'.join(modifier_rows[i+1:end]).strip(),
                                   sameTypeBonusStacks=False)
    add('modifier-types', 'RULES', 'MODIFIER TYPES', '<!-- stage-s49:end -->', typesById=modifier_types)
    return records
