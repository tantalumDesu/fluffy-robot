# D&D 3.5 core canon audit

The repository’s TXT files, including explicit table rulings, are the baseline. This audit distinguishes source retention, structured data, and executable behavior. None implies the others.

## What to tackle next

| Priority | Finding | Next step |
| --- | --- | --- |
| **Medium — transformations** | Regular claw routines and the two extra claws on a confirmed pounce now share a weapon type. The standalone catalogue still does not apply templates or automate full form changes. | Integrate lycanthropy and undead separately; see [template design](template-design.md). |
| **Medium — targeted effect coverage** | Many spells and feats lack entries in the checked effect catalogs. That does not mean every one needs automation: targeting, forced behavior, and other non-sheet effects may deliberately stay with the table. | Pick a frequently used spell or feat family and compare the source to its sheet and encounter behavior before adding effects. Do not prioritize by raw missing counts alone. |

**Recommended next: creature sheets and roles.** Start with one typed creature sheet and separate links for advancement, work, and riding. Then test the same creature first as an animal companion and later as that character’s confirmed mount, without creating a second creature or duplicating its bonuses.

## Core data consolidation before expanding creature sheets

The consolidation is implemented. Keep source prose and explicit overrides even when mechanical consumers share a single typed field.

| Area | Canonical data and consumer lookup |
| --- | --- |
| **Creature and race size** | Regular and Improved Familiar creature records use `sizeId` against `mechanics.sizeCategoriesById`. Races store explicit size once; `race_size_id` follows inheritance when absent (Drow inherits Medium from Elf). Classification and stat blocks remain source/display text. |
| **Purchase, training, capacity** | Pack links reference creature and purchase IDs. Explicit capacity lives on the creature and is shared by mounted and vehicle load helpers. A purchase or acquisition stores only `trainingPurposeId`; `acquisition_training` instantiates the purpose’s tricks for the individual. Distinct purchased and companion stat blocks remain distinct. |
| **Saddle fit** | Required saddle size defaults to the current creature size. A confirmed fitting exception can override it; actual saddle size and standard/exotic family still have to match. |
| **Conditions** | Each condition carries its mechanics once. `condition_policies` builds the ID lookup used by sheet, encounter and component consumers. |
| **Spellcasting** | Classes own track tradition, mode and spell list. `magic.castingPoliciesByClassId` contains additional behavior; `casting_profile` assembles it with the class track and derives domain support from progression. |

## Next audit target: companions, familiars, working beasts, and mounts

These roles overlap, but they do not grant the same things. A creature’s base statistics and current HP, gear, load, and conditions belong to its instance. Companion, familiar, and special-mount advancement depends on the qualifying class relationship. Pulling a vehicle or carrying a rider is a separate assignment; neither grants advancement. Do not infer training, suitability as a mount, or permission to stack advancement just because a creature appears in more than one source list.

| Area | What is wired now | What is missing or needs verification |
| --- | --- | --- |
| **Animal companions** | The Druid projection uses adjusted effective master level, bonus HD, supplied HP rolls, Strength/Dexterity, natural armor, tricks, BAB and saves. Recognized natural attacks and pounce claws are typed. | Record bonus-HD skill and feat choices and activate them only at the appropriate HD. Finish attacks, damage modifiers, and special ability projection; verify Ranger effective progression and any other eligible master tracks rather than relying on generic caller-supplied level adjustments. Sources: `ANIMAL COMPANIONS.txt`, `ALTERNATIVE ANIMAL COMPANIONS.txt`, `DRUID.txt`, `RANGER.txt`, and epic progression. |
| **Familiars** | Standard and Improved Familiar source records exist; the latter have 31 catalogued options and eligibility checks. Linked sheets project selected stats, half master HP, effective HD and SR; a separate helper resolves release/death XP and the replacement wait. | Verify base saves, skill ranks and adjustments rather than treating source skill totals as ranks. Type the master-side familiar bonus and Alertness with the appropriate proximity/presence facts; do not assume a projected link means the familiar is nearby. Link Familiar Spell to the actual familiar and its daily-use state. Review Wizard/Sorcerer and epic progression together. |
| **Beasts of burden** | Purchased working beasts have their own data in `BEASTS OF BURDEN.txt`, including pack limits; training and vehicle load helpers already exist. Purchased work stock is not automatically combat-trained and does not inherit companion advancement. | Project purchased beasts as actors even without a master-linked advancement role. Feed carried tack, packs, riders, and cargo into encumbrance and movement without counting the animal’s own body weight as cargo. Keep pack load and pulled vehicle load distinct; connect confirmed training/work state rather than granting a combat routine by default. |
| **Mounts** | The source covers Ride and mounted combat (`SKILLS.txt`, `SPECIAL ATTACKS.txt`), feats (`FEATS.txt`), and Paladin/epic special-mount progression. These are not a unified rider–mount sheet workflow. | Type ordinary and special mount relationships separately; project special-mount HD, armor, ability adjustments, and source-backed features. A confirmed mount link should identify the rider, mount, tack, training, carried rider load, and applicable Ride/feat modifiers. Keep control checks, movement decisions, and reactions table-confirmed. |

### First implementation slice

- The rider sheet now references a linked creature instance rather than building a second mount. The same entry carries its original Druid/Ranger companion, Wizard/Sorcerer familiar, or purchased working-beast package. Ranger acquisition uses half Ranger level starting at Ranger 4. Purchased working beasts have a base sheet; riding does not activate class advancement. The three war-mount purchase items link to the typed base sheets in `WAR MOUNTS.txt` and seed combat-riding training. A linked special-mount acquisition separately applies the Paladin package.
- The mounted projection checks relative size, confirmed suitability, carried weight and fitted saddles. It exposes Ride modifiers, the combat-control DC, and confirmed charge/lance damage metadata without executing a mounted action. Confirm unusual saddle fit. The training-choice preview uses the same prerequisites as the training planner and reports known, available, blocked, and needs-review choices. Completing Handle Animal training updates the creature's own training state; combat readiness is not inferred from owning a saddle.
- The generated core exposes 24 source-priced barding profiles, keyed by armor and mount size. The mounted projection applies weight, listed speed reductions, flight and running restrictions, and barding AC where a base AC is available. Normal saddlebags hold at most the mount's light load; their contents, the gear itself, barding, and rider all still count toward total carried load.

The `unusual-mounts:*` definitions retain their supplied stat blocks, natural weapons, and any listed flying movement. Griffon, pegasus, and giant owl carry source-backed exotic saddle requirements and a friendly-attitude, DC 25, six-week combat-riding workflow. Griffon rake projects as two extra claws on a confirmed pounce. The giant eagle’s training details remain unconfirmed. The giant wasp remains a candidate, with no fly speed, Intelligence value, or training inferred from omitted fields. Both require exotic saddles under the campaign rule.

Encounter helpers now distinguish a projected pairing from an active mount. They spend mount/dismount actions, track the current rider and mount, apply combat control, spend the mount’s movement budget on the rider’s initiative, and prepare mounted attacks or fall outcomes from confirmed inputs. The active mount does not also take an independent initiative turn.

**Open items surfaced by this slice:**

| Area | What remains |
| --- | --- |
| **Mount definitions and fit** | Numeric Paladin progression is wired for the three war mounts and DM-confirmed riding dogs and Large sharks. Calling/dismissal, death/replacement tracking and remaining special-ability effects are open. Other alternate species need an explicit progression profile. The campaign assigns exotic saddles to flying and non-quadrupedal mounts, and preserves explicit exotic requirements in creature entries. Suitability and unclassified body plans still require confirmation. Define barding body fit beyond size before allowing arbitrary same-size creatures to exchange it. |
| **Load and movement** | Flight load limits are still unconfirmed for the new aerial mounts; base carrying capacity is not proof that an animal can fly with that load. Base speeds outside the sourced barding table and higher-speed encumbrance without barding need a source-backed reduction or a ruling; the projection flags gaps. Draft links reuse sourced pack-animal instances and project vehicle loads and Work commands. Puller-carried cargo, draft barding restrictions, and simultaneous riding and pulling still need adjudication. Confirm how to handle a pack saddle that is already fitted when attempting to ride bareback. |
| **Mounted encounter actions** | The current projection reports control, fit, charge/lance and saddle effects. It does not spend actions, resolve falls, apply mounted ranged/casting penalties, or model movement and reach. Wire confirmed event helpers and mounted feats rather than inferring reactions or terrain. Confirm multiplier interactions against the existing damage rules when adding Spirited Charge. |
| **Advancement and familiar effects** | Companion bonus-HD skill/feat allocations, familiar master-side benefits, and bonus-HD choices for special mounts remain open. Review additional qualifying master levels rather than expanding the current caller-supplied adjustment by default. |

### Confirmed creature and mounted combat rulings

Use one creature instance, one sheet calculation, and separate links for ownership, advancement, training, riding, and draft work. An animal does not get a second HP pool, inventory, or set of bonuses when it takes on a second job.

| Area | Confirmed ruling |
| --- | --- |
| **Advancement** | The creature uses the advancement package inherited from how it was gained. Ordinary riding and draft work do not change or add a package. Combine class levels only where the source for that package allows it. |
| **Riding suitability** | A mount must be at least one size category larger than its rider and have enough carrying capacity for the rider and all worn and carried inventory. Include the mount’s tack and other carried cargo in its total load. Size and capacity are necessary, not proof of suitable anatomy. For an otherwise possible but ill-suited pairing, apply −5 on Ride checks. |
| **Starting training** | Creatures generally sold as riding animals start riding-trained. War ponies and warhorses start combat-riding-trained, as do riding dogs under the existing source rule. Seed these from the acquisition definition; do not infer training for a wild or work-only animal from its species alone. |
| **Mounted combat** | The mounted lance charge multiplier applies to a charge on any mount, not only a horse. Ordinary riding training does not waive the check to control a non-combat-trained mount in battle. |

### Saddle fit and Ride effects

Each potential mount definition needs a source-backed or DM-confirmed **saddle size** and **fit family**: standard `Saddle` or `Saddle, Exotic` (see `MUNDANE ITEMS.txt`). Fit belongs to the mount’s current body, not the rider or the advancement package. Define fit separately from saddle purpose, and use the same three purposes for both families. If a source does not establish the fit, mark it unconfirmed rather than treating every mount as standard. The rider sheet should only apply saddle benefits for a fitted saddle that supports a rider.

| Saddle purpose | Sheet and encounter effects |
| --- | --- |
| **Military** | Supports a rider. Grants +2 circumstance on Ride checks to stay in the saddle, not on all Ride checks. If the rider is knocked unconscious, they have a 75% chance to stay mounted; the table supplies the roll. |
| **Pack** | Carries gear, not a rider. It does not increase the mount’s carrying capacity or count as a riding saddle. Include the saddle itself in carried load. |
| **Riding** | Supports a rider and uses the normal 50% chance to stay in the saddle when knocked unconscious. No military-saddle bonus. |

**Bareback:** Apply −5 on Ride checks without a fitted rider-supporting saddle (`SKILLS.txt`). Keep that penalty separate from the ill-suited-mount penalty. A pack saddle does not seat a rider; if the DM confirms the rider can ride bareback despite the load or tack, do not grant rider-saddle benefits. Retain the mounted fall rules in `SPECIAL ATTACKS.txt` for encounter adjudication.

### Remaining defaults and exceptions to confirm

| Decision | Recommended default to approve or amend |
| --- | --- |
| **Master-side benefits and presence** | Confirm presence, distance, contact, or availability separately as each familiar or companion rule requires; a saved link alone is not proof. For unsourced cases, leave benefits off until confirmed. Confirm only any house-rule overrides to those source requirements, not a new global proximity radius. |
| **Missing statistics and replacement choices** | Keep unavailable base ranks, saves, HD rolls, or training facts explicitly unknown; don’t reverse-engineer ranks from a listed total or invent choices. Record companion bonus-HD choices once and suppress/reactivate them as master progression changes. If a companion, familiar, or special mount is replaced, its individual gear, training, choices, and damage do not transfer to the new creature. Only source-defined master benefits or restrictions carry over. Confirm any exceptions you want. |
| **Load and concurrent assignments** | Count a rider, tack, packs, and carried cargo once against the mount; use separate draft limits for what it pulls. Use source speeds and load bands, and let the DM decide unusual fit or incompatible simultaneous jobs. A creature can have both riding and draft training without automatically doing both in the same action. Confirm only any house rules for combined carrying and pulling. |

**No ruling needed to start:** source extraction for typed base sheets, standard class progression and explicit special-mount features, Ride and Handle Animal DCs/action costs, and training updates on a single creature instance. Riding training is Handle Animal DC 15 for three weeks; combat riding is DC 20 for six weeks, or three weeks to upgrade ordinary riding. Store learned and bonus tricks separately. Ordinary riding alone does not waive the DC 20 Ride check to control a non-combat-trained mount in battle. Keep rolls, handling commands, unusual suitability, and effects beyond sheet numbers table-confirmed.

**Suggested first implementation slice:** a Druid companion with source-backed base stats, persistent training, and optional rider/tack/load; then reuse that sheet for a purchased working animal, a familiar with master-side effects, and a Paladin special mount. This tests the shared interfaces without requiring a complete nonstandard-mount catalogue first.

**First acceptance cases:** (1) a Druid companion gains bonus HD, then loses and regains access to its exact choices with master level changes; (2) a familiar’s owner gains and loses only the bonuses that depend on its presence; (3) a pack animal’s movement changes when loaded without adding its own weight to the load; and (4) the same companion can be ridden without receiving Paladin special-mount advancement. Add an ordinary war-trained mount and a Paladin special mount as separate cases. Audit the source exceptions before declaring coverage complete; preserve adjudication prose for special abilities and interactions beyond sheet numbers.

## Current coverage

- The structural audit finds no missing IDs from the `RULES.txt` index and no errors in its checked references or adjudication text fields.
- The source audit compares spell summaries and descriptions, condition descriptions, and feat bodies against source blocks. It checks race traits, class abilities, and special-ability paragraphs against their source files. It does not verify every numeric rule or parser against every source.
- **Typed effects are partial.** The structural audit counts 558 of 611 spells and 89 of 124 feats without entries in the effect catalogs it checks. All 124 feats have selection metadata. Those counts do not measure every implementation: some mechanics live in casting plans, item profiles, or actor-state helpers.
- **Feat and equipment projection:** Epic feats carry a source-linked character level 21 gate. The sheet projects confirmed selections for weapon and school feats, repeatable grants, equipment slots, and two-weapon routines. It does not execute attacks, spend uses, or resolve reactions.
- **Drain and actual level loss:** Failed saves cause immediate actual loss. Restoration uses one day per restoring caster level; Greater Restoration uses one week per restoring caster level. Both measure from each failed save. No fixed expiry is attached to an energy-drain loss. Recovery options show elapsed time and the rounded-up timing minimum. Ordinary Cleric casting floors are CL 7 for the 4th-level spell and CL 13 for the 7th-level spell. A confirmed Greater Restoration cast charges the caster 500 XP. Raise Dead losses cannot be restored. Each re-earned level replaces one outstanding loss with fresh choices; only unreplaced losses remain candidates. Restoration reactivates levels in order and never substitutes a missing progression choice.
- **Level-up casting choices:** Bard, Sorcerer and Assassin gains and scheduled swaps, Magewright mastery, and prestige casting targets are recorded atomically. The active level prefix determines effective progression and known spells. New spontaneous casts require the current known set; a cached plan cannot preserve a suppressed feat grant. Slot-budget reconciliation retains spent-slot state, and a cast already started remains in the encounter ledger for resolution.
- **Wizard spellbooks:** Each volume has an instance ID, independent capacity, and its own inscriptions. Preparation searches accessible, intact entries; the table decides which books or entries are lost or damaged. The existing study, inscription, and specialization checks still apply to ordinary Wizard learning.
- **Natural weapons:** Racial natural weapons and recognized companion full-attack entries share weapon-type IDs. Improved Natural Attack is selected by type and projects one damage step on each matching entry across forms. Custom or template forms supply an explicit typed roster. Special attacks outside recognized weapon routines and unsupported damage steps still require adjudication; source attack text remains available.
- **Epic casting feats:** Improved Spell Capacity checks the chosen track, records one daily slot per pick, and applies ability bonus slots only once for a newly unlocked level. Spell Knowledge requires at least one level in the chosen arcane class and the ability to cast at least one spell in that class. Each chosen spell is capped at the highest level the character can currently cast on that track, not the class’s normal maximum. It records two new arcane spells and grants no slots. The receiving list supplies the spell level when available; otherwise the arcane source list supplies it (confirm a list when levels differ). The chosen arcane casting track is independent of the class gained at level-up. Only a Wizard-track pick requires room in accessible books and automatically inscribes both spells; prohibited schools still apply. Level loss and restoration project both feats from the saved picks; restoration does not repair lost or damaged books.

## Open findings

| Area | What remains |
| --- | --- |
| Class ability prose | 15 descriptions do not match a contiguous source passage. The Wizard spellbook conflict is resolved. `tools/source_audit.py` lists the records; a paraphrase or joined passage is not necessarily a rules discrepancy. |
| Feat eligibility | Improved Familiar uses the dedicated acquisition catalog; unlisted candidates remain a DM ruling. Familiar Spell validates known spell levels and XP components; unpriced materials are negligible; stated costs may need confirmation. |
| Spell preparation | Spell Mastery validates selections and marks mastered spells, but does not bypass the current Wizard book requirement. The caller confirms book access and study/writing time; item-use school checks are separate from cast scheduling. |
| Combat context | The caller supplies cover, concealment, flanking, and opportunity triggers. There is no map geometry or automatic reaction engine. Exposed-item damage on a natural 1 remains manual. For casting injury, the caller confirms the interruption and supplies the Concentration roll; the cast helper checks the DC. |
| Effect stacking | The sheet uses the highest bonus and most negative penalty per named type. Same-source overlap is a DM ruling. |
| Damage and drain | The sheet projects class DR and confirmed external grants; aligned weapon properties supply bypass tags, not automatic extra damage. Actor helpers reconcile existing spell ledgers after actual loss, recovery, and replacement advancement. The caller still supplies confirmed events and keeps current HP, timed conditions, and inventory in their respective ledgers. |

## Verification

Fresh run: generated core and standalone template normalization are current; the structural audit reported no checked errors; all 153 unit tests passed. The source audit reported 15 class-ability prose findings and no findings in its other compared groups. These are structural and targeted behavioral checks, not exhaustive numeric or gameplay validation.

```sh
python tools/organize_core.py --check
python tools/audit_core.py
python tools/source_audit.py
python tools/normalize_templates.py --check
python -m unittest discover -s tools
```

## Spellcasting integration audit

`casting_profile` assembles the independent casting tracks from class `spellcasting` and `magic.castingPoliciesByClassId`. Domain eligibility comes from progression; policies add Wizard book requirements and Cleric or Druid conversion. Druid conversion no longer requires separate authorization for each eligible spell; Cleric cure/inflict authorization is still supplied from the character’s alignment, deity, and permanent choice. Prepared domain slots cannot be converted.

Caster level and effective slot progression are separate. `base_caster_level` and the optional cast-plan `class_level` input implement the class baseline, including half level for Paladin and Ranger from class level 4. Apply temporary adjustments separately. Daily recovery is available for Wizard, Bard, Sorcerer, Cleric, Druid, Paladin, Ranger, Adept, Magewright, Blackguard, and Assassin. Assassin follows Bard recovery. Adept’s daily prayer is explicit in its source; Magewright and Blackguard follow their stated Wizard and Cleric procedures respectively.

A cast plan can be checked against confirmed components and conditions. Blocked plans cannot be scheduled or spent. `resolve_cast_completion` refuses unchecked components and combines supplied component, Concentration, and armor rolls before releasing a spell for targeting and effect resolution. Scheduling still reports timing completion, not success. The caller confirms inventory, timing, area membership, and any changes during a multi-round cast; roll results and mutable equipment do not belong in shared rules data.

### Current table rulings

- Divine casters choose their preparation time each day. Wizard full and partial preparation use the same verified eight hours of uninterrupted rest and one hour of uninterrupted study.
- Materials with a stated cost require the actual accessible item. All unpriced materials, including named ones, are supplied by an equipped pouch or waived by Eschew Materials. Unpriced materials remain negligible for Familiar Spell.
- DM-confirmed deafness adaptation halves the initiative penalty and verbal failure chance; Listen still automatically fails.
- Casting injury uses Concentration DC 10 + damage taken + spell level. Halve the last damage from an ongoing continuous source, round down, and ignore a source that already ended. Separate repeated hits are checked individually.

### Source clarification still useful

- Unusual component alternatives and variable costs still need case-by-case confirmation.
- The rule for a Focus component still uses an accessible pouch. Named foci are distinct from named **materials**; their individual requirements remain in spell prose.

### Remaining integration work that does not need a new ruling

- Unusual off-list Sorcerer learning through study and ordinary Wizard acquisition remain separate from the per-level known-spell transaction. Prestige admission and unmodeled class choices still require table confirmation.
- Feed recorded domain selections, Cleric conversion choice, temporary caster-level bonuses, and live component access from actor state into each cast. Apply spell effects only after the table confirms targeting, saves, and spell resistance.
- Batch recovery already reapplies active negative levels. Persist its returned ledgers alongside actor state. Greater Restoration has a confirmed-cast XP transaction; general component consumption and other spell XP charges still need live actor integration.

The Large monstrous spider is catalogued separately from the Small familiar. Its hunter speed adjustment, web-spinning restrictions, and silk support rule are preserved as source prose. The supplemental SRD stat block establishes a 20 ft. climb speed. The +8 racial bonus in the Climb rule and the spider entry describes the same bonus, not two bonuses. The campaign permits mounted climbing with a climb speed and a DC 5 Ride check to stay seated. The spider requires an exotic saddle; its suitability, carrying limits, and training or control remain unconfirmed; silk support alone does not establish any of those.

Training purpose suitability and attitudes without source rules still require table confirmation. Generic trick training outside the source’s Intelligence 1–2 capacity table is not automated; species-specific training follows its own rule.
