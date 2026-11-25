import json
import unittest

from tools.organize_core import PATH
from tools.source_audit import audit_source


class SourceAuditTest(unittest.TestCase):
    def test_source_descriptions_preserved(self):
        core = json.loads(PATH.read_bytes())
        report = audit_source(core)
        for category in ('unmatchedSpell', 'spellSummary', 'spellDescription', 'conditionDescription',
                         'featDescription', 'raceTraitDescription', 'specialAbilityParagraph'):
            self.assertFalse(report['findings'].get(category), category)
        ward = next(s for s in core['magic']['spells'] if s['id'] == 'protection-from-energy')
        self.assertIn('same absorption pool', ward['longDescription'])
