# D&D 3.5 rules core

This is a personal D&D 3.5 rules project in development, not a released application. `dnd-core.json` holds shared rules data, separate from character saves and encounter state. The repository’s `.txt` files are the rules baseline. The Python tools generate and audit the data and prototype parts of the eventual software.

**DM authority:** Automation handles default rules and bookkeeping; the DM always has the final say. Even a fully typed rule can be overridden, skipped, or adjudicated manually. Keep one-off rulings in encounter or character state rather than changing the shared canon. This is a design requirement for integrations, not a guarantee that every helper already exposes an override. See [rules-lawyer.md](rules-lawyer.md).

For all effects, automatic application is limited to numeric changes on the recipient’s sheet. Effects beyond the recipient or without a sheet-number change remain available through their description or cited rule for player and DM adjudication. Typed data and explicit resolution helpers do not authorize automatic application.

| Section | What it contains |
| --- | --- |
| `progression` | Races and classes, including prestige, NPC and epic classes. Use class progression rows for standard class-level contributions; don't add derived rates on top. Store an ordered level history so the sheet can distinguish character level, class level, effective spellcasting level and eligibility at the time of each choice. |
| `skills`, `feats` | Existing skills and synergies; indexed general and epic feat entries. Feat text is reference-only, not an executable prerequisite or benefit. Record skill purchases by level and feat choices with any selections they require. |
| `magic` | Spell definitions, list membership and domains. Store learned/prepared spells and expended slots per casting class, including the chosen destination of prestige casting advancement. |
| `effects` | Conditions and special abilities, plus explicit spell- and feat-effect catalogs keyed by entity ID. A prose mention is not a grant. Benefits absent from the catalogs remain manual. |
| `inventory` | Purchasable definitions with prices in integer copper pieces, known weights in pounds, armor/weapon table fields, pack animal purchase links and Strength 1–29 load thresholds. Raw table cells are retained. `null` is not zero; consult the raw field for dashes, special cases or missing values. Mundane gear prices and weights come from `MUNDANE ITEMS.txt`. `fallbackWeaponId` is unarmed strike; attack profiles with `carriedSeparately: false` do not create inventory stacks. Shield bashes and spiked attacks reference their equipped host, and spike additions contribute zero weight. Size/body-plan adjustments, special gear and load penalties still need evaluation rules. |
| `companions` | Source-backed base creature records and separate familiar and animal companion advancement tables. Use the companion's adjusted effective master level to select its advancement row. A purchased beast does not gain companion advancement just because it uses the same base creature definition. Purchased donkey, mule, ox, pony, and both horses use `BEASTS OF BURDEN.txt`; their companion records, where present, remain separate. Purchased working beasts are not combat trained and have no attacks. Donkey and mule are separate purchases at 8 gp each. The donkey weighs 500 lb; the mule uses 800 lb as a table estimate, not an SRD weight. Animal body weight is not carried cargo. Pack profiles expose source-listed light, medium, heavy, and drag limits; drag is not a carried load. |
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

`advance_level_history` commits an adjusted XP award and exactly one class choice together when the award earns a level. With racial Hit Dice or level adjustment, XP is checked against effective character level, while general feat and ability grants use actual character level. The API validates row existence and Paladin continuity: Paladin can be entered after another class but cannot be resumed after advancing a different class. Monk can resume if otherwise eligible. Validate alignment and prestige prerequisites before committing a choice. `classBaseCombat` sums the latest class rows through character level 20 only (not racial HD). `epicCharacterBonuses` is a separate character-level lookup for the sourced levels 21–30; do not add the epic numbers embedded in class rows again. Equipment, skill purchases, and other build decisions are not inferred from the progression row.

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

The generator refreshes source-backed catalogs, spell and condition descriptions, and source anchors. It does not rebuild every record from scratch; some class, spell, and skill fields still come from the existing JSON. Keep IDs stable when renaming entries so references continue to work. Use `python tools/audit_core.py` for structural checks and `python tools/source_audit.py` for the TXT comparison report.

## Pulled vehicle inventory

`PULLED VEHICLES.txt` defines the pulling rules and the transport entries tagged
`pulledVehicle`. Create a vehicle **instance** with its own inventory carrier ID;
store cargo under that ID and link the team by animal actor ID (not species or
purchase item ID). `validate_vehicle_assignments` rejects animals assigned to
more than one vehicle. `evaluate_vehicle_load` takes the vehicle definition, the
team mapping from actor ID to pack profile ID, and the total passenger and cargo
weights. Use its `maxCargoLb` and `canPull` to display the limit and overload state.

Each animal contributes five times its heavy-load limit. Add the team capacities,
apply any DM-selected terrain multiplier, and subtract the empty vehicle and
passenger weights to find the cargo allowance. A separately sourced vehicle
payload rating can cap it further; current catalog entries have no such rating.
Do not count the pulling animals or their personal loads as vehicle cargo.
Wheeled vehicles assume reasonably passable ground; there is no invented default
penalty for hills, rough ground, or sleds. Supply a multiplier when appropriate.

## Handle Animal training

`skills.animalTraining` contains the tricks and general-purpose packages from
`SKILLS.txt`. Use each purchased beast's `initialTraining` as a template for
its own saved training state. `plan_training` checks trained-only use, trick
slots, and the scent prerequisite; the caller confirms physical suitability
for general-purpose training. Save the training plan, time worked (3 hours
per day), and the adjusted Handle Animal check made halfway through. Apply
`training_status`'s resulting state only after the remaining work succeeds.

Teach **Work** on its own or take **Heavy Labor** (Come and Work). Before that,
commanding a physically capable animal to pull a medium or heavy load is a
DC 25 push; afterward, commanding Work is DC 10. These commands are independent
of the vehicle capacity check. Training never edits the shared stat block or
creates attacks for draft animals: combat tricks require a separate attack-capable
profile and are not a conversion into a war-trained creature.

For current source discrepancies and the coverage check, see [the canon audit](CANON-AUDIT.md).

## Feat selection

Every `feats.byId` record keeps the original text, a `benefitText` fallback,
structured prerequisite clauses, and repeatability metadata. Typed numerical
benefits remain in `effects.featEffectsByFeatId` only where implemented.

Call `tools.feat_selection.check_feat_selection` **before** recording each
choice, with the facts available at that level and the feats already owned
(including source-granted feats). Use `validChoiceIdsByKey` for ordinary
catalog choices and `eligibleChoiceIdsByFeat` for choices that have already
been validated against feat-specific rules. The result is `eligible`,
`ineligible`, or `needs-review`; only the first is an automatic approval.
Pass a Monk bonus slot only for the corresponding class choice, not for a
general feat. The caller manages slot availability, builds the level-time
snapshot, and resolves prerequisites still marked manual. This checker does
not automatically commit choices or revalidate benefit use after selection.

For Improved Spell Capacity and Spell Knowledge, pass `spellcastingLevels` as
an exhaustive map from each base casting class to its effective **spell
progression** level, including applicable prestige advancement. A caster-level
bonus alone never qualifies. Each threshold pairs one class with its own ability
score; Spell Knowledge filters to arcane rows. Pass `castingClassId` when checking
which class receives an Improved Spell Capacity slot. The checker does not
allocate spell slots or choose spells.

## Spellcasting slots and metamagic

Use `tools.spellcasting.spellcasting_levels` to replay class progress and explicit
prestige targets. Build a separate daily budget for each actual casting class
with `slot_budget`; use the score eligible for bonus slots, not a temporary buff.
A blank progression cell is locked, while a printed `0` can grant bonus slots.
Domain slots are separate, and sourced epic spell-per-day caps do not stop
spellcasting progression itself. Pass verified extra-slot grants separately.

`new_slots` creates the per-class daily ledger. Use `plan_cast` before preparing
or casting, then `prepare_spell` and `spend_slot` to update that ledger without
mutating the previous snapshot. Preparation records the exact spell and
metamagic choices. The caller supplies known or accessible spell IDs, selected
domain spells, and authorized conversion spells (including cure/inflict choice).
Rest timing, learning spells, class prerequisites, and allocation of extra slots
from class features or feats are not inferred by the ledger.

The nine standard feats and Improved Metamagic have typed cast operations in
`magic.metamagicByFeatId`. The plan distinguishes slot level from effective
spell level and returns timing, components, and effect transforms. Pass it to
`apply_spell` to double the duration of supported timed effects; range and area
transforms are for the caller to apply, and `numeric_spell_result` handles an
eligible random numeric result. Spell metadata cannot establish every random
roll's eligibility: pass `random_numeric` explicitly when needed. The caller
still tracks the once-per-round Quicken limit, rolls, targeting, and saves.

## Time, turns, and recovery

`TIMING.txt` defines the shared clocks and spell recovery profiles. Each spell
has `timing.casting` and `timing.duration` in the JSON. The cast plan's `timing`
separates **action cost** from **when the spell completes**; `castingTime` is
retained as display text. Conditional or ambiguous source timings are marked
`manual` and are not scheduled automatically. Concentration, discharge,
dismissal, readied actions, and other special triggers still require their own
handling.

`tools.game_time` provides an initiative-ordered encounter with start/end turn
transitions, regular and surprise action budgets, pending casts, and round or
elapsed-time expiry. `begin_encounter_cast` spends the action and spell slot
together; apply the spell only when it is returned as completed. An interrupted
cast does not refund the slot. Callers still adjudicate interruption, targets,
and exceptional actions. Outside combat, `schedule_downtime_cast` calculates
completion on the elapsed game-seconds clock; the caller records the slot spend
and confirms continuous casting. Timed spell effects accept `encounter_clock`
or `{'gameSeconds': ...}`; an entire effect list can also use integer rounds. Handle Animal plans expose typed work hours, separately from
continuous elapsed time.

Use timestamped slot spends and `recover_slots` to refresh an existing daily
ledger. It checks full preparation or focus time, verified rest where required,
the scheduled divine preparation time, and the eight-hour recent-casting
window. It keeps uncast preparations and leaves recent expenditures unavailable.
It does not automate partial Wizard preparation, verify rest interruptions,
reschedule missed divine preparation, or guess a recovery profile for an
unlisted class. `new_slots` is for initialisation, not a recovery operation.

## Creature and equipment size

`mechanics.sizeCategoriesById` is the shared size table. Races and companion
stat blocks reference it with `sizeId`. Derive size modifiers once from the
current size; do not also add size bonuses repeated in racial trait records.
`size_profile` returns modifiers suitable for the modifier resolver, and
`carrying_limits` applies the biped/quadruped multiplier to Strength limits or
uses explicitly supplied stat-block limits. Existing pack animal and pulled
vehicle limits remain unchanged.

Use `weapon_fit` with the intended wielder size recorded on the item instance.
It checks melee handedness and applies the per-step attack penalty separately
from nonproficiency. Damage uses the weapon's size, not the wielder's. The source
provides Small/Medium dice and a Tiny/Large conversion table, so unsupported
dice and mismatched non-melee cases may need review. `armor_fit` prices and
weighs manufactured sizes using `ARMOR.txt`; mismatched size or body shape
withholds the armor bonus rather than inventing an attack or AC penalty. Full
plate needs individual fit confirmation; its refit cost is recorded separately.

Enlarge/Reduce Person and their mass variants change current size and adjust
Strength/Dexterity through the size profile. Call `equipment_size` only for gear
still affected by the spell; unaffected gear keeps its manufactured size. For
armor, pass the calculated size separately as `effective_armor_size` so fitting
does not change the catalog price. The source does not give a separate magical
armor weight table; resized armor reports its manufactured weight separately
and leaves current weight unspecified. The caller adjudicates constrained growth
and what equipment remains affected, including thrown weapons and projectiles.

## Alignment

`mechanics.alignmentsById` stores both axes. `source_alignment_context` supplies
alignment tags to protection-spell checks; `aligned_burst_plan` handles the
alignment branches of Holy Smite and Unholy Blight. The caller supplies the target
creature type and save result, rolls damage/condition duration, and handles
special rules (such as alignment subtypes) not represented by personal alignment.
Cleric and Druid cast planning checks opposed descriptors against personal and
deity alignment. Specify `deity_known=True` if the character has no deity.

Supply `alignment_by_level` with the facts at each recorded level and
`current_alignment` when advancing. Existing saves without alignment facts can
still replay, but those levels are not alignment-validated. `evaluate_alignment_change`
reports class feature retention separately from advancement and persists fallen
class IDs until confirmed atonement. The caller applies feature suppression and
confirms conduct events; the engine does not infer alignment from behavior.

Under the campaign alignment rules in their class source files, Assassin,
Blackguard, and Dwarven Defender temporarily lose access to class abilities
while ineligible. Returning to an eligible alignment restores abilities and
advancement without atonement. Paladin's permanent multiclass advancement lock
is separate from the alignment, conduct, and atonement gates on its abilities.
`inventory.weaponAlignmentPropertiesById` classifies Holy, Unholy, Axiomatic,
and Anarchic weapons independently of their wielder; this does not guess their
individual damage, wielding, or damage-reduction mechanics.

## Negative levels

`mechanics.negativeLevels` captures the general drain rule. Save timed drain
levels on the affected actor; each has its own Fortitude DC and 24-hour due time.
`resolve_drain_level` handles a save or restoration and reports permanent level
loss for the caller to reconcile with the build. `summarize_negative_levels`
returns sheet modifiers, HP and effective-level changes, and the death threshold.
Bestower temporary HP and possible next-night creature revival are separate
outcomes; the caller applies them to the appropriate actor or encounter.

For aligned weapons, derive live levels with `weapon_negative_levels` from
currently wielded item instances. These levels end when the weapon is no longer
wielded by an opposed character; they do not call for saves or permanent loss.
When levels are gained, call `allocate_spell_losses` with the new levels and the
character's ledgers. After eligible recovery, call it again with `recovery=True`
and the levels still active, using only the casting tracks being renewed. Ties
require the player's choice. The spell ledger blocks access to affected slots;
the caller coordinates these steps as one character-state update.

`effects.negativeLevelOperationsBySpellId` adds Enervation, Energy Drain,
Restoration, and Greater Restoration to that same state model. Resolve the
ray hit and spell resistance before calling `apply_drain_spell` with the completed
cast plan. Enervation expires automatically; Energy Drain waits for separate
saves at the spell DC. Death Ward blocks new negative energy but does not remove
old levels. Restore permanent level records only when eligible; Restoration
cannot remove a level that is still imposed by a wielded weapon. `energy-drained`
is derived from active levels, not a second modifier. Use the returned typed
`hp` and `effective-level` modifiers **or** their summary fields, not both.

See [rules-lawyer.md](rules-lawyer.md) for live-sheet coverage, manual rulings, and next decisions.
