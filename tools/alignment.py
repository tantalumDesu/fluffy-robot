"""Alignment axes, class qualification, and explicit ex-class state."""

OPPOSITES = {'law': 'chaos', 'chaos': 'law', 'good': 'evil', 'evil': 'good'}


def alignment_catalog(lines):
    names = {'LG': 'Lawful Good', 'NG': 'Neutral Good', 'CG': 'Chaotic Good',
             'LN': 'Lawful Neutral', 'N': 'Neutral', 'CN': 'Chaotic Neutral',
             'LE': 'Lawful Evil', 'NE': 'Neutral Evil', 'CE': 'Chaotic Evil'}
    text = lines('ALIGNMENT.txt')
    table = {}
    for key, name in names.items():
        order, morality = ('N', 'N') if key == 'N' else key
        line = next(i for i, value in enumerate(text, 1) if value.startswith(name + ','))
        table[key] = dict(name=name, orderAxis={'L': 'law', 'N': 'neutral', 'C': 'chaos'}[order],
                          moralAxis={'G': 'good', 'N': 'neutral', 'E': 'evil'}[morality],
                          playerStandard=morality != 'E', source={'file': 'ALIGNMENT.txt', 'line': line})
    consequences = {}
    for key, lead, policy, atonement, triggers in (
        ('barbarian', 'A barbarian who becomes lawful', 'lose-rage-only', False, []),
        ('bard', 'A bard who becomes lawful', 'retain-features', False, []),
        ('monk', 'A monk who becomes nonlawful', 'retain-features', False, []),
        ('paladin', 'A paladin who ceases to be lawful good', 'retain-proficiencies-only', True,
         ['willful-evil-act', 'gross-code-violation']),
        ('druid', 'A druid who ceases to revere nature', 'retain-proficiencies-only', True,
         ['cease-revering-nature', 'teach-druidic-to-nondruid']),
        ('cleric', 'A cleric who grossly violates', 'retain-armor-shield-simple-weapons', True,
         ['gross-deity-code-violation']),
    ):
        file = key.upper() + '.txt'
        line = next(i for i, value in enumerate(lines(file), 1) if value.startswith(lead))
        consequences[key] = dict(featurePolicy=policy, requiresAtonement=atonement,
                                 triggeredByIneligibleAlignment=key != 'cleric', conductTriggers=triggers,
                                 source={'file': file, 'line': line})
    for class_name in ('ASSASSIN', 'BLACKGUARD', 'DWARVEN DEFENDER'):
        file = 'Prestige Class ' + class_name + '.txt'
        line = next(i for i, value in enumerate(lines(file), 1) if value.startswith('Alignment Loss (table rule):'))
        consequences[class_name.lower().replace(' ', '-')] = dict(
            featurePolicy='suppress-class-abilities', requiresAtonement=False,
            triggeredByIneligibleAlignment=True, restoresOnCompatibleAlignment=True, conductTriggers=[],
            source={'file': file, 'line': line})
    return table, consequences


def alignment_tags(core, alignment_id):
    entry = core['mechanics']['alignmentsById'][alignment_id]
    return {tag for tag in (entry['orderAxis'], entry['moralAxis']) if tag != 'neutral'}


def source_alignment_context(core, alignment_id, *, base=None):
    return dict(base or {}, sourceAlignmentTags=sorted(alignment_tags(core, alignment_id)))


def class_alignment_status(core, class_id, alignment_id, *, deity_alignment=None, deity_known=False, fallen=()):
    """Return only the alignment/conduct component of eligibility, not all prerequisites."""
    classes = {record['id']: record for record in core['progression']['classes']}
    cls = classes[class_id]
    key = cls['extends'] or class_id
    allowed = classes[key]['alignments']
    catalog = core['mechanics']['alignmentsById']
    alignment = catalog[alignment_id]
    if deity_alignment is not None:
        deity = catalog[deity_alignment]
    if key in fallen:
        return 'atonement-required'
    if allowed and alignment_id not in allowed:
        return 'ineligible'
    if key == 'cleric':
        if deity_alignment is None:
            return 'eligible' if deity_known else 'needs-review'
        values = {'law': -1, 'chaos': 1, 'good': -1, 'evil': 1, 'neutral': 0}
        distance = sum(abs(values[alignment[axis]] - values[deity[axis]]) for axis in ('orderAxis', 'moralAxis'))
        if distance > 1 or (alignment_id == 'N' and deity_alignment != 'N'):
            return 'ineligible'
    return 'eligible'


def evaluate_alignment_change(core, class_ids, new_alignment, *, fallen=(), conduct_events=None,
                              atoned=(), deity_alignment=None, deity_known=False):
    """Caller confirms alignment/conduct/atonement; keep persistent loss until atonement."""
    alignment_tags(core, new_alignment)
    rules = core['mechanics']['alignmentConsequencesByClassId']
    locks = set(fallen) - set(atoned)
    results = {}
    for key in class_ids:
        rule = rules.get(key)
        eligibility = class_alignment_status(core, key, new_alignment, deity_alignment=deity_alignment,
                                             deity_known=deity_known)
        triggers = set((conduct_events or {}).get(key, ()))
        applies = bool(rule and (triggers.intersection(rule['conductTriggers']) or
                       (rule['triggeredByIneligibleAlignment'] and eligibility == 'ineligible')))
        if applies and rule['requiresAtonement']:
            locks.add(key)
        policy = (rule['featurePolicy'] if rule and (applies or key in locks) else
                  'needs-review' if eligibility in ('ineligible', 'needs-review') else 'retain-features')
        results[key] = dict(advancement='atonement-required' if key in locks else eligibility, features=policy)
    return dict(alignmentId=new_alignment, fallenClassIds=sorted(locks), classes=results)


def check_spell_alignment(core, class_id, spell, alignment_id, *, deity_alignment=None, deity_known=False):
    if class_id not in ('cleric', 'druid'):
        return 'eligible'
    descriptors = {tag.casefold() for tag in spell.get('descriptors', ())} & OPPOSITES.keys()
    if not descriptors:
        return 'eligible'
    personal = alignment_tags(core, alignment_id) if alignment_id is not None else set()
    deity = alignment_tags(core, deity_alignment) if deity_alignment is not None else set()
    if any(OPPOSITES[tag] in personal | deity for tag in descriptors):
        return 'ineligible'
    if alignment_id is None or (deity_alignment is None and not deity_known):
        return 'needs-review'
    return 'eligible'


def aligned_burst_plan(core, spell_id, target_alignment_id, caster_level, *, target_is_outsider, will_saved):
    """Determine target-specific damage dice, multiplier and condition; caller rolls."""
    rule = core['magic']['alignmentTargetRulesBySpellId'][spell_id]
    moral = core['mechanics']['alignmentsById'][target_alignment_id]['moralAxis']
    if type(caster_level) is not int or caster_level < 1 or type(will_saved) is not bool or type(target_is_outsider) is not bool:
        raise ValueError('Supply caster level, outsider status, and Will save result')
    if moral == rule['unaffectedAxis']:
        return dict(diceCount=0, dieSides=None, damageDivisor=1, condition=None)
    opposed = moral == rule['opposedAxis']
    stronger = opposed and target_is_outsider
    return dict(diceCount=min(10, caster_level) if stronger else min(5, caster_level // 2),
                dieSides=6 if stronger else 8, damageDivisor=(1 if opposed else 2) * (2 if will_saved else 1),
                condition=rule['condition'] if opposed and not will_saved else None)


def weapon_alignment_tags(core, property_ids):
    """Resolve weapon property tags without substituting them for wielder alignment."""
    catalog = core['inventory']['weaponAlignmentPropertiesById']
    return {catalog[key]['alignmentTag'] for key in property_ids}
