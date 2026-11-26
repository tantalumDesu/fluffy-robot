"""Project confirmed feat selections without spending actions or uses."""
import re


def feat_effects(core, picks, keys):
    catalog = core['effects']['featEffectsByFeatId']
    return [(effect, pick.get('choices', {})) for pick in picks if pick['featId'] in keys
            for effect in catalog.get(pick['featId'], ())]


def weapon_proficiency_grants(core, picks):
    items = core['inventory']['itemsById']
    rules = core['feats']['byId']
    result = set()
    for pick in picks:
        feat = rules.get(pick['featId'], {})
        grant = feat.get('weaponProficiencyGrant')
        if not grant:
            continue
        key = pick.get('choices', {}).get('weaponId')
        item = items.get(key, {})
        if item.get('kind') != 'weapon' or item.get('proficiency') != grant['category']:
            raise ValueError('Weapon proficiency feat must select a weapon of its category')
        result.add(key)
    return result


def critical_profile(raw, *, expanded=False):
    match = re.fullmatch(r'(?:(\d+)[–-]20/)?[x×](\d+)', raw or '')
    if not match:
        return None
    minimum, multiplier = int(match[1] or 20), int(match[2])
    return dict(threatMinimum=max(1, 21 - (21 - minimum) * (2 if expanded else 1)), multiplier=multiplier)
