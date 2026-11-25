"""Compare retained adjudication prose with the TXT baseline."""
import difflib
import json
import re
from collections import defaultdict

if __package__:
    from .source_text import normalized, spell_sources
    from .organize_core import PATH, lines
else:
    from source_text import normalized, spell_sources
    from organize_core import PATH, lines




def audit_source(core):
    findings = defaultdict(list)
    counts = defaultdict(int)

    def compare(category, key, actual, expected, *, contained=False):
        counts[category] += 1
        a, e = normalized(actual), normalized(expected)
        if (a in e and bool(a)) if contained else a == e:
            return
        if contained:
            findings[category].append({'id': key, 'excerpt': actual[:240]})
            return
        delta = list(difflib.ndiff(e.split(), a.split()))
        findings[category].append({'id': key, 'missing': ' '.join(w[2:] for w in delta if w.startswith('- '))[:300],
                                  'added': ' '.join(w[2:] for w in delta if w.startswith('+ '))[:300]})

    sources = spell_sources(lines)
    for record in core['magic']['spells']:
        key = normalized(record['name'])
        if key not in sources:
            findings['unmatchedSpell'].append(record['id'])
            continue
        short, long = sources[key]
        compare('spellSummary', record['id'], record['shortDescription'], short)
        compare('spellDescription', record['id'], record['longDescription'], long)
    txt = lines('CONDITIONS.txt')
    conditions = core['effects']['conditions']
    for i, record in enumerate(conditions):
        start = record['mechanics']['source']['line'] - 1
        end = conditions[i+1]['mechanics']['source']['line'] - 1 if i+1 < len(conditions) else len(txt)
        expected = '\n'.join(txt[start:end]).split(':', 1)[1].split('Tracking progressive fatigue:', 1)[0]
        compare('conditionDescription', record['id'], record['desc'], expected)
    for record in core['feats']['byId'].values():
        src = record['source']
        block = []
        for line in lines(src['file'])[src['line']:]:
            if re.search(r'\[(?:GENERAL|EPIC|ITEM CREATION|METAMAGIC|SPECIAL|DIVINE|WILD|PSIONIC)[^]]*\]\s*$', line, re.I):
                break
            block.append(line)
        compare('featDescription', record['id'], record['text'], '\n'.join(block))
    for record in core['progression']['classes']:
        source = '\n'.join(lines(record['file']))
        for ability in record.get('abilities', []):
            compare('classAbilityDescription', f"{record['id']}:{ability['id']}", ability['description'], source,
                    contained=True)
    race_source = '\n'.join(lines('RACES.txt'))
    for record in core['progression']['races']:
        for trait in record.get('traits', []):
            compare('raceTraitDescription', trait['id'], trait['text'], race_source, contained=True)
    special_source = '\n'.join(lines('SPECIAL ABILITIES.txt'))
    for record in core['effects']['specialAbilities']:
        for i, paragraph in enumerate(record.get('paragraphs', [])):
            compare('specialAbilityParagraph', f"{record['id']}:{i + 1}", paragraph['text'], special_source,
                    contained=True)
    return {'compared': dict(counts), 'findings': dict(findings)}


if __name__ == '__main__':
    print(json.dumps(audit_source(json.loads(PATH.read_bytes())), indent=2))
