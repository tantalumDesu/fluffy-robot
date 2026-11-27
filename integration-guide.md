# Rules core integration guide

Implementation notes for the Python prototypes and future application. See the [project overview](README.md) and [canon audit](CANON-AUDIT.md).

## DM authority and source rules

The TXT files are the rules authority. Generated JSON is reference and typed rules data; the Python helpers are opt-in consumers, not a complete tabletop engine. A typed rule is not necessarily enforced by the sheet or encounter.

Automation never takes precedence over a DM ruling, even for a fully typed rule. The DM may supply missing facts, override a result, skip or replace a transition, or adjudicate manually. Record one-off decisions in character or encounter state rather than shared canon. This is a design requirement for integrations, not a claim that every helper has an override API.

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
more than one vehicle. `evaluate_vehicle_load` takes the core, the vehicle item ID, the
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
`SKILLS.txt`. Use `acquisition_training` to instantiate the purchase or
acquisition’s `trainingPurposeId` as the animal’s own saved training state. `plan_training` checks trained-only use, trick
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
score for Improved Spell Capacity. Spell Knowledge instead requires at least one level and a castable spell on the chosen arcane track; its spell picks are capped at that track’s current castable level. Both feats take `castingClassId`.
When committing a level, `record_level_choices` resolves their grants atomically:

- **Improved Spell Capacity:** Supply `slotLevel`. Use `feat_slot_budget` with
  active feat picks to build the daily budget. It counts repeated picks on the
  selected track and applies eligible ability bonus slots once per level.
- **Spell Knowledge:** Supply two entries in `spells`, each with `spellId` and,
  if a cross-list spell has different arcane levels, `sourceListId`. Use the
  receiving class's level when it has the spell. Pass active picks to `plan_cast`
  for the learned spells; there are no extra slots. Supply baseline known spells
  in `knownSpellIdsByClassId` to check for duplicates.
- **Wizard books:** Register each physical volume under `spellbooksById` using
  `add_spellbook`; commit ordinary inscription or table-adjudicated damage/loss
  with `update_spellbook`. A Wizard-track Spell Knowledge pick requires
  `accessibleSpellbookIds` and enough room for both spells. The helper places
  them automatically, splitting across volumes if needed. Only the chosen track matters; choosing
  another arcane track does not require books, even on a Wizard level-up.
  Use `active_spellbooks` for preparation to account for feat suppression and
  unavailable books or entries. Damage does not free pages. Losing a book does
  not unlearn its spells or retroactively clear prepared slots.

After permanent loss, use `projected_level_grants()['featChoices']` for the active
picks. Restoration reactivates grants but does not change the physical books.

## Spellcasting slots and metamagic

For an advancing prestige row, supply `castingTargets` in the row’s listed order.
For Bard, Sorcerer, Assassin or Magewright advancement, use
`spellChoicesByClassId` with `learn` (spell IDs) and, where allowed, `swap`
(`remove` and `learn` IDs). The transaction checks the normal list, source table
counts, castable levels, and swap schedule. Unusual off-list Sorcerer study and
ordinary Wizard inscription are separate workflows. `projected_level_grants`
returns active `spellcastingLevels` and `knownSpellIdsByClassId` after loss or
restoration. Pass the current known IDs to `spend_slot` for new spontaneous casts
and Magewright casts; planning does not authorize later spending on its own.
Use `reconcile_slot_budget` with the projected budget to suppress or restore slots
without refunding spent slots. A cast already started stays in the encounter ledger.


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
ledger. It checks preparation or focus time, verified rest where required, and the eight-hour recent-casting window. Divine casters choose their preparation time each day. It keeps uncast preparations and leaves recent expenditures unavailable.
`recover_spell_tracks` handles same-time recovery and reapplies active drain to the refreshed slots. Use `prepare_wizard_session` for any number of Wizard preparations after eight uninterrupted hours of rest and one uninterrupted hour of study. The caller verifies uninterrupted time. `new_slots` is for initialisation, not a recovery operation.

## Creature and equipment size

`mechanics.sizeCategoriesById` is the shared size table. Races and companion
stat blocks reference it with `sizeId`. Races with no explicit size inherit it
through `race_size_id`. Derive size modifiers once from the
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
`resolve_drain_level` handles a save or restoration and reports a drained level on failure. Use `tools.drain_history` to commit drain, irreversible loss, and restoration while preserving the original build. `summarize_negative_levels`
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
old levels. Restore recoverable drained levels only within the chosen casting’s recovery window; Restoration
cannot remove a level that is still imposed by a wielded weapon. `energy-drained`
is derived from active levels, not a second modifier. Use the returned typed
`hp` and `effective-level` modifiers **or** their summary fields, not both.

See [Permanent level loss](#permanent-level-loss) for exact grant projection and restoration.

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

## Equipment slots and two-weapon fighting

`derive_sheet` accepts role-based `hand` assignments (`primary` or `offhand`), independent of physical handedness. Give a two-handed weapon `gripHands=['primary', 'offhand']`; one-handed weapons can use `hand` alone. Shields reserve their assigned grip except for bucklers, and locked gauntlets occupy a separate gauntlet slot on each hand. Optional `slotId` reserves a body slot (including `ring-left` and `ring-right`); these are caller-confirmed placements, not inferred magic-item eligibility. Conflicting declared slots are rejected. Unassigned weapons still get their standalone attack profiles but do not form a two-weapon routine.

Pass verified `feat_ids` and optional `ranger_combat_style='two-weapon'`. A separate `twoWeaponRoutine` shows the full-attack penalties and the extra off-hand attacks from Improved and Greater Two-Weapon Fighting. Ranger style applies in light or no armor. Set `double_weapon_instance_id` to use both ends of an equipped double weapon. Two-Weapon Defense contributes a nonstacking shield bonus (+2 with confirmed `fightingDefensively` or `totalDefense` context). The routine does not spend actions or decide which attacks the player makes.

For a shield bash, provide `bashWeaponId` on a shield assigned to a hand, plus `additionIds` for installed spikes. For a confirmed bash, pass the shield instance in `shieldBashUsedInstanceIds` to suppress its AC bonus unless the actor has Improved Shield Bash. For confirmed weapon use with the buckler arm, supply `bucklerArmUsedInstanceIds` to suppress its defense. Record these facts in encounter state; merely equipping gear does not execute an attack or reload a crossbow.

### Familiar Spell choices and display

Supply `known_spell_levels` (spell ID → level at which the character knows it) to `derive_sheet`. `familiarSpellChoices` separates eligible spells from those needing material-cost confirmation. Only known spells of levels 0–8 qualify; XP components and material components above 1 gp disqualify a spell. Pass confirmed costs through `verified_material_cost_gp`. Use `check_familiar_spell_selection` to validate the pick together with the feat prerequisites.

Store each selection as a separate `feat_choices` entry with `featId='familiar-spell'` and `choices={'spellId': ...}`. `familiarSpellGrants` groups those choices by spell ID and labels them, for example `Familiar Spell, Magic Missile 2/day`. This is the daily grant, not the number of uses remaining.

### Weapon Focus choices and display

Pass confirmed `weapon_proficiencies` to `derive_sheet` to list choices even when the weapon is not equipped. The sheet also recognizes equipped weapons explicitly marked proficient. Grapple and Unarmed Strike are always listed; Ray is listed with at least one level in a spellcasting class. `check_weapon_focus_selection` validates the choice, BAB +1, and the restriction against taking the same choice twice.

Record each selection in `feat_choices` with `featId='weapon-focus'` and `choices={'weaponId': ...}`. `weaponFocusGrants` displays labels such as `Weapon Focus, Ray`; the sheet applies the +1 to matching weapon attacks, unarmed strikes, or grapple checks. Core generation marks spells whose **Effect** text contains `ray` or `rays` with `attackProfile.kind: ray` and links them to the typed Ray choice. With Ray selected, each matching known spell shows `weaponFocusAttackBonus: 1`. Pass the updated `known_spell_levels` when a spell is learned; there is no per-spell feat entry to maintain.

Greater Weapon Focus and both Weapon Specialization feats use the same exact weapon choice as their prerequisites. The sheet combines confirmed selections as attack and weapon damage modifiers, including ray spell entries. Overwhelming Critical checks the selected melee weapon against the matching Weapon Focus and Improved Critical picks; its extra critical dice are reference data for a confirmed critical, not an automatic roll.

### Spell Focus choices and saving throws

The core defines school IDs in `magic.schoolsById` and links every spell to its school. `spellFocusChoices` lists available schools for Spell Focus and Greater Spell Focus, excluding Universal. Greater Spell Focus requires Spell Focus for the same school. Each contributes +1 to saving-throw DCs for that school; the two distinct feats stack, but duplicate selections of the same feat and school do not. Confirmed `feat_choices` supply the bonus in known-spell entries and in `plan_cast`. This modifies the defender’s **saving throw DC**, not caster-level checks to overcome spell resistance.

### Other feat grants

Every epic feat carries a source-linked character level 21 requirement in `prerequisites.allOf`. Confirmed `feat_choices` feed Skill Focus into skill totals, add martial and exotic proficiency grants, and project Improved Critical and Rapid Reload on matching equipment. Keen and Improved Critical do not multiply one another. Reload timing is descriptive; the encounter still adjudicates hand use and opportunity attacks.

Toughness contributes `featMaxHpBonus`; add it once when assembling the actor’s maximum HP. Pass confirmed `turning_pool_ids` to project Extra Turning's daily capacity bonuses independently of uses remaining. Spell Penetration and Greater Spell Penetration contribute `spellResistanceCheckBonus` to cast plans, independently of Spell Focus. Spell Mastery is repeatable: record each pick’s `spellIds`, using the Wizard’s known spells and Intelligence modifier at selection. The spell list flags mastered spells; it does not bypass the Wizard spellbook requirement.

The generated `inventory.equipmentSlots` lists slot IDs and Ranger two-weapon style grants; weapon `gripProfile` entries and shield `reservesGrip` flags hold the item-specific defaults. Runtime helpers validate the declared equipment and apply those defaults. Familiar Spell limits and per-selection daily uses are in `feats.byId.familiar-spell.spellGrant`; known spells, verified component costs, and remaining uses stay outside the core.

### Wizard spellbooks

`magic.wizardSpellbook` defines the standard 100-page book and the page rule: one page per Wizard spell level, minimum one page. Track separate book instances with inventory. `new_spellbook` creates a blank record and `learn_wizard_spells` records confirmed acquisitions, using Wizard list levels and rejecting a batch that exceeds capacity. Starting spells, level-up choices, and copies use the same page accounting; eligibility to acquire a spell is confirmed before recording it.

Pass accessible books to `prepare_spell` as `accessible_spellbooks`. The Wizard spell must be recorded at its base level on the Wizard track (for a cross-list Spell Knowledge pick, use the recorded grant level); metamagic changes slot cost, not pages. The table's spellbook requirement applies even to *read magic*. Spell Mastery remains visible on the sheet but does not bypass this preparation check. Losing a book does not erase an already-prepared spell. Other class tracks continue to use their own spell access rules, even when the character is also a Wizard or knows the same spell through both classes.

### Wizard study and school specialization

Keep `new_wizard_learning()` state per Wizard casting track. `begin_wizard_study` records the accessible scroll or other wizard’s book and the study deadline; `finish_wizard_study` takes a table-confirmed Spellcraft total **before** the separate specialty bonus. Failure records actual ranks for the retry gate. Success returns a scroll instance ID to remove (if applicable), but does not add a known spell. `inscribe_understood_spell` checks a separate full day, book capacity, and materials (100 gp per page) and returns the updated book and known-spell state. Persist each returned state together with its inventory/material changes. `learn_wizard_spells` remains the low-level writer for confirmed starting or level-up grants; external study uses the staged workflow.

Use `choose_wizard_specialization` at first **Wizard class level** to record the permanent choice of a specialty or generalist. Keep the returned record even for a generalist and supply it as `existing_choice` on any attempted update; pass the saved choice to learning, slot budgeting, and cast planning. The specialization validator enforces two distinct prohibited schools (one for a diviner), and does not allow prohibiting Divination or choosing Universal. The Wizard-only `specialist` pool holds one additional slot for each available spell level, and cast plans for this pool require a matching school. Use `wizard_spell_item_school_allowed` for the prohibited-school check when the character is using a scroll or wand as a Wizard. The caller confirms access, uninterrupted study/writing, and item use; other casting tracks are unaffected.

### Spell components and casting conditions

Spells have a generated `componentProfile`, including tradition alternatives such as `M/DF`, and source text and stated amounts for recognized priced materials. Unpriced materials, including named ones, are supplied by an equipped pouch or waived by Eschew Materials. Materials with a stated cost require actual inventory access; confirm it through `accessibleMaterialSpellIds`. Focus uses an accessible pouch; divine focus uses the class-specific item types in `magic.componentRules` or a confirmed equipped deity weapon for holy-symbol classes. Use `choose_cleric_holy_weapon` at first Cleric class level and persist its result.

Pass `component_context` to `plan_cast` for an actual casting decision: `equippedItemIds`, `accessibleItemIds`, `accessiblePricedMaterialSpellIds`, condition IDs/flags, and any confirmed `holyWeaponId`, `silenced` or `hasFreeSomaticHand` facts. An omitted context produces `not-checked`, not a readiness confirmation. A blocked plan cannot be scheduled. Silent Spell removes the verbal requirement before Silence and deafness checks; Still Spell removes the somatic requirement before free-hand and armor checks. Conditions preventing action/concentration can block casting; Entangled adds a Concentration check. Use `resolve_component_cast` with the table’s rolls before applying effects. Check armor failure separately. The caller confirms area membership, access, and any component consumption or XP cost; Focus prose, unusual conditional costs, remain available for table review. Set `deafnessAdapted` in cast context and `deafness_adapted` on the sheet only after a DM ruling. Calculate confirmed casting injury DCs with `casting_injury_concentration_dc` and pass the checks to `resolve_cast_completion`.

Holy symbols, holly, and mistletoe carry `divineFocus` profiles on their item definitions. A confirmed deity weapon inherits a holy-symbol focus profile for that actor only. Pass the saved selection as `holy_weapon_id` for sheet display and `holyWeaponId` in casting context; the cast check requires the selected weapon to be equipped.

### Permanent level loss

A failed save removes an actual level immediately and records the save time. `minimum_restoration_caster_level` returns the timing minimum for a recorded energy-drain loss: round elapsed time up to whole days for Restoration or whole weeks for Greater Restoration (minimum 1). Actual spell access is checked separately. Restoration returns one eligible level; Greater Restoration returns all eligible levels in active-prefix order. Neither restores a Raise Dead cost, nor does an out-of-window casting automatically make the loss irrevocable. Apply a confirmed Raise Dead level cost with `apply_permanent_level_loss(..., cause='raise-dead')`; first-level Constitution costs and the rest of the spell are table-owned.

`record_level_choices` awards XP normally while losses are outstanding. Each earned level replaces the lowest unresolved level with fresh choices and removes that loss from the Restoration candidates. Higher losses keep their original timestamps and choices. For example, earning 9th level after losing 9th and 10th leaves only 10th recoverable. If a new choice makes a later saved progression invalid (such as a missing prestige casting target), resolve that conflict at the table rather than silently substituting a choice.

`lost_level_recovery_options` reports each outstanding loss, elapsed time, the timing minimum, and the ordinary Cleric casting floor: Restoration is a Cleric 4 spell (normally caster level 7), and Greater Restoration is a Cleric 7 spell (normally caster level 13). The displayed minimum for an ordinary Cleric is the greater of timing and that floor. `commit_restoration_cast` takes a confirmed casting, applies the cure, and charges the caster 500 XP for Greater Restoration without reducing their level. Existing spell ledgers are reconciled after actual loss, restoration, or replacement advancement without refunding spent slots. Call `derive_level_loss_sheet` with `now` to include timed negative levels; `maxHp` reflects the active build, while `effectiveMaxHp` includes negative-level penalties. Current HP and inventory remain separate.

Use `derive_level_loss_sheet` to show the surviving character numbers and reproject linked companions. Falling below all qualifying levels suspends a companion’s advancement and flags the relationship for table review. Coordinate current HP, actual spell ledgers, and other mutable state with the projection; this helper does not replay recovery or inventory events.

## Natural weapons and forms

Use `mechanics.naturalWeapons` for the shared weapon types and damage-die steps.
Racial attacks and recognized creature attack routines expose `naturalWeapons`
with a `naturalAttackId`, attack count, damage dice, and physical damage types.
Use `tools.natural_weapons.weapon` to build typed attacks for custom sources.
Record `naturalAttacks` for permanent additions, `availableNaturalFormIds` for
confirmed accessible forms, and `activeNaturalFormId` for the current form.
Catalog creature IDs supply built-in rosters; `naturalFormsById` supplies explicit
rosters for custom or template forms. The active form roster replaces the base
roster for this projection; this does not itself activate a transformation or
change size, reach, or ability scores.

Improved Natural Attack requires BAB +4 and an eligible `naturalAttackId`.
The choice applies once to all matching attacks, including across forms. Use
`naturalWeapons` for the projected dice; retained source attack text still
shows the original stat block. Alternatives and special riders remain subject
to the source routine and table adjudication.

For creatures whose source grants rake on a pounce, `pounceNaturalWeapons`
contains two extra claws with the listed rake dice and attack bonus. Pass
`confirmed_pounce=True` on the charge to include them in the active routine;
this does not resolve the charge or its attacks. A claw feat pick applies to
those claws as well as to the normal claw routine.

## Mount and barding projection

Link each creature instance once in `companion_links`; purchase definitions can
use the `beasts-of-burden:*` records. Use `acquiredByClassId` for a Ranger or
Sorcerer acquisition and save the animal's completed Handle Animal state as
`training`. Supply `mount_link` on the rider sheet with that same `instanceId`,
`rider_weight_lb`, and `rider_inventory_lb`. Optional inputs include saddle
`itemId` and `sizeId`, `barding_id`, `saddlebags_payload_lb`, and confirmed
`suitability` or `saddle_fit`. A confirmed mounted charge with `weapon_id` exposes
lance damage metadata without resolving the attack. Use `mounted` for the
contextual Ride modifiers and mounted load/movement; required saddle size tracks
the mount’s current size unless confirmed fit overrides it; the base creature sheet
remains independent of the rider's current assignment. The armor's listed price
and weight already include size multipliers. Normal saddlebags hold up to a light
load, but their payload is not an extra allowance above total carrying capacity.

The three `war-mounts:*` definitions come from `WAR MOUNTS.txt`. A purchase uses
the ordinary base sheet and its combat-riding acquisition training. Set
`acquiredByClassId='paladin'` only for a creature actually acquired via that class,
and supply recorded `bonusHitDieRolls`. The helper projects the Paladin package
for the heavy warhorse and warpony; other sourced war mounts require
`dmConfirmedSpecialMount`. The riding dog and Large shark also reuse their existing base definitions with `dmConfirmedSpecialMount=True`. Calling, dismissal, and death workflows are not yet implemented. When directing a
combat-trained mount to attack, the rider’s own attacks use the separate DC 10
Ride check, not the DC 20 check to control an untrained mount in battle.

The `unusual-mounts:*` sheets come from `UNUSUAL MOUNTS.txt`. Standard
mounted projection uses their listed land and flying movement separately.
`flightStatus` leaves flight load eligibility for confirmation; medium or heavy
barding still prevents flight. For griffon, pegasus, and giant owl, supply a
fitted exotic rider saddle. Use `plan_training` with `friendly_confirmed=True`
only after the table confirms attitude; their source-specific combat-riding
plan uses DC 25 and six weeks. A successful plan records combat readiness
without inventing other learned tricks.

Use `acquisition='ordinary'` on a creature link to reuse an existing companion
or Improved Familiar base block without granting a class package. A separate
`mount_link` uses that same `instanceId`. Hippogriff and howler use their
listed training and exotic saddle rules. Worg suitability is sourced and it takes a standard saddle; willingness still requires confirmation. Flying and non-quadrupedal mounts require a fitted exotic rider saddle under the campaign rule. Mounted climbing exposes the
campaign’s DC 5 Ride check when a climb speed is listed.

`derive_sheet(..., draft_links=...)` accepts vehicle links with `instanceId`,
`vehicleItemId`, and `pullerInstanceIds`, plus optional `passenger_weight_lb`,
`cargo_weight_lb`, and `terrain_multiplier`. `draftByInstanceId` holds vehicle
load and Work command projections. Only sourced pack-animal profiles are
supported; one puller cannot be assigned to two vehicles or simultaneously
ridden and assigned to draft work in this projection.

Ordinary riding is class-independent. `riding` and `combat-riding` are separate
Handle Animal general purposes. Only a creature explicitly acquired through
Paladin’s level-5 special mount feature receives the special mount package
and starts combat-riding trained under the campaign rule. The initial training
is retained alongside further recorded tricks.

To display training choices alongside a creature sheet, pass `trainingContext`
on its link (or call `training_choices` directly). Supply `handler_ranks` and
optionally `purpose_suitability` keyed by purpose ID, `has_scent`, and
`friendly_confirmed`. `True` confirms a prerequisite; `False` rules it out;
omission leaves an unsourced prerequisite for review. Choices return `known`,
`available`, `blocked`, or `needs-review`. Available choices show the DC,
training time, and tricks gained or lost. This is a preview, not an assignment:
use `plan_training` and only save `trainingState` after `training_status`
reports completion.

### Mounted encounter actions

Pass the rider sheet’s `mounted` projection to `tools.mounted_encounter`.
A sheet link alone does not put anyone in the saddle: `mount_or_dismount`
updates `mountedByRiderId` after validating the pairing and spending the
rider’s action. Pass resolved Ride totals (including applicable modifiers
and fast-mount armor check penalties). Confirm reach or dismount space at
the table. `control_mount` handles non-combat-trained mounts in battle.

`move_mounted` uses the mount’s movement budget on the rider’s turn. Declare
and confirm the movement sequence before asking for its attack modifiers;
ranged double-move/run attack timing is reported, not simulated. Use
`spend_mounted_attack` to spend the rider’s attack action and obtain its
modifiers, then resolve hits and damage separately. `resolve_mount_fall`
removes the link and reports fall damage dice; a failed mounted-climb check
instead flags fall position and damage for a ruling. Map movement, charge
paths, unusual movement and load, and the mount’s ability to act still need
confirmation. Mounted feat exceptions, mounted spell timing, and automatic
unconscious-rider checks are not resolved by these helpers.
