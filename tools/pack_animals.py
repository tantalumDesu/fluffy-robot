"""Extract pack-animal stat blocks and explicit load limits from source text."""
import re

FILE = 'BEASTS OF BURDEN.txt'
SCORES = ('str', 'dex', 'con', 'int', 'wis', 'cha')


def capacity_from_prose(text):
    limits = re.search(r'up to ([\d,]+) pounds; a medium load, [\d,]+[–-]([\d,]+) pounds; '
                       r'and a heavy load, [\d,]+[–-]([\d,]+) pounds\..*?can drag ([\d,]+) pounds', text)
    if not limits:
        raise ValueError(f'Unrecognized carrying capacity: {text}')
    return dict(zip(('lightLb', 'mediumLb', 'heavyLb', 'dragLb'),
                    (int(limit.replace(',', '')) for limit in limits.groups())))


def beasts(lines):
    text = lines(FILE)
    headings = [text.index(name) for name in ('Pony', 'Donkey', 'Mule', 'Ox', 'Horse, Light', 'Horse, Heavy')]
    for start, end in zip(headings, headings[1:] + [len(text)]):
        name = text[start]
        raw = text[start:end]
        def value(label):
            return raw[raw.index(label) + 1].strip()

        ability_scores = {key: int(value(key.upper())) for key in SCORES}
        saves = [int(value) for value in value('Fort / Ref / Will').split('/')]
        classification = raw[2]
        speed, hit_dice, initiative = (value(key) for key in ('Speed', 'Hit Dice', 'Initiative'))
        capacity_offset = next(i for i, line in enumerate(raw) if line.startswith('Carrying Capacity:'))
        capacity = capacity_from_prose(raw[capacity_offset])
        if set(ability_scores) != set(SCORES) or len(saves) != 3:
            raise ValueError(f'Incomplete beast stats for {name}')
        details = {}
        if 'Base Attack / Grapple' in raw:
            details['baseAttackBonus'], details['grappleBonus'] = map(int, value('Base Attack / Grapple').split('/'))
        if 'Attack' in raw or 'Full Attack' in raw:
            raise ValueError(f'Working beast {name} must not have attacks')
        for label, key in (('Skills', 'skillText'), ('Rules Origin', 'rulesOrigin')):
            if label in raw:
                details[key] = value(label)
        if 'Feats' in raw:
            feat_start = raw.index('Feats') + 1
            feat_end = raw.index('', feat_start)
            details['featNames'] = raw[feat_start:feat_end]
        yield dict(id='beasts-of-burden:' + re.sub(r'[^a-z]+', '-', name.lower()), name=name, role='pack-animal',
                   combatTrained=False, attacks=[],
                   classification=classification, size=classification.split()[0].lower(), abilityScores=ability_scores,
                   hitDiceText=hit_dice, hitPoints=int(re.search(r'\((\d+) hp\)', hit_dice)[1]),
                   landSpeedFt=int(re.search(r'(\d+) ft', speed)[1]), initiative=int(initiative),
                   saves=dict(zip(('fort', 'ref', 'will'), saves)), source={'file': FILE, 'line': start + 1},
                   carryingCapacity=dict(capacity, source={'file': FILE, 'line': start + capacity_offset + 1}),
                   automation='partial', raw='\n'.join(raw).strip(), **details)
