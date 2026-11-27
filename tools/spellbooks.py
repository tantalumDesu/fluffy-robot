"""Wizard spellbook instances; immutable updates and numbered page capacity."""


def spellbook_catalog(lines, source):
    file = 'WIZARD.txt'
    line = next(i for i, row in enumerate(lines(file), 1) if row.startswith('Spellbooks:'))
    study_line = next(i for i, row in enumerate(lines(file), 1) if row.startswith('Learning from a Scroll'))
    specialty_line = lines(file).index('SCHOOL SPECIALIZATION') + 1
    return dict(externalLearning=dict(studyDays=1, inscriptionDays=1, spellcraftBaseDc=15, retryRankIncrease=1,
                                     materialsGpPerPage=100, consumeScrollOnSuccess=True, source=source(file, line=study_line)),
                specialization=dict(defaultProhibitedSchoolCount=2, prohibitedSchoolCountBySpecialty={'divination': 1},
                                    cannotProhibitSchoolIds=['divination'], spellcraftLearningBonus=2,
                                    extraSlotsPerSpellLevel=1, chooseAtWizardLevel=1, optional=True, permanent=True,
                                    source=source(file, line=specialty_line)),
                classId='wizard', spellListId='sorcerer-wizard', standardPages=100, standardItemId='gear:spellbook-wizard-s-blank',
                minimumPagesPerSpell=1, pagesPerSpellLevel=1, requiredForLearning=True,
                requiredForPreparation=True, source=source(file, line=line))


def new_spellbook(core, instance_id):
    """Create a blank standard book. Ownership and access live with inventory."""
    rule = core['magic']['wizardSpellbook']
    return dict(instanceId=instance_id, itemId=rule['standardItemId'], capacityPages=rule['standardPages'], spellsById={})


def pages_used(book, rule):
    capacity = book['capacityPages']
    if type(capacity) is not int or capacity < 1:
        raise ValueError('Spellbook capacity must be a positive integer')
    levels = book['spellsById'].values()
    if any(type(level) is not int or level < 0 for level in levels):
        raise ValueError('Invalid spellbook entry level')
    used = sum(max(rule['minimumPagesPerSpell'], level * rule['pagesPerSpellLevel']) for level in levels)
    if used > capacity:
        raise ValueError('Spellbook capacity exceeded')
    return used


def learn_wizard_spells(core, book, spell_ids, *, specialization=None):
    """Record confirmed Wizard learning or copying; it is atomic across the batch."""
    rule = core['magic']['wizardSpellbook']
    if book is None:
        raise ValueError('Learning Wizard spells requires a spellbook')
    pages_used(book, rule)
    wizard_levels = {spell['id']: row['level'] for spell in core['magic']['spells']
                     for row in spell['lists'] if row['listId'] == rule['spellListId'] and school_access(core, spell, specialization)}
    entries = dict(book['spellsById'])
    for key in spell_ids:
        if key not in wizard_levels:
            raise ValueError(f'Spell is not available on this Wizard spell list: {key}')
        entries[key] = wizard_levels[key]
    result = dict(book, spellsById=entries)
    pages_used(result, rule)
    return result


def wizard_specialization(core, specialty_school_id=None, prohibited_school_ids=()):
    """Validate and normalize the Wizard's permanent school choices."""
    rule = core['magic']['wizardSpellbook']['specialization']
    prohibited = tuple(prohibited_school_ids)
    available = {key for key, school in core['magic']['schoolsById'].items() if school['focusEligible']}
    count = (0 if specialty_school_id is None else
             rule['prohibitedSchoolCountBySpecialty'].get(specialty_school_id, rule['defaultProhibitedSchoolCount']))
    if ((specialty_school_id is not None and specialty_school_id not in available) or
            len(prohibited) != count or len(set(prohibited)) != count or
            not set(prohibited) <= available or set(prohibited).intersection(rule['cannotProhibitSchoolIds']) or
            specialty_school_id in prohibited):
        raise ValueError('Invalid Wizard specialty or prohibited schools')
    return dict(specialtySchoolId=specialty_school_id, prohibitedSchoolIds=sorted(prohibited))


def school_access(core, spell, specialization):
    options = specialization or {}
    validated = wizard_specialization(core, options.get('specialtySchoolId'), options.get('prohibitedSchoolIds', ()))
    return spell['schoolId'] not in validated['prohibitedSchoolIds']


def wizard_spell_item_school_allowed(core, spell_id, specialization=None):
    """School gate for Wizard use of a scroll or wand; not a full item-use check."""
    spell = next(spell for spell in core['magic']['spells'] if spell['id'] == spell_id)
    return school_access(core, spell, specialization)


def new_wizard_learning():
    return dict(failedRanksBySpellId={}, understoodAtDayBySpellId={}, knownSpellIds=[])


def begin_wizard_study(core, learning, destination, source, spell_id, *, day, spellcraft_ranks, specialization=None):
    """Start study with caller-confirmed access to a source and destination book."""
    rule = core['magic']['wizardSpellbook']
    if type(day) is not int or day < 0 or type(spellcraft_ranks) is not int or spellcraft_ranks < 0:
        raise ValueError('Supply a nonnegative campaign day and Spellcraft ranks')
    if destination is None:
        raise ValueError('Learning Wizard spells requires a spellbook')
    pages_used(destination, rule)
    if learning.get('pendingStudy'):
        raise ValueError('A Wizard study is already pending')
    spell = next((spell for spell in core['magic']['spells'] if spell['id'] == spell_id), None)
    level = next((r['level'] for r in spell['lists'] if r['listId'] == rule['spellListId']), None) if spell else None
    if level is None or not school_access(core, spell, specialization):
        raise ValueError('Spell unavailable to this Wizard')
    if (spell_id in learning['knownSpellIds'] or spell_id in destination['spellsById'] or
            spell_id in learning['understoodAtDayBySpellId']):
        raise ValueError('Spell is already known or understood')
    prior = learning['failedRanksBySpellId'].get(spell_id)
    if prior is not None and spellcraft_ranks < prior + rule['externalLearning']['retryRankIncrease']:
        raise ValueError('Gain another Spellcraft rank before retrying this spell')
    kind = source['kind']
    if kind == 'scroll':
        valid = source.get('spellId') == spell_id and not source.get('consumed', False)
    elif kind == 'spellbook':
        valid = source.get('spellsById', {}).get(spell_id) == level and source['instanceId'] != destination['instanceId']
    else:
        valid = False
    if not valid:
        raise ValueError('Source does not contain an available copy of this spell')
    external = rule['externalLearning']
    return dict(learning, pendingStudy=dict(spellId=spell_id, sourceInstanceId=source['instanceId'], sourceKind=kind,
                startDay=day, checkDay=day + external['studyDays'], checkDc=external['spellcraftBaseDc'] + level,
                specialtySpellcraftBonus=rule['specialization']['spellcraftLearningBonus'] if
                spell['schoolId'] == (specialization or {}).get('specialtySchoolId') else 0,
                spellcraftRanks=spellcraft_ranks))


def finish_wizard_study(core, learning, *, day, spellcraft_total):
    """Resolve the supplied check total excluding the separate specialty bonus."""
    pending = learning.get('pendingStudy')
    if not pending or type(day) is not int or day < pending['checkDay'] or type(spellcraft_total) is not int:
        raise ValueError('Study must be complete and a Spellcraft total supplied')
    spell = pending['spellId']
    success = spellcraft_total + pending['specialtySpellcraftBonus'] >= pending['checkDc']
    failed = dict(learning['failedRanksBySpellId'])
    understood = dict(learning['understoodAtDayBySpellId'])
    if success:
        understood[spell] = day
        failed.pop(spell, None)
    else:
        failed[spell] = pending['spellcraftRanks']
    rule = core['magic']['wizardSpellbook']['externalLearning']
    consumed = pending['sourceInstanceId'] if success and pending['sourceKind'] == 'scroll' and rule['consumeScrollOnSuccess'] else None
    return dict(learning=dict(learning, pendingStudy=None, failedRanksBySpellId=failed,
                              understoodAtDayBySpellId=understood), success=success, consumedScrollInstanceId=consumed)


def inscribe_understood_spell(core, learning, book, spell_id, *, start_day, day, materials_gp, specialization=None):
    """Finish confirmed inscription and return updated book, known spells and funds."""
    rule = core['magic']['wizardSpellbook']
    understood = learning['understoodAtDayBySpellId'].get(spell_id)
    external = rule['externalLearning']
    if (understood is None or type(start_day) is not int or type(day) is not int or
            start_day < understood or day < start_day + external['inscriptionDays']):
        raise ValueError('Inscription requires a full day after the spell is understood')
    if book is not None and spell_id in book['spellsById']:
        raise ValueError('Spell is already in the destination book')
    updated = learn_wizard_spells(core, book, [spell_id], specialization=specialization)
    cost = max(0, pages_used(updated, rule) - pages_used(book, rule)) * external['materialsGpPerPage']
    if type(materials_gp) is not int or materials_gp < cost:
        raise ValueError('Insufficient inscription materials')
    remaining = dict(learning['understoodAtDayBySpellId'])
    del remaining[spell_id]
    return dict(book=updated, learning=dict(learning, understoodAtDayBySpellId=remaining,
                knownSpellIds=sorted(set(learning['knownSpellIds']) | {spell_id})),
                materialsGpSpent=cost, materialsGpRemaining=materials_gp - cost)


def choose_wizard_specialization(core, *, wizard_class_level, existing_choice=None,
                                 specialty_school_id=None, prohibited_school_ids=()):
    """Record the first Wizard level's permanent choice, including generalist."""
    rule = core['magic']['wizardSpellbook']['specialization']
    if existing_choice is not None:
        raise ValueError('The Wizard school choice is already recorded and cannot change')
    if type(wizard_class_level) is not int or wizard_class_level != rule['chooseAtWizardLevel']:
        raise ValueError('Wizard school specialization can only be chosen at Wizard class level 1')
    return wizard_specialization(core, specialty_school_id, prohibited_school_ids)


def add_spellbook(core, books, instance_id):
    """Add another physical book without replacing any existing volume."""
    if not instance_id or instance_id in books:
        raise ValueError('Spellbook instance IDs must be unique and nonempty')
    return dict(books, **{instance_id: new_spellbook(core, instance_id)})


def available_spellbooks(books, accessible_ids):
    """Resolve inventory access; damage is adjudicated per entry by the table."""
    return tuple(dict(book, spellsById={key: level for key, level in book['spellsById'].items()
                                       if key not in book.get('damagedSpellIds', ())})
                 for key in dict.fromkeys(accessible_ids) if (book := books.get(key)) is not None
                 and not book.get('lost') and not book.get('destroyed'))


def update_spellbook(core, books, book):
    """Commit a single book update (inscription, damage, loss or recovery)."""
    key = book['instanceId']
    if key not in books:
        raise ValueError('Unknown spellbook instance')
    if not set(book.get('damagedSpellIds', ())) <= book['spellsById'].keys():
        raise ValueError('Damage must name entries in this spellbook')
    pages_used(book, core['magic']['wizardSpellbook'])
    return dict(books, **{key: book})
