import json
import unittest

from tools.audit_core import audit
from tools.organize_core import PATH, lines


class CombatCatalogTest(unittest.TestCase):
    def test_index_and_source_anchors(self):
        core = json.loads(PATH.read_bytes())
        self.assertEqual(audit(core)['rulesListedInCanonButAbsent'], [])
        rules = {r['id']: r for r in core['mechanics']['rules'] if r.get('automaticApplication') is False}
        self.assertIn('initiative-order', rules)
        for rule in rules.values():
            with self.subTest(rule=rule['id']):
                src = rule['source']
                self.assertEqual(rule['summary'], '\n'.join(lines(src['file'])[src['line']-1:src['endLine']]).strip())
        prone = next(row for row in rules['combat-modifier-tables']['mechanic']['attack'] if row['condition'] == 'Prone')
        self.assertEqual(prone['melee'], -4)
        self.assertEqual(prone['ranged'], 0)
        types = rules['modifier-types']['mechanic']['typesById']
        for key in ('dodge', 'circumstance'):
            self.assertFalse(types[key]['sameTypeBonusStacks'])
            self.assertTrue(types[key]['description'])
