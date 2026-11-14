# Structural Refinement Report (`smoovSailing.md`)

Audit and lossless schema refinement of `fluffy-robot/dnd-core.json` (Stage S36, tool: `tools/stage_s36_refine_schema.mjs`). Every change below preserves **100% of the underlying game data and meaning** while making the JSON smaller, cleaner, more uniform, easier to navigate, and simpler to extend.

---

## 1. Headline Metrics (Before vs. After)

| Metric | Before (S35) | After (S36) | Delta |
|---|---:|---:|---:|
| Pretty-printed `dnd-core.json` | 6.79 MB | **5.42 MB** | **−1.37 MB (−20.1%)** |
| Minified JSON payload | 4.54 MB | **3.57 MB** | **−0.97 MB (−21.4%)** |
| `spells[]` (611 records) | 2,327.7 KB | **1,464.7 KB** | **−863.0 KB (−37.1%)** |
| `classes[]` (42 records) | 787.2 KB | **739.8 KB** | **−47.4 KB (−6.0%)** |
| `stats{}` (98 keys) | 317.3 KB | **265.8 KB** | **−51.5 KB (−16.2%)** |
| `races[]` (15 records) | 157.0 KB | **130.6 KB** | **−26.4 KB (−16.8%)** |
| `meta` | 28.0 KB | **10.6 KB** | **−17.4 KB (−62.1%)** |
| Unified `rules[]` (`schema: 1`) | 17 (+12 in `meta.rules`) | **25 (single source)** | **0 split/duplicate rules** |
| Null noise keys stripped | 7,036 | **0** | **−3,478 effects / −3,558 stats** |
| Validation checks passing | 84 / 84 | **88 / 88** | **+4 schema-hygiene checks** |
| Schema fingerprint (`meta.schema`) | `structure-3f16c939` | **`structure-63eec16b`** | Updated |

---

## 2. Structural Inefficiencies Found & Fixed (Lossless)

### A. Pure Redundancy & Duplicated Mirrors Eliminated (~1.0 MB minified saved)
1. **`spells[]` duplicated prose & derived mirrors (−863 KB):**
   - `shortDescription` was 100% identical to `summary` on all **611 / 611** spells (~34 KB duplicated). Removed `shortDescription`; `summary` is the single canonical short summary (`summaryVariants` kept on the 41 spells that carry per-list variant text).
   - `longDescription` was 100% identical to `description` on all **611 / 611** spells (~505 KB duplicated — half a megabyte copying every spell's prose twice). Removed `longDescription`; `description` is the single canonical full text.
   - `tags` (~243 KB) was a flat copy of 17 fields already stored as typed properties on the exact same spell object (`type`, `traditions`, `school`, `subschools`, `descriptors`, `duration.category`, `range.category`, `components.codes`, `savingThrow.type`, `spellResistance`, `mechanics.damageTypes`, etc.). Removed `tags`.
   - `lists`, `classes`, and `classSpellLevels` stored the exact same class-list memberships three separate ways (~82 KB redundant). Consolidated into one canonical **`lists: [{ listId, class, level }]`** array per spell.
2. **`races[]` redundant `own` blocks (−26.4 KB):**
   - 14 of the 15 races have `inherits: null`, yet all 14 carried a full duplicate `own` summary object alongside `effective` (which had already drifted out of sync when S30 added `weaponProficiencyIds` to `effective`).
   - Removed `own` on non-inheriting races; **`own` is now present only when `inherits !== null`** (`Drow`, where `own` vs. `effective` captures the Elf inheritance delta).
3. **Dual rule storage (`meta.rules` vs. `rules[]`) eliminated:**
   - Previously, rules were split between a legacy `meta.rules` dictionary (12 ad-hoc shapes) and the typed `rules[]` collection (17 `schema: 1` objects), including an active duplication hazard (`meta.rules.bonusSpellsTable` vs. `rules[ability-modifiers-and-bonus-spells]` flagged as **R1** in `dndsucks.md`), duplicate `meta.rules.domainSpellNotes` (already stored on `domains[].spells[].special`), duplicate `meta.rules.spellDcFormula` (already in `rules[derived-combat-stats]`), and stale `meta.rules.speakLanguageKeyAbility` (which still said `ability: null` after S27 resolved B11 to `"None"`).
   - **Promoted all 8 unique rule blocks into `rules[]` as canonical `schema: 1` rules** (bringing `rules[]` from 17 → **25**):
     - `spellcasting-ability-minimums`
     - `spontaneous-spell-conversion`
     - `zero-slot-bonus-spell-casting`
     - `prestige-spellcasting-advancement`
     - `epic-save-and-attack-bonuses`
     - `take-10-and-take-20`
     - `weapon-mechanics`
     - `armor-and-shield-mechanics`
   - Removed `meta.rules` and obsolete `meta.placeholders` (whose only entry was `status: "filled"` referencing old `dnd core.json`).
4. **Sparse `null` noise compacted (−99 KB across `classes[]` & `stats{}`):**
   - **40.0%** of all keys inside `classes[].abilities[].effects[]` (3,478 of 8,685 keys) and **3,558** keys inside `stats{}[]` were explicit `null` placeholders (`amount: null, dice: null, unit: null, bonusType: null, condition: null, state: null, level: null`).
   - Stripped `null` optional keys from effect objects, `stats{}` entries, and `stateChanges[]`, keeping every populated key untouched.
5. **Other minor duplicates cleaned:**
   - `conditions[].mechanics.modifiers[]`: removed 43 redundant `type` keys that duplicated `kind` (`"penalty"` / `"bonus"`).
   - Uniform `reviewFlags`: omitted empty `reviewFlags: []` across all collections so `reviewFlags` appears **only** on records that actually carry a flag.

---

### B. Cross-Collection Field Naming Harmonized
Previously, fields grew organically across 35 stages and used inconsistent names for identical concepts:

| Concept | Before (inconsistent) | After (unified everywhere) |
|---|---|---|
| Provenance filename | `file` (`classes`, `skills`, `spells`, `spellLists`), `source` (10 collections), missing (`domains`, `synergies`) | **`source`** on all 16 collections |
| Full rules prose | `desc` (`conditions`), `description` + `longDescription` (`spells`), `description` (others) | **`description`** everywhere |
| Short 1-line summary | `summary` + `shortDescription` (`spells`), `summary` (others) | **`summary`** everywhere |
| Modifier polarity | `kind` + `type` (`conditions`) | **`kind`** (`"penalty"` \| `"bonus"`) |
| Rule store | Split across `meta.rules{}` and `rules[]` | **`rules[]`** (`schema: 1` uniform envelope) |

Every record across every collection now also follows a predictable **per-record key order**:
1. Identity & provenance (`id`, `name`, `type`/`category`, `source`)
2. Prose (`summary`, `description`)
3. Typed mechanics, stats & tables
4. Cross-references (`*Refs`, `references`, `classSkillFor`, `favoredByRaces`, etc.)
5. `reviewFlags` (only if present)

---

### C. Less Cumbersome, Architectural Ordering

#### 1. Top-Level Keys (21 keys — grouped like the PHB/DMG instead of chronological append order)
Previously, top-level keys appeared in the order files were added (`meta, classes, domains, skills, synergies, spells, spellLists, stats, stateChanges, rules, conditions, races, specialAbilities, ..., feats, specialAttacks, weapons, armor`). They are now ordered into 6 intuitive architectural groups while staying **flat at the top level** (preserving clean `$.collection[i]` JSONPaths):

1. **Metadata & Unified Rules**: `meta`, `rules`
2. **Character Options**: `races`, `classes`, `skills`, `synergies`, `feats`
3. **Equipment**: `weapons`, `armor`
4. **Magic**: `spells`, `spellLists`, `domains`
5. **Combat & Special Mechanics**: `specialAttacks`, `conditions`, `specialAbilities`, `specialAbilityTypes`, `diseases`, `poisons`, `listenCheckDCs`
6. **Derived Reverse Indexes**: `stats`, `stateChanges`

#### 2. Within-Collection Ordering Fixed
| Collection | Before (cumbersome) | After (clean & predictable) |
|---|---|---|
| `classes[]` (42) | Interleaved by `.txt` filename (`Barbarian..Druid`, `Epic *`, `Fighter..Monk`, `NPC *`, `Paladin`, `Prestige *`, `Ranger..Wizard`) | **Grouped by tier**: `base` (11 A–Z) → `prestige` (14 A–Z) → `npc` (6 A–Z) → `epic` (11 A–Z) |
| `races[]` (15) | Paste order (`Bugbear..Tiefling`, then `Aasimar, Goblin, Half-Elf` tacked on at the end) | **Strict A–Z** (`Aasimar` → `Tiefling`) |
| `diseases[]` (10) | Almost A–Z, except `The Shakes` sat before `Slimy doom` | **Strict A–Z** (`Blinding sickness` → `The Shakes`) |
| `synergies[]` (29) | Random scrape order | **Sorted by `from.skillId` → `to.skillId / toCheck`** |
| `spellLists[]` (10) | Mixed order | **Grouped by tier**: base A–Z → prestige A–Z → NPC A–Z |
| `rules[]` (25) | Chronological stage append order | **Grouped by category** (`character-creation` → `multiclassing` → `class-mechanic` → `spellcasting` → `skills` → `combat` → `equipment`) → `id` A–Z |
| `stats{}` (98) | Insertion order | **Keys A–Z**; entries sorted by `ownerType`, `ownerId`, `ability` |
| `stateChanges[]` (8) | Unsorted | **Sorted by `classId`, `ability`, `name`** |

**Intentionally preserved canonical table orders** (better than alphabetical for rules lookup):
- `weapons[]` (77): Simple → Martial → Exotic, grouped by handedness (Unarmed → Light → One-Handed → Two-Handed → Ranged → Ammunition)
- `armor[]` (21): Light → Medium → Heavy → Shield → Extra
- `poisons[]` (34): Contact → Ingested → Inhaled → Injury, ordered by DC
- `feats[]` (123): Core (110 A–Z) → Epic (13 A–Z)
- `specialAbilities[]` (34): Overview (`Special Abilities`) first, then A–Z

---

## 3. Extensibility Guidelines Going Forward

When adding new files (e.g., `EQUIPMENT.txt`, `MONSTERS.txt`, `MAGIC ITEMS.txt`, `EPIC SPELLS.txt`):
1. **Top-level arrays** of `{ id, name, source, ... }` records, placed in the matching domain group (e.g., `gear` right after `armor`; `monsters` after `poisons`).
2. **All game rules live exclusively in `rules[]`** using the `schema: 1` envelope (`schema`, `id`, `name`, `category`, `status`, `source`, `summary`, `appliesTo`, `mechanic`). Never add new rules under `meta`.
3. **Never duplicate prose or derived tag bags** (`shortDescription`/`longDescription`/`tags`): store one canonical `summary` and one canonical `description`, and derive search/filter indexes in memory at load time.
4. **Always use `source` (not `file`)**, `description` (not `desc`), omit empty `reviewFlags`, and omit `null` noise keys on sparse modifier/effect objects.
5. **Run `node tools/stage_s36_refine_schema.mjs`** after major additions to re-enforce ordering, key hygiene, schema fingerprinting, and full validation.

---

## 4. Explorer Updates Applied Alongside This Refinement
- **Deleted the 1st-level character creator UI** (`src/views/CharacterBuilderView.tsx` removed; `builder` tab removed from `src/App.tsx` and `src/types/dnd.ts`). The 10 Stage S33 character-creation rules remain intact inside `rules[]` and `RULES.txt`.
- **Synced all explorer views** to the harmonized schema (`conditions[].description`, `spells[].summary`/`description`/`lists`, `source` across all views, `rules[]` for `armor-and-shield-mechanics` and `epic-save-and-attack-bonuses`, and added `smoovSailing.md` to the **Audit & Logs** tab).
