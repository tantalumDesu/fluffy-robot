import json
import unittest

from tools.audit_core import audit
from tools.organize_core import PATH, lines


class AuditCoreTest(unittest.TestCase):
    def test_reference_integrity_and_spell_swap_sources(self):
        core = json.loads(PATH.read_bytes())
        self.assertFalse(any(audit(core)['errors'].values()))
        rules = {rule['id']: rule for rule in core['mechanics']['rules']}
        self.assertNotIn('spell-replacement', rules)
        for class_id, stated, derived in (
            ('bard', [5, 8, 11], [14, 17, 20]), ('sorcerer', [4, 6, 8], [10, 12, 14, 16, 18, 20]),
            ('assassin', [6, 8, 10], []),
        ):
            key = class_id + '-spell-swap'
            rule = rules[key]
            anchor = rule['source']
            self.assertEqual(lines(anchor['file'])[anchor['line'] - 1], anchor['excerpt'])
            params = rule['mechanic']['parameters']
            self.assertEqual((params['statedEligibleLevels'], params['derivedEligibleLevels']), (stated, derived))
            klass = next(c for c in core['progression']['classes'] if c['id'] == class_id)
            self.assertIn(key, klass['ruleIds'])
