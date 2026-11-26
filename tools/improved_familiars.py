"""Improved Familiar options and eligibility from the dedicated table."""

FILE = 'IMPROVED FAMILIARS.txt'
ALIGNMENTS = {'LG', 'NG', 'CG', 'LN', 'N', 'CN', 'LE', 'NE', 'CE'}


def catalog(lines, source, slug):
    rows = lines(FILE)
    header = rows.index('Familiar\tAlignment\tMinimum Wizard Level\tMinimum BAB')
    entries = []
    for i in range(header + 1, len(rows)):
        if not rows[i].strip():
            break
        name, alignment, level, bab = (value.strip() for value in rows[i].split('\t'))
        if alignment not in ALIGNMENTS or not name:
            raise ValueError(f'Invalid improved familiar row {i + 1}')
        key = slug(name)
        heading = {'formian-worker': 'Formian, Worker', 'quasit': 'Demon, Quasit',
                   'viper-medium': 'Snake, Viper Medium',
                   'vargouille-without-kiss': 'Vargouille'}.get(key, name)
        entries.append((next(j for j in range(i + 1, len(rows)) if rows[j].strip().casefold() == heading.casefold()),
                        dict(id=key, name=name, alignmentId=alignment, minimumWizardLevel=int(level),
                             minimumBaseAttackBonus=None if bab in ('', '—') else int(bab),
                             source=source(FILE, line=i + 1))))
    entries.sort(key=lambda entry: entry[0])
    result = {}
    for index, (start, entry) in enumerate(entries):
        end = entries[index + 1][0] if index + 1 < len(entries) else len(rows)
        entry['statBlockText'] = '\n'.join(rows[start:end]).strip()
        entry['statBlockSource'] = source(FILE, line=start + 1, endLine=end)
        if entry['id'] == 'vargouille-without-kiss':
            entry['excludedAbilityIds'] = ['kiss']
            entry['adjudicationText'] = 'The familiar does not have Kiss; ignore it in the retained base stat block.'
        if entry['id'] in result:
            raise ValueError(f'Duplicate improved familiar: {entry["id"]}')
        result[entry['id']] = entry
    return result


def check_improved_familiar(core, option_id, snapshot):
    """Check acquisition, separately from learning the feat; never acquire an actor."""
    options = core['companions']['improvedFamiliarOptionsById']
    option = options.get(option_id)
    failed, review = [], []

    def check(value, label):
        if value is None:
            review.append(label)
        elif not value:
            failed.append(label)

    feats = snapshot.get('feats')
    check(None if feats is None else any(f['featId'] == 'improved-familiar' for f in feats), 'Improved Familiar feat')
    can_acquire = snapshot.get('canAcquireFamiliar')
    check(can_acquire if type(can_acquire) is bool else None, 'Can acquire a new familiar now')
    if option is None:
        review.append('Unlisted familiar: confirm eligibility with the DM')
    else:
        levels = snapshot.get('classLevels')
        check(None if levels is None else levels.get('wizard', 0) >= option['minimumWizardLevel'], 'Minimum Wizard level')
        bab = snapshot.get('baseAttackBonus')
        minimum = option['minimumBaseAttackBonus']
        if minimum is not None:
            check(None if bab is None else bab >= minimum, 'Minimum base attack bonus')
        alignments = core['mechanics']['alignmentsById']
        actual = alignments.get(snapshot.get('alignmentId'))
        target = alignments[option['alignmentId']]
        check(None if actual is None else all(actual[axis] == target[axis] or 'neutral' in (actual[axis], target[axis])
              for axis in ('orderAxis', 'moralAxis')), 'Compatible alignment on both axes')
    return dict(status='ineligible' if failed else 'needs-review' if review else 'eligible',
                failed=failed, needsReview=review, option=option)
