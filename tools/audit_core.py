"""Report structural integrity and selected canon coverage, not full semantic parity."""
import json
import re

if __package__:
    from .organize_core import PATH, lines
else:
    from organize_core import PATH, lines


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
    errors = {
        'duplicateRuleIds': sorted({r['id'] for r in rules if sum(other['id'] == r['id'] for other in rules) > 1}),
        'danglingRuleIds': sorted(missing_rules - rule_ids),
        'danglingSpellIds': sorted((missing_spells | set(effects['spellEffectsBySpellId'])) - spell_ids),
        'danglingSpellConditionIds': sorted(missing_conditions - conditions),
        'danglingFeatEffectIds': sorted(set(effects['featEffectsByFeatId']) - feats.keys()),
        'spellsWithMissingDescriptions': sorted(s['id'] for s in spells if not all(
            (s.get(field) or '').strip() for field in ('shortDescription', 'longDescription'))),
    }
    return {'errors': errors, 'rulesListedInCanonButAbsent': sorted(listed - rule_ids),
            'spellsWithoutTypedEffects': len(spell_ids - effects['spellEffectsBySpellId'].keys()),
            'featsWithoutTypedEffects': len(feats.keys() - effects['featEffectsByFeatId'].keys()),
            'featsWithoutSelectionMetadata': sum('selection' not in feat for feat in feats.values())}


if __name__ == '__main__':
    report = audit(json.loads(PATH.read_bytes()))
    print(json.dumps(report, indent=2))
    raise SystemExit(int(any(report['errors'].values())))
