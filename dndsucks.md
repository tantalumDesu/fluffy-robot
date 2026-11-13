# Spell Descriptions Reconciliation — Decisions Required (`dndsucks.md`)

> **Status: EXECUTED — see §0 for what was done and §0.1 for ambiguities resolved on your behalf.** The original decision workbook (§§1–8) is retained below as the record of what was decided from.
> This file is a decision workbook. Work through §§3–6, tick/edit your choice on each row, answer the questions in §8, and hand it back. Only then will the `.txt` files and `dnd core.json` be changed (and logged in `fixingdnd.md`).

Scope of this pass: `SPELL DESCRIPTIONS.txt` vs. the spell lists in `SPELL LISTS.txt` / `dnd core.json` (`spellLists`), the domain spell lists in `DOMAINS.txt` / `domains`, and every other `.txt` in the repo where a spell is named.

## 0. OUTCOME — decisions executed (this pass)

| Decision | Result |
|---|---|
| **D01–D28 flavourful renames** | ✅ **Done everywhere.** All 28 spells renamed to the description names in `SPELL LISTS.txt`, `DOMAINS.txt`, `NPC MAGEWRIGHT.txt`, in-text cross-references in `SPELL DESCRIPTIONS.txt`, and in `dnd core.json` (`spells[].name`, **`spells[].id` changed to the flavourful slug** e.g. `acid-arrow` → `melfs-acid-arrow`, all `spellLists[].levels[].spellIds` and `domains[].spells[].spellIds` repointed; no old id survives as a value anywhere in the JSON). Generic noun uses were *not* renamed (e.g. "the clenched fist can…", "object's magic aura" — see Ambiguity A6). |
| **Corrupt Weapon description** | ✅ **Added** to `SPELL DESCRIPTIONS.txt` (line 1188, alphabetically between *Control Winds* and *Create Food and Water*), text exactly as supplied. The JSON already had `corrupt-weapon` on the blackguard list; verified it now has a description. |
| **X01–X15 domain normalisation** | ✅ **Done** in `DOMAINS.txt` and JSON `domains[]` (name + `spellIds` point at the canonical list spell in every case; X01/X09 use `Blasphemy + Holy Word` / `Holy Aura + Unholy Aura` as a single choice-of-two domain slot, both ids retained). |
| **Domain purge** | ✅ **46 domains purged, 35 kept** (rule: after normalisation, a domain is purged if any of its spells is on no class spell list). Removed from both `DOMAINS.txt` and JSON `domains[]`. Kept: Air, Animal, Charm, Community, Death, Destruction, Earth, Fate, Fire, Hatred, Healing, Inquisition, Knowledge, Liberation, Luck, Magic, Nobility, Oracle, Planning, Plant, Protection, Rune, Skalykind, Storm, Strength, Summoner, Sun, Travel, Trickery, Tyranny, Undeath, War, Water, Wealth, Weather. Full purged list with offending spells: `fixingdnd.md` S6. |
| **Protection from [alignment] split** | ✅ Grouped entries removed; *Protection from Chaos/Evil/Good/Law* are now four individual spells in `SPELL LISTS.txt`, JSON `spellLists`, and `spells[]`. The four descriptions already existed individually and are unchanged. Paladin keeps only Chaos + Evil (the old pair) — see A3. |
| **Protection from [energy] split** | ✅ *Protection from Energy* replaced by **Protection from Acid / Cold / Electricity / Fire / Sonic**, each with its own edited description in `SPELL DESCRIPTIONS.txt` (same header statistics, body specialised to its energy), five entries per list in `SPELL LISTS.txt`, and five JSON spells/list memberships. Cross-references in *Hallow*, *Unhallow* and *Resist Energy* updated. Luck/Protection domain handling: see A2. |
| **JSON mechanical check** | ✅ 0 dangling `spellIds`; every `spells[].lists` exactly matches `spellLists`; `meta.counts` updated (domains 81 → **35**, spells 760 → **607**); explorer rebuilt successfully. Orphan cleanup: see A5. |

## 0.1 Ambiguities found & how I resolved them (challenge any of these)

| # | Ambiguity | Resolution taken |
|---|---|---|
| A1 | **JSON id policy was never specified** (old Q4). | Changed ids to flavourful slugs (`mages-sword` → `mordenkainens-sword`) and repointed every reference, because the id *is* derived from the name everywhere else in this dataset. Consequence: external references to old slugs break. Reversible in one pass if you prefer stable ids. |
| A2 | Luck & Protection domains grant *Protection from Energy* as **one domain slot**; after the split there is no single spell to point at. | **Superseded (see §0.2):** this choice-of-five was rolled back at your instruction; Luck/Protection again grant the restored generic *Protection from Energy*. |
| A3 | Which alignments does each class get after splitting *Protection from Chaos/Evil/Good/Law*? | Cleric, sorcerer/wizard and adept (the grouped lists) get **all four**; paladin (the old *Chaos/Evil* pair) gets **Chaos + Evil only**. This preserves exactly the coverage the grouped entries encoded, and matches the description headers (Pal is listed only under Chaos and Evil). |
| A4 | Purging domains also orphans their signature spells. | Signature spells of purged domains that **have descriptions** (*Chaos Hammer, Holy Smite, Order’s Wrath, Unholy Blight*) were **kept** in `spells[]` with `lists: []` — the descriptions (your §4 keep/purge decision from the last round was never returned, and this instruction purged *domains*, not spells). If you want them gone, that is a one-line follow-up. |
| A5 | What happens to `spells[]` entries referenced by nothing after the purge? | **Removed 159** entries that were on no class list, in no surviving domain, and have no description (the Appendix A set from the previous round, including the superseded standalone `blindness`, replaced by `blindness-deafness` per X02). Retention rule used: keep iff on a class list, OR in a surviving domain, OR described in `SPELL DESCRIPTIONS.txt`. |
| A6 | "Rename all instances" vs. generic noun uses of the same words. | Renamed spell-name instances (headings, list entries, cross-references like "functions like…", "As Resilient Sphere…", permanency-table entries, summon-table "Can’t cast Otto’s Irresistible Dance"). Left descriptive noun uses ("The clenched fist can also interpose…", "the freezing sphere bursts…", "object’s magic aura" in the *Nystul’s Magic Aura* summary — one such summary overreach during the pass was caught and reverted). |
| A7 | *Corrupt Weapon* text as supplied uses `Transmutation [evil]`, `Saving Throw: none`, `Spell Resistance: no`, "the paladins spell" (no apostrophe). | Inserted **verbatim as supplied**; not silently copy-edited. Say the word if you want it normalised to house style (`[Evil]`, `None`, `No`, `paladin’s`). |
| A8 | Only the Protection families were ordered to be split. | *Detect…*, *Dispel…* and *Magic Circle against…* remain grouped in lists/JSON. 7 described spells still have no entry of their own (*Detect Chaos/Evil/Good/Law, Dispel Good, Dispel Law, Magic Circle against Law*). Splitting them is the same operation whenever you want it. |
| A9 | The energy-split descriptions: is each a separate spell for *domain* and *specialisation* purposes? | Treated purely as five spells sharing the original header statistics; no descriptor added to the school line (`Abjuration`, not `Abjuration [Fire]` etc.), to avoid inventing mechanics. |
| A10 | `meta.counts` contains generator counters (`abilities`, `effects`, `stats`…) that count class features, not spells. | Left untouched; only `domains` and `spells` counts were recalculated, since only those changed. |

---
## 0.2 Follow-up (this pass): Protection from Energy un-nerfed, three renames

| Item | Result |
|---|---|
| **Protection from Energy restored** | ✅ Re-added as a spell in its own right: original entry restored in `SPELL DESCRIPTIONS.txt` (between *Protection from Chaos* and *Protection from Evil*), and `protection-from-energy` re-added to JSON `spells[]` (608 spells). It is **not** back on the class spell lists — see ambiguity F1. |
| **Luck & Protection domains rolled back** | ✅ Their level-3 slots again read `Protection from Energy` → `protection-from-energy` in `DOMAINS.txt` and JSON (choice-of-five entry and its note removed). These two domains are now deliberate exceptions to the S6 purge rule (they contain a spell on no class list) — at your instruction, not by oversight. |
| **Split variants kept** | ✅ *Protection from Acid/Fire/Frost/Lightning/Thunder* remain in `SPELL DESCRIPTIONS.txt` and every class spell list (for future potion/scroll use). Their description `Level:` headers no longer claim Luck/Protection domain levels — the generic spell carries those; the variants keep Clr/Drd/Rgr/Sor-Wiz only (F2). |
| **Renames** | ✅ *Protection from Cold* → **Protection from Frost**, *Protection from Electricity* → **Protection from Lightning**, *Protection from Sonic* → **Protection from Thunder** — headings, bodies, spell lists, blackguard list, JSON names and ids (`protection-from-frost/-lightning/-thunder`). Entries re-alphabetised in `SPELL DESCRIPTIONS.txt`. |

**New ambiguities (F):**
- **F1 — Where does the restored generic spell live?** "Add Protection from Energy as a separate spell" + "keep the variants in the spell lists" was read as: generic returns as a *described, domain* spell (`lists: []`), not as a sixth choice on every class list alongside its own variants. If you want it back on class lists too, that is a small follow-up.
- **F2 — Damage-type vocabulary.** The flavour names protect against the canonical damage types: *Frost* ↔ cold damage, *Lightning* ↔ electricity, *Thunder* ↔ sonic. Bodies and summaries keep the canonical terms ("grants temporary immunity to cold… cold damage"), so no new "frost/thunder damage" type was invented.
- **F3 — "Roll back changes to Domain spells"** was read narrowly: only the two level-3 energy slots (Luck, Protection). The X01–X15 normalisation and the S6 domain purge were **not** rolled back — say if you meant those too.

## 0.3 SPELLBOOK pass (this pass): removal, harmonisation, typed mechanics

| Item | Result |
|---|---|
| **Hardening removed completely** | ✅ No occurrence of the spell's name remains in any `.txt` (including the new `SPELLBOOK.txt`) or in `dnd core.json`: list entry, magewright list entry, `spells[]` entry and magewright `spellIds` all deleted. (The ordinary English word "hardened" in unrelated prose is not a spell reference and was left alone.) |
| **Protection spells on the lists** | ✅ *Protection from Energy* (generic) added to cleric 3, druid 3, ranger 2, sorcerer/wizard 3, blackguard 3 — in the lists and JSON — alongside Acid/Fire/Frost/Lightning/Thunder, which remain everywhere they were. It was already on the Luck/Protection domain lists. |
| **`SPELLBOOK.txt` created** | ✅ `SPELL LISTS.txt` + `SPELL DESCRIPTIONS.txt` merged and then **deleted**; `SPELLBOOK.txt` (611 entries, alphabetical) is now the single spell source. Every entry: name, Short Description, Long Description, and the full tag block (Class, Class Spell Level, Type, School, Domain, Duration, Range, Target/Area/Effect, Components, Casting Time, Saving Throw, Spell Resistance, Damage Type, Damage/Dice Rolls, Healing). The JSON `spells[]` carries the same short+long pair and typed tags for all **607** spells (0 missing short, 0 missing long), `file: "SPELLBOOK.txt"`, and the explorer filters on the new tags. |
| **Class level tags** | ✅ Filled from the class spell lists (the authoritative source) — e.g. grouped-list spells and abbreviated entries now carry every class+level they belong to. Tags for the purged Chaos/Evil/Good/Law domains were stripped: only domains that still exist appear in Domain tags. |
| **Mechanics typed & damage catalogued** | ✅ Every spell JSON now has parsed components (code+name), casting-time/range/duration categories (+dismissible), target/area/effect, saving-throw type+effect, spell-resistance flag, traditions, and `mechanics` (damage types + per-type dice, all dice rolls, healing flag, caster-level scaling). Damage-type catalogue (spell counts): Acid 10, Cold 16, Electricity 12, Fire 33, Sonic 16, Force 23, Positive Energy 3, Negative Energy 6, Divine 1, Bludgeoning 6, Piercing 3, Slashing 1 — also printed at the end of `SPELLBOOK.txt`. |

**Ambiguities in this pass (G):**
- **G1 — "Type" tag** was undefined in the brief; implemented as casting tradition (**Arcane/Divine**, derived from the spell's lists; domain-only spells count as Divine). School descriptors (e.g. `[Fire]`) live in the School tag. If "type" meant something else, this is a relabel.
- **G2 — Omitted Saving Throw / Spell Resistance** in the old abbreviated headers are harmonised to `None` / `No` (that's what omission means in this stat-block format); they are marked as defaults in the spell's field notes.
- **G3 — 723 field instances were inherited** from base spells named in the text ("functions like *cure light wounds*…"), e.g. the *Cure … , Mass* and *Detect …* families. Inherited values are the base spell's, flagged in field notes; the four alignment signature spells and one *Overland Flight* casting time had no base to inherit from and show `See text`-category placeholders.
- **G4 — Grouped spells stay grouped in the JSON/lists** (Detect/Dispel/Magic Circle), but in `SPELLBOOK.txt` they are individual entries (as their descriptions always were); grouped JSON spells' long descriptions are the concatenation of their variants'.
- **G5 — Short descriptions** for individual alignment variants reuse the grouped list summary, since the old lists only ever wrote one summary per family.

## 0.4 Rules system (latest pass)

Spell replacement is back — as a typed mechanic in the new top-level `rules` collection of the JSON (not as the deleted Charisma tables), and the Ability Modifiers and Bonus Spells table now lives in `RULES.txt` with a canonical typed implementation beside it. Two things to be aware of: **(R1)** the bonus-spells table now exists twice — canonically in `rules[]` and as the legacy mirror `meta.rules.bonusSpellsTable`; if they ever disagree, `rules[]` wins. **(R2)** the swap mechanic is built from the class-feature prose (levels and constraints), since the per-level Charisma tables were removed at your instruction; if you want an ability-score gate back, it would be a new parameter, not the old table. Adding a rule from here: add its text/table to `RULES.txt`, add one `schema: 1` object to `rules[]`, and reference it from the relevant classes' `ruleIds`.

## 0.5 Conditions wiring (latest pass)

All 38 conditions from `CONDITIONS.txt` are now a typed collection in the JSON, referenced from 280 spell entries and 39 class abilities. One caveat worth knowing **(C1):** reference *relations* (`inflicts`/`removes`/`interacts`/`mentions`) are derived heuristically from the sentence a condition is mentioned in — every reference carries its evidence sentence precisely so you can audit it, and borderline cases will exist (e.g. a spell that discusses a condition it neither causes nor cures will still be linked as `mentions`; *Blown Away* and *Checked* are wind-effects with almost no textual footprint, so they have few or no links). The condition *mechanics* (penalties, movement, restrictions) are extracted from the condition's own text, not inferred from spells.

> **Update (Stage S16):** the RACES.txt audit below is superseded. `RACES.txt` was reformatted from the supplied trait sets, which resolves most of the issues listed. The per-race audit is kept below as the record of what was found.

## RACES.txt audit (latest pass — AUDIT ONLY, nothing implemented yet)

Downloaded `RACES.txt` from upstream `main` into `fluffy-robot/RACES.txt` (15 races, ~44 KB, 639 lines): Bugbear, Drow, Dwarf, Elf, Gnome, Goblin, Half-Elf, Half-Orc, Halfling, Hobgoblin, Human, Minotaur, Orc, Tiefling, Aasimar. It is **not in `dnd core.json` at all** yet — no `races` collection, no JSON implementation. Per your note, non-core entries are *wanted*, so provenance is flagged for information, not as a defect: **PHB core** = Dwarf, Elf, Gnome, Half-Elf, Half-Orc, Halfling, Human; **Monster Manual playable** = Bugbear, Drow, Goblin, Hobgoblin, Minotaur, Orc; **FRCS (Forgotten Realms)** = Tiefling, Aasimar.

### Systemic issues (affect most or all entries)

| # | Issue | Detail |
|---|---|---|
| R-S1 | **`Type` field is wrong / misleading throughout** | Every humanoid reads e.g. `Humanoid (good reflex)` or `Humanoid (good fort)`. That parenthetical is a *save progression*, not a subtype — and it is meaningless for PHB races with no racial Hit Dice (Dwarf, Gnome, Half-Orc, Orc all say "good fort"). The actual subtypes are missing everywhere: (goblinoid) for Bugbear/Goblin/Hobgoblin, (elf) for Elf/Drow, (dwarf), (gnome), (orc) for Half-Orc/Orc, (native) for the planetouched `Outsider` entries. Minotaur (`Monstrous Humanoid`) inconsistently has no parenthetical at all. |
| R-S2 | **Languages are expressed two different ways** | Some races repeat `Automatic Languages:` / `Bonus Languages:` inside Racial Traits (Bugbear, Dwarf, Gnome, Goblin, Half-Orc, Hobgoblin); others have only the top `Languages` block (Drow, Elf, Halfling, Orc, Minotaur, planetouched). For the second group it is impossible to tell which languages are automatic and which are bonus. |
| R-S3 | **No ECL anywhere** | Races with racial Hit Dice and/or LA never state Effective Character Level (Bugbear should be ECL 4 = 3 RHD + LA +1; Minotaur ECL 8 = 6 RHD + LA +2). A player cannot build the character from the entry alone. |
| R-S4 | **Character-creation tables absent** | No starting age, aging, height/weight or alignment-tendency data in stat form. Some PHB descriptions give height/weight in prose (Elf, Half-Elf, Gnome), most monster/FRCS entries give nothing (Drow, Half-Orc, Hobgoblin, Minotaur, Orc, Tiefling, Aasimar). Flagging as a gap only — these may be intentionally out of scope. |
| R-S5 | **Encoding / copy artefacts** | Em-dash minus signs: `—2 Charisma` / `—2 Constitution` / `—2 Strength` (Dwarf, Elf, Gnome) will parse as punctuation, not −2. Stray control character `\u0001` before the Dwarf poison line and at the end of the Dwarf Craft line, and in the Gnome weapon-familiarity line. Typos: `exccept` (Tiefling, Aasimar), `just finde` (same shared paragraph, both entries), broken Dwarf speed sentence ("…or whose speed is reduced in such conditions)" — unmatched bracket, and the canonical "medium or heavy load" clause is missing). |
| R-S6 | **Unexplained source abbreviations** | `Also appears in: Rac` (Bugbear, Goblin, Hobgoblin, Half-Elf, Half-Orc), `RD` (Tiefling, Aasimar), `FRCS` — `Rac` appears truncated and none are expanded anywhere in the file. |
| R-S7 | **Ordering** | Aasimar sits after Tiefling at the very end, out of the file's otherwise source-book grouping; the two planetouched also share a word-for-word identical "Native Outsider" section (fine as shared boilerplate, but see the Tiefling error below). |

### Per-race audit

| Race (source) | Missing stats | Ambiguities / errors |
|---|---|---|
| **Bugbear** (MM) | Subtype (goblinoid) — see R-S1; ECL (R-S3) | Otherwise the most complete monster entry: ability mods, 3 RHD with BAB/saves/skill points/feats, natural armour, skill bonus, darkvision, Scent, languages, Favoured Class all present. Scent has no mechanics beyond the flavour sentence (no tracking DCs — normal for a race entry, but a JSON mechanic would need the Scent rules from elsewhere). |
| **Drow** (MM) | **Ability score modifiers completely missing** (canonical: +2 Dex, −2 Con, +2 Int, +2 Cha); **Favoured Class missing** (canonical: Wizard — or Cleric for females in FR); automatic/bonus language split (R-S2), including no Drow Sign Language anywhere; subtype (elf) | The `Languages` block lists Common as if automatic (canonically a bonus language). The Will-save trait conflates two separate traits (+2 vs spells/spell-like abilities, and the elven +2 vs enchantment) into one sentence. Spell resistance, SLAs, weapon proficiencies, skill bonuses and Light Blindness are all present. |
| **Dwarf** (PHB) | — (mechanically complete) | `—2 Charisma` em-dash (R-S5); two `\u0001` artefacts; garbled speed sentence (above). |
| **Elf** (PHB) | **Favoured Class missing** (canonical: Wizard); automatic/bonus languages missing from traits (canonical bonus: Draconic, Gnoll, Goblin, Orc, Sylvan) — only the top `Languages` block | `—2 Constitution` em-dash. Otherwise complete (sleep immunity, low-light vision, weapon proficiencies, secret-door sense). |
| **Gnome** (PHB) | — (mechanically complete) | SLA save-DC line reads "save DC 10 + **stonehunter** gnome's Cha modifier" — *stonehunter* is a subrace from *Races of Stone* that has leaked into the core gnome entry: which gnome is this? `—2 Strength` em-dash; one `\u0001` artefact. |
| **Goblin** (MM) | Subtype (goblinoid) — R-S1 | Complete for a 0-LA monster race (ability mods, size traits, darkvision, skill bonuses, languages, Favoured Class: Rogue). |
| **Half-Elf** (PHB) | **Favoured Class missing** (canonical: **Any**) | No ability modifiers is *correct* for a half-elf, but the entry never says so — silence is ambiguous (compare Human). Everything else present (sleep immunity, low-light vision, skill/diplomacy bonuses, Elven Blood, languages). |
| **Half-Orc** (PHB) | **Ability score modifiers completely missing** (canonical: +2 Str, −2 Int, −2 Cha); **Favoured Class missing** (canonical: Barbarian) | Only Darkvision, Orc Blood and languages are given — as written, a half-orc character has no ability adjustments and no favoured class. Also no height/weight prose (R-S4). |
| **Halfling** (PHB) | **Speed header block missing** (every other race has one; the 20 ft speed is only in the traits); automatic/bonus languages missing from traits (canonical bonus: Dwarven, Elven, Gnome, Goblin, Orc) | No vision trait is *correct* (halflings have neither darkvision nor low-light vision), but again it is silence rather than an explicit "none". Ability mods, size traits, all skill/save/attack bonuses and Favoured Class present. |
| **Hobgoblin** (MM) | Subtype (goblinoid) — R-S1 | No size trait line, but Medium with no size modifiers is the default, so this is silence-as-default again. Ability mods, speed, darkvision, Move Silently bonus, languages, Favoured Class: Fighter, LA +1 all present. No racial HD is correct. |
| **Human** (PHB) | **Favoured Class missing** (canonical: **Any**) | No ability modifiers is *correct* for humans but, as with Half-Elf, never stated. Bonus feat, bonus skill points, size, speed and languages all present. |
| **Minotaur** (MM) | **Ability score modifiers completely missing** (canonical: +8 Str, +4 Con, −4 Int, −2 Cha); **natural armour missing** (canonical +5); **Racial Hit Dice not quantified** — skill points/feats are mentioned but the entry never says "6 levels of monstrous humanoid, 6d8 HD, BAB +6, base saves…"; **Favoured Class missing** (canonical: Barbarian); automatic/bonus language split; ECL | **Speed reads "Land 40 ft." — canonical minotaur speed is 30 ft.; this looks like a data error, please confirm.** "Special Attacks (see above): Powerful charge" and "Special Qualities (see above): Natural cunning, scent" are **dangling references**: there is no "above" in this file (they pointed at the monster stat block in the book), so Powerful Charge has no gore-charge damage and Natural Cunning/Scent have no rules text at all. Gore (1d8) and weapon proficiencies are present. |
| **Orc** (MM) | **Ability score modifiers completely missing** (canonical: +4 Str, −2 Int, −2 Wis, −2 Cha); **Favoured Class missing** (canonical: Barbarian); automatic language — the `Languages` block lists only **Common**, and canonically an orc's automatic language is **Orc** (Common is a bonus language) | Only Darkvision and Light Sensitivity are given. As written an orc character has no ability adjustments, no favoured class, and apparently does not speak Orc. |
| **Tiefling** (FRCS) | Automatic/bonus language labels (R-S2); subtype (native) in the Type field | **Copy-paste error: the traits say "Outsider: Aasimar are native outsiders" — in the Tiefling entry.** `Languages` block says "Common, Home Region" — "Home Region" is not a language and is meaningless outside the Forgotten Realms context. Ability mods, resistances, *darkness* SLA, skill bonuses, darkvision and Favoured Class: Rogue all present. `exccept` / `just finde` typos in the shared Native Outsider text. |
| **Aasimar** (FRCS) | Automatic/bonus language labels (R-S2); subtype (native) in the Type field | Same "Home Region" language ambiguity as Tiefling; same shared-paragraph typos; out-of-order placement (R-S7). Mechanically otherwise complete (+2 Wis/Cha, resistances, *light* SLA, skill bonuses, darkvision, Favoured Class: Paladin, LA +1 stated twice — once in the header block and once as a trait bullet). |

### Questions before any implementation

- **Q-R1:** Should the audit's canonical values (ability mods for Drow/Half-Orc/Orc/Minotaur, Favoured Classes, Elf/Halfling bonus languages, Minotaur speed 30 ft. and natural armour +5, etc.) be *filled in*, or flagged only? They come from the cited source books, not from this file.
- **Q-R2:** Is the `(good reflex)` / `(good fort)` parenthetical wanted as data (racial-HD save progression), or should `Type` become the real type/subtype?
- **Q-R3:** Scope of a race entry for this project: mechanics only, or also starting age/aging/height/weight (R-S4)?
- **Q-R4:** Are the FRCS planetouched in scope as-is ("Home Region" languages and all), given the rest of the dataset is largely setting-neutral?

## 0.6 Races in the JSON (latest pass)

`RACES.txt` is now the `races` collection in the JSON, with typed mechanics for every rules sentence (see Stage S17 in `fixingdnd.md`). Points to be aware of:

- **(RC1) Derived creature types:** Bugbear, Half-Elf, Human and the other humanoid races have no stated type in the reformatted text, so they are recorded as `humanoid` with `derived: true`. Monstrous Humanoid (Minotaur) and Outsider (native, Tiefling and Aasimar) are stated in the text and not derived.
- **(RC2) Drow inheritance:** Drow inherits from Elf and the replaced traits are removed from its effective values. The inheritance mapping is by keyword ("low-light vision", "weapon proficiency", "automatic and bonus languages", "favored class"), so any new Elf trait that matches those keywords would be replaced too.
- **(RC3) Not executed:** named special abilities such as Stonecunning, Stability, Natural Cunning, Powerful Charge and Scent have their rules text kept but no typed effects. Narrative sentences are `note`.
- **(RC4) Race-level only:** these are race entries. They do not yet feed character building, and ECL is computed as level adjustment plus racial Hit Dice levels.

## 0.7 Race corrections and ex-paladin rule (Stage S18)

- **(RC5) Hobgoblin racial Hit Dice** are derived from the 1st-level hobgoblin warrior entry (1d8, BAB +1, base saves Fort +2, Ref +0, Will +0). Please confirm these are the values you want, since the source gives the warrior's total saves rather than the racial base saves.
- **(RC6) Ex-paladin rule** is enforced as a level-sequence constraint (`paladin-continuous-levels`). The rule is that a character can't take a paladin level after taking a level in another class. It does not model the Blackguard or other ex-paladin mechanics, which are outside this rule.
- **(RC7) Parser provenance:** the race parser from Stage S17 was not kept in the project. The JSON is verified against RACES.txt (trait text matches exactly), but re-parsing needs the parser to be saved in the project first.

## 0.8 Special abilities wired (Stage S21)

- **(SA1) Shadowdancer Darkvision:** the class text says Su but SPECIAL ABILITIES.txt defines darkvision as Ex. The class value is kept and flagged (`specialAbilityConflict`). Confirm which is intended.
- **(SA2) Assassin Death Attack:** the type is not stated in SPECIAL ABILITIES.txt, so no type is filled (`abilityTypeNote`). Please supply one.
- **(SA3) Disease nature:** Demon fever, devil chills, mummy rot and slimy doom are marked Su, inferred from the SRD because the italics were lost in the text (see Stage S20).
- **(SA4) Mixed types:** gaseous form, paralysis and gaze attacks list two possible types, so no single type is filled. Gaze attacks is Su for non-spell gazes, per the text.
- **(SA5) Text-based links** (`source: text`) are heuristics for words such as "fear", "invisibility" and "turn". They are kept as "mentions" and can be reviewed individually.

## 0.9 Audit (Stage S22) — incoherence, ambiguity and items for human review

No data was changed in this pass. Findings are ordered by severity. "Fix" is the suggested action, not something already done.

### A. Defects (fix before relying on the data)

| # | Where | Finding | Evidence | Suggested fix |
|---|---|---|---|---|
| A1 | `src/views/Skills.tsx` lines 70, 84, 163–164 | **Runtime crash on the Skills tab.** Five synergies have `to: null` (targets are checks such as "rally checks", "turning checks", "bardic knowledge checks", not skills). The code reads `x.to.skillId` unguarded, so the grid card for Diplomacy, Intimidate, Handle Animal and Knowledge, and the detail view for any skill, throw. The build still passes because this is a runtime error. | `diplomacy-to-rally-checks`, `intimidate-to-rally-checks`, `handle-animal-to-wild-empathy-checks`, `knowledge-history-to-bardic-knowledge-checks`, `knowledge-religion-to-turning-checks` | Guard with `?.`, and give check-targeted synergies a typed `toCheck` target. |
| A2 | Races: Bugbear, Drow, Goblin, Hobgoblin descriptions | **Race text names domains that were purged.** Chaos and Evil are no longer in the domain list, so the stated choices cannot be resolved. | Bugbear "Chaos, Evil, Trickery, and War"; Drow "Chaos, Destruction, Evil, or Trickery"; Goblin "Chaos, Evil, or Trickery"; Hobgoblin "Evil, Destruction, or Trickery" | Decide whether to restore Chaos and Evil as domains, or to mark these choices as unavailable. |
| A3 | `SPELLBOOK.txt` / `dnd core.json` components | **Component parsing is not clean.** Compound codes were not split, so the JSON holds codes such as `XP; SEE TEXT`, `F; SEE TEXT`, `(F); SEE TEXT`, and `V (BRD ONLY)`. Spells with "V (Brd only), S, M; see text" (Hypnotic Pattern, Rainbow Pattern) and "V, S, M, (F); see text" (Trap the Soul) are affected. | `components.codes` value counts | Split on `;` and `,`, strip parentheses, and keep qualifiers in a separate field. |
| A4 | `dnd core.json` conditions; `CONDITIONS.txt` | **Encoding damage and a typo are in the source and in the JSON.** `⏻9` should be `–9` (Dying). `Â–` should be `–` (Confused, Prone). `Â’` should be `’` (Energy Drained). "Alos see" should be "Also see". | 1 `⏻`, 6 `Â`, 1 "Alos see" in JSON | Correct in `CONDITIONS.txt` and re-derive the condition records. |
| A5 | Condition `mechanics` (extracted by heuristics) | **Several extracted modifiers are truncated or mis-targeted.** Blinded carries "−4 on Search checks and on most Strength-" as its target. Entangled's target is cut mid-phrase. Cowering's target is cut at "loses her Dexterity". Energy Drained shows only the attack penalty, but the condition also applies −1 to skill and ability checks and to saves, and −5 hp. Prone's restriction text still has the `Â` damage. | Condition records, Blinded/Entangled/Cowering/Energy Drained/Prone | Hand-review all 38 condition mechanics against CONDITIONS.txt. |
| A6 | Spell names: SPELLBOOK vs JSON | **Apostrophe mismatch.** SPELLBOOK uses curly apostrophes (’); the JSON names still use straight ones (24 names, for example "Bull's Strength"). Any join on names will miss these. | 24 JSON names; the 7 entries in the book that are not in the JSON are listed below | Normalise the JSON names to curly apostrophes, or normalise both sides before joining. |
| A7 | Spell index vs book | **Grouped alignment entries differ between book and JSON.** The book has 7 entries the JSON lacks (Detect Chaos, Detect Evil, Detect Good, Detect Law, Dispel Good, Dispel Law, Magic Circle against Law). The JSON has 3 grouped entries the book lacks (Detect/Dispel/Magic Circle "Chaos/Evil/Good/Law"). This is the decision recorded as A8 and Q6, not yet applied. | Name comparison after apostrophe normalisation | Decide split or grouped and apply to both. |
| A8 | Class abilities | **Some "abilities" are not abilities.** Feat-list tables are stored as abilities ("Epic Barbarian Bonus Feat List", and the same pattern for Epic Bard, Cleric, Druid, Fighter, Monk, Paladin, Ranger, Rogue, Sorcerer, Wizard). Epic Rogue has a placeholder ability named "Special Abilities". Paladin, Wizard, Sorcerer and Epic Wizard have "Special Mount" and "Familiar" entries, and Hierophant has "Special Ability", and Rogue has "Special Abilities". | 20 records matched by name | Re-home feat lists onto a separate `featLists` field; rename placeholders. |
| A9 | Source typo | "The wizards's familiar continues to increase" (Epic Wizard). | `EPIC WIZARD.txt` and the JSON | Correct to "wizard's". |
| A10 | Poison drain notation | **Two sources disagree on ability drain.** ASSASSIN.txt gives Burnt othur fumes as "1 Con Drain"; SPECIAL ABILITIES.txt gives "1 Con*" (asterisk means drain). The Assassin file also repeats the poisons table with straight apostrophes and different spacing. | Assassin file vs `poisons` collection | Pick one notation. Consider making ASSASSIN.txt reference the poisons table rather than duplicate it. |

### B. Incoherence in the wider project

| # | Finding | Detail |
|---|---|---|
| B1 | **The fluffy-robot repository is no longer a git clone.** The `.git` folder was removed in Stage S2. Local work cannot be diffed, and GitHub is out of date. | Restore the clone or make the local folder a new repository with its own remote, before the next push. |
| B2 | Stale statements in the JSON | `meta.placeholders` describes SPELL LISTS.txt and SPELL DESCRIPTIONS.txt as sources. `spellLists[].file` (10 records) still says "SPELL LISTS.txt". Both files were removed. |
| B3 | Stale statements in SPELLBOOK.txt | The preamble names SPELL LISTS.txt and SPELL DESCRIPTIONS.txt as merged sources. |
| B4 | Explorer hard-coded value | `src/views/Overview.tsx` shows the raw JSON as "2.3 MB". The file is now about 5.8 MB. |
| B5 | Explorer: Spells "All sources" filter | After the merge, every spell has the same source, so the filter has no effect. |
| B6 | Explorer: no view for races | Races exist only in the JSON Data tab. There is no Races tab. |
| B7 | Explorer: new links not shown | Special ability links (`specialAbilityRefs`) are not shown on class ability cards, and conditions' `referencedBySpecialAbilities` is not shown on condition pages. |
| B8 | Explorer: bundle size | The JSON is inlined into a single 7.8 MB HTML file. Consider lazy loading per tab. |
| B9 | Tooling | `tools/` has only the special-abilities script. The race parser from Stage S17 was never saved (RC7), so the race wiring cannot be reproduced. |
| B10 | Logs out of date | `dndsucks.md` §6.1 still lists Hardening as an open gap and Q7 is still open, with no note that the spell was removed (S9). `fixingdnd.md` Stage S1 "Pending" items are not annotated as superseded. |
| B11 | Skill key ability | *Speak Language* has `keyAbility: null` (source heading says "NONE; TRAINED ONLY"). Use an explicit value, and separate the "trained only" flag. |
| B12 | Class `category` field | Classes have `type` only. The `category` field from the first version of the data is absent. The explorer uses `type`, so this is only an inconsistency. |
| B13 | Spells with no list | Chaos Hammer, Holy Smite, Order's Wrath and Unholy Blight are retained with no class list and no domain (Stage S6 A4 decision). Confirm this is still wanted. |

### C. Source-text formatting not yet normalised

| File | Problem |
|---|---|
| `SKILLS.txt` | Table titles are duplicated inline, for example "Table: Climb Climb DC", "Table: Disguise Disguise …", "Table: Foundering Foundering in…". Straight apostrophes ("Grappler's"). |
| `DOMAINS.txt` | Several domain spell rows run onto one line (for example "8 Incendiary Cloud … 7 Acid Fog"), so the domain spell tables cannot be parsed reliably from the text. |
| `CONDITIONS.txt` | Encoding damage (A4). |
| `Prestige Class ASSASSIN.txt` | Duplicated poisons table (A10). |
| `EPIC WIZARD.txt` | Possessive typo (A9). |
| `RACES.txt`, `SPECIAL ABILITIES.txt`, `RULES.txt` | Normalised in Stages S16, S18 and S20. Not re-checked since. |

### D. Ambiguities that need a human decision

| # | Question |
|---|---|
| D1 | **Shadowdancer Darkvision:** Su in the class text, Ex in the definition. Which applies? (SA1) |
| D2 | **Assassin Death Attack:** no type in the source. What type should it be? (SA2) |
| D3 | **Disease nature:** demon fever, devil chills, mummy rot and slimy doom are Su by inference from the SRD. Confirm. (SA3) |
| D4 | **Hobgoblin racial Hit Dice** are derived from the 1st-level warrior (1d8, BAB +1, base saves +2/+0/+0). Confirm. (RC5) |
| D5 | **"Type" tag on spells** is derived from class lists (Arcane/Divine). Spells with no list are tagged Divine by default. Confirm the meaning you want. (G1) |
| D6 | **Omitted Saving Throw / Spell Resistance** in the old headers are recorded as None / No. Confirm for the 165 spells this affected. (G2) |
| D7 | **Derived creature types for humanoid races** are "humanoid, derived". Should the subtypes (goblinoid, elf, orc, dwarf and so on) be added? (RC1) |
| D8 | **Drow inheritance by keyword.** Any future Elf trait matching "low-light vision", "weapon proficiency", "automatic and bonus languages" or "favored class" would also be replaced. Confirm this is the intent. (RC2) |
| D9 | **Ex-paladin rule.** The rule enforces continuous paladin levels. It does not model Blackguard or other ex-paladin features. Confirm the scope. (RC6) |
| D10 | **Protection from Energy:** the generic spell is not on class lists (only its domain slots). Confirm. (F1) |
| D11 | **Luck and Protection domains** are exceptions to the purge rule because they hold a spell that is not on a class list. Confirm. |
| D12 | **Stage S6 exceptions** — whether Chaos and Evil should come back (see A2). |

### E. Checks that passed

- All counts in `meta.counts` match the collections: classes 42, domains 35, spells 607, spell lists 10, skills 36, synergies 35, conditions 38, races 15, special abilities 34, diseases 10, poisons 36, Listen DC rows 7.
- No duplicate ids in any collection, and no duplicate spell names.
- Every reference in the JSON resolves: spell list ids, domain spell ids, class and race references, condition references, special ability references.
- RULES.txt matches the bonus-spells rule in both the `rules` collection and the legacy copy (23 rows, no differences).
- The Human and Half-Elf "no ability adjustments" flag, and the Minotaur Piercing Gore value, are in both the text and the JSON.
- No "Hardening", "Spell Replacement" or "Spell Swap" content remains in the spell data or the text files, except the rule name `spell-replacement` and the deliberate Stage S12 history.
- Race effective values agree with their own data (ECL = level adjustment + racial Hit Dice).
- No doubled words in RACES.txt, SPECIAL ABILITIES.txt or RULES.txt.

---

## 1. How the comparison was done (so you can trust / challenge it)

- Parsed **every spell heading** in `SPELL DESCRIPTIONS.txt` using its `Level:` line as anchor (school line immediately above, spell name above that). Result: **605 distinct described spells, no duplicates**.
- Compared against: (a) the **10 class spell lists** in the JSON `spellLists` (bard, cleric, druid, paladin, ranger, sorcerer-wizard, blackguard, assassin, adept, magewright — from `SPELL LISTS.txt`); (b) the **81 domain spell lists** in `domains` (from `DOMAINS.txt`); (c) the 760-entry `spells` index in the JSON.
- Name matching normalised curly apostrophes (`’` → `'`), then applied an author-prefix alias pass (`Melf’s …` ≡ `Acid …` after stripping `Melf’s/Bigby’s/…`, `Confusion, Lesser` ≡ `Lesser Confusion`, `Mage’s …` ≡ `Mordenkainen’s …`) so that alternative names are reported as **renames to decide**, not as false "missing" spells.
- "Everywhere a spell is named" impact counts were obtained by case-insensitive search of **all 49 `.txt` files** for both name forms.

### Definitions used — you may overrule them in §8

| Term | Meaning in this document |
|---|---|
| **Class spell list** | One of the 10 lists in `spellLists` / `SPELL LISTS.txt` |
| **Domain spell list** | The 9 spells granted by one of the 81 domains in `domains` / `DOMAINS.txt` |
| **In a spell list** (strict) | Appears in at least one **class** spell list. Domain-only spells are flagged separately, because whether domains "count" is your call (Question Q1) |
| **Core** | Provisionally: appears in a core class list (base classes bard/cleric/druid/paladin/ranger/sorcerer-wizard). Prestige/NPC-only appearances are flagged, not assumed core or non-core |
| **Flavourful name** | The older possessive form used as the heading in `SPELL DESCRIPTIONS.txt` (e.g. *Tenser’s Floating Disk*) |
| **List name** | The de-named form used in `SPELL LISTS.txt` and the JSON (e.g. *Floating Disk*) |

---

## 2. Headline findings

| # | Finding | Count | Where to decide |
|---|---|---:|---|
| 1 | Spell descriptions parsed in `SPELL DESCRIPTIONS.txt` | **605** | — |
| 2 | Described spells matched to a JSON `spells` entry (after alias pass) | **594** | — |
| 3 | Described spells with **no JSON entry of their own** — all are individual alignment spells hidden inside grouped JSON entries | **11** | §5 |
| 4 | Described spells whose list name ≠ description heading (**alternative names**) | **28** | §3 |
| 5 | Described spells in **no class spell list** (domain-only) — the strict purge candidates | **4** | §4 |
| 6 | Described spells in no class **or** domain list at all | **0** | §4 |
| 7 | Class-list spells with **no description** | **7 entries = 2 true gaps + 5 grouped entries** | §6.1 |
| 8 | Domain-referenced spells with **no description** (159 of them not in any class list either) | **163** | §6.2, Appendix A |
| 9 | Duplicate headings inside `SPELL DESCRIPTIONS.txt` | **0** | — |

> **Headline you should know before deciding:** on a strict reading, `SPELL DESCRIPTIONS.txt` contains almost **no** excess. 590 of its 605 spells are on a class spell list, 4 more are domain-only, and the remaining 11 are core alignment spells that the lists/JSON express as grouped entries (`Detect Chaos/Evil/Good/Law`, etc.). The described set is, in effect, the standard 3.5 SRD spell set. The genuinely "extra" spell material in the repo is **not in the descriptions file** — it is the 159 domain-only spells in `DOMAINS.txt`/the JSON that have no description at all (§6.2 / Appendix A). If your definition of "core" is narrower (e.g. base classes only, no prestige/NPC lists, no domains), say so in §8 and the candidate list will be regenerated under that definition — I have not silently applied a narrower one.

---

## 3. DECISION A — Alternative names (28 spells)

Your stated default is to **retain the flavourful older names**. Because renaming must be reflected *everywhere a spell is named*, each row needs your individual confirmation — tick one box per row (or edit the "Your choice" cell). "Rename impact" counts current occurrences of each form across all 49 `.txt` files; the JSON impact is described after the table.

| # | Your choice | Flavourful name (description heading, `SPELL DESCRIPTIONS.txt` line) | Current list / JSON name | JSON id now → if renamed | Appears on (class lists) | Rename impact in `.txt` files |
|---:|---|---|---|---|---|---|
| A01 | [ ] flavourful · [ ] list name | **Melf’s Acid Arrow** (line 1) | Acid Arrow | `acid-arrow` → `melfs-acid-arrow` | sorcerer-wizard 2 | list-name ×2 (SPELL DESCRIPTIONS.txt×1, SPELL LISTS.txt×1); flavourful ×1 (SPELL DESCRIPTIONS.txt×1) |
| A02 | [ ] flavourful · [ ] list name | **Evard’s Black Tentacles** (line 509) | Black Tentacles | `black-tentacles` → `evards-black-tentacles` | sorcerer-wizard 4 | list-name ×4 (SPELL DESCRIPTIONS.txt×2, SPELL LISTS.txt×1, DOMAINS.txt×1); flavourful ×2 (SPELL DESCRIPTIONS.txt×1, DOMAINS.txt×1) |
| A03 | [ ] flavourful · [ ] list name | **Bigby’s Clenched Fist** (line 829) | Clenched Fist | `clenched-fist` → `bigbys-clenched-fist` | sorcerer-wizard 8 | list-name ×4 (SPELL DESCRIPTIONS.txt×2, SPELL LISTS.txt×1, DOMAINS.txt×1); flavourful ×1 (SPELL DESCRIPTIONS.txt×1) |
| A04 | [ ] flavourful · [ ] list name | **Confusion, Lesser** (line 1013) | Lesser Confusion | `lesser-confusion` → `confusion-lesser` | bard 1 | list-name ×1 (SPELL LISTS.txt×1); flavourful ×2 (SPELL DESCRIPTIONS.txt×1, DOMAINS.txt×1) |
| A05 | [ ] flavourful · [ ] list name | **Bigby’s Crushing Hand** (line 1248) | Crushing Hand | `crushing-hand` → `bigbys-crushing-hand` | sorcerer-wizard 9 | list-name ×6 (SPELL DESCRIPTIONS.txt×3, SPELL LISTS.txt×1, DOMAINS.txt×2); flavourful ×2 (SPELL DESCRIPTIONS.txt×1, DOMAINS.txt×1) |
| A06 | [ ] flavourful · [ ] list name | **Tenser’s Floating Disk** (line 2398) | Floating Disk | `floating-disk` → `tensers-floating-disk` | sorcerer-wizard 1, magewright 1 | list-name ×4 (SPELL DESCRIPTIONS.txt×1, SPELL LISTS.txt×2, NPC MAGEWRIGHT.txt×1); flavourful ×2 (SPELL DESCRIPTIONS.txt×1, NPC MAGEWRIGHT.txt×1) |
| A07 | [ ] flavourful · [ ] list name | **Bigby’s Forceful Hand** (line 2454) | Forceful Hand | `forceful-hand` → `bigbys-forceful-hand` | sorcerer-wizard 6 | list-name ×7 (SPELL DESCRIPTIONS.txt×6, SPELL LISTS.txt×1); flavourful ×1 (SPELL DESCRIPTIONS.txt×1) |
| A08 | [ ] flavourful · [ ] list name | **Otiluke’s Freezing Sphere** (line 2504) | Freezing Sphere | `freezing-sphere` → `otilukes-freezing-sphere` | sorcerer-wizard 6 | list-name ×6 (SPELL DESCRIPTIONS.txt×4, SPELL LISTS.txt×1, DOMAINS.txt×1); flavourful ×2 (SPELL DESCRIPTIONS.txt×1, DOMAINS.txt×1) |
| A09 | [ ] flavourful · [ ] list name | **Bigby’s Grasping Hand** (line 2716) | Grasping Hand | `grasping-hand` → `bigbys-grasping-hand` | sorcerer-wizard 7 | list-name ×7 (SPELL DESCRIPTIONS.txt×4, SPELL LISTS.txt×1, DOMAINS.txt×2); flavourful ×2 (SPELL DESCRIPTIONS.txt×1, DOMAINS.txt×1) |
| A10 | [ ] flavourful · [ ] list name | **Tasha’s Hideous Laughter** (line 2973) | Hideous Laughter | `hideous-laughter` → `tashas-hideous-laughter` | bard 1, sorcerer-wizard 2 | list-name ×3 (SPELL DESCRIPTIONS.txt×1, SPELL LISTS.txt×2); flavourful ×1 (SPELL DESCRIPTIONS.txt×1) |
| A11 | [ ] flavourful · [ ] list name | **Drawmij’s Instant Summons** (line 3270) | Instant Summons | `instant-summons` → `drawmijs-instant-summons` | sorcerer-wizard 7 | list-name ×4 (SPELL DESCRIPTIONS.txt×2, SPELL LISTS.txt×1, DOMAINS.txt×1); flavourful ×1 (SPELL DESCRIPTIONS.txt×1) |
| A12 | [ ] flavourful · [ ] list name | **Bigby’s Interposing Hand** (line 3286) | Interposing Hand | `interposing-hand` → `bigbys-interposing-hand` | sorcerer-wizard 5 | list-name ×11 (SPELL DESCRIPTIONS.txt×10, SPELL LISTS.txt×1); flavourful ×1 (SPELL DESCRIPTIONS.txt×1) |
| A13 | [ ] flavourful · [ ] list name | **Otto’s Irresistible Dance** (line 3374) | Irresistible Dance | `irresistible-dance` → `ottos-irresistible-dance` | bard 6, sorcerer-wizard 8 | list-name ×7 (SPELL DESCRIPTIONS.txt×4, SPELL LISTS.txt×2, DOMAINS.txt×1); flavourful ×2 (SPELL DESCRIPTIONS.txt×1, DOMAINS.txt×1) |
| A14 | [ ] flavourful · [ ] list name | **Mordenkainen’s Disjunction** (line 3542) | Mage's Disjunction | `mages-disjunction` → `mordenkainens-disjunction` | sorcerer-wizard 9 | list-name ×6 (SPELL DESCRIPTIONS.txt×4, SPELL LISTS.txt×1, DOMAINS.txt×1); flavourful ×1 (SPELL DESCRIPTIONS.txt×1) |
| A15 | [ ] flavourful · [ ] list name | **Mordenkainen’s Faithful Hound** (line 3554) | Mage's Faithful Hound | `mages-faithful-hound` → `mordenkainens-faithful-hound` | sorcerer-wizard 5 | list-name ×1 (SPELL LISTS.txt×1); flavourful ×1 (SPELL DESCRIPTIONS.txt×1) |
| A16 | [ ] flavourful · [ ] list name | **Mordenkainen’s Lucubration** (line 3568) | Mage's Lucubration | `mages-lucubration` → `mordenkainens-lucubration` | sorcerer-wizard 6 | list-name ×1 (SPELL LISTS.txt×1); flavourful ×1 (SPELL DESCRIPTIONS.txt×1) |
| A17 | [ ] flavourful · [ ] list name | **Mordenkainen’s Magnificent Mansion** (line 3576) | Mage's Magnificent Mansion | `mages-magnificent-mansion` → `mordenkainens-magnificent-mansion` | sorcerer-wizard 7 | list-name ×1 (SPELL LISTS.txt×1); flavourful ×2 (SPELL DESCRIPTIONS.txt×1, DOMAINS.txt×1) |
| A18 | [ ] flavourful · [ ] list name | **Mordenkainen’s Private Sanctum** (line 3588) | Mage's Private Sanctum | `mages-private-sanctum` → `mordenkainens-private-sanctum` | sorcerer-wizard 5 | list-name ×3 (SPELL DESCRIPTIONS.txt×2, SPELL LISTS.txt×1); flavourful ×1 (SPELL DESCRIPTIONS.txt×1) |
| A19 | [ ] flavourful · [ ] list name | **Mordenkainen’s Sword** (line 3602) | Mage's Sword | `mages-sword` → `mordenkainens-sword` | sorcerer-wizard 7 | list-name ×1 (SPELL LISTS.txt×1); flavourful ×2 (SPELL DESCRIPTIONS.txt×2) |
| A20 | [ ] flavourful · [ ] list name | **Nystul’s Magic Aura** (line 3618) | Magic Aura | `magic-aura` → `nystuls-magic-aura` | bard 1, sorcerer-wizard 1, magewright 1 | list-name ×12 (SPELL DESCRIPTIONS.txt×3, SPELL LISTS.txt×6, NPC MAGEWRIGHT.txt×1, DOMAINS.txt×2); flavourful ×2 (SPELL DESCRIPTIONS.txt×1, NPC MAGEWRIGHT.txt×1) |
| A21 | [ ] flavourful · [ ] list name | **Rary’s Mnemonic Enhancer** (line 3965) | Mnemonic Enhancer | `mnemonic-enhancer` → `rarys-mnemonic-enhancer` | sorcerer-wizard 4 | list-name ×3 (SPELL DESCRIPTIONS.txt×2, SPELL LISTS.txt×1); flavourful ×1 (SPELL DESCRIPTIONS.txt×1) |
| A22 | [ ] flavourful · [ ] list name | **Otiluke’s Resilient Sphere** (line 4936) | Resilient Sphere | `resilient-sphere` → `otilukes-resilient-sphere` | sorcerer-wizard 4 | list-name ×6 (SPELL DESCRIPTIONS.txt×2, SPELL LISTS.txt×2, DOMAINS.txt×2); flavourful ×3 (SPELL DESCRIPTIONS.txt×1, DOMAINS.txt×2) |
| A23 | [ ] flavourful · [ ] list name | **Leomund’s Secret Chest** (line 5174) | Secret Chest | `secret-chest` → `leomunds-secret-chest` | sorcerer-wizard 5, magewright 5 | list-name ×5 (SPELL DESCRIPTIONS.txt×1, SPELL LISTS.txt×2, NPC MAGEWRIGHT.txt×1, DOMAINS.txt×1); flavourful ×3 (SPELL DESCRIPTIONS.txt×1, NPC MAGEWRIGHT.txt×1, DOMAINS.txt×1) |
| A24 | [ ] flavourful · [ ] list name | **Leomund’s Secure Shelter** (line 5198) | Secure Shelter | `secure-shelter` → `leomunds-secure-shelter` | bard 4, sorcerer-wizard 4 | list-name ×4 (SPELL DESCRIPTIONS.txt×2, SPELL LISTS.txt×2); flavourful ×1 (SPELL DESCRIPTIONS.txt×1) |
| A25 | [ ] flavourful · [ ] list name | **Otiluke’s Telekinetic Sphere** (line 6400) | Telekinetic Sphere | `telekinetic-sphere` → `otilukes-telekinetic-sphere` | sorcerer-wizard 8 | list-name ×4 (SPELL DESCRIPTIONS.txt×2, SPELL LISTS.txt×1, DOMAINS.txt×1); flavourful ×2 (SPELL DESCRIPTIONS.txt×1, DOMAINS.txt×1) |
| A26 | [ ] flavourful · [ ] list name | **Rary’s Telepathic Bond** (line 6414) | Telepathic Bond | `telepathic-bond` → `rarys-telepathic-bond` | sorcerer-wizard 5 | list-name ×9 (SPELL DESCRIPTIONS.txt×5, SPELL LISTS.txt×1, DOMAINS.txt×3); flavourful ×2 (SPELL DESCRIPTIONS.txt×1, DOMAINS.txt×1) |
| A27 | [ ] flavourful · [ ] list name | **Leomund’s Tiny Hut** (line 6502) | Tiny Hut | `tiny-hut` → `leomunds-tiny-hut` | bard 3, sorcerer-wizard 3 | list-name ×3 (SPELL DESCRIPTIONS.txt×1, SPELL LISTS.txt×2); flavourful ×1 (SPELL DESCRIPTIONS.txt×1) |
| A28 | [ ] flavourful · [ ] list name | **Tenser’s Transformation** (line 6544) | Transformation | `transformation` → `tensers-transformation` | sorcerer-wizard 6 | list-name ×2 (SPELL DESCRIPTIONS.txt×1, SPELL LISTS.txt×1); flavourful ×1 (SPELL DESCRIPTIONS.txt×1) |

### Special cases inside those 28 — read before ticking

- **A04 `Confusion, Lesser` ↔ `Lesser Confusion`** is *not* an author name: it is word-order (suffix style, as in `Cure Light Wounds, Mass`). Decide separately whether you want suffix style (`Confusion, Lesser`) or list style (`Lesser Confusion`) — consistency with the `…, Mass` spells argues for suffix style.
- **A14–A19 `Mordenkainen’s …` ↔ `Mage’s …`**: the lists did not strip the possessive, they genericised it (`Mage’s Disjunction`). Renaming these restores the proper name; not renaming keeps a half-way house.
- **The other 21** are the classic stripped-author set: Melf, Evard, Bigby (×5), Tenser (×2), Otiluke (×3), Tasha, Drawmij, Otto, Nystul, Rary (×2), Leomund (×3).
- Body text matters, not just headings: e.g. `Bigby’s Forceful Hand`'s description references the other Hand spells, and `…, Mass` spells say "functions like *bull’s strength*". A rename pass must catch in-text references (the impact counts above include them), including lower-case references inside other spells, domains, and class files (e.g. `NPC MAGEWRIGHT.txt` already uses `Leomund's secret chest` in its spell list).

### What a "flavourful" choice will change (per spell, when you confirm)

1. `SPELL DESCRIPTIONS.txt` — heading is already flavourful; in-body cross-references normalised to the chosen form.
2. `SPELL LISTS.txt` — list entry renamed.
3. `DOMAINS.txt` — domain spell entry renamed where present (several Hand/Sphere spells appear there, in both forms today).
4. Class / prestige / NPC `.txt` files — any spell-list or prose mention renamed (counts in the table show where).
5. `dnd core.json` — `spells[].name`, `spells[].id` (slug — **Question Q4: change the id or keep it stable?**), `spellLists[].levels[].spellIds`, `domains[].spells[].name` + `.spellIds`, and any `summaryVariants`.
6. The explorer rebuilds its indexes from the JSON, so no app code change is needed — but external links/bookmarks using old slugs would break if ids change.

---

## 4. DECISION B — Purge candidates: described spells in no class spell list (4)

These are the **only** spells in `SPELL DESCRIPTIONS.txt` that meet your stated purge test ("non-core and do not appear in any spell lists") under the strict definition. All four **do** appear in domain spell lists, and all four are the signature 4th-level spells of the PHB alignment domains (Chaos/Good/Law/Evil) — so my assessment is that they are **core domain spells, not excess**, *unless* you decide domains do not count as spell lists (Q1) or those domains are themselves out of scope. Tick per spell:

| # | Your choice | Spell (`SPELL DESCRIPTIONS.txt`) | School / Level header | Domain list(s) | Elsewhere in `.txt` | My assessment |
|---:|---|---|---|---|---|---|
| P1 | [ ] keep · [ ] purge | **Chaos Hammer** (line 744, id `chaos-hammer`) | Evocation [Chaotic] — Level: Chaos 4 Components: V, S Casting Time: 1 standard action Range: Medium (100 ft. + 1… | Chaos 4 | SPELL DESCRIPTIONS.txt×1, DOMAINS.txt×1 | Core **if** alignment domains are in scope; purge only with the domain |
| P2 | [ ] keep · [ ] purge | **Holy Smite** (line 3043, id `holy-smite`) | Evocation [Good] — Level: Good 4 Components: V, S Casting Time: 1 standard action Range: Medium (100 ft. + 10… | Glory 4, Good 4 | SPELL DESCRIPTIONS.txt×1, DOMAINS.txt×2 | Core **if** alignment domains are in scope; purge only with the domain |
| P3 | [ ] keep · [ ] purge | **Order’s Wrath** (line 4110, id `orders-wrath`) | Evocation [Lawful] — Level: Law 4 Components: V, S Casting Time: 1 standard action Range: Medium (100 ft. + 10 … | Law 4 | SPELL DESCRIPTIONS.txt×1, DOMAINS.txt×1 | Core **if** alignment domains are in scope; purge only with the domain |
| P4 | [ ] keep · [ ] purge | **Unholy Blight** (line 6726, id `unholy-blight`) | Evocation [Evil] — Level: Evil 4 Components: V, S Casting Time: 1 standard action Range: Medium (100 ft. + 10… | Evil 4 | SPELL DESCRIPTIONS.txt×1, DOMAINS.txt×1 | Core **if** alignment domains are in scope; purge only with the domain |

**Borderline, for completeness (not strict candidates):** `Magic Circle against Good` is the only described spell whose *only* class-list appearance is a prestige list (assassin 3) — it stays core under any definition that includes prestige lists, and is independently a domain-family spell (§5). No described spell is NPC-list-only.

If you purge any of P1–P4, the deletion must also remove: its entry in `DOMAINS.txt` (or the whole domain, your call), its `spells[]` entry and `domains[].spells[]` entry in the JSON. Purging the description alone would leave a dangling domain spell — the §6 gap problem in reverse.

---

## 5. DECISION C — Grouped alignment spells: 11 descriptions vs. 5 grouped JSON entries

`SPELL LISTS.txt`/the JSON sometimes enter four alignment variants as **one** grouped spell; `SPELL DESCRIPTIONS.txt` always describes them **individually**. This is why 11 described spells have no JSON entry of their own. It is a gap (§6) and a naming decision at once:

| Described individually in `SPELL DESCRIPTIONS.txt` | Grouped JSON entry that currently covers it | Grouped entry appears on | Individual JSON entries that *also* exist (from ungrouped lists) |
|---|---|---|---|
| Detect Chaos (1504) · Detect Evil (1510) · Detect Good (1547) · Detect Law (1553) | `detect-chaos-evil-good-law` — Detect Chaos/Evil/Good/Law | cleric 1, adept 1 | none |
| Dispel Good (1831) · Dispel Law (1837) — *Dispel Chaos/Evil are described too and do have entries* | `dispel-chaos-evil-good-law` — Dispel Chaos/Evil/Good/Law | cleric 5 | `dispel-chaos` (paladin 4), `dispel-evil` (paladin 4) |
| Magic Circle against Law (3669) — *Chaos/Evil/Good described and entered* | `magic-circle-against-chaos-evil-good-law` | cleric 3, sorcerer-wizard 3 | `magic-circle-against-chaos` (paladin 3), `…-evil` (paladin 3), `…-good` (assassin 3) |
| Protection from Chaos (4591) · Protection from Evil (4605) · Protection from Good (4619) · Protection from Law (4625) | `protection-from-chaos-evil-good-law` + pair entry `protection-from-chaos-evil` | cleric 1, sorcerer-wizard 1, adept 1; pair: paladin 1 | none |

**Your choice (Q6):** [ ] **Split** — replace each grouped entry with the individual spells everywhere (lists, domains, JSON ids), matching the descriptions; · [ ] **Keep grouped** — leave lists/JSON as-is and accept 11 descriptions sharing 5 index entries; · [ ] **Hybrid** — keep grouped list entries but give each described variant its own JSON spell entry cross-linked to the group.
Note the existing asymmetry splitting would fix: today a paladin finds `Dispel Chaos` as its own spell while a cleric finds only the grouped `Dispel Chaos/Evil/Good/Law`.

---

## 6. Gaps — where the lists/JSON name a spell the descriptions do not cover

### 6.1 Class spell lists (7 entries, only 2 true gaps)

| Spell (JSON id) | On lists | Status | Evidence / your options |
|---|---|---|---|
| Detect Chaos/Evil/Good/Law (`detect-chaos-evil-good-law`) | cleric 1, adept 1 | ✅ covered by 4 individual descriptions | §5 — split or keep grouped |
| Dispel Chaos/Evil/Good/Law (`dispel-chaos-evil-good-law`) | cleric 5 | ✅ covered by 4 individual descriptions | §5 |
| Magic Circle against Chaos/Evil/Good/Law (`magic-circle-against-chaos-evil-good-law`) | cleric 3, sorcerer-wizard 3 | ✅ covered by 4 individual descriptions | §5 |
| Protection from Chaos/Evil/Good/Law (`protection-from-chaos-evil-good-law`) | cleric 1, sorcerer-wizard 1, adept 1 | ✅ covered by 4 individual descriptions | §5 |
| Protection from Chaos/Evil (`protection-from-chaos-evil`) | paladin 1 | ✅ covered by Protection from Chaos + Protection from Evil | §5 |
| **Corrupt Weapon** (`corrupt-weapon`) | blackguard 1 | ❌ **TRUE GAP** — no entry in `SPELL DESCRIPTIONS.txt` | Only text in repo: list summary "Weapon strikes true against good foes" (`SPELL LISTS.txt`) and a prose mention in `Prestige Class BLACKGUARD.txt` ("the opposing counterpart of the paladin spell bless weapon… more effective against good foes"). Options: [ ] author a description entry (from what source?) · [ ] leave as summary-only · [ ] drop from list |
| **Hardening** (`hardening`) | magewright 4 | ❌ **TRUE GAP** — no entry in `SPELL DESCRIPTIONS.txt`, and no fuller text anywhere in the repo | Only occurrences in the whole repo: summary "Increases hardness of target by 1 per 2 levels" (`SPELL LISTS.txt` line 2544) and the name in the magewright list (`NPC MAGEWRIGHT.txt` line 67). This spell is also not a PHB/SRD spell — it is a candidate **non-core list entry** in its own right. Options: [ ] find/source a description · [ ] leave summary-only · [ ] purge from magewright list + JSON |

### 6.2 Domain spell lists (163 undescribed spells — the real "excess" question)

- Domain lists reference **484** distinct spells; **321** have descriptions, **163** do not. Of those, **159** are on no class list either (full list in Appendix A).
- These spells (e.g. *Abyssal Frenzy, Black Sand, Haboob, Fimbulwinter, Investiture of the Pit Fiend*) come with the supplemental (non-PHB) domains — Sand, Thirst, Vile Darkness, Diabolic, Seafolk, etc. They cannot be "purged from `SPELL DESCRIPTIONS.txt`" (they were never in it); deciding their fate means deciding the fate of their **domains** in `DOMAINS.txt` and the JSON.
- Undescribed count by domain (worst first):

| Domain | Undescribed / total domain spells | Domain | Undescribed / total |
|---|---:|---|---:|
| Sand | 9/9 | Purification | 8/9 |
| Hunger | 7/9 | Pleasure | 7/9 |
| Seafolk | 7/9 | Spite | 7/9 |
| Thirst | 7/9 | Winter | 7/9 |
| Destiny | 6/9 | Diabolic | 6/9 |
| Sky | 6/9 | Wrath | 6/9 |
| Joy | 5/9 | Summer | 5/9 |
| Corruption | 4/9 | Courage | 4/9 |
| Demonic | 4/9 | Mysticism | 4/11 |
| Pact | 4/9 | Pestilence | 4/9 |
| Chaos | 3/9 | Competition | 3/9 |
| Darkness | 3/9 | Evil | 3/9 |
| Fey | 3/9 | Good | 3/9 |
| Greed | 3/9 | Herald | 3/9 |
| Law | 3/9 | Madness | 3/9 |
| Mind | 3/9 | Ooze | 3/9 |
| Vile Darkness | 3/9 | Creation | 2/9 |
| Domination | 2/9 | Dragon | 2/9 |
| Endurance | 2/9 | Entropy | 2/9 |
| Fury | 2/9 | Glory | 2/9 |
| Ocean | 2/9 | Temptation | 2/9 |
| Cold | 1/9 | Dream | 1/9 |
| Force | 1/9 | Inquisition | 1/9 |
| Repose | 1/9 |  |  |

---

## 7. What is *not* a problem (checked, so you don't have to)

- No duplicate or missing headings inside `SPELL DESCRIPTIONS.txt` (605/605 parsed cleanly, including the `Summon Nature’s Ally IV` entry whose header is split across extra blank lines).
- No described spell is absent from the JSON index except the 11 grouped variants in §5.
- Every JSON spell (760) is accounted for as class-list (597), domain-list (484), or both — there are no orphan JSON spells.
- Apostrophe style is the only systematic textual difference besides the 28 names: descriptions use curly `’`, lists/JSON use straight `'` (see Q5).

---

## 8. Questions I need answered before touching any file

- **Q1 — Do domain spell lists count as "spell lists"** for the purge test? (If yes, §4 has zero purge candidates. If no, P1–P4 are your candidates.)
- **Q2 — What is "core" scope for lists?** [ ] base classes only · [ ] base + prestige · [ ] base + prestige + NPC (status quo) — and for domains: [ ] PHB domains only · [ ] all 81 domains (status quo). A narrower scope regenerates §§4/6.2.
- **Q3 — Alternative names:** tick each row in §3 (A01–A28). Is your flavourful default to apply to *all* rows except ones you mark otherwise?
- **Q4 — JSON ids:** when a spell is renamed, [ ] change its slug id to match (clean, but breaks existing references) · [ ] keep the old id as a stable identifier and only change `name` · [ ] change id but record the old id in an `aliases` field.
- **Q5 — Apostrophes:** [ ] keep curly `’` in `.txt` headings and straight `'` in JSON/lists (status quo) · [ ] normalise everything to one form (which?).
- **Q6 — Grouped alignment spells:** split / keep grouped / hybrid (see §5).
- **Q7 — True gaps:** what should happen to *Corrupt Weapon* and *Hardening* (see §6.1)? Is an external source (e.g. printed SRD/Spell Compendium) in bounds, or repo-only?
- **Q8 — Purge mechanics:** for any spell you purge, also delete it from [ ] domain lists [ ] class lists [ ] JSON `spells` index (recommended: all three, to avoid dangling references) — confirm, and say whether purged spells should be archived somewhere (e.g. a `purged` JSON file) or deleted outright.

---

## Appendix A — Domain-only spells with no description (159)

Not in `SPELL DESCRIPTIONS.txt`, not on any class spell list. Listed so you can decide the fate of the supplemental domains (§6.2/Q2) — **these are not purge candidates from the descriptions file**, they are the gap/excess list for `DOMAINS.txt` and the JSON.

| Abyssal Frenzy (Fury 7) | Abyssal Frenzy, Mass (Fury 9) | Abyssal Rift (Entropy 9) |
| Aerial Alacrity (Sky 4) | Affliction (Wrath 3) | Airy Water (Seafolk 6) |
| Armor of Darkness (Darkness 4) | Aspect of the Deity (Herald 7) | Awaken Sand (Sand 6) |
| Beckoning Call (Temptation 2) | Befoul (Corruption 8, Ooze 8) | Bestow Curse, Greater (Destiny 7) |
| Bestow Wound (Spite 1) | Bite of the King (Hunger 8) | Black Sand (Sand 2) |
| Blacklight (Darkness 3) | Blast of Force (Force 3) | Blast of Sand (Sand 4) |
| Blinding Beauty (Fey 4) | Blindness (Darkness 2) | Blizzard (Winter 5) |
| Bolt of Glory (Glory 6) | Bolts of Bedevilment (Madness 5) | Brain Spider (Mind 7) |
| Castigate (Purification 4) | Celestial Blood (Pleasure 6) | Chaav's Laugh (Joy 5) |
| Cheat (Greed 1) | Choose Destiny (Destiny 9) | Cloak of Bravery (Courage 3) |
| Cloak of Bravery, Greater (Courage 9) | Cloak of Hate (Spite 6) | Crown of Glory (Glory 8, Herald 8) |
| Curse of Lycanthropy (Pestilence 6) | Damning Darkness (Vile Darkness 4) | Dance of the Unicorn (Purification 5) |
| Darkbolt (Vile Darkness 2) | Death Hail (Winter 6) | Death Pact (Pact 8) |
| Deific Vengeance (Purification 2) | Delay Death (Destiny 3) | Demon Wings (Demonic 3) |
| Demoncall (Demonic 2) | Demonflesh (Demonic 1) | Depthsurge (Seafolk 8) |
| Desert Binding (Sand 8) | Desiccate (Thirst 2) | Desiccate, Mass (Thirst 5) |
| Despoil (Corruption 9) | Devil's Ego (Diabolic 3) | Devil's Eye (Diabolic 2) |
| Dispel Water (Thirst 4) | Distilled Joy (Joy 3) | Dragon Ally (Dragon 7) |
| Dream Sight (Dream 6) | Elation (Joy 2) | Empyreal Ecstasy (Pleasure 7) |
| Enduring Flight (Sky 3) | Energize Potion (Wrath 2) | Entice Gift (Greed 2) |
| Eyes of the King (Hunger 6) | Field of Ghouls (Hunger 7) | Fiendish Clarity (Demonic 7) |
| Fimbulwinter (Winter 9) | Fins to Feet (Seafolk 2) | Fire in the Blood (Spite 5) |
| Fires of Purity (Purification 6) | Flaywind Burst (Sand 5) | Genesis (Creation 9) |
| Ghoul Gauntlet (Hunger 5) | Ghoul Gesture (Hunger 3) | Ghoul Glyph (Hunger 2) |
| Ghoul Light (Hunger 1) | Greater Aspect of the Deity (Herald 9) | Haboob (Sand 3) |
| Heart's Ease (Pleasure 3) | Hellfire (Diabolic 4) | Hellfire Storm (Diabolic 7) |
| Impede Sun's Brilliance (Summer 1) | Imprison Soul (Spite 9) | Inspired Aim (Fey 3) |
| Investiture of the Pit Fiend (Diabolic 9) | Last Judgment (Wrath 8) | Lastai's Caress (Pleasure 2) |
| Lesser Telepathic Bond (Mind 3) | Lion's Roar (Courage 8) | Maddening Scream (Madness 8) |
| Maelstrom (Ocean 8) | Mantle of Pure Spite (Spite 8) | Mastery of the Sky (Sky 8) |
| Megalodon Empowerment (Seafolk 7) | Mephit Mob (Thirst 7) | Monstrous Thrall (Domination 9) |
| Morality Undone (Corruption 4) | Nimbus of Light (Purification 1) | Obedient Avalanche (Cold 9) |
| Omen of Peril (Destiny 1) | Oozepuppet (Ooze 5) | Otyugh Swarm (Pestilence 9) |
| Pact of Return (Spite 7) | Parching Touch (Thirst 1) | Phantasmal Thief (Greed 8) |
| Plague of Rats (Pestilence 5) | Pox (Corruption 6) | Probe Thoughts (Mind 6) |
| Pronouncement of Fate (Spite 4) | Protection from Dessication (Summer 3) | Quickswim (Seafolk 1) |
| Radiant Shield (Wrath 4) | Raptor's Sight (Sky 1) | Recitation (Purification 3) |
| Refreshment (Endurance 3) | Remove Fatigue (Pleasure 4) | Renewal Pact (Pact 7) |
| Righteous Smite (Wrath 7) | Righteous Wrath of the Faithful (Purification 7) | Scales of the Sealord (Seafolk 3) |
| Scourge (Pestilence 7) | Siren's Call (Seafolk 4) | Skin of the Cactus (Summer 4) |
| Slime Wave (Ooze 7) | Snow Walk (Winter 2) | Snowsight (Winter 1) |
| Soul Link (Temptation 7) | Spread of Contentment (Pleasure 8) | Stalwart Pact (Destiny 5, Pact 5) |
| Starmantle (Joy 7) | Sublime Revelry (Pleasure 9) | Summon Desert Ally IX (Sand 9) |
| Summon Devoted Roc (Sky 9) | Summon Dire Hawk (Sky 2) | Summon Giants (Frost Giants Only) (Winter 8) |
| Sunstroke (Summer 2) | Surelife (Repose 8) | Sustain (Endurance 4) |
| Symbol of Thirst (Thirst 6) | Tormenting Thirst (Thirst 3) | Touch of Madness (Madness 2) |
| True Creation (Creation 8) | True Domination (Domination 8) | Unearthly Beauty (Fey 8) |
| Unearthly Heat (Summer 5) | Utterdark (Vile Darkness 8) | Valiant Fury (Courage 5) |
| Vengeance Halo (Wrath 6) | Visage of the Deity (Mysticism 6) | Visage of the Deity, Greater (Competition 9, Mysticism 9, Purification 9) |
| Visage of the Deity, Lesser (Mysticism 3) | Vision of Entropy (Entropy 2) | Vision of Heaven (Joy 1) |
| Vitrify (Sand 7) | Voice of the Dragon (Dragon 4) | Warp Destiny (Destiny 6) |
| Waste Strider (Sand 1) | Waterspout (Ocean 7) | Weapon of the Deity (Mysticism 4) |
| Winter's Embrace (Winter 3) | Zeal (Competition 2) | Zealot Pact (Competition 6, Pact 6) |

---

## Appendix B — Files a confirmed rename/purge will touch

| File | Rename impact | Purge impact |
|---|---|---|
| `SPELL DESCRIPTIONS.txt` | headings (already flavourful) + in-body cross-references | delete entry between neighbouring spells |
| `SPELL LISTS.txt` | every list entry under the old name | delete list line |
| `DOMAINS.txt` | domain spell names (both forms occur today) | delete domain spell line / whole domain (Q8) |
| Class, prestige & NPC `*.txt` (49 files searched) | spell-list sections and prose mentions, per §3 counts | remove mentions |
| `dnd core.json` | `spells[].name/id`, `spellLists[].levels[].spellIds`, `domains[].spells[].name/spellIds`, `summaryVariants`, counts in `meta` | remove entries + recount `meta.counts` |
| Explorer (`src/`) | none — indexes rebuild from JSON at load | none |

## 0.10 Audit response (Stage S23)

| Item | Outcome |
|---|---|
| Recorded counts stale | Self-validating. `tools/validate_and_refresh.py` recomputes every count and runs 25 cross-file checks; all pass. |
| Domain spell restrictions detached from rows | Special column added to every domain spell row; footnote text moved into it. |
| Domain notes include removed domains | Rebuilt from the Special column; no purged domains remain. |
| Alignment domains retired | Chaos, Evil, Law and Good restored from the supplied text, with SPELLBOOK short descriptions, in DOMAINS.txt and the JSON. Race domain choices now resolve (this also resolves A2). |
| Condition classifier | Rebuilt with explicit relation rules and confidence. 111 low-confidence mentions remain and are visible as such. Known false positives fixed. |
| Abbreviated spell blocks | Functions-like inheritance verified: 131 entries inherit with overrides recorded. 45 non-functions-like entries had invented None/No values; these are now "Not stated in source" and need your decision (D6 is reversed for them). |
| Class-level tags unchecked | Checked against upstream SPELL LISTS.txt. Five SPELLBOOK corrections applied (A7 and D-items resolved for alignment families). |
| Disease supernatural classification | Demon fever, devil chills and mummy rot are Su; Slimy doom is Ex (resolves SA3 and D3). |
| Poison Special outcomes | Siren's breath and Blasphemix removed everywhere they appear (resolves A10's Special cases). |
| Shadowdancer darkvision | Class-granted and unlinked from the darkvision definition (resolves SA1 and D1). |
| Shared definitions without explicit links | Flagged (`reviewFlags`) for later linking. |
| Race campaign and interpretive text | Flagged (`reviewFlags`) for later review. |
| House swap thresholds | Removed (15 scaling entries). The class-prose rule is kept. |
| Schema text | `meta.schema` is now derived from the structure. "schema 9" was not found in the repo or the explorer, so it may be in a document outside this project. |

Decisions still open: D6 for the 45 unstated spells; whether the four restored alignment domains should keep their "Granted Power" wording; and the CONDITIONS.txt encoding fix (A4). The Skills tab crash (A1) remains open.
