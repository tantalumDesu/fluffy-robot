"""Project confirmed locked-gauntlet state, without resolving actions."""

ITEM_ID = 'armor:gauntlet-locked'


def locked_gauntlet_rule(lines, source):
    text = lines('ARMOR.txt')
    start = next(i for i, row in enumerate(text) if row.startswith('Gauntlet, Locked:'))
    end = next(i for i in range(start, len(text)) if text[i].startswith('Like a normal gauntlet,'))
    return dict(source=source('ARMOR.txt', line=start + 1), description='\n'.join(text[start:end + 1]),
                disarmDefenseBonus=10, listedWeightLb=5, fullWeightArmorIds=['armor:breastplate'],
                fullWeightArmorCategories=['light'], attachDetachAction='full-round',
                provokesAttacksOfOpportunity=True, lockedHandCannotCastOrUseSkills=True,
                allowsLethalUnarmedStrike=True,
                adjudicationText=(
                    'Attaching or detaching a weapon takes a full-round action and provokes attacks of opportunity. '
                    'Record the secured weapon only after the player and DM resolve the action. '
                    'While locked, that hand cannot be used to cast spells or employ skills. '
                    'Somatic casting can still use the other hand if it is free; the listed 100% is not '
                    'a blanket spell failure chance for the wearer. '
                    'If an effect would make the wearer drop the secured weapon, adjudicate whether it remains '
                    'attached and whether it can still be wielded. '
                    'An unarmed strike made with the gauntlet may deal lethal instead of nonlethal damage; '
                    'declare the strike and damage choice before resolving it.'))


def project_gauntlets(core, equipped, worn_armor):
    items = core['inventory']['itemsById']
    rule = items[ITEM_ID]['lockedGauntlet']
    full_weight = not worn_armor or any(
        item['id'] in rule['fullWeightArmorIds'] or
        item['category'].lower().split()[0] in rule['fullWeightArmorCategories'] for item in worn_armor)
    weapons = {entry['instanceId'] for entry in equipped if items[entry['itemId']]['kind'] == 'weapon'}
    result = []
    secured = set()
    hands = set()
    for entry in equipped:
        if entry['itemId'] != ITEM_ID:
            continue
        hand = entry.get('hand')
        if hand is not None:
            if hand not in ('left', 'right') or hand in hands:
                raise ValueError('Invalid or duplicate locked gauntlet hand')
            hands.add(hand)
        weapon = entry.get('securedWeaponInstanceId')
        if weapon is not None:
            if hand is None or weapon not in weapons or weapon in secured:
                raise ValueError('A locked gauntlet requires its hand and a distinct equipped weapon')
            secured.add(weapon)
        result.append(dict(instanceId=entry['instanceId'], hand=hand, securedWeaponInstanceId=weapon,
                           effectiveWeightLb=rule['listedWeightLb'] if full_weight else 0,
                           disarmDefenseBonus=rule['disarmDefenseBonus'] if weapon is not None else 0,
                           handUnavailableForCastingOrSkills=weapon is not None,
                           allowsLethalUnarmedStrike=rule['allowsLethalUnarmedStrike'],
                           description=rule['description'], adjudicationText=rule['adjudicationText']))
    return result
