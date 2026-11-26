"""Familiar Spell choices and display labels; does not cast or spend daily uses."""


def familiar_spell_choices(core, known_spell_levels, *, verified_material_cost_gp=None):
    """Use actual known spell levels, not every spell on a class list."""
    rule = core['feats']['byId']['familiar-spell']['spellGrant']
    costs = verified_material_cost_gp or {}
    options, review = [], []
    for spell in core['magic']['spells']:
        key = spell['id']
        level = known_spell_levels.get(key)
        if type(level) is not int or not 0 <= level <= rule['maximumKnownSpellLevel']:
            continue
        codes = {c['code'].upper() for c in spell['components']['codes']}
        if codes.intersection(rule['prohibitedComponentCodes']):
            continue
        option = dict(spellId=key, name=spell['name'], level=level)
        if 'M' in codes and key not in costs:
            review.append(dict(option, maximumMaterialCostGp=rule['maximumMaterialCostGp'],
                               reason='Confirm material component cost is within the limit'))
        elif key not in costs or 0 <= costs[key] <= rule['maximumMaterialCostGp']:
            options.append(option)
    return dict(eligible=sorted(options, key=lambda o: (o['level'], o['name'])),
                needsReview=sorted(review, key=lambda o: (o['level'], o['name'])))


def familiar_spell_grants(core, feat_choices):
    names = {s['id']: s['name'] for s in core['magic']['spells']}
    totals = {}
    daily = core['feats']['byId']['familiar-spell']['spellGrant']['dailyUsesPerTake']
    for feat in feat_choices:
        if feat['featId'] != 'familiar-spell':
            continue
        key = feat.get('choices', {}).get('spellId')
        if key not in names:
            raise ValueError('Familiar Spell requires a valid spellId')
        totals[key] = totals.get(key, 0) + daily
    return [dict(featId='familiar-spell', spellId=key, spellName=names[key], usesPerDay=count,
                 label=f'Familiar Spell, {names[key]} {count}/day')
            for key, count in sorted(totals.items(), key=lambda pair: names[pair[0]])]
