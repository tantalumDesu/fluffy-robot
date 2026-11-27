"""Report structural integrity and selected canon coverage, not full semantic parity."""
import json
import re

if __package__:
    from .effect_policy import POLICY, application_mode
    from .organize_core import PATH, lines
else:
    from effect_policy import POLICY, application_mode
    from organize_core import PATH, lines


if __package__:
    from .condition_rules import condition_policies
else:
    from condition_rules import condition_policies

def audit(core):
    rules = core['mechanics']['rules']
    rule_ids = {rule['id'] for rule in rules}
    spells = core['magic']['spells']
    spell_ids = {spell['id'] for spell in spells}
    conditions = {record['id'] for record in core['effects']['conditions']}
    feats = core['feats']['byId']
    effects = core['effects']
    listed = set(re.findall(r'^- `([a-z][a-z0-9-]+)`(?=[: (])', '\n'.join(lines('RULES.txt')), re.M))
    missing_rules = set(core['progression']['ruleIds']) | {rule_id for c in core['progression']['classes']
                                                            for rule_id in c.get('ruleIds', [])}
    missing_spells = {id_ for spell_list in core['magic']['spellLists'] for level in spell_list['levels']
                      for id_ in level['spellIds']}
    missing_conditions = {ref['conditionId'] for spell in spells for ref in spell.get('conditions', [])}
    typed_spell_ids = (set(effects['spellEffectsBySpellId']) | set(effects.get('negativeLevelOperationsBySpellId', {}))
                       | set(core['magic'].get('alignmentTargetRulesBySpellId', {}))
                       | set(effects.get('conditionCuresBySpellId', {})))
    classes = core['progression']['classes']
    text_categories = {
        'spells': (spells, ('longDescription',)),
        'conditions': (effects['conditions'], ('desc',)),
        'feats': (list(feats.values()), ('benefitText', 'text')),
        'specialAbilities': (effects['specialAbilities'], ('summary', 'paragraphs', 'tables', 'subsections')),
        'classAbilities': ([a for c in classes for a in c.get('abilities', [])], ('description',)),
        'raceTraits': ([t for r in core['progression']['races'] for t in r.get('traits', [])], ('text',)),
        'rules': (rules, ('summary', 'table', 'source')),
        'inventory': (list(core['inventory']['itemsById'].values()), ('raw', 'source')),
        'creatures': (list(core['companions']['creaturesById'].values()), ('raw', 'source')),
        'diseases': (effects['diseases'], ('description', 'note', 'damage')),
        'poisons': (effects['poisons'], ('initialDamage', 'secondaryDamage', 'natureNote')),
    }
    missing_text = {category: [r['id'] for r in records if not any(r.get(key) for key in keys)]
                    for category, (records, keys) in text_categories.items()}
    scoped = [entry for entries in (*effects['spellEffectsBySpellId'].values(),
                                    *effects['featEffectsByFeatId'].values(),
                                    *(r['modifiers'] for r in condition_policies(core).values()))
              for entry in entries]
    focus_choices = feats['weapon-focus']['selection']['specialWeaponChoices']
    errors = {
        'danglingSpellSchoolIds': sorted(s['id'] for s in spells if s.get('schoolId') not in core['magic']['schoolsById']),
        'danglingSpellAttackFocusChoices': sorted(s['id'] for s in spells if s.get('attackProfile')
            and s['attackProfile'].get('weaponFocusChoiceId') not in focus_choices),
        'missingAdjudicationText': {key: value for key, value in missing_text.items() if value},
        'invalidApplicationModes': [e['id'] for e in scoped if e.get('applicationMode') != application_mode(e)],
        'missingGlobalEffectPolicy': [key for key, value in POLICY.items()
                                      if effects['applicationPolicy'].get(key) != value],
        'duplicateRuleIds': sorted({r['id'] for r in rules if sum(other['id'] == r['id'] for other in rules) > 1}),
        'danglingRuleIds': sorted(missing_rules - rule_ids),
        'danglingSpellIds': sorted((missing_spells | typed_spell_ids) - spell_ids),
        'danglingSpellConditionIds': sorted(missing_conditions - conditions),
        'danglingFeatEffectIds': sorted(set(effects['featEffectsByFeatId']) - feats.keys()),
        'spellsWithMissingDescriptions': sorted(s['id'] for s in spells if not all(
            (s.get(field) or '').strip() for field in ('shortDescription', 'longDescription'))),
    }
    return {'errors': errors, 'adjudicationTextCoverage': {key: len(rows) - len(missing_text[key])
                    for key, (rows, _) in text_categories.items()}, 'rulesListedInCanonButAbsent': sorted(listed - rule_ids),
            'spellsWithoutTypedEffects': len(spell_ids - typed_spell_ids),
            'featsWithoutTypedEffects': len(feats.keys() - effects['featEffectsByFeatId'].keys()),
            'featsWithoutSelectionMetadata': sum('selection' not in feat for feat in feats.values())}


if __name__ == '__main__':
    report = audit(json.loads(PATH.read_bytes()))
    print(json.dumps(report, indent=2))
    raise SystemExit(int(any(report['errors'].values())))
