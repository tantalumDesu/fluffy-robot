"""Replay ordinary known-spell choices and effective prestige casting targets."""
from collections import Counter

from .epic_spell_feats import epic_known_levels
from .spellcasting import slot_budget, spellcasting_levels


def casting_targets(character, history):
    ledger = character.get('levelGrantsByLevel', {})
    return {level: grant['castingTargets'] for entry in history['entries']
            if (grant := ledger.get(str(level := entry['characterLevel']), ledger.get(level, {}))).get('castingTargets')}


def ordinary_known(character, history):
    result = {}
    ledger = character.get('levelGrantsByLevel', {})
    for entry in history['entries']:
        level = entry['characterLevel']
        for track, change in ledger.get(str(level), ledger.get(level, {})).get('knownSpellChanges', {}).items():
            known = result.setdefault(track, {})
            for key in change['removed']:
                known.pop(key, None)  # A replaced lower level may not grant the original spell.
            known.update(change['learned'])
    return result


def active_known(character, history, feats):
    result = {track: set(ids) for track, ids in character.get('knownSpellIdsByClassId', {}).items()}
    ordinary = ordinary_known(character, history)
    tracks = set(ordinary) | {p['spellGrant']['classId'] for p in feats if p.get('spellGrant')}
    for track in tracks:
        result.setdefault(track, set()).update(ordinary.get(track, {}))
        result[track].update(epic_known_levels(feats, track))
    return {track: sorted(ids) for track, ids in result.items()}


def record_casting_choices(core, actor, prior, history, choices, *, prior_scores):
    level = history['entries'][-1]['characterLevel']
    targets = casting_targets(actor, prior)
    selected = list(choices.get('castingTargets', ()))
    targets[level] = selected
    old = spellcasting_levels(core, prior, casting_targets(actor, prior))
    new = spellcasting_levels(core, history, targets)
    ordinary = ordinary_known(actor, prior)
    active = active_known(actor, prior, actor.get('featChoices', ()))
    changes = {}
    supplied = dict(choices.get('spellChoicesByClassId', {}))
    tables = core['magic']['ordinarySpellsKnown']
    for track, current in new.items():
        previous = old.get(track, 0)
        if current == previous or track not in tables and track != 'magewright':
            continue
        cls = next(c for c in core['progression']['classes'] if c['id'] == track)
        casting = cls['spellcasting']
        score = actor['abilityScores'][casting['abilityStat'].lower()]
        levels = {s['id']: r['level'] for s in core['magic']['spells'] for r in s['lists']
                  if r['listId'] == casting['spellListId']}
        known = ordinary.get(track, {})
        occupied = set(active.get(track, ()))
        budget = slot_budget(core, track, current, score)
        highest = max((n for pool, n in budget if pool == 'regular'), default=-1)
        pick = supplied.pop(track, {})
        learned = list(pick.get('learn', ()))
        removed = []
        if len(set(learned)) != len(learned) or any(key in occupied or key not in levels for key in learned):
            raise ValueError(f'Choose distinct new spells from the {track} list')
        swap = pick.get('swap')
        if track == 'magewright':
            old_budget = slot_budget(core, track, previous, prior_scores[casting['abilityStat'].lower()]) if previous else {}
            old_highest = max((n for pool, n in old_budget if pool == 'regular'), default=-1)
            initial = not previous
            extra_cantrip = not initial and (highest > old_highest or current == 20)
            required = max(0, (score - 10) // 2) + int(extra_cantrip) if initial or extra_cantrip else 0
            if (len(learned) != required or (extra_cantrip and not any(levels[k] == 0 for k in learned))
                    or any(levels[k] > highest for k in learned) or swap):
                raise ValueError('Choose the required Magewright mastery spells, including the extra cantrip when due')
        else:
            rows = tables[track]['byLevel']
            cap = max(map(int, rows))
            current_total = rows[str(min(cap, current))]
            known_count = Counter(known.values())
            minimum = casting['minSpellLevel']
            required = Counter()
            for n, total in enumerate(current_total, minimum):
                # Bard/Assassin first-access entries depend on having the bonus slot.
                if (track == 'sorcerer' and score >= 10 + n) or ('regular', n) in budget:
                    count = total - known_count[n]
                    if count > 0:
                        required[n] = count
            if Counter(levels[key] for key in learned) != required:
                raise ValueError(f'Choose the required {track} spells by level: {dict(required)}')
            if swap:
                before, after = swap['remove'], swap['learn']
                rule = next(r['mechanic']['parameters'] for r in core['mechanics']['rules'] if r['id'] == track + '-spell-swap')
                if (current not in rule['statedEligibleLevels'] + rule['derivedEligibleLevels'] or before not in known
                        or after in occupied or after in learned or after not in levels or levels[after] != known[before]
                        or levels[after] > highest - rule['minLevelsBelowHighestCastable']):
                    raise ValueError(f'Invalid {track} spell swap')
                removed.append(before)
                learned.append(after)
        if learned or removed:
            changes[track] = dict(learned={key: levels[key] for key in learned}, removed=removed)
    if supplied:
        raise ValueError('Spell choices supplied for a track without applicable advancement')
    return selected, new, changes
