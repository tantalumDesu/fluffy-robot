"""School-linked feat selections and saving-throw modifiers."""

FEATS = ('spell-focus', 'greater-spell-focus')


def school_choices(core, feat_id, feats):
    schools = core['magic']['schoolsById']
    owned = {(entry['featId'], entry.get('choices', {}).get('schoolId')) for entry in feats}
    return [dict(schoolId=key, name=school['name']) for key, school in schools.items()
            if school['focusEligible'] and (feat_id, key) not in owned
            and (feat_id != 'greater-spell-focus' or ('spell-focus', key) in owned)]


def focus_bonus(core, spell, feat_choices):
    selected = {(entry['featId'], entry.get('choices', {}).get('schoolId')) for entry in feat_choices}
    school = spell['schoolId']
    if not core['magic']['schoolsById'][school]['focusEligible'] or ('spell-focus', school) not in selected:
        return 0
    return sum(effect['amount'] for feat in FEATS if (feat, school) in selected
               for effect in core['effects']['featEffectsByFeatId'][feat]
               if effect['statId'] == 'spell-save-dc')


def focus_grants(core, feat_choices):
    schools = core['magic']['schoolsById']
    picks = {(e['featId'], e.get('choices', {}).get('schoolId')) for e in feat_choices if e['featId'] in FEATS}
    if any(key not in schools or not schools[key]['focusEligible'] for _, key in picks):
        raise ValueError('Spell Focus requires a valid schoolId')
    return [dict(featId=feat, schoolId=key, label=f"{core['feats']['byId'][feat]['name'].title()}, {schools[key]['name']}")
            for feat, key in sorted(picks)]
