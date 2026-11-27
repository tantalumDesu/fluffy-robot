"""Typed tack, barding, and projection of a confirmed rider–mount pairing."""
from fractions import Fraction
import re


def mounted_catalog(items, lines, source, table, slug):
    for family in ('standard', 'exotic'):
        for purpose in ('military', 'pack', 'riding'):
            item = items['gear:saddle-' + ('exotic-' if family == 'exotic' else '') + purpose]
            item['saddle'] = dict(family=family, purpose=purpose, supportsRider=purpose != 'pack',
                                  stayMountedRideCircumstance=2 if purpose == 'military' else 0,
                                  unconsciousStayPercent=75 if purpose == 'military' else 50)
    barding = {}
    def amount(text):
        return int(text.split()[0].replace(',', ''))
    for line, (armor, category, med_cost, med_weight, lg_cost, lg_weight) in table('ARMOR.txt', 'Table: Medium and Large Barding'):
        for size, cost, weight in (('medium', med_cost, med_weight), ('large', lg_cost, lg_weight)):
            armor_id = 'armor:' + slug(armor)
            if armor_id not in items:
                raise ValueError(f'Unknown base armor for barding: {armor_id}')
            key = f'barding:{size}:{slug(armor)}'
            barding[key] = dict(id=key, baseArmorId=armor_id, sizeId=size, category=category.split()[0].lower(),
                                priceCp=100 * amount(cost), weightLb=amount(weight),
                                source=source('ARMOR.txt', line=line))
    speed = {category.lower(): dict(zip(('40', '50', '60'), map(amount, values)))
             for _, (category, *values) in table('ARMOR.txt', 'Table: Barding Speed')}
    return dict(bardingById=barding, bardingSpeedByCategory=speed, heavyRunMultiplier=3,
                bardingDonRemoveMultiplier=5, bardingBlocksFlight=['medium', 'heavy'],
                barebackRidePenalty=-5, illSuitedRidePenalty=-5, controlInBattleDc=20, fightAlongsideMountRideDc=10,
                encounterActions=dict(fastMountDc=20, softFallDc=15, higherGroundBonus=1,
                                      chargeAttackBonus=2, chargeArmorAdjustment=-2,
                                      rangedPenaltyByPace={'double-move': -4, 'run': -8},
                                      rideSource=source('SKILLS.txt', heading='Ride')),
                mountedClimbing=dict(stayMountedRideDc=5, source=source('SKILLS.txt', heading='Mounted Climbing (Campaign Rule)')),
                lanceChargeMultiplier=2, saddlebagsLimitBand='light',
                source=source('SPECIAL ATTACKS.txt', heading='MOUNTED COMBAT'))


def training_seed(rules, purpose=None):
    return dict(purposeId=purpose, learnedTrickIds=list(rules['purposesById'][purpose]['tricks']) if purpose else [],
                bonusTrickIds=[])


def acquisition_training(core, definition, *, purchase_item_id=None):
    """Instantiate mutable tricks from the source's training-purpose reference."""
    inventory = core['inventory']
    if purchase_item_id is None:
        profile = next((p for p in inventory['packAnimalsById'].values() if p['creatureId'] == definition['id']), None)
        if profile:
            purchase_item_id = profile['purchaseItemId']
        elif definition.get('role') == 'ordinary-mount':
            purchase_item_id = next((item['id'] for item in inventory['itemsById'].values()
                                    if item.get('creatureId') == definition['id']), None)
    source = inventory['itemsById'][purchase_item_id] if purchase_item_id else definition
    return training_seed(core['skills']['animalTraining'], source.get('trainingPurposeId'))


def mount_profile(definition):
    """Assign saddle family independently of whether the creature can be ridden."""
    key = definition['id'].split(':')[-1]
    standard = key in ('horse-light', 'horse-heavy', 'pony', 'warpony', 'warhorse-light', 'warhorse-heavy', 'dog-riding')
    text = definition.get('statBlockText', '')
    biped = key in ('eagle', 'eagle-giant', 'owl', 'owl-giant', 'ape', 'ape-dire', 'hawk', 'raven') or key.startswith('dinosaur-') and key.endswith(('deinonychus', 'megaraptor', 'tyrannosaurus'))
    nonquadruped = biped or key.startswith(('snake-', 'viper-', 'shark-', 'squid', 'octopus', 'whale-', 'monstrous-', 'formian-', 'mephit-', 'air-elemental-', 'fire-elemental-', 'earth-elemental-', 'water-elemental-')) or key in ('porpoise', 'giant-wasp', 'quasit', 'stirge', 'vargouille-without-kiss', 'elasmosaurus', 'dinosaur-elasmosaurus')
    flying = bool(definition.get('flight') or re.search(r'\bfly\s+\d+\s*ft', text, re.I) or key in ('bat', 'bat-dire', 'hippogriff', 'pseudodragon'))
    quadruped = standard or key.startswith(('badger', 'bear-', 'boar', 'crocodile', 'dog', 'lion', 'tiger', 'wolf', 'wolverine', 'weasel', 'rat', 'lizard')) or key in ('blink-dog', 'bison', 'camel', 'cat', 'cheetah', 'donkey', 'elephant', 'hell-hound', 'krenshar', 'leopard', 'mule', 'ox', 'rhinoceros', 'shocker-lizard', 'toad', 'worg', 'dinosaur-triceratops', 'winter-wolf')
    source_exotic = 'requires an exotic saddle' in text
    exotic = source_exotic or flying or nonquadruped
    training = re.search(r'Training a (friendly )?[^.]+ requires six weeks of work and a DC (\d+) Handle Animal check', text)
    if training and 'combatRidingTraining' not in definition:
        definition['combatRidingTraining'] = dict(dc=int(training[2]), weeks=6, requiresFriendly=bool(training[1]),
                                                source=definition.get('statBlockSource', definition['source']))
    return dict(saddleFamily='exotic' if exotic else 'standard' if quadruped else None,
                suitability='suitable' if standard or source_exotic or key in ('eagle-giant', 'worg') else 'needs-review',
                **({'requiresFittedSaddle': True} if exotic else {}),
                **({'locomotion': 'biped'} if key in ('eagle-giant', 'owl-giant', 'ape-dire', 'ape') else {}))


def project_mount(core, definition, *, creature_sheet=None, rider_size_id, rider_weight_lb,
                  rider_inventory_lb=0, training=None, saddle=None, barding_id=None,
                  saddlebags_payload_lb=0, other_cargo_lb=0, suitability=None, saddle_fit=None,
                  locomotion=None, charging=False, weapon_id=None):
    """Read one creature instance and project its confirmed tack, load and Ride effects."""
    from .creature_size import carrying_limits

    rules = core['mechanics']['mountedCombat']
    items = core['inventory']['itemsById']
    sheet = creature_sheet or {}
    profile = definition.get('mountProfile', {})
    size = sheet.get('size', sheet.get('sizeId', definition.get('sizeId')))
    sizes = core['mechanics']['sizeCategoriesById']
    suitability = suitability or profile.get('suitability', 'needs-review')
    if suitability not in ('suitable', 'ill-suited', 'impossible', 'needs-review'):
        raise ValueError('Invalid mount suitability')
    fit = saddle_fit or profile
    expected_size = fit.get('saddleSizeId', size)
    expected_family = 'exotic' if profile.get('requiresFittedSaddle') else fit.get('saddleFamily')
    review, blocked = [], []
    if sizes[size]['order'] <= sizes[rider_size_id]['order']:
        blocked.append('Mount must be larger than its rider')
    if suitability == 'impossible':
        blocked.append('Creature is not physically suitable for this rider')
    elif suitability == 'needs-review':
        review.append('Confirm suitability for this rider')
    base_str = definition['abilityScores']['str']
    strength = sheet.get('abilityScores', {}).get('str', base_str)
    if not locomotion and definition['id'].endswith(('snake-giant-constrictor', 'monstrous-spider-large', 'giant-wasp', 'shark-large')):
        review.append('Confirm carrying-capacity body plan; default estimate is provisional')
    limits = carrying_limits(core, strength, size, locomotion or profile.get('locomotion', 'quadruped'),
                             explicit=definition.get('carryingCapacity') if strength == base_str and size == definition.get('sizeId') else None)
    def weight(raw):
        result = Fraction(str(raw))
        if result < 0:
            raise ValueError('Mounted weights must be nonnegative')
        return result
    rider_load = weight(rider_weight_lb) + weight(rider_inventory_lb)
    bags = weight(saddlebags_payload_lb)
    extra = weight(other_cargo_lb)
    tack = weight(items['gear:saddlebags']['weightLb']) if bags else 0
    military = False
    supports_rider = False
    if saddle is not None:
        item = items[saddle['itemId']]
        detail = item.get('saddle')
        if detail is None:
            raise ValueError('Expected a saddle item')
        tack += weight(item['weightLb'])
        if expected_family is None or expected_size is None:
            review.append('Confirm the saddle size and standard/exotic fit')
        elif saddle.get('sizeId') != expected_size or detail['family'] != expected_family:
            review.append('Saddle does not fit; no rider-saddle effects apply')
        else:
            supports_rider = detail['supportsRider']
            military = supports_rider and detail['purpose'] == 'military'
            if not supports_rider:
                review.append('A pack saddle does not seat a rider; confirm bareback use with this tack')
    if profile.get('requiresFittedSaddle') and not supports_rider:
        blocked.append('This mount requires a fitted exotic rider saddle')
    armor = rules['bardingById'][barding_id] if barding_id else None
    armor_stats = None
    if armor:
        if armor['sizeId'] != size:
            raise ValueError('Barding size does not fit the mount')
        tack += weight(armor['weightLb'])
        if extra:
            blocked.append('Barded mounts cannot carry cargo outside normal saddlebags')
    if bags > limits[rules['saddlebagsLimitBand'] + 'Lb']:
        blocked.append('Saddlebags exceed the mount’s light-load allowance')
    if armor:
        base = items[armor['baseArmorId']]
        armor_stats = {key: base[key] for key in ('armorClassBonus', 'maxDexBonus', 'armorCheckPenalty', 'arcaneSpellFailurePercent') if key in base}
    load = rider_load + bags + extra + tack
    band = next((band for band in ('light', 'medium', 'heavy') if load <= limits[band + 'Lb']), 'overloaded')
    if band == 'overloaded':
        blocked.append('Rider, tack, and cargo exceed carrying capacity')
    base_speed = sheet.get('landSpeedFt', definition.get('landSpeedFt'))
    if base_speed is None:
        text = definition.get('statBlockText', '')
        match = re.search(r'^Speed\s*\n\s*(?:Land\s+)?(\d+) ft', text, re.M)
        base_speed = int(match[1]) if match else None
    reduced = base_speed
    speed_rules = rules['bardingSpeedByCategory'].get(armor['category'] if armor else None, {})
    if speed_rules:
        reduced = speed_rules.get(str(base_speed))
        if reduced is None:
            review.append('Confirm barding speed for this base movement rate')
    if band in ('medium', 'heavy'):
        load_speed = core['inventory']['encumbranceByBand'][band]['speedByBaseFt'].get(str(base_speed))
        if load_speed is not None and reduced is not None:
            reduced = min(reduced, load_speed)
        elif str(base_speed) not in speed_rules:
            review.append('Confirm encumbered speed for this base movement rate')
    projected_ac = None
    if armor_stats and sheet.get('armorClass'):
        current = sheet['armorClass']
        dex = sheet.get('abilityScores', definition['abilityScores']).get('dex')
        dex_mod = (dex - 10) // 2 if dex is not None else 0
        dex_delta = min(dex_mod, armor_stats['maxDexBonus']) - dex_mod
        bonus = armor_stats['armorClassBonus']
        projected_ac = dict(normal=current['normal'] + bonus + dex_delta, touch=current['touch'] + dex_delta,
                            flatFooted=current['flatFooted'] + bonus)
    if training is None:
        training = acquisition_training(core, definition)
    combat_trained = training.get('purposeId') == 'combat-riding'
    riding_trained = combat_trained or training.get('purposeId') == 'riding'
    if not riding_trained:
        review.append('Confirm how this mount accepts a rider; no riding purpose is recorded')
    penalties = dict(bareback=0 if supports_rider else rules['barebackRidePenalty'],
                     illSuited=rules['illSuitedRidePenalty'] if suitability == 'ill-suited' else 0)
    flight = sheet.get('flight', definition.get('flight'))
    flight_blocked = bool(armor and armor['category'] in rules['bardingBlocksFlight'])
    flight_status = ('blocked-by-barding' if flight_blocked else 'not-listed' if not flight
                     else 'confirm-load-and-flight')
    climb_speed = sheet.get('climbSpeedFt', definition.get('climbSpeedFt'))
    climbing = dict(climbSpeedFt=climb_speed, **rules['mountedClimbing']) if climb_speed else None
    return dict(status='blocked' if blocked else 'needs-review' if review else 'ready', blockedReasons=blocked,
                mountSizeSteps=sizes[size]['order'] - sizes[rider_size_id]['order'],
                needsReview=review, mountedLoadLb=float(load), loadBand=band,
                capacityLb={key: float(value) for key, value in limits.items()},
                mountedClimbing=climbing, swimSpeedFt=sheet.get('swimSpeedFt', definition.get('swimSpeedFt')), landSpeedFt=reduced, flightBlocked=flight_blocked, flight=flight, flightStatus=flight_status,
                runMultiplier=rules['heavyRunMultiplier'] if band == 'heavy' or armor and armor['category'] == 'heavy' else 4,
                barding=armor, armorModifiers=armor_stats, armorClass=projected_ac, ridePenalties=penalties, ridePenalty=sum(penalties.values()),
                stayMountedRideCircumstance=2 if military else 0, unconsciousStayPercent=75 if military else 50,
                ridingTrained=riding_trained, combatRidingTrained=combat_trained,
                controlInBattleDc=None if combat_trained else rules['controlInBattleDc'],
                fightAlongsideMountRideDc=rules['fightAlongsideMountRideDc'] if combat_trained else None,
                lanceChargeMultiplier=rules['lanceChargeMultiplier'] if not blocked and not review and charging and weapon_id == 'weapon:lance' else 1)
