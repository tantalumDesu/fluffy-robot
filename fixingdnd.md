# Fix Log — Spell Descriptions Pass (`fixingdnd.md`)

Log of every change made to the `.txt` files and `dnd core.json` during the spell-descriptions work. Newest entries first.

---

## Stage S1 — Reconciliation & decision list (NO data changes)

| Item | Detail |
|---|---|
| **Change to `.txt` files** | **None.** No spell was purged or renamed in this stage, pending the individual decisions requested in `dndsucks.md` (§§3–6, Q1–Q8). |
| **Change to `dnd core.json`** | **None.** |
| Files created | `fluffy-robot/dndsucks.md` (decision workbook), `fluffy-robot/fixingdnd.md` (this log) |
| Method | Parsed all 605 headings in `SPELL DESCRIPTIONS.txt` (`Level:`-anchored); matched against the 10 `spellLists`, 81 `domains`, and 760-entry `spells` index in the JSON; normalised curly apostrophes and applied an author-prefix alias pass (Melf/Bigby/Tenser/Otiluke/Leomund/Rary/Nystul/Drawmij/Otto/Tasha/Evard/`Mage’s`→Mordenkainen’s, plus `Confusion, Lesser` inversion) so renames are not misreported as gaps; counted both name forms across all 49 `.txt` files. |
| Result (summary) | 28 alternative-name pairs (§3 of `dndsucks.md`); 4 strict purge candidates, all domain-only alignment-domain spells (§4); 11 described spells covered only by 5 grouped JSON entries (§5); 2 true description gaps — *Corrupt Weapon*, *Hardening* (§6.1); 163 domain-referenced spells without descriptions, 159 of them class-list-less (Appendix A). |
| Untouched-file verification (SHA-256, first 16) | `SPELL DESCRIPTIONS.txt` 37bba9486195dd2c; `SPELL LISTS.txt` 099944d6903497cc; `DOMAINS.txt` a36e3376ceaf69c7; `dnd core.json` 7bd28a41e53ad935 |

### Originally-planned stages (superseded by S2–S7 below)

- [ ] **S2 Renames** (per `dndsucks.md` §3 decisions): for each confirmed spell — `SPELL DESCRIPTIONS.txt` cross-refs, `SPELL LISTS.txt`, `DOMAINS.txt`, class/prestige/NPC `.txt` mentions, JSON `name`/`id`/`spellIds` (id policy per Q4). Entry template: *old name → new name · files touched · occurrences changed · new id/slug*.
- [ ] **S3 Purges** (per §4/Q1/Q2/Q8): description entry removed, list/domain lines removed, JSON entries removed, `meta.counts` recalculated. Entry template: *spell · where removed from · archived or deleted outright*.
- [ ] **S4 Grouped alignment spells** (per §5/Q6): split / keep / hybrid, with resulting JSON id changes itemised.
- [ ] **S5 Gap closures** (per §6/Q7): any description added for *Corrupt Weapon* / *Hardening* will cite its source here; if a spell is dropped from a list instead, that removal is logged as a purge under S3.
- [ ] **S6 Explorer verification**: rebuild (`npm run build`), confirm spell counts in the UI match the post-change `meta.counts`, and confirm no dangling `spellIds` (class lists, domains) point at renamed/purged ids — verification result recorded here.

> Rule for this log: no `.txt` or JSON edit is considered done until it has an entry above with files and occurrence counts. Decisions live in `dndsucks.md`; executions live here.

---

## Stage S2 — Flavourful renames D01–D28 (EXECUTED)

All 28 renamed in every `.txt` where the spell is named and in `dnd core.json`. JSON ids changed to flavourful slugs and every `spellId` reference repointed (verified: no old id survives as a value anywhere in the JSON).

| # | Old (list name / id) | New name / id |
|---|---|---|
| D01 | Acid Arrow / `acid-arrow` | Melf’s Acid Arrow / `melfs-acid-arrow` |
| D02 | Black Tentacles / `black-tentacles` | Evard’s Black Tentacles / `evards-black-tentacles` |
| D03 | Clenched Fist / `clenched-fist` | Bigby’s Clenched Fist / `bigbys-clenched-fist` |
| D04 | Crushing Hand / `crushing-hand` | Bigby’s Crushing Hand / `bigbys-crushing-hand` |
| D05 | Floating Disk / `floating-disk` | Tenser’s Floating Disk / `tensers-floating-disk` |
| D06 | Forceful Hand / `forceful-hand` | Bigby’s Forceful Hand / `bigbys-forceful-hand` |
| D07 | Freezing Sphere / `freezing-sphere` | Otiluke’s Freezing Sphere / `otilukes-freezing-sphere` |
| D08 | Grasping Hand / `grasping-hand` | Bigby’s Grasping Hand / `bigbys-grasping-hand` |
| D09 | Hideous Laughter / `hideous-laughter` | Tasha’s Hideous Laughter / `tashas-hideous-laughter` |
| D10 | Instant Summons / `instant-summons` | Drawmij’s Instant Summons / `drawmijs-instant-summons` |
| D11 | Interposing Hand / `interposing-hand` | Bigby’s Interposing Hand / `bigbys-interposing-hand` |
| D12 | Irresistible Dance / `irresistible-dance` | Otto’s Irresistible Dance / `ottos-irresistible-dance` |
| D13 | Lesser Confusion / `lesser-confusion` | Confusion, Lesser / `confusion-lesser` |
| D14 | Mage's Disjunction / `mages-disjunction` | Mordenkainen’s Disjunction / `mordenkainens-disjunction` |
| D15 | Mage's Faithful Hound / `mages-faithful-hound` | Mordenkainen’s Faithful Hound / `mordenkainens-faithful-hound` |
| D16 | Mage's Lucubration / `mages-lucubration` | Mordenkainen’s Lucubration / `mordenkainens-lucubration` |
| D17 | Mage's Magnificent Mansion / `mages-magnificent-mansion` | Mordenkainen’s Magnificent Mansion / `mordenkainens-magnificent-mansion` |
| D18 | Mage's Private Sanctum / `mages-private-sanctum` | Mordenkainen’s Private Sanctum / `mordenkainens-private-sanctum` |
| D19 | Mage's Sword / `mages-sword` | Mordenkainen’s Sword / `mordenkainens-sword` |
| D20 | Magic Aura / `magic-aura` | Nystul’s Magic Aura / `nystuls-magic-aura` |
| D21 | Mnemonic Enhancer / `mnemonic-enhancer` | Rary’s Mnemonic Enhancer / `rarys-mnemonic-enhancer` |
| D22 | Resilient Sphere / `resilient-sphere` | Otiluke’s Resilient Sphere / `otilukes-resilient-sphere` |
| D23 | Secret Chest / `secret-chest` | Leomund’s Secret Chest / `leomunds-secret-chest` |
| D24 | Secure Shelter / `secure-shelter` | Leomund’s Secure Shelter / `leomunds-secure-shelter` |
| D25 | Telekinetic Sphere / `telekinetic-sphere` | Otiluke’s Telekinetic Sphere / `otilukes-telekinetic-sphere` |
| D26 | Telepathic Bond / `telepathic-bond` | Rary’s Telepathic Bond / `rarys-telepathic-bond` |
| D27 | Tiny Hut / `tiny-hut` | Leomund’s Tiny Hut / `leomunds-tiny-hut` |
| D28 | Transformation / `transformation` | Tenser’s Transformation / `tensers-transformation` |

Files touched by the rename pass: `SPELL LISTS.txt` (every list entry), `DOMAINS.txt` (domain spell entries, straight-apostrophe forms normalised to `’`), `NPC MAGEWRIGHT.txt` (magewright list), `SPELL DESCRIPTIONS.txt` (cross-references: "functions like Bigby’s Interposing Hand…", summon-monster tables, permanency table). Class/prestige files contained no other spell-name instances of these 28 (verified by full-text search; remaining hits are generic noun uses, left alone — see `dndsucks.md` A6). JSON summaries containing cross-references were updated too (e.g. *Otiluke’s Telekinetic Sphere*: "As Otiluke’s Resilient Sphere, but…").

## Stage S3 — Corrupt Weapon description added (EXECUTED)

- `SPELL DESCRIPTIONS.txt`: new entry inserted at line 1188, alphabetically between *Control Winds* and *Create Food and Water*, text **exactly as supplied** (including `[evil]`, `none`, `no`, "the paladins spell" — flagged as A7 in `dndsucks.md`).
- JSON: `corrupt-weapon` already existed (`blackguard 1`); verified present with correct membership after the list rebuild.

## Stage S4 — Domain normalisation X01–X15 (EXECUTED)

| # | Domain(s) | Was | Now points to |
|---|---|---|---|
| X01 | Mysticism | Blasphemy/Holy Word | Blasphemy + Holy Word (`blasphemy`, `holy-word`) |
| X02 | Darkness | Blindness (`blindness`) | Blindness/Deafness (`blindness-deafness`); standalone `blindness` spell entry removed in S7 |
| X03 | Domination, Herald, Nobility | Greater Command | Command, Greater (`command-greater`) |
| X04 | Liberation | Greater Dispel Magic | Dispel Magic, Greater |
| X05 | Rune | Greater Glyph of Warding | Glyph of Warding, Greater |
| X06 | Joy | Greater Heroism | Heroism, Greater |
| X07 | Skalykind | Greater Magic Fang | Magic Fang, Greater |
| X08 | Summoner | Greater Planar Ally | Planar Ally, Greater |
| X09 | Mysticism | Holy Aura/Unholy Aura | Holy Aura + Unholy Aura (`holy-aura`, `unholy-aura`) |
| X10 | Summoner | Lesser Planar Ally | Planar Ally, Lesser |
| X11 | Rune | Lesser Planar Binding | Planar Binding, Lesser |
| X12 | Endurance | Mass Bear's Endurance | Bear's Endurance, Mass |
| X13 | Pleasure | Mass Eagle's Splendor | Eagle's Splendor, Mass |
| X14 | Community | Mass Heal | Heal, Mass |
| X15 | Temptation | Mass Suggestion | Suggestion, Mass |

Applied in `DOMAINS.txt` (spell-name column) and in JSON `domains[].spells[].name/.spellIds`. Note: X02, X06, X12, X13, X15 sit in domains that were then purged in S6 for *other* spells — the normalisation was still applied first, so the purge reasons in S6 are post-normalisation.

## Stage S5 — Protection spells separated (EXECUTED)

- **Alignment:** removed `protection-from-chaos-evil-good-law` and `protection-from-chaos-evil`; added `protection-from-chaos/evil/good/law` as individual spells. `SPELL LISTS.txt`: cleric, sorcerer/wizard, adept 1st-level entries expanded to four; paladin to two (Chaos, Evil). `NPC ADEPT.txt` list expanded likewise. Domain entries (Chaos/Good/Evil/Law/Diabolic) repointed to the individual ids. Descriptions already existed individually — unchanged.
- **Energy:** removed `protection-from-energy`; added `protection-from-acid/cold/electricity/fire/sonic`. `SPELL DESCRIPTIONS.txt`: original entry deleted and five specialised entries inserted alphabetically (*Acid* before *Arrows*; *Cold*, *Electricity* before *Evil*; *Fire* before *Good*; *Sonic* before *Spells*), each with the original header statistics and an energy-specific body/note. `SPELL LISTS.txt`: all five list entries (cleric 3, druid 3, ranger 2, sorcerer/wizard 3, blackguard 3) expanded to five spells each. `Prestige Class BLACKGUARD.txt` list expanded to the five names. *Hallow*, *Unhallow* and *Resist Energy* references updated. Luck/Protection domain slots kept as a single choice-of-five entry (see `dndsucks.md` A2).
- Net list memberships: 1,200 → **1,230** (+9 alignment expansions in grouped lists, +1 paladin, +20 energy expansions).

## Stage S6 — Domain purge (EXECUTED): 46 purged, 35 kept

Rule applied, after S2–S5: purge any domain containing a spell that is on no class spell list. Removed from `DOMAINS.txt` (whole domain section) and JSON `domains[]`. Offending spell(s) per purged domain:

| Purged domain | Spell(s) not on any class list |
|---|---|
| Chaos | 4:Chaos Hammer (chaos-hammer) |
| Cold | 9:Obedient Avalanche (obedient-avalanche) |
| Competition | 2:Zeal (zeal); 6:Zealot Pact (zealot-pact); 9:Visage of the Deity, Greater (visage-of-the-deity-greater) |
| Corruption | 4:Morality Undone (morality-undone); 6:Pox (pox); 8:Befoul (befoul); 9:Despoil (despoil) |
| Courage | 3:Cloak of Bravery (cloak-of-bravery); 5:Valiant Fury (valiant-fury); 8:Lion's Roar (lions-roar); 9:Cloak of Bravery, Greater (cloak-of-bravery-greater) |
| Creation | 8:True Creation (true-creation); 9:Genesis (genesis) |
| Darkness | 3:Blacklight (blacklight); 4:Armor of Darkness (armor-of-darkness) |
| Demonic | 1:Demonflesh (demonflesh); 2:Demoncall (demoncall); 3:Demon Wings (demon-wings); 7:Fiendish Clarity (fiendish-clarity) |
| Destiny | 1:Omen of Peril (omen-of-peril); 3:Delay Death (delay-death); 5:Stalwart Pact (stalwart-pact); 6:Warp Destiny (warp-destiny); 7:Bestow Curse, Greater (bestow-curse-greater); 9:Choose Destiny (choose-destiny) |
| Diabolic | 2:Devil's Eye (devils-eye); 3:Devil's Ego (devils-ego); 4:Hellfire (hellfire); 7:Hellfire Storm (hellfire-storm); 9:Investiture of the Pit Fiend (investiture-of-the-pit-fiend) |
| Domination | 8:True Domination (true-domination); 9:Monstrous Thrall (monstrous-thrall) |
| Dragon | 4:Voice of the Dragon (voice-of-the-dragon); 7:Dragon Ally (dragon-ally) |
| Dream | 6:Dream Sight (dream-sight) |
| Endurance | 3:Refreshment (refreshment); 4:Sustain (sustain) |
| Entropy | 2:Vision of Entropy (vision-of-entropy); 9:Abyssal Rift (abyssal-rift) |
| Evil | 4:Unholy Blight (unholy-blight) |
| Fey | 3:Inspired Aim (inspired-aim); 4:Blinding Beauty (blinding-beauty); 8:Unearthly Beauty (unearthly-beauty) |
| Force | 3:Blast of Force (blast-of-force) |
| Fury | 7:Abyssal Frenzy (abyssal-frenzy); 9:Abyssal Frenzy, Mass (abyssal-frenzy-mass) |
| Glory | 4:Holy Smite (holy-smite); 6:Bolt of Glory (bolt-of-glory); 8:Crown of Glory (crown-of-glory) |
| Good | 4:Holy Smite (holy-smite) |
| Greed | 1:Cheat (cheat); 2:Entice Gift (entice-gift); 8:Phantasmal Thief (phantasmal-thief) |
| Herald | 7:Aspect of the Deity (aspect-of-the-deity); 8:Crown of Glory (crown-of-glory); 9:Greater Aspect of the Deity (greater-aspect-of-the-deity) |
| Hunger | 1:Ghoul Light (ghoul-light); 2:Ghoul Glyph (ghoul-glyph); 3:Ghoul Gesture (ghoul-gesture); 5:Ghoul Gauntlet (ghoul-gauntlet); 6:Eyes of the King (eyes-of-the-king); 7:Field of Ghouls (field-of-ghouls); 8:Bite of the King (bite-of-the-king) |
| Joy | 1:Vision of Heaven (vision-of-heaven); 2:Elation (elation); 3:Distilled Joy (distilled-joy); 5:Chaav's Laugh (chaavs-laugh); 7:Starmantle (starmantle) |
| Law | 4:Order's Wrath (orders-wrath) |
| Madness | 2:Touch of Madness (touch-of-madness); 5:Bolts of Bedevilment (bolts-of-bedevilment); 8:Maddening Scream (maddening-scream) |
| Mind | 3:Lesser Telepathic Bond (lesser-telepathic-bond); 6:Probe Thoughts (probe-thoughts); 7:Brain Spider (brain-spider) |
| Mysticism | 3:Visage of the Deity, Lesser (visage-of-the-deity-lesser); 4:Weapon of the Deity (weapon-of-the-deity); 6:Visage of the Deity (visage-of-the-deity); 9:Visage of the Deity, Greater (visage-of-the-deity-greater) |
| Ocean | 7:Waterspout (waterspout); 8:Maelstrom (maelstrom) |
| Ooze | 5:Oozepuppet (oozepuppet); 7:Slime Wave (slime-wave); 8:Befoul (befoul) |
| Pact | 5:Stalwart Pact (stalwart-pact); 6:Zealot Pact (zealot-pact); 7:Renewal Pact (renewal-pact); 8:Death Pact (death-pact) |
| Pleasure | 2:Lastai's Caress (lastais-caress); 3:Heart's Ease (hearts-ease); 4:Remove Fatigue (remove-fatigue); 6:Celestial Blood (celestial-blood); 7:Empyreal Ecstasy (empyreal-ecstasy); 8:Spread of Contentment (spread-of-contentment); 9:Sublime Revelry (sublime-revelry) |
| Pestilence | 5:Plague of Rats (plague-of-rats); 6:Curse of Lycanthropy (curse-of-lycanthropy); 7:Scourge (scourge); 9:Otyugh Swarm (otyugh-swarm) |
| Purification | 1:Nimbus of Light (nimbus-of-light); 2:Deific Vengeance (deific-vengeance); 3:Recitation (recitation); 4:Castigate (castigate); 5:Dance of the Unicorn (dance-of-the-unicorn); 6:Fires of Purity (fires-of-purity); 7:Righteous Wrath of the Faithful (righteous-wrath-of-the-faithful); 9:Visage of the Deity, Greater (visage-of-the-deity-greater) |
| Repose | 8:Surelife (surelife) |
| Sand | 1:Waste Strider (waste-strider); 2:Black Sand (black-sand); 3:Haboob (haboob); 4:Blast of Sand (blast-of-sand); 5:Flaywind Burst (flaywind-burst); 6:Awaken Sand (awaken-sand); 7:Vitrify (vitrify); 8:Desert Binding (desert-binding); 9:Summon Desert Ally IX (summon-desert-ally-ix) |
| Seafolk | 1:Quickswim (quickswim); 2:Fins to Feet (fins-to-feet); 3:Scales of the Sealord (scales-of-the-sealord); 4:Siren's Call (sirens-call); 6:Airy Water (airy-water); 7:Megalodon Empowerment (megalodon-empowerment); 8:Depthsurge (depthsurge) |
| Sky | 1:Raptor's Sight (raptors-sight); 2:Summon Dire Hawk (summon-dire-hawk); 3:Enduring Flight (enduring-flight); 4:Aerial Alacrity (aerial-alacrity); 8:Mastery of the Sky (mastery-of-the-sky); 9:Summon Devoted Roc (summon-devoted-roc) |
| Spite | 1:Bestow Wound (bestow-wound); 4:Pronouncement of Fate (pronouncement-of-fate); 5:Fire in the Blood (fire-in-the-blood); 6:Cloak of Hate (cloak-of-hate); 7:Pact of Return (pact-of-return); 8:Mantle of Pure Spite (mantle-of-pure-spite); 9:Imprison Soul (imprison-soul) |
| Summer | 1:Impede Sun's Brilliance (impede-suns-brilliance); 2:Sunstroke (sunstroke); 3:Protection from Dessication (protection-from-dessication); 4:Skin of the Cactus (skin-of-the-cactus); 5:Unearthly Heat (unearthly-heat) |
| Temptation | 2:Beckoning Call (beckoning-call); 7:Soul Link (soul-link) |
| Thirst | 1:Parching Touch (parching-touch); 2:Desiccate (desiccate); 3:Tormenting Thirst (tormenting-thirst); 4:Dispel Water (dispel-water); 5:Desiccate, Mass (desiccate-mass); 6:Symbol of Thirst (symbol-of-thirst); 7:Mephit Mob (mephit-mob) |
| Vile Darkness | 2:Darkbolt (darkbolt); 4:Damning Darkness (damning-darkness); 8:Utterdark (utterdark) |
| Winter | 1:Snowsight (snowsight); 2:Snow Walk (snow-walk); 3:Winter's Embrace (winters-embrace); 5:Blizzard (blizzard); 6:Death Hail (death-hail); 8:Summon Giants (Frost Giants Only) (summon-giants-frost-giants-only); 9:Fimbulwinter (fimbulwinter) |
| Wrath | 2:Energize Potion (energize-potion); 3:Affliction (affliction); 4:Radiant Shield (radiant-shield); 6:Vengeance Halo (vengeance-halo); 7:Righteous Smite (righteous-smite); 8:Last Judgment (last-judgment) |

Kept (35): Air, Animal, Charm, Community, Death, Destruction, Earth, Fate, Fire, Hatred, Healing, Inquisition, Knowledge, Liberation, Luck, Magic, Nobility, Oracle, Planning, Plant, Protection, Rune, Skalykind, Storm, Strength, Summoner, Sun, Travel, Trickery, Tyranny, Undeath, War, Water, Wealth, Weather.

## Stage S7 — JSON spell-index cleanup & mechanical verification (EXECUTED)

- Removed **159 orphan `spells[]` entries** (no class list, no surviving domain, no description) — the full set is the Appendix A list in the previous `dndsucks.md`; includes superseded standalone `blindness`.
- Retention rule: a spell stays in `spells[]` iff it is on a class list, in a surviving domain, or described in `SPELL DESCRIPTIONS.txt` (so the four alignment-domain signature spells survive with `lists: []` — see `dndsucks.md` A4).
- Rebuilt every `spells[].lists` from `spellLists`; verification: **0 dangling `spellIds`** in `spellLists`/`domains`, **0 lists mismatches**, `DOMAINS.txt` headings (35) match JSON domains (35), `meta.counts` = {domains: 35, spells: 607}.
- Described spells now: **610** headings in `SPELL DESCRIPTIONS.txt` (605 + *Corrupt Weapon* + 5 energy splits − 1 combined *Protection from Energy*); all have their own JSON entry except the 7 remaining grouped-alignment variants (`dndsucks.md` A8).
- Explorer rebuilt with the new data: `npm run build` ✅ (single-file `dist/index.html`).


## Stage S8 — Protection from Energy restored; Frost/Lightning/Thunder renames (EXECUTED)

- **Generic spell restored:** `SPELL DESCRIPTIONS.txt` — original *Protection from Energy* entry re-inserted alphabetically (after *Protection from Chaos*); JSON `spells[]` re-added `protection-from-energy` ("Absorb 12 points/level of damage from one kind of energy.", Abjuration, `lists: []`, file `DOMAINS.txt`). `meta.counts.spells` 607 → **608**. Not re-added to class spell lists (see `dndsucks.md` F1).
- **Domain rollback:** `DOMAINS.txt` lines for Luck (3) and Protection (3) restored to `Protection from Energy`; JSON `domains[]` for Luck/Protection: name `Protection from Energy`, `spellIds: [protection-from-energy]`, added `note` removed. X-normalisation and the S6 purge were **not** rolled back (F3).
- **Renames (name + JSON id, everywhere the spell is named):**

| Was | Now | JSON id |
|---|---|---|
| Protection from Cold | Protection from Frost | `protection-from-cold` → `protection-from-frost` |
| Protection from Electricity | Protection from Lightning | `protection-from-electricity` → `protection-from-lightning` |
| Protection from Sonic | Protection from Thunder | `protection-from-sonic` → `protection-from-thunder` |

  Applied in `SPELL DESCRIPTIONS.txt` (headings, bodies, cross-reference lists in *Hallow/Unhallow/Resist Energy*; entries moved to their new alphabetical positions — Frost between Fire and Good, Lightning between Law and Spells, Thunder after Spells), `SPELL LISTS.txt` (all five list blocks), `Prestige Class BLACKGUARD.txt`, and the JSON (`spells[].name/id`, `spellLists` membership, rebuilt `spells[].lists`). Canonical damage words (cold/electricity/sonic damage) retained in bodies and summaries (F2).
- **Description headers:** the five variant entries' `Level:` lines changed from `Clr 3, Drd 3, Luck 3, Protection 3, Rgr 2, Sor/Wiz 3` to `Clr 3, Drd 3, Rgr 2, Sor/Wiz 3`; the restored generic entry keeps the original header including Luck 3, Protection 3.
- **Verification:** 0 dangling `spellIds`; no occurrence of the three old names in any `.txt` or the JSON; domains 35 unchanged; explorer rebuilt (`npm run build` ✅). Luck/Protection are now intentional exceptions to the S6 purge rule.

## Stage S9 — Hardening removed completely (EXECUTED)

- `SPELL LISTS.txt`: `Hardening: …` list entry deleted (before the file was merged in S11).
- `NPC MAGEWRIGHT.txt`: `hardening` removed from the 4th-level magewright list.
- `dnd core.json`: `spells[]` entry `hardening` deleted; `magewright 4` membership removed; all `spells[].lists` rebuilt. Verified: zero occurrences of the spell's name in any `.txt` or the JSON ("hardened" as an ordinary verb in unrelated prose left untouched).

## Stage S10 — Protection from Energy added to class spell lists (EXECUTED)

- `SPELL LISTS.txt` + JSON `spellLists`: `Protection from Energy` added at cleric 3, druid 3, ranger 2, sorcerer/wizard 3, blackguard 3 (immediately before the Acid/Frost/Lightning/Fire/Thunder variants, which are unchanged). `protection-from-energy` now has those five `lists` memberships. Resolves `dndsucks.md` F1 in favour of list membership.

## Stage S11 — SPELLBOOK.txt merge, harmonisation & typed mechanics (EXECUTED)

- **Created `SPELLBOOK.txt`** (611 entries, alphabetical, CRLF): merged short descriptions (ex-`SPELL LISTS.txt`) and long descriptions (ex-`SPELL DESCRIPTIONS.txt`) in a single entry per spell, keyed to its classes. **`SPELL LISTS.txt` and `SPELL DESCRIPTIONS.txt` deleted** after the merge (the explorer now points at `SPELLBOOK.txt`).
- **Harmonised tags on every entry** (all present, `—` where genuinely none): Class, Class Spell Level (both filled from the class spell lists), Type (Arcane/Divine tradition — G1), School (school/subschool/descriptors), Domain (surviving domains only — Chaos/Evil/Good/Law domain tags stripped as nonexistent), Duration, Range, Target (+Area/Effect), Components, Casting Time, Saving Throw, Spell Resistance, Damage Type, Damage dice, Dice Rolls, Healing. Missing source fields filled by inheritance from "functions like …" base spells (723 field instances) or by the None/No omission defaults (G2/G3), all flagged in entry field notes.
- **JSON wired up:** every one of the 607 `spells[]` now has `shortDescription`, `longDescription` (= `description`), `classes`, `domains`, `type`, typed `components` (code+name), `castingTime`/`range`/`duration` (raw + category; duration also `dismissible`), `target` (raw/area/effect), `savingThrow` (type+effect), `spellResistance` (applies flag), `mechanics` (damageTypes, per-type damage expressions, all diceRolls, healing, scalesWithCasterLevel), a flat searchable `tags` object, and `file: "SPELLBOOK.txt"`. 0 spells missing a short description, 0 missing a long description. Damage catalogue: Acid 10, Cold 16, Electricity 12, Fire 33, Sonic 16, Force 23, Positive Energy 3, Negative Energy 6, Divine 1, Bludgeoning 6, Piercing 3, Slashing 1 (no spell deals Desiccation damage under that name). `meta.placeholders` for `spells[].description` marked filled.
- **Explorer:** spell search now covers long descriptions; new filters for damage type, range category, duration category and saving-throw type; spell detail shows the full typed tag grid plus short/long descriptions and a `SPELLBOOK.txt` source link.
- **Verification:** every SPELLBOOK entry carries all 14 tag lines (611/611); 0 dangling `spellIds`; `npm run build` ✅.

## Stage S12 — Spell Replacement tables removed (EXECUTED)

- **Txt:** `BARD.txt` — "Table: Bard Spell Replacement" (title, header, all 20 rows) deleted; `SORCERER.txt` — "Table: Sorcerer Spell Replacement" (title, header, all 20 rows) deleted. The surrounding *Spells* prose (which describes the swap in words) is unchanged — only the tables were ordered removed.
- **JSON:** deleted `meta.rules.spellReplacement`; deleted the `Bard Spell Replacement` and `Sorcerer Spell Replacement` entries from `classes[].auxTables` for Bard and Sorcerer; deleted the derived `Spell Swap` effects from both classes' *Spells* abilities and the whole `stats["Spell Swap"]` index (the JSON implementations of the replacement mechanic). `meta.counts` adjusted: auxTables 20 → 18, effects 696 → 694, stats 99 → 98.
- **Verification:** zero occurrences of "Spell Replacement" or "Spell Swap" remain in any `.txt` or in `dnd core.json`; explorer rebuilt (`npm run build` ✅) — the Overview's universal-rules cards and class detail no longer show the tables.

## Stage S13 — Rules system: spell replacement as a mechanic + Ability Modifiers/Bonus Spells rule (EXECUTED)

- **New top-level `rules` collection in `dnd core.json`** (incremental, each rule carries `schema: 1`, `id`, `category`, `status`, `source`, `appliesTo`, typed `mechanic`). Future rules are added as new objects in this array — plus their table/prose in `RULES.txt` — without changing the schema. This is the canonical home for implemented rules from now on; `meta.rules` is retained as the legacy store.
- **Spell replacement re-implemented as a mechanic** (`rules[0]`, `mechanic.type: "scheduled-spell-swap"`): Bard schedule first eligible 5th, every 3 levels (5, 8, 11, 14, 17, 20); Sorcerer first eligible 4th, every 2 levels (4, 6, 8, …, 20); parameters `swapsPerEligibleLevel: 1`, new spell same level as replaced, `minLevelsBelowHighestCastable: 2`, chosen when gaining new spells known for the level; with an `evaluation` block (inputs, eligibility, `maxReplaceableSpellLevel = highestCastable - 2`). The Charisma-threshold tables deleted in S12 are *not* used. Bard and Sorcerer classes (and every spellcasting class, for the rule below) gained a `ruleIds` array wiring them to the rules.
- **`RULES.txt` created** in fluffy-robot, containing "Table: Ability Modifiers and Bonus Spells" exactly as supplied (score 1 to 44-45, generated from the verified table data).
- **Bonus spells implemented as a rule** (`rules[1]`, `mechanic.type: "table-lookup"`): full 23-row typed table (`scoreMin/scoreMax/modifier/canCast/bonusSpells[0..9]`), `abilityByClass` wiring derived from each spellcasting class's key ability, and the score ≤ 9 "can't cast" special case. The rows match the existing `meta.rules.bonusSpellsTable` (which is kept as a legacy mirror — the `rules` copy is canonical).
- **Explorer:** new **Rules** tab — searchable rule cards with class links, a spell-swap eligibility checker (class + level + highest castable → eligible and maximum replaceable spell level), an ability-score slider with modifier/bonus-spell readout plus the full table, and a raw-JSON view for every rule (so future rules render even before bespoke widgets exist). `rules` also appears in the JSON Data view.
- **Verification:** all `ruleIds` and `appliesTo.classIds` resolve to real classes/rules (0 dangling); `npm run build` ✅.

## Stage S14 — CONDITIONS.txt wired in with typed mechanics and cross-references (EXECUTED)

- **New top-level `conditions` collection in `dnd core.json`**: all 38 conditions parsed from `CONDITIONS.txt` (continuation paragraphs re-attached to their condition), each with `id`, `name`, manually-assigned typed `category` (ability / sensory / fear / movement / mental / combat / form / undead / vital), `summary` (first sentence), full `description`, `source: "CONDITIONS.txt"`, and typed `mechanics`: extracted `modifiers[]` (target, signed amount, penalty/bonus), `losesDexterityBonusToAC`, `movement` (speed multiplier where stated), `actionRestrictions[]` and `automaticFailures[]` (verbatim sentences, typed as lists). `meta.counts.conditions = 38`.
- **References throughout spells:** every `spells[]` entry gained `conditions[]` — 280 references in total — each `{conditionId, condition, relation, evidence}` where relation is one of `inflicts` / `removes` / `interacts` / `mentions`, derived sentence-by-sentence from the spell's summary and long description (with summary references promoted to `inflicts`, immunity/interaction phrasing typed as `interacts`, and synonym patterns such as "turns into a statue" → Petrified). Conditions carry the reverse index: `references.inflictedBySpells`, `removedBySpells`, `mentionedInSpells`.
- **References throughout special abilities:** every `classes[].abilities[]` gained the same `conditions[]` structure (39 references — e.g. Rage → Fatigued `inflicts`, Uncanny Dodge → Flat-Footed/Invisible `interacts`), and conditions list `references.referencedByAbilities` with class/ability/relation.
- **Explorer:** new **Conditions** tab (search + category filter, mechanics cards, detail with full typed-mechanics grid, inflicting/curing spell lists linking to spells, ability references linking to classes, raw JSON). Spell detail pages and expanded class abilities now show condition chips (relation-labelled, evidence as tooltip) that jump to the condition. `conditions` added to the JSON Data view.
- **Verification:** 0 dangling condition/spell references in either direction; `npm run build` ✅.

## Stage S15 — RACES.txt downloaded and audited (NO implementation yet)

- **Downloaded** `RACES.txt` from upstream `main` (`raw.githubusercontent.com/tantalumDesu/fluffy-robot/main/RACES.txt`) into `fluffy-robot/RACES.txt`: 15 races, ~44 KB, 639 lines. No edits were made to the downloaded file.
- **Audit only:** every race entry was checked for missing character stats (ability modifiers, favoured class, racial Hit Dice/ECL, natural armour/weapons, languages, vision, subtype) and ambiguities, and the results written to `dndsucks.md` ("RACES.txt audit"): 7 systemic issues (R-S1–R-S7, incl. the misleading `(good reflex/good fort)` Type field, absent ECL, and encoding artefacts) plus a per-race table. Headline gaps: Drow, Half-Orc, Orc and Minotaur have **no ability modifiers at all**; Elf, Half-Elf, Half-Orc, Human, Drow, Orc and Minotaur are **missing Favoured Class**; Minotaur's speed reads 40 ft. (canonical 30 ft.) and its Powerful Charge/Natural Cunning are dangling "(see above)" references; Tiefling's traits say "Aasimar are native outsiders". Non-core provenance (MM/FRCS races) is noted as wanted, per the user's instruction.
- **Not yet done (awaiting answers to Q-R1–Q-R4 in `dndsucks.md`):** no `races` collection in the JSON, no changes to `RACES.txt`, no explorer wiring.

## Stage S16 — RACES.txt reformatted from supplied trait sets (EXECUTED, txt only)

- **Rewritten:** `RACES.txt` rebuilt from the supplied RACIAL TRAITS blocks for all 15 races, in the supplied order (Bugbear, Drow, Dwarf, Elf, Gnome, Half-Orc, Halfling, Hobgoblin, Human, Minotaur, Orc, Tiefling, Aasimar, Goblin, Half-Elf). Each race is a name heading, descriptive text, then `<NAME> RACIAL TRAITS` with four-space-indented trait lines. Traits are verbatim from the supplied text except for the Drow references below.
- **Drow:** "high elf" is replaced with "elf" throughout, keeping the elf inheritance (low-light vision replacement, weapon proficiency replacement, languages replacement, favoured class replacement). The "Drow Traits (Ex)" intro is retained.
- **Setting-specific descriptive text removed:**
  - Deity names and the sentences naming them: Lolth (Drow), Hruggek (Bugbear), Maglubiyet (Goblin and Hobgoblin). Each domain rule that depended on them is kept, without the deity.
  - Forgotten Realms references (Faerûn, Toril, FRCS): removed from the Tiefling and Aasimar native-outsider text. Rewritten generically around the Material Plane.
  - Book citations and cross-references (Monster Manual, Player's Handbook, page numbers, chapter references, "see XP for Multiclass Characters", "see the speak with animals spell description", "see below"): removed.
  - Stray "Home Region" language entries: removed. Languages now come only from the supplied Automatic/Bonus lines.
  - "stonehunter" (Races of Stone leaking into the Gnome SLA line): removed, so the save DC reads "gnome's Cha modifier".
- **Verification:** scanned the output for Hruggek, Maglubiyet, Lolth, Faer, Toril, Forgotten, FRCS, Monster Manual, Player's Handbook, page, Chapter, XP for, stonehunter, Home Region, and "high elf". None remain.
- **Not changed:** `dnd core.json` (no races collection yet). `dndsucks.md` §RACES audit is superseded by this reformat. Issues it raised that are now resolved in the text: em-dash minus signs, control characters, the Tiefling "Aasimar are native outsiders" line, the Minotaur "(see above)" references, and the missing Favoured Class / ability modifiers on Drow, Half-Orc, Orc, Minotaur, and the humans. Open items are the audit's Q-R1 to Q-R4, most of which the supplied text now answers.

## Stage S17 — RACES wired into the JSON with typed mechanics (EXECUTED)

- **New top-level `races` collection** in `dnd core.json`: all 15 races from `RACES.txt`, in file order, each with `id`, `name`, `source`, `description` (paragraphs), `levelAdjustment`, `inherits`, `traits[]` (every trait line with `id`, `label`, verbatim `text`, typed `mechanics[]`, and `conditions[]`), and two summaries: `own` (the race's own traits) and `effective` (after inheritance). `meta.counts.races = 15`.
- **Parser:** each trait line is split into sentences, each sentence keeps its own label, and each is classified into a typed mechanic. Mechanic types: `abilityAdjustment`, `abilityFloor`, `size`, `carryingCapacity`, `speed`, `speedException`, `reach`, `darkvision`, `lowLightVision`, `racialHitDice`, `racialSkillPoints`, `racialClassSkills`, `racialFeats`, `bonusFeat`, `bonusSkillPoints`, `naturalArmor`, `naturalWeapon`, `bonus` (kind `skill` / `save` / `attack` / `ac` / `ability-check`, with bonus type, against-list, skill list, save type), `dcBonus`, `resistance`, `spellResistance`, `spellLikeAbility` (frequency, caster level, save DC, requirements, linked `spellId`), `spellLikeCasting`, `immunity`, `creatureType`, `creatureSubtype`, `languages` (automatic / bonus / any, with exclusions), `favoredClass` (class ids and gender conditions), `multiclassXpExemption`, `weaponProficiency`, `weaponFamiliarity`, `dodgeBonusLoss`, `replacement`. `note` marks narrative sentences that are not rules; `specialQuality` marks named special abilities whose rules text is kept but not executed (Stonecunning, Stability, Natural Cunning, Powerful Charge, Scent, Light Sensitivity, Light Blindness, Orc Blood, Elven Blood, Low-Light Vision and Weapon Proficiency-style flavour).
- **Inheritance:** Drow inherits from Elf. Elf's traits that Drow replaces (low-light vision, weapon proficiency, automatic/bonus languages, favoured class) are dropped from `effective`; the rest are inherited. Effective Drow values: +2 Dex, −2 Con, +2 Int, +2 Cha; favoured class wizard (male) or cleric (female); darkvision 120 ft; languages from the Drow list.
- **Conditions:** race trait text is cross-referenced to conditions (Blinded, Dazzled, Flat-Footed) with relation and evidence. Conditions gained `references.referencedByRaces`.
- **Classes:** each class gained `favoredByRaces` (7 classes linked; Human and Half-Elf are `any` and are listed on the race only).
- **Effective values checked against the source:** Bugbear ECL 4 (LA 1 + 3 HD); Minotaur ECL 8 (LA 2 + 6 HD) with Int floor 3; Half-Orc Int floor 3; Gnome and Goblin Hide +4 (size); Gnome SLA speak with animals (no Cha requirement), dancing lights/ghost sound/prestidigitation (Cha 10); Dwarf poison and spell saves +2; Halfling +1 all saves, +2 morale vs fear; Tiefling resist 5 cold/electricity/fire; Aasimar daylight at the higher of 1st level or class level.
- **Verification:** 0 dangling condition, spell, or class ids; race ids unique; `races` added to the JSON Data view; `npm run build` passes.
- **Gaps (not typed):** rules text for Stonecunning, Stability, Natural Cunning, Powerful Charge, Scent and Light Sensitivity is kept in `specialQuality.text` for reference but not executed. Derived creature types (humanoid for Bugbear, Half-Elf, Human, etc.) are flagged `derived: true` because RACES.txt no longer states them. Narrative sentences are kept as `note`.

## Stage S18 — Race corrections, ex-paladin rule, RACES.txt normalised, JSON re-wired (EXECUTED)

**Race corrections**
- **Human and Half-Elf** now state **"No ability score adjustments."** in RACES.txt (and `noAbilityAdjustments: true` in the JSON). Before this they were silent, which read the same as missing data.
- **Hobgoblin** gained racial Hit Dice in RACES.txt: "one level of humanoid, which provides 1d8 Hit Dice, a base attack bonus of +1, and base saving throw bonuses of Fort +2, Ref +0, and Will +0." JSON: `racialHitDice` = 1d8, BAB +1, saves +2/+0/+0; effective character level 2 (LA +1 + 1 HD level). These values are derived from the 1st-level hobgoblin warrior (Fort +4, Ref +1, Will −1, Dex +1, Con +2, Wis −1), with the base saves set to Fort good, Ref and Will poor. See dndsucks.md §0.7 for confirmation.
- **Minotaur**: Gore is now `1d8 piercing` (RACES.txt and `naturalWeapons[].damageType = "Piercing"`).
- **Tiefling**: the Outsider (Native) trait is left as written, per instruction.
- **Aasimar**: Daylight's caster level is now "her character level" (RACES.txt and `spellLikeAbilities[].casterLevel`), matching Tiefling's Darkness. The earlier "1st-level or class level, whichever is higher" is removed.

**Ex-paladin continuity (new rule)**
- New rule `paladin-continuous-levels` in the `rules` collection: type `level-sequence-constraint`. A character cannot take a paladin level after taking a level in any other class, so the paladin levels must be consecutive from the first. Source: the Aasimar favoured-class sentence (RACES.txt) and PALADIN.txt.
- Linked from: the Paladin class (`ruleIds`, `restrictions`), the Aasimar race (`ruleIds`, and `relatedRaceRules` on `aasimar-trait-10`).
- Rules tab: a level-sequence checker. Enter a sequence such as "fighter paladin paladin" to see whether it is valid, and where it breaks.

**RACES.txt normalised**
- Size lines: "Medium:" / "Small:" become "Medium size:" / "Small size:" (the lines that state size and its modifiers).
- Speed lines: "A bugbear's base land speed is 30 feet." and the other variants become "Base land speed is N feet."
- Level Adjustment: "Level adjustment +N." becomes "Level Adjustment: +N."
- Languages: "Automatic Language:" (Human) becomes "Automatic Languages:".
- Spell-like abilities: "1/day-" becomes "1/day: " (Gnome).
- Blank lines collapsed to a single blank line between blocks.

**JSON wired**
- All 15 races re-synced to RACES.txt: every own trait's `text` and `label` match the file exactly (checked: 0 mismatches). Inserted traits are numbered in sequence and their ids updated.
- Drow's effective traits rebuilt from the updated Elf traits, with the replaced traits removed.
- No dangling references: conditions, spells, rules and classes all resolve.

**Process note:** the parser scripts used for Stage S17 were in `/tmp`, which was cleared during this stage. The changes above were therefore applied to the JSON directly, using the parser's structure, and verified against RACES.txt by comparing trait text. Re-parsing from scratch would need the parser to be rewritten and saved in the project.

## Stage S19 — SPECIAL ABILITIES.txt downloaded (NO wiring yet)

- Downloaded `SPECIAL ABILITIES.txt` from upstream `main` into `fluffy-robot/` (624 lines, ~60 KB). No edits made.
- Structure found: 32 ALL-CAPS sections (Ability Score Loss, Antimagic, Blindsight/Blindsense, Breath Weapon, Damage Reduction, Death Attacks, Disease, Energy Drain, Evasion, Fast Healing, Fear, Gaze Attacks, Invisibility, Level Loss, Poison, Polymorph, Regeneration, Resistance to Energy, Scent, Spell Resistance, Tremorsense, Turn Resistance and others); 4 tables (Special Ability Types, Diseases, Listen Check DCs to Detect Invisible Creatures, Poisons); 3 type definitions (Ex / Sp / Su).
- Wiring plan and open questions are in the reply to the user, not yet executed.

## Stage S20 — SPECIAL ABILITIES.txt normalised (EXECUTED, txt only)

- **Tables rebuilt** from explicit data, every row checked for column count:
  - *Table: Special Ability Types* — header now `Property | Extraordinary | Spell-Like | Supernatural`; the four rows and definitions are unchanged, with a blank line before the definitions.
  - *Table: Diseases* — split the merged `Infection DC` cell into separate `Nature` (Ex/Su), `Infection`, `DC` and `Incubation`/`Damage` columns, and a `Note` column that holds the footnote numbers previously stuck to the names and damage (`Str1`, `Con2`, `Devil chills3`, `Mummy rot4`). Footnotes 1–4 are now numbered list items. Empty notes are `—`.
  - *Table: Listen Check DCs to Detect Invisible Creatures* — header now `Invisible creature is | DC` (was all caps with an ellipsis).
  - *Table: Poisons* — the header was split across two physical lines; now one header row. `Type and DC to Resist` split into `Delivery` and `DC to Resist`. Prices written as `N gp` with thousands separators kept as in the source. Footnote kept below the table after a blank line.
- **Errors fixed:** "Some magic creatures" → "Some magical creatures"; "avoid the affect" → "avoid the effect"; "contaminated attack touches" → "contaminated attack, touches"; "added the appropriate bonus" → "add the appropriate bonus"; "Exhaustion ou unconsciousness" → "Exhaustion or unconsciousness"; "75gp" → "75 gp"; mojibake `creatureÂ’s` / `canÂ’t` / `Â’` removed (3 instances).
- **Consistency:** straight apostrophes converted to curly (’) throughout; a blank line added before and after every section heading and sub-heading (Disease Descriptions, Healing a Disease, Perils of Using Poison, Poison Immunities, When Spell Resistance Applies, Successful Spell Resistance); blank line before every table title; trailing whitespace removed; CRLF line endings kept.
- **Disease nature (needs confirmation):** the source said supernatural diseases are "printed in italic in the table", but italics do not survive in the text. Demon fever, devil chills, mummy rot and slimy doom are marked Su, following the SRD. The definition sentence now refers to the Nature column instead of italics.
- **Verified:** all four tables have consistent column counts; no mojibake or straight quotes remain; no prose lost (non-blank line count differs only by the merged Poisons header); no duplicate rows.
- **Not changed:** game values in the tables (DCs, damage, prices) and the rules text are as in the source, apart from the typo fixes above. The duplicate sentence "Invisible creatures cannot use gaze attacks" appears in both the Gaze Attacks and Invisibility sections and is kept.

## Stage S21 — SPECIAL ABILITIES wired into the JSON and cross-referenced (EXECUTED)

- **Tool saved in the project:** `tools/wire_special_abilities.py` (re-runnable and idempotent; it clears its own earlier output first). The parser used for the race work was lost, so this one is kept in the repo.
- **New collections:**
  - `specialAbilities` (34): one record per section of SPECIAL ABILITIES.txt, with paragraphs, subsections, a typed `type` (value, confidence, evidence, candidates), `propertiesByType` from the matrix, typed `mechanics`, and condition, spell, class and race references.
  - `diseases` (10): typed DC, incubation, damage components, nature (Ex/Su) and footnote notes.
  - `poisons` (36): typed delivery list, DC to resist, initial and secondary damage components (ability damage, ability drain via `*`, hp, status, vulnerability), price in gp, DC to create.
  - `listenCheckDCs` (7 rows): typed DC (fixed, Move Silently result with modifier, per-distance).
  - `specialAbilityTypes`: the Ex/Sp/Su property matrix as typed booleans.
- **Class cross-references:** 30 curated links (for example Monk and Rogue Evasion, Barbarian Damage Reduction, Dragon Disciple Breath Weapon and Blindsense, Assassin Death Attack, Paladin and Epic Paladin Remove Disease, Druid Venom Immunity, Assassin Poison Use, Monk Diamond Soul, Paladin Aura of Courage and Bard Inspire Courage, Cleric turning) plus 22 text-based mentions. Each linked ability gets `specialAbilityRefs` and `specialAbilityProperties`.
- **Filled information:** where the source states a type, class and race records with a missing type are filled. Race traits gained `abilityType` for Darkvision, Scent, Spell Resistance and Resistance to Energy (usually Ex). The Shadowdancer Darkvision conflict and the Assassin Death Attack gap are recorded on the record, not overwritten.
- **Back-references:** spells gained `specialAbilityRefs`; conditions gained `referencedBySpecialAbilities` and `referencedByDiseasesOrPoisons`; each special ability lists its classRefs and raceRefs.
- **Explorer:** new "Special Abilities" tab with Abilities (search, type badges, typed mechanics, condition/spell/class links), Diseases, Poisons, Listen DCs and Type matrix. New collections are in the JSON Data view.
- **Verification:** every reference resolves (0 dangling across classes, races, conditions, spells, diseases, poisons); `npm run build` passes.

## Stage S22 — Full audit (NO data changes)

- Audited the JSON (counts, duplicate ids, reference integrity, spell tags, class abilities, races, conditions, special abilities, diseases, poisons, skills and synergies), the text sources (SPELLBOOK, RULES, RACES, SPECIAL ABILITIES, CONDITIONS, DOMAINS, SKILLS, ASSASSIN, EPIC WIZARD), the explorer source and both logs.
- Findings are recorded in `dndsucks.md` §0.9 with severity, evidence and suggested fixes: 10 defects (A1–A10), 13 project-level inconsistencies (B1–B13), source formatting still to normalise (C), and 12 decisions for human review (D).
- Most serious: the Skills tab crashes on render (A1); race text names purged domains (A2); the fluffy-robot repository has lost its git history (B1).

## Stage S23 — Audit response (EXECUTED)

Tools (all re-runnable, in run order):
1. `tools/stage_spellbook.py` — corrects propagated class tags, re-checks "functions like" inheritance, replaces invented None/No defaults with "Not stated in source".
2. `tools/sync_spells.py` — rebuilds `dnd core.json` spells and spell lists from SPELLBOOK.txt (authoritative).
3. `tools/stage_domains.py` — canonical DOMAINS.txt with a Special column, adds Chaos, Evil, Law, Good; regenerates SPELLBOOK Domain tags, JSON domains and domainSpellNotes.
4. `tools/wire_condition_references.py` — rebuilt condition classifier with explicit relation rules and confidence.
5. `tools/stage_cleanup.py` — disease nature, Special-outcome poisons, Shadowdancer darkvision, house swap thresholds, review flags.
6. `tools/validate_and_refresh.py` — recomputes every recorded count, runs 25 cross-file checks, derives the schema identifier, records the result in `meta.validation`.
Reference: `tools/check_class_tags_upstream.py` (independent check against upstream SPELL LISTS.txt).

Changes:
- **Counts:** recomputed. spells 607 → 611; domains 35 → 39; poisons 36 → 34; stats 99 → 98; abilities 301 and effects 619 now counted from the JSON (previous generator totals of 364 and 696 used a different definition, now documented in `meta.countDefinitions`).
- **Domain Special column:** every domain spell row now has a Special column. Footnote text (*, †, **) moved from separate lines into that column; the Skalykind footnotes (†, *) were restored from the upstream file, where the marks had been lost.
- **Domain notes:** `domainSpellNotes` rebuilt from the Special column; 15 rows, all for live domains.
- **Alignment domains added:** Chaos, Evil, Law and Good, in DOMAINS.txt with brief descriptions from SPELLBOOK short descriptions and the Summon Monster IX restriction in the Special column. The four alignment domains are restored in the JSON as live domains.
- **Alignment spells split:** Detect, Dispel and Magic Circle against Chaos/Evil/Good/Law are individual spells in SPELLBOOK and JSON (seven new records). The three grouped records are removed.
- **Class tags:** checked against upstream SPELL LISTS.txt. Corrected in SPELLBOOK: Dispel Chaos and Dispel Evil gain Cleric 5; Magic Circle against Chaos, Evil and Good gain Cleric 3 and Sorcerer/Wizard 3. Remaining differences: Hardening (removed on instruction) and the Protection from Acid/Frost/Lightning/Fire/Thunder entries (added on instruction).
- **Functions-like inheritance:** 131 entries inherit stated fields from their base, with the override clause recorded in Field Notes. 45 entries that are not functions-like had Saving Throw and Spell Resistance filled with invented defaults; these now read "Not stated in source" and are flagged for review.
- **Condition classifier:** rebuilt. Spell references 279 → 283: 148 high-confidence, 24 medium, 111 low (mentions). Examples now correct: Heal removes its listed conditions; "does not remove negative levels" is an exception; See Invisibility is a mention, not an infliction; Remove Fear and Remove Blindness/Deafness remove their conditions; Invisibility Purge removes Invisible.
- **Diseases:** only demon fever, devil chills and mummy rot are supernatural. Slimy doom is Ex (JSON and SPECIAL ABILITIES.txt).
- **Poisons:** Siren's breath and Blasphemix removed, because their outcome is "Special" with no stated rules. Removed from JSON, SPECIAL ABILITIES.txt, ASSASSIN.txt and SKILLS.txt.
- **Shadowdancer Darkvision:** class-granted (`definedBy: class`), type Su, unlinked from the darkvision definition.
- **House swap threshold:** 15 "max 4th-level" scaling entries removed from the Bard and Sorcerer Spells abilities. The "two levels lower" rule stays because it is in the class prose.
- **Review flags:** 8 special abilities with no explicit links; 8 races whose descriptions contain setting or interpretive wording. Kept, flagged, not changed.
- **Schema:** `meta.schema` is derived from the structure (`structure-3dcbdaef`) and written by the validator. The text "schema 9" was not found in the repo or the explorer; the explorer footer already reads `meta.schema`.
- **Retired references:** SPELLBOOK preamble and the meta placeholder no longer name deleted files; `spellLists[].file` is SPELLBOOK.txt.

Still open (not in this batch): Skills tab null-synergy crash (A1); condition mechanic hand-review (A5); CONDITIONS.txt encoding (A4); SKILLS.txt table-title formatting (C).
