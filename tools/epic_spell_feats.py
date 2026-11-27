"""Resolve repeatable epic casting feats and project their active benefits."""
from collections import Counter
from itertools import product

from .feat_selection import check_feat_selection
from .spellbooks import available_spellbooks, school_access, update_spellbook
from .spellcasting import slot_budget

CAPACITY = 'improved-spell-capacity'
KNOWLEDGE = 'spell-knowledge'


def epic_slot_grants(feats, class_id):
    return dict(Counter(p['spellGrant']['slotLevel'] for p in feats
                        if p.get('featId') == CAPACITY and p.get('spellGrant', {}).get('classId') == class_id))


def epic_known_levels(feats, class_id):
    return {spell['spellId']: spell['level'] for p in feats
            if p.get('featId') == KNOWLEDGE and p.get('spellGrant', {}).get('classId') == class_id
            for spell in p['spellGrant']['spells']}


def apply_epic_spell_pick(core, actor, pick, snapshot):
    """Validate one pick, returning its exact grant and an updated book registry."""
    feat = pick['featId']
    rule = core['magic']['epicSpellFeatRules'][feat]
    choices = pick.get('choices', {})
    track = choices.get('castingClassId')
    if not track or check_feat_selection(core['feats']['byId'], feat, snapshot, choices=choices)['status'] != 'eligible':
        raise ValueError('Choose a qualifying casting track for this epic feat')
    cls = next(c for c in core['progression']['classes'] if c['id'] == track)
    profile = core['magic']['castingProfilesByClassId'][track]
    ability = cls['spellcasting']['abilityStat'].lower()
    progression = snapshot.get('spellcastingLevels', {}).get(track, 0)
    score = snapshot.get('abilityScores', {}).get(ability)
    if progression < 1 or score is None:
        raise ValueError('Supply the casting progression and ability score for the chosen class')
    prior = snapshot['feats']
    slots = slot_budget(core, track, progression, score,
                        extra_slots=epic_slot_grants(prior, track))
    castable_levels = [level for pool, level in slots if pool == 'regular']
    if not castable_levels:
        raise ValueError('The chosen casting class must be able to cast at least one spell')
    highest = max(castable_levels)
    books = dict(actor.get('spellbooksById', {}))
    if feat == CAPACITY:
        level = choices.get('slotLevel')
        if type(level) is not int or not cls['spellcasting']['minSpellLevel'] <= level <= highest + rule['aboveCurrentMaximum']:
            raise ValueError('Capacity must select a slot through one level above the current maximum')
        return dict(pick, spellGrant=dict(classId=track, slotLevel=level)), books
    selections = choices.get('spells', ())
    count = rule['spellsPerPick']
    if len(selections) != count or len({s['spellId'] for s in selections}) != count:
        raise ValueError('Spell Knowledge requires two distinct new arcane spells')
    known = set(actor.get('knownSpellIdsByClassId', {}).get(track, ())) | epic_known_levels(prior, track).keys()
    if track == 'wizard':
        known |= set(actor.get('wizardLearning', {}).get('knownSpellIds', ()))
        known.update(key for book in books.values() for key in book['spellsById'])
    catalog = {s['id']: s for s in core['magic']['spells']}
    arcane = {p['spellListId'] for p in core['magic']['castingProfilesByClassId'].values() if p['tradition'] == 'arcane'}
    grant = []
    for choice in selections:
        key = choice['spellId']
        spell = catalog.get(key)
        if key in known or spell is None or (track == 'wizard' and not school_access(core, spell, actor.get('wizardSpecialization'))):
            raise ValueError(f'Spell is already known or unavailable: {key}')
        rows = {r['listId']: r['level'] for r in spell['lists'] if r['listId'] in arcane}
        source = profile['spellListId'] if profile['spellListId'] in rows else choice.get('sourceListId')
        if source is None and len(set(rows.values())) == 1:
            source = sorted(rows)[0]
        level = rows.get(source)
        if level is None or level > highest:
            raise ValueError(f'Choose an eligible arcane list and spell level for {key}')
        record = dict(spellId=key, level=level)
        if source is not None:
            record['sourceListId'] = source
        grant.append(record)
    if track == 'wizard':
        ids = sorted(book['instanceId'] for book in available_spellbooks(books, snapshot.get('accessibleSpellbookIds', ())))
        for destinations in product(ids, repeat=len(grant)):
            updated = books
            try:
                for record, book_id in zip(grant, destinations):
                    book = updated[book_id]
                    updated = update_spellbook(core, updated, dict(book, spellsById=dict(
                        book['spellsById'], **{record['spellId']: record['level']})))
            except ValueError:
                continue
            books = updated
            for record, book_id in zip(grant, destinations):
                record['bookId'] = book_id
            break
        else:
            raise ValueError('Spell Knowledge requires enough accessible spellbook capacity for both spells')
    return dict(pick, spellGrant=dict(classId=track, spells=grant)), books


def active_spellbooks(actor, active_feats, accessible_ids):
    """Mask suppressed feat inscriptions without changing physical book state."""
    active = epic_known_levels(active_feats, 'wizard')
    suppressed = epic_known_levels(actor.get('featChoices', ()), 'wizard').keys() - active.keys()
    return tuple(dict(book, spellsById={k: v for k, v in book['spellsById'].items() if k not in suppressed})
                 for book in available_spellbooks(actor.get('spellbooksById', {}), accessible_ids))
