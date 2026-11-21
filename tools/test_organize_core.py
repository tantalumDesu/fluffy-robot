import json
import unittest

from tools.organize_core import GROUPS, PATH, ROOT, build


class CoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = json.loads(PATH.read_bytes())

    def test_idempotent_and_lossless(self):
        core = self.core
        self.assertEqual(build(core), core)
        meta = core['meta'].copy()
        for field in ('schema', 'validation', 'counts'):
            meta[field] = meta.pop('legacy' + field.title())
        meta['rules'] = core['mechanics']['lookups']
        legacy = {'meta': meta, **{key: core[group][key] for group, keys in GROUPS.items() for key in keys}}
        legacy['spells'] = [dict(spell, description=spell['longDescription'], summary=spell['shortDescription'])
                            for spell in legacy['spells']]
        self.assertEqual(build(legacy), core)

    def test_spell_descriptions_have_no_aliases(self):
        for spell in self.core['magic']['spells']:
            self.assertNotIn('description', spell)
            self.assertNotIn('summary', spell)
            self.assertTrue(spell['longDescription'].strip())
            self.assertTrue(spell['shortDescription'].strip())

    def test_multiclass_and_spell_references(self):
        classes = {row['id']: row for row in self.core['progression']['classes']}
        self.assertEqual(sum(classes[id_]['progression'][0]['fort'] for id_ in ('fighter', 'barbarian')), 4)
        spell_ids = {spell['id'] for spell in self.core['magic']['spells']}
        self.assertTrue(set(self.core['effects']['spellEffectsBySpellId']) <= spell_ids)
        for spell_list in self.core['magic']['spellLists']:
            for level in spell_list['levels']:
                self.assertTrue(set(level['spellIds']) <= spell_ids)

    def test_progression_rules(self):
        core = self.core
        rules = {r['id']: r for r in core['mechanics']['rules']}
        for rule_id in core['progression']['ruleIds']:
            anchor = rules[rule_id]['source']
            text = (ROOT / anchor['file']).read_text(encoding='utf-8').splitlines()
            self.assertTrue(text[anchor['line'] - 1].startswith(anchor['headingOrLead']))
        xp = rules['character-advancement']['mechanic']
        thresholds = {row['characterLevel']: row['minimumXp'] for row in xp['thresholds']}
        self.assertEqual([thresholds[level] for level in (1, 2, 3, 4, 5, 20)], [0, 1000, 3000, 6000, 10000, 190000])
        # The source example caps a level-3 character's 11,000 XP total at 9,999.
        self.assertEqual(xp['maxLevelsPerAdventureAward'], 1)
        self.assertEqual(min(5000 + 6000, thresholds[3 + xp['maxLevelsPerAdventureAward'] + 1] - 1), 9999)
        skills = rules['skill-points-and-ranks']['mechanic']
        self.assertEqual((skills['purchaseClassSkillScope'], skills['capClassSkillScope']), ('class-advanced', 'any-class-taken'))
        self.assertEqual(skills['crossClassRanksPerPoint'], 0.5)
        self.assertEqual(rules['multiclassing-progression']['mechanic']['startingBenefits'], 'first-character-level-only')
        option = core['rulesets']['optionsById']['multiclass-xp-penalty']
        self.assertFalse(option['defaultEnabled'])
        self.assertEqual(rules[option['ruleId']]['mechanic']['percentPerClass'], 20)

    def test_mundane_weights_match_source(self):
        items = self.core['inventory']['itemsById']
        text = (ROOT / 'MUNDANE ITEMS.txt').read_text(encoding='utf-8').splitlines()
        gear = [item for item in items.values() if item['kind'] == 'gear']
        self.assertEqual(sum(1 + len(item.get('aliases', [])) for item in gear), len(text) - 2)
        for item in gear:
            for entry in [item, *item.get('aliases', [])]:
                row = text[entry['source']['line'] - 1].split('\t')
                self.assertEqual(item['weightLb'], float(row[3]), entry['name'])
        self.assertEqual(items['gear:backpack-empty']['weightLb'], 2)
        self.assertEqual(items['gear:fishhook']['weightLb'], 0.01)

    def test_equipment_and_companion_sources(self):
        inventory = self.core['inventory']
        creatures = self.core['companions']['creaturesById']
        self.assertEqual(inventory['itemsById']['weapon:dart']['weightLb'], 0.5)
        self.assertEqual(inventory['itemsById']['weapon:dart']['priceCp'], 50)
        self.assertEqual(inventory['itemsById']['armor:full-plate']['armorClassBonus'], 8)
        self.assertEqual(inventory['carryingCapacity'][9]['heavyLb'], 100)
        for animal in inventory['packAnimalsById'].values():
            self.assertIn(animal['purchaseItemId'], inventory['itemsById'])
            if animal['creatureId']:
                self.assertIn(animal['creatureId'], creatures)
        ape = creatures['alternative-animal-companions:ape']
        self.assertEqual((ape['minimumMasterLevel'], ape['effectiveLevelAdjustment']), (4, -3))
        for creature in creatures.values():
            anchor = creature['source']
            text = (ROOT / anchor['file']).read_text(encoding='utf-8').splitlines()
            self.assertEqual(text[anchor['line'] - 1], creature['name'])
            self.assertEqual(set(creature['abilityScores']), set(('str', 'dex', 'con', 'int', 'wis', 'cha')))


if __name__ == '__main__':
    unittest.main()
