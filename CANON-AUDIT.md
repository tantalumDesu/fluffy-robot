# D&D 3.5 core canon audit

The repository’s TXT files, including explicit table rulings, are the baseline. This audit distinguishes source retention, structured data, and executable behavior. None implies the others.

## Current coverage

- The structural audit finds no missing IDs from the `RULES.txt` index and no errors in its checked references or adjudication text fields.
- The source audit compares spell summaries and descriptions, condition descriptions, and feat bodies against source blocks. It checks race traits, class abilities, and special-ability paragraphs against their source files. It does not verify every numeric rule or parser against every source.
- **Typed effects are partial.** The structural audit counts 558 of 611 spells and 89 of 124 feats without entries in the effect catalogs it checks. All 124 feats have selection metadata. Those counts do not measure every implementation: some mechanics live in casting plans, item profiles, or actor-state helpers.
- **Feat and equipment projection:** Epic feats carry a source-linked character level 21 gate. The sheet projects confirmed selections for weapon and school feats, repeatable grants, equipment slots, and two-weapon routines. It does not execute attacks, spend uses, or resolve reactions.
- **Wizard spellbooks:** Each volume has an instance ID, independent capacity, and its own inscriptions. Preparation searches accessible, intact entries; the table decides which books or entries are lost or damaged. The existing study, inscription, and specialization checks still apply to ordinary Wizard learning.
- **Natural weapons:** Racial natural weapons and recognized companion full-attack entries share weapon-type IDs. Improved Natural Attack is selected by type and projects one damage step on each matching entry across forms. Custom or template forms supply an explicit typed roster. Special attacks outside recognized weapon routines and unsupported damage steps still require adjudication; source attack text remains available.
- **Epic casting feats:** Improved Spell Capacity checks the chosen track, records one daily slot per pick, and applies ability bonus slots only once for a newly unlocked level. Spell Knowledge requires at least one level in the chosen arcane class and the ability to cast at least one spell in that class. Each chosen spell is capped at the highest level the character can currently cast on that track, not the class’s normal maximum. It records two new arcane spells and grants no slots. The receiving list supplies the spell level when available; otherwise the arcane source list supplies it (confirm a list when levels differ). The chosen arcane casting track is independent of the class gained at level-up. Only a Wizard-track pick requires room in accessible books and automatically inscribes both spells; prohibited schools still apply. Level loss and restoration project both feats from the saved picks; restoration does not repair lost or damaged books.

## Open findings

| Area | What remains |
| --- | --- |
| Class ability prose | 15 descriptions do not match a contiguous source passage. `tools/source_audit.py` lists the records; a paraphrase or joined passage is not necessarily a rules discrepancy. |
| Feat eligibility | Improved Familiar uses the dedicated acquisition catalog; unlisted candidates remain a DM ruling. Familiar Spell validates known spell levels and XP components; unpriced materials are negligible; stated costs may need confirmation. |
| Spell preparation | Spell Mastery validates selections and marks mastered spells, but does not bypass the current Wizard book requirement. The caller confirms book access and study/writing time; item-use school checks are separate from cast scheduling. |
| Combat context | The caller supplies cover, concealment, flanking, and opportunity triggers. There is no map geometry or automatic reaction engine. Exposed-item damage on a natural 1 and concentration after taking damage during casting remain manual. |
| Effect stacking | The sheet uses the highest bonus and most negative penalty per named type. Same-source overlap is a DM ruling. |
| Damage and drain | The sheet projects class DR and confirmed external grants; aligned weapon properties supply bypass tags, not automatic extra damage. The caller coordinates spell pools, condition transitions, permanent level loss, and restoration with actor state. |

## Feat choices and repeated grants

Review of `FEATS.txt` and `EPIC FEATS.txt` against generated selection/effect data and the sheet and casting consumers. Remaining gaps after projecting confirmed feat grants:

| Priority | Feat or family | Missing connection |
| --- | --- | --- |

Dodge is a different kind of choice: the opponent designation is encounter state, not part of the permanent feat name. Improved Metamagic already counts repeat selections in cast planning; it does not need a target picker.

## Run the checks

```sh
python tools/organize_core.py --check
python tools/audit_core.py
python tools/source_audit.py
python -m unittest discover -s tools
```

## Spellcasting integration audit

`magic.castingProfilesByClassId` describes the independent casting tracks, including tradition, preparation mode, domain eligibility, Wizard book requirements, and the allowed Cleric and Druid conversion spells. The helpers use these profiles for planning. Druid conversion no longer requires separate authorization for each eligible spell; Cleric cure/inflict authorization is still supplied from the character’s alignment, deity, and permanent choice. Prepared domain slots cannot be converted.

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

- Commit known-spell gains and swaps per spontaneous track and Magewright mastery gains; the slot ledger currently accepts the verified known/access set.
- Feed recorded domain selections, Cleric conversion choice, temporary caster-level bonuses, and live component access from actor state into each cast. Apply spell effects only after the table confirms targeting, saves, and spell resistance.
- Use batch recovery to reapply active negative levels and persist slot changes together. Keep component consumption and XP charges in actor inventory and advancement state.
