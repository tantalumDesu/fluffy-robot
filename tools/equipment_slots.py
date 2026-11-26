"""Project declared equipment slots and optional two-weapon attack routines."""

HANDS = ('primary', 'offhand')
BODY_SLOTS = ('head', 'face', 'throat', 'shoulders', 'body', 'torso', 'waist', 'arms', 'hands', 'feet',
              'ring-left', 'ring-right')
CROSSBOW_PENALTIES = {'weapon:crossbow-' + kind: penalty for kind, penalty in (
    ('light', -2), ('heavy', -4), ('repeating-light', -2), ('repeating-heavy', -4), ('hand', 0))}


def equipment_rules(items, lines, source):
    """Encode stable slot policy and source-backed grip exceptions once at generation."""
    for item in items.values():
        key = item['id']
        if item['kind'] == 'weapon':
            bow = any(name in key for name in ('longbow', 'shortbow'))
            crossbow = key in CROSSBOW_PENALTIES
            item['gripProfile'] = dict(
                requiresTwoHands=bow,
                oneHandAttackPenalty=CROSSBOW_PENALTIES.get(key, 0),
                ignoresBucklerAttackPenalty=bow or crossbow,
                countsAsLightOffHand=key in ('weapon:crossbow-light', 'weapon:crossbow-repeating-light', 'weapon:crossbow-hand'))
        elif item['kind'] == 'shield':
            item['reservesGrip'] = key != 'armor:buckler'
    ranger = [dict(minimumClassLevel=level, featId=feat, source=source('RANGER.txt', line=next(
        i for i, line in enumerate(lines('RANGER.txt'), 1) if line.startswith(heading))))
        for level, feat, heading in ((2, 'two-weapon-fighting', 'Combat Style (Ex):'),
                                    (6, 'improved-two-weapon-fighting', 'Improved Combat Style (Ex):'),
                                    (11, 'greater-two-weapon-fighting', 'Combat Style Mastery (Ex):'))]
    return dict(handIds=list(HANDS), bodySlotIds=list(BODY_SLOTS), armorSlotId='armor', shieldSlotId='shield',
                rangerTwoWeaponStyle=dict(classId='ranger', allowedWornArmorBands=['light'], grants=ranger))


def allocate_slots(core, equipped):
    inventory = core['inventory']
    items, rules = inventory['itemsById'], inventory['equipmentSlots']
    hands = rules['handIds']
    slots, grips, shields, gauntlets = {}, {}, {}, {}
    seen = set()

    def claim(slot, instance):
        if slot in slots:
            raise ValueError(f'Equipment slot already occupied: {slot}')
        slots[slot] = instance

    for entry in equipped:
        item = items[entry['itemId']]
        kind, instance = item['kind'], entry['instanceId']
        if instance in seen:
            raise ValueError(f'Duplicate equipped instance: {instance}')
        seen.add(instance)
        hand, grip, slot = entry.get('hand'), entry.get('gripHands'), entry.get('slotId')
        if hand is not None and hand not in hands:
            raise ValueError('Invalid equipment hand')
        if kind == 'weapon' and (grip is not None or hand is not None):
            grip = tuple(grip) if grip is not None else (hand,)
            if not grip or any(h not in hands for h in grip) or len(grip) != len(set(grip)) or (hand and hand not in grip):
                raise ValueError('Invalid weapon grip')
            for h in grip:
                claim('grip-' + h, instance)
            grips[instance] = grip
        elif grip is not None:
            raise ValueError('Only weapons declare gripHands')
        if kind == 'armor':
            claim(rules['armorSlotId'], instance)
        elif kind == 'shield':
            claim(rules['shieldSlotId'], instance)
            if hand is not None:
                shields[hand] = item['id']
                if item['reservesGrip']:
                    claim('grip-' + hand, instance)
        elif item['id'] == 'armor:gauntlet-locked' and hand is not None:
            claim('gauntlet-' + hand, instance)
            gauntlets[hand] = entry.get('securedWeaponInstanceId')
        elif hand is not None and kind != 'weapon':
            claim('grip-' + hand, instance)
        if slot is not None:
            if slot not in rules['bodySlotIds']:
                raise ValueError(f'Unknown body slot: {slot}')
            claim(slot, instance)
    for hand, secured in gauntlets.items():
        if secured is not None and secured in grips and hand not in grips[secured]:
            raise ValueError('Secured weapon is assigned to the wrong hand')
        if secured is not None and slots.get('grip-' + hand, secured) != secured:
            raise ValueError('Locked gauntlet hand is already occupied by its secured weapon')
    return dict(bySlot=slots, gripByInstance=grips, shieldByHand=shields, primaryHand='primary', offHand='offhand')


def grip_adjustment(item, line, grip):
    """Return (valid, attack penalty) for declared grips; reloads are separate."""
    if len(grip) != 1:
        return True, 0
    profile = item.get('gripProfile', {})
    return (not (profile.get('requiresTwoHands') or line['effectiveCategory'] == 'Two-Handed Melee Weapon'),
            profile.get('oneHandAttackPenalty', 0))


def fighting_feats(core, history, feat_ids, worn_armor, ranger_style):
    feats = set(feat_ids)
    rule = core['inventory']['equipmentSlots']['rangerTwoWeaponStyle']
    if ranger_style == 'two-weapon' and all(item['category'].lower().split()[0] in rule['allowedWornArmorBands']
                                           for item in worn_armor):
        level = history.get('classLevels', {}).get(rule['classId'], 0)
        feats.update(grant['featId'] for grant in rule['grants'] if level >= grant['minimumClassLevel'])
    return feats


def two_weapon_routine(core, slots, attacks, feats, *, double_weapon_instance_id=None, for_defense=False):
    by_id = {a['instanceId']: a for a in attacks if a.get('canAct') or (for_defense
             and a['status'] == 'wieldable' and a.get('blockedReason') != 'two-hands-required')}
    occupied = slots['bySlot']
    main = by_id.get(occupied.get('grip-' + slots['primaryHand']))
    off = by_id.get(occupied.get('grip-' + slots['offHand']))
    if not main or not off:
        return None
    double = main is off
    if double:
        if main['instanceId'] != double_weapon_instance_id or '/' not in (main.get('damageDice') or ''):
            return None
    elif any(len(slots['gripByInstance'][attack['instanceId']]) != 1 for attack in (main, off)):
        return None
    off_light = double or off['effectiveCategory'] == 'Light Melee Weapon' or off.get('countsAsLightOffHand', False)
    penalties = next(rule['mechanic']['penalties'] for rule in core['mechanics']['rules']
                     if rule['id'] == 'two-weapon-fighting')
    row = next(row for row in penalties if row['offHandLight'] == off_light and
               row['hasFeat'] == ('two-weapon-fighting' in feats))
    main_bonus = main['attackBonus'] + row['mainHand']
    off_bonus = off['attackBonus'] + row['offHand']
    base_bab = main['breakdown']['iterativeBaseAttack']
    main_steps = range(min(4, max(1, (base_bab - 1) // 5 + 1)))
    off_steps = 3 if 'greater-two-weapon-fighting' in feats else 2 if 'improved-two-weapon-fighting' in feats else 1
    dice = main['damageDice'].split('/') if double else None
    return dict(action='full-attack', doubleWeapon=double, mainHandPenalty=row['mainHand'], offHandPenalty=row['offHand'],
                mainHand=dict(instanceId=main['instanceId'], attackBonuses=[main_bonus - i * 5 for i in main_steps],
                              damageDice=dice[0] if double else main['damageDice']),
                offHand=dict(instanceId=off['instanceId'], attackBonuses=[off_bonus - i * 5 for i in range(off_steps)],
                             damageDice=dice[1] if double else off['damageDice']))
