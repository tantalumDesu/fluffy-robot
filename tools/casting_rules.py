"""Generate static casting policies separately from character and encounter state."""
import re


def casting_catalog(classes, spells, lines, source):
    def anchor(file, text):
        return source(file, line=next(i for i, row in enumerate(lines(file), 1) if text in row))

    profiles = {}
    for cls in classes:
        track = cls.get('spellcasting', {})
        if track.get('source') != 'own':
            continue
        key, file = cls['id'], cls['file']
        profile = dict(requiresSpellbook=True) if key == 'wizard' else {}
        if key in ('paladin', 'ranger'):
            profile['casterLevel'] = dict(minimumClassLevel=4, classLevelDivisor=2,
                                          source=anchor(file, 'her caster level is one-half' if key == 'paladin'
                                                        else 'his caster level is one-half'))
        if key in ('cleric', 'druid'):
            choices = {}
            for spell in spells:
                if not any(row['listId'] == track['spellListId'] for row in spell['lists']):
                    continue
                match = re.search(r'\b(cure|inflict)\b', spell['name'], re.I) if key == 'cleric' else None
                if match:
                    choices[spell['id']] = match[1].lower()
                elif key == 'druid' and spell['id'].startswith('summon-natures-ally-'):
                    choices[spell['id']] = 'summon-natures-ally'
            profile['conversion'] = dict(pool='regular', familyBySpellId=choices,
                                         requiresFamilyAuthorization=key == 'cleric',
                                         source=anchor(file, 'Spontaneous Casting:'))
        if profile:
            profiles[key] = profile
    return profiles


def casting_profile(core, class_id):
    """Join the class track with its optional additional casting policy."""
    cls = next(c for c in core['progression']['classes'] if c['id'] == class_id)
    track = cls['spellcasting']
    if track['source'] != 'own':
        raise ValueError('Choose an actual spellcasting track')
    return dict(tradition=track['kind'], mode='spontaneous' if track['spontaneous'] else 'prepared',
                spellListId=track['spellListId'],
                allowsDomainSlots=any(row.get('domainSpellsPerDay') for row in cls['progression']),
                **{'requiresSpellbook': False, **core['magic']['castingPoliciesByClassId'].get(class_id, {})})


def extend_recovery(profiles, lines, source):
    for key, base, file, phrase in (
        ('assassin', 'bard', 'TIMING.txt', 'Assassins use the Bard recovery profile'),
        ('adept', 'cleric', 'NPC ADEPT.txt', 'Each adept must choose a time each day'),
        ('magewright', 'wizard', 'NPC MAGEWRIGHT.txt', 'A magewright prepares spells as a wizard does'),
        ('blackguard', 'cleric', 'Prestige Class BLACKGUARD.txt', 'A blackguard prepares and casts spells just as a cleric does'),
    ):
        line = next(i for i, row in enumerate(lines(file), 1) if phrase in row)
        profiles[key] = dict(profiles[base], inheritedFromClassId=base, source=source(file, line=line))
