"""Extract pack-animal stat blocks and explicit load limits from source text."""
import re

FILE = 'BEASTS OF BURDEN.txt'
SCORES = ('str', 'dex', 'con', 'int', 'wis', 'cha')


def capacity_from_prose(text):
    limits = re.search(r'up to ([\d,]+) pounds; a medium load, [\d,]+[–-]([\d,]+) pounds; '
                       r'and a heavy load, [\d,]+[–-]([\d,]+) pounds\.(?:.*?can drag ([\d,]+) pounds)?', text)
    if not limits:
        raise ValueError(f'Unrecognized carrying capacity: {text}')
    return {key: int(limit.replace(',', '')) for key, limit in zip(
        ('lightLb', 'mediumLb', 'heavyLb', 'dragLb'), limits.groups()) if limit is not None}


def beasts(lines, *, war_mounts=False, unusual_mounts=False):
    file = 'UNUSUAL MOUNTS.txt' if unusual_mounts else 'WAR MOUNTS.txt' if war_mounts else FILE
    mount = unusual_mounts or war_mounts
    text = lines(file)
    names = ('Warpony', 'Warhorse, Light', 'Warhorse, Heavy') if war_mounts else (
        'Pony', 'Donkey', 'Mule', 'Ox', 'Horse, Light', 'Horse, Heavy')
    if unusual_mounts:
        names = ('Griffon', 'Pegasus', 'Eagle, Giant', 'Owl, Giant', 'Giant Wasp', 'Monstrous Spider, Large')
    headings = [text.index(name) for name in names]
    for start, end in zip(headings, headings[1:] + [len(text)]):
        name = text[start]
        raw = text[start:end]
        def value(label):
            return raw[raw.index(label) + 1].strip()

        ability_scores = {key: int(value(key.upper())) if key.upper() in raw and value(key.upper()) != '—' else None for key in SCORES}
        saves = [int(value) for value in value('Fort / Ref / Will').split('/')]
        classification = raw[2]
        speed, hit_dice, initiative = (value(key) for key in ('Speed', 'Hit Dice', 'Initiative'))
        capacity_offset = next((i for i, line in enumerate(raw) if line.startswith('Carrying Capacity:')), None)
        if capacity_offset is None and not unusual_mounts:
            raise ValueError(f'Missing carrying capacity: {name}')
        if set(ability_scores) != set(SCORES) or len(saves) != 3:
            raise ValueError(f'Incomplete beast stats for {name}')
        details = {}
        if 'Base Attack / Grapple' in raw:
            details['baseAttackBonus'], details['grappleBonus'] = map(int, value('Base Attack / Grapple').split('/'))
        if not mount and ('Attack' in raw or 'Full Attack' in raw):
            raise ValueError(f'Working beast {name} must not have attacks')
        for label, key in (('Skills', 'skillText'), ('Rules Origin', 'rulesOrigin')):
            if label in raw:
                details[key] = value(label)
        if 'Feats' in raw:
            feat_start = raw.index('Feats') + 1
            feat_end = raw.index('', feat_start)
            details['featNames'] = raw[feat_start:feat_end]
        if capacity_offset is not None:
            details['carryingCapacity'] = dict(capacity_from_prose(raw[capacity_offset]),
                                               source={'file': file, 'line': start + capacity_offset + 1})
        if climb := re.search(r'climb (\d+) ft', speed, re.I):
            details['climbSpeedFt'] = int(climb[1])
        if flight := re.search(r'fly (\d+) ft\.? \(([^)]+)\)', speed, re.I):
            details['flight'] = dict(speedFt=int(flight[1]), maneuverability=flight[2].lower())
        for offset, line in enumerate(raw):
            if rule := re.search(r'Training a friendly .+ requires six weeks of work and a DC (\d+) Handle Animal check', line):
                details['combatRidingTraining'] = dict(dc=int(rule[1]), weeks=6, requiresFriendly=True,
                    source={'file': file, 'line': start + offset + 1})
        namespace = 'unusual-mounts' if unusual_mounts else 'war-mounts' if war_mounts else 'beasts-of-burden'
        yield dict(id=(namespace + ':') + re.sub(r'[^a-z]+', '-', name.lower()),
                   name=name, role='ordinary-mount' if mount else 'pack-animal',
                   **({'statBlockText': '\n'.join(raw).strip()} if mount else {'attacks': []}),
                   classification=classification, size=classification.split()[0].lower(), abilityScores=ability_scores,
                   hitDiceText=hit_dice, hitPoints=int(re.search(r'\((\d+) hp\)', hit_dice)[1]),
                   landSpeedFt=int(re.search(r'(\d+) ft', speed)[1]), initiative=int(initiative),
                   saves=dict(zip(('fort', 'ref', 'will'), saves)), source={'file': file, 'line': start + 1},
                   automation='partial', raw='\n'.join(raw).strip(), **details)
