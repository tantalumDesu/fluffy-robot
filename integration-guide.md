# Rules core integration guide

Implementation notes for the Python prototypes and future application. See the [project overview](README.md) and [table-play coverage](rules-lawyer.md).

## Data layout

| Section | What it contains |
| --- | --- |
| `progression` | Races and classes, including prestige, NPC and epic classes. Use class progression rows for standard class-level contributions; don't add derived rates on top. Store an ordered level history so the sheet can distinguish character level, class level, effective spellcasting level and eligibility at the time of each choice. |
| `skills`, `feats` | Existing skills and synergies; indexed general and epic feat entries. Feat text is reference-only, not an executable prerequisite or benefit. Record skill purchases by level and feat choices with any selections they require. |
| `magic` | Spell definitions, list membership and domains. Store learned/prepared spells and expended slots per casting class, including the chosen destination of prestige casting advancement. |
| `effects` | Conditions and special abilities, plus explicit spell- and feat-effect catalogs keyed by entity ID. A prose mention is not a grant. Benefits absent from the catalogs remain manual. |
| `inventory` | Purchasable definitions with prices in integer copper pieces, known weights in pounds, armor/weapon table fields, pack animal purchase links and Strength 1–29 load thresholds. Raw table cells are retained. `null` is not zero; consult the raw field for dashes, special cases or missing values. Mundane gear prices and weights come from `MUNDANE ITEMS.txt`. `fallbackWeaponId` is unarmed strike; attack profiles with `carriedSeparately: false` do not create inventory stacks. Shield bashes and spiked attacks reference their equipped host, and spike additions contribute zero weight. Equipment fit, load penalties, and equipped attack profiles are projected by the sheet helpers. |
| `companions` | Source-backed base creature records and separate familiar and animal companion advancement tables. Use the companion's adjusted effective master level to select its advancement row. A purchased beast does not gain companion advancement just because it uses the same base creature definition. Purchased donkey, mule, ox, pony, and both horses use `BEASTS OF BURDEN.txt`; their companion records, where present, remain separate. Purchased working beasts are not combat trained and have no attacks. Donkey and mule are separate purchases at 8 gp each. The donkey weighs 500 lb; the mule uses 800 lb as a table estimate, not an SRD weight. Animal body weight is not carried cargo. Pack profiles expose source-listed light, medium, heavy, and drag limits; drag is not a carried load. |
| `positioning` | Source pointers for combat positioning, reach, modifiers and initiative; not a grid or movement evaluator. |
| `mechanics` | `rules` and `lookups`, including Listen. A rule described in `RULES.txt` is not necessarily present as a typed record. |
| `rulesets` | Baseline and an opt-in option registry. The multiclass XP penalty has structured parameters and defaults off; the sheet must still evaluate it. |
| `referenceIndexes` | Indexes for `stats` and `stateChanges`. Use for browsing, not as extra modifier inputs. |

## Applying sheet effects

`spellEffectsBySpellId` and `featEffectsByFeatId` contain source-backed benefits, not full casting or feat-eligibility rules. When the player confirms an application, the sheet should store the effect ID, recipient, selection parameters, caster level if applicable, and expiry on the target actor. Feats with selections use canonical `skillId` or `weaponId` values; Dodge uses the chosen `opponentId`. Alertness granted by familiar proximity requires the caller to establish eligibility before activating it.

`tools.sheet_effects.modifier_total` is a reference resolver for a single stat. Supply active `(effect, parameters)` pairs and include comparable equipment modifiers in the same calculation so their bonus types can compete. Use `save:will` (or `save:fort`/`save:ref`), `skill:<id>`, and `ability:<id>` for specific checks. Context can include `weaponId`, `attackerId`, `sourceAlignmentTags` (e.g. `["law", "evil"]`), `saveAgainst: fear`, `attackMode: touch` or `incorporeal-touch`, and the `denied-dex-to-ac` flag. Apply natural armor enhancement in the natural armor subtotal, not as a second direct AC modifier. Evaluate downstream effects of ability changes once, rather than also adding manual modifiers to the resulting checks.

`tools.effect_state` provides per-actor application and expiry on round or game-seconds clocks, explicit opposing-spell removal, temporary HP creation and consumption, Constitution-driven HP deltas, and helpers for Haste movement/full attacks, Combat Reflexes and explicit immunities/defenses. Callers still confirm targeting, resolve saves and spell resistance, establish whether opposing spells actually dispel one another, choose the order of distinct temporary HP pools, and enforce feat prerequisites. Reapplying an already active spell requires explicitly choosing which casting to keep. Protection-from-alignment entries still automate only AC and saves, not mental control or summoned-creature contact.

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
roll's eligibility: pass `random_numeric` explicitly when needed. Encounter scheduling tracks the once-per-round Quicken limit. The caller resolves rolls, targeting, and saves.

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
cast does not refund the slot. For armor spell failure, pass confirmed gear to `plan_cast` via `worn_armor_and_shields`, then use `resolve_armor_spell_failure` with the table’s percentile roll before applying effects. Callers still adjudicate interruption, targets,
and exceptional actions. Outside combat, `schedule_downtime_cast` calculates
completion on the elapsed game-seconds clock; the caller records the slot spend
and confirms continuous casting. Timed spell effects accept `encounter_clock`
or `{'gameSeconds': ...}`; an entire effect list can also use integer rounds. Handle Animal plans expose typed work hours, separately from
continuous elapsed time.

Use timestamped slot spends and `recover_slots` to refresh an existing daily
ledger. It checks full preparation or focus time, verified rest where required,
the scheduled divine preparation time, and the eight-hour recent-casting
window. It keeps uncast preparations and leaves recent expenditures unavailable.
`recover_spell_tracks` handles same-time recovery and reapplies active drain to the refreshed slots. The recovery tools do not automate partial Wizard preparation, verify rest interruptions,
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
loss. Use `tools.drain_history` to commit permanent loss or restoration while preserving the original build. `summarize_negative_levels`
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
cast plan. Enervation expires when timed effects are evaluated; Energy Drain waits for separate
saves at the spell DC. Death Ward blocks new negative energy but does not remove
old levels. Restore permanent level records only when eligible; Restoration
cannot remove a level that is still imposed by a wielded weapon. `energy-drained`
is derived from active levels, not a second modifier. Use the returned typed
`hp` and `effective-level` modifiers **or** their summary fields, not both.

See [rules-lawyer.md](rules-lawyer.md) for live-sheet coverage, manual rulings, and next decisions.

## Damage reduction and HP

`derive_sheet` exposes separate `damageReduction` ratings, including Barbarian and Dwarven Defender class DR. Pass other confirmed active sources (armor, spells, feats, or special abilities) as `damage_reduction_grants`; the caller resolves prerequisites, duration, and finite spell pools. Each grant has `amount` and `bypassAnyOf` (OR of AND clauses); an empty list means no ordinary bypass. For example, `[['good', 'slashing'], ['adamantine']]` is bypassed by either a good slashing hit or an adamantine hit. Each attack profile carries physical damage and confirmed bypass tags, including tags from aligned weapon properties. Pass material/magic tags explicitly; wielder alignment does not align the weapon.

After the table confirms a hit and its rolled damage, call `resolve_sheet_damage` with the defender sheet, injury state, attack profile, and a unique round ID. Choose the damage type for an either/or weapon. The resolver takes the highest applicable DR, subtracts the allowance already used that round, then applies the remaining damage through the normal injury workflow. Pass equipped spike/host damage profiles explicitly when resolving those attacks. This does not automatically grant aligned bonus damage or run a combat action.

## Contextual combat modifiers

Pass the confirmed incoming attack kind when projecting AC. Prone gives −4 AC against melee and +4 against ranged, and applies −4 to the prone attacker’s melee attacks. Crossbows, darts, and shuriken can be used prone without an extra penalty; other ranged attacks are flagged as unavailable. Standing is a move action that provokes; resolve reactions at the table. Numeric stacking keeps the highest bonus and most negative penalty per named type; the DM resolves same-source overlap.

## Improved Familiar

`IMPROVED FAMILIARS.txt` supplies the listed acquisition options, including each option’s minimum **Wizard class level**, any minimum BAB, and alignment. `companions.improvedFamiliarOptionsById` retains the stat blocks as source text; it does not automatically create an actor. The Vargouille option specifically excludes Kiss.

Use `hasFamiliarAcquisitionAbility` when checking whether a character qualifies to learn the feat. At acquisition, call `tools.improved_familiars.check_improved_familiar` separately with confirmed feat ownership, `canAcquireFamiliar`, `classLevels`, `alignmentId`, and `baseAttackBonus` when required. Alignment can differ by up to one step on each axis. Older examples not in the dedicated table and other unlisted candidates need a DM ruling. Familiar advancement and the feat’s exceptions remain governed by `FAMILIARS.txt` and `FEATS.txt`.

## Companion stat blocks on the sheet

Pass confirmed companion links to `derive_sheet` as `companion_links=[{'instanceId': ..., 'definitionId': ...}]`. The returned `companions` entries contain the entire source stat block and base fields alongside the projected numbers and cumulative feature names. Keep current damage, chosen tricks, feats, skill ranks, and other mutable state on the linked actor. Purchased animals do not use these advancement tables.

Familiar progression uses Wizard class levels; animal companion progression uses Druid class levels, including the listed alternative companion adjustments. Pass any independently confirmed stacking contribution as `otherEligibleClassLevels`. Familiar HP uses half of `master_max_hp` (exclude temporary HP), and its attack and save calculations use the master’s class combat progression where the familiar rules call for it. Supply confirmed `baseSaveBonuses` for improved familiars as needed. Animal companions gain bonus Hit Dice, ability adjustments, natural armor, and bonus trick slots. Record each bonus d8 in `bonusHitDieRolls`; missing rolls leave projected maximum HP unset rather than inventing a number.

The projection does not acquire a companion, allocate feats or skills, choose tricks, or execute special abilities. Attack routines project attack bonuses where the source notation supports it and preserve source damage text for review. The source stat block is reference data, not a second set of bonuses to apply.

Dismissing a familiar (including to adopt an improved familiar), or losing it to death, requires a DC 15 Fortitude save: lose 200 XP per level in the relevant Wizard or Sorcerer class on failure, or 100 XP per class level on success, with a floor of zero XP. A replacement must wait a year and a day. `companions.familiarLossByClassId` preserves the source rule, and `resolve_familiar_loss` calculates XP from the table’s save total. The caller records the loss, updates XP, and enforces the replacement wait using the campaign calendar before setting `canAcquireFamiliar`.
