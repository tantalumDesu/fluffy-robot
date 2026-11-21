# D&D 3.5 rules core

`dnd-core.json` v2 is shared rules data, not a character save or a rules engine. The repository's `.txt` files are the reference baseline. Existing entity IDs and records are retained, with redundant spell description aliases removed. Consumers of v1 need to update their top-level paths and use `longDescription` and `shortDescription` instead of `description` and `summary` on spells. Legacy counts and validation describe the old snapshot, not v2 automation coverage.

| v2 section | Consumer contract |
| --- | --- |
| `progression` | Races and classes, including prestige, NPC and epic classes. Use class progression rows for standard class-level contributions; don't add derived rates on top. Store an ordered level history so the sheet can distinguish character level, class level, effective spellcasting level and eligibility at the time of each choice. |
| `skills`, `feats` | Existing skills and synergies; indexed general and epic feat entries. Feat text is reference-only, not an executable prerequisite or benefit. Record skill purchases by level and feat choices with any selections they require. |
| `magic` | Spell definitions, list membership and domains. Store learned/prepared spells and expended slots per casting class, including the chosen destination of prestige casting advancement. |
| `effects` | Conditions and special abilities, plus explicit spell- and feat-effect catalogs keyed by entity ID. A prose mention is not a grant. Benefits absent from the catalogs remain manual. |
| `inventory` | Purchasable definitions with prices in integer copper pieces, known weights in pounds, armor/weapon table fields, pack animal purchase links and Strength 1–29 load thresholds. Raw table cells are retained. `null` is not zero; consult the raw field for dashes, special cases or missing values. Mundane gear prices and weights come from `MUNDANE ITEMS.txt`. `fallbackWeaponId` is unarmed strike; attack profiles with `carriedSeparately: false` do not create inventory stacks. Shield bashes and spiked attacks reference their equipped host, and spike additions contribute zero weight. Size/body-plan adjustments, special gear and load penalties still need evaluation rules. |
| `companions` | Source-backed base creature records and separate familiar and animal companion advancement tables. Use the companion's adjusted effective master level to select its advancement row. A purchased beast does not gain companion advancement just because it uses the same base creature definition. Donkeys/mules and oxen have prices but no linked stat blocks. |
| `positioning` | Source pointers for combat positioning, reach, modifiers and initiative; not a grid or movement evaluator. |
| `mechanics` | Existing `rules` and former `meta.rules` (now `lookups`), plus Listen lookup. A rule described in `RULES.txt` is not necessarily present as a typed record. |
| `rulesets` | Baseline and an opt-in option registry. The multiclass XP penalty has structured parameters and defaults off; the sheet must still evaluate it. |
| `referenceIndexes` | Former top-level `stats` and `stateChanges`. Use for browsing, not as extra modifier inputs. |

## Applying sheet effects

`spellEffectsBySpellId` and `featEffectsByFeatId` contain source-backed benefits, not full casting or feat-eligibility rules. When the player confirms an application, the sheet should store the effect ID, recipient, selection parameters, caster level if applicable, and expiry on the target actor. Feats with selections use canonical `skillId` or `weaponId` values; Dodge uses the chosen `opponentId`. Alertness granted by familiar proximity requires the caller to establish eligibility before activating it.

`tools.sheet_effects.modifier_total` is a reference resolver for a single stat. Supply active `(effect, parameters)` pairs and include comparable equipment modifiers in the same calculation so their bonus types can compete. Use `save:will` (or `save:fort`/`save:ref`), `skill:<id>`, and `ability:<id>` for specific checks. Context can include `weaponId`, `attackerId`, `sourceAlignmentTags` (e.g. `["law", "evil"]`), `saveAgainst: fear`, `attackMode: touch` or `incorporeal-touch`, and the `denied-dex-to-ac` flag. Apply natural armor enhancement in the natural armor subtotal, not as a second direct AC modifier. Evaluate downstream effects of ability changes once, rather than also adding manual modifiers to the resulting checks.

`tools.effect_state` provides per-actor application and expiry on a round clock, explicit opposing-spell removal, temporary HP creation and consumption, Constitution-driven HP deltas, and helpers for Haste movement/full attacks, Combat Reflexes and explicit immunities/defenses. Callers still confirm targeting, resolve saves and spell resistance, establish whether opposing spells actually dispel one another, choose the order of distinct temporary HP pools, and enforce feat prerequisites. Reapplying an already active spell requires explicitly choosing which casting to keep. Protection-from-alignment entries still automate only AC and saves, not mental control or summoned-creature contact.

## Character creation and leveling

`progression.ruleIds` links to the generated progression entries in `mechanics.rules`. They use the two dedicated experience and multiclass source files, with creation defaults and the XP threshold formula from `RULES.txt`. `status: structured` describes data coverage, not an implemented calculator. Use the ordered advancement steps: in particular, a permanent Intelligence increase at the level-up affects that level's skill budget, and class-skill purchase costs use the class just advanced while rank caps use all classes taken. Do not reapply starting wealth, maximum first Hit Die, or the first-level skill multiplier when entering a second class. Apply racial bonuses from the race records separately.

Character advancement uses `minimum XP = 500 × level × (level − 1)`, a general feat at level 1 and every third character level, and a +1 ability score choice every fourth character level. `tools.character_advancement` evaluates these formulas, including exact XP boundaries and the one-level-per-award cap. It returns newly earned choices without choosing a feat, editing an ability score, or advancing a class. Apply any XP award adjustments before calling it. The formulas continue beyond level 20; epic class progression and eligibility, racial Hit Dice and level adjustment, class-specific choices, and derived combat totals still require separate handling.

## Ordered level history

Persist `classChoices` in order, for example `["fighter", "barbarian", "fighter"]`. With no racial Hit Dice this is character level 3, Fighter 2 / Barbarian 1. `tools.level_history.replay_level_history` derives the counts and returns exactly one progression row per choice, along with character-level feat and ability grants. Do not sum cumulative class rows across history. When a base class continues into an available epic table, keep recording the base class ID; the replay selects the epic progression row automatically.

`advance_level_history` commits an adjusted XP award and exactly one class choice together when the award earns a level. With racial Hit Dice or level adjustment, XP is checked against effective character level, while general feat and ability grants use actual character level. The API validates the existence of each row, not prestige prerequisites, class continuity, or other eligibility rules; validate those before committing a choice. Equipment, skill purchases, and other build decisions are not inferred from the progression row.

## Keep character and encounter state separate

A future save format should record inputs, not cached totals. Suggested boundaries:

- **Build:** race ID, base abilities, ordered level choices (class ID, HP choice, skill purchases, feats and spellcasting advancement choices), and enabled rule option IDs.
- **Actors:** character, familiar, companion and purchased animal each get an instance ID. Links identify the master and role. Save damage and other mutable state per actor; derive advancement from the associated build.
- **Inventory:** store each stack once with definition ID, quantity, carrier actor ID and optional container instance ID. Equipment slots reference owned item instances. Transfer changes the carrier/container instead of duplicating the stack. For packaged ammunition, respect the listed purchase quantity before calculating individual unit weight or price. Unknown weights should make the load total incomplete, not silently lighter.
- **Encounter:** save positions (including elevation), map scale, turn/round or game time, and active effect instances with source, target, duration and choices. Apply typed effects to derived totals with stacking rules; prompt for unsupported effects rather than guessing. Keep positions and effect timers out of the shared catalog.

## Refresh and verify

From the repository root, with Python 3.9 or later:

```sh
python tools/organize_core.py
python tools/organize_core.py --check
python -m unittest discover -s tools
```

The tool migrates v1 or refreshes v2's added catalogs from text. It does **not** regenerate the existing class, spell, skill or other legacy extraction. Stable IDs are part of the consumer API: if a source name changes, preserve the published ID explicitly before refreshing. Source line anchors are regenerated after text edits.
