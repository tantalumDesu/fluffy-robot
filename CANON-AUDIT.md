# D&D 3.5 core canon audit

The `.txt` files in this repository are the baseline, including explicit table
rules for draft animals and vehicles. Historical implementation notes in
`RULES.txt` and `meta.legacyValidation` are not proof of current JSON coverage.
This is a targeted audit, not a line-by-line verification of all 71 sources.

## Corrected

- Replaced the retired `spell-replacement` rule with separate Bard, Sorcerer,
  and Assassin rules. Each links to the exact source paragraph; explicit
  levels and continued schedules are stored separately. This restores the
  missing Assassin schedule and confines the other two to available class rows.
- A same-type negative modifier was previously ignored by the numeric resolver.
  As required by the stacking section in `RULES.txt`, it now keeps the best
  bonus and worst penalty for a nonstacking type. Full same-source and
  circumstance adjudication still depends on source identity and context.

## Remaining findings

| Priority | Finding | Disposition |
| --- | --- | --- |
| High | `RULES.txt` names 35 rule IDs absent from `mechanics.rules` among its backtick-led list entries. Examples: AC and attack formulas, cover, concealment, flanking, initiative, and modifier stacking. Monk and Paladin continuity now have typed rules sourced directly from their class files. | Transcribe the clear rules first. An absent ID is not proof the mechanic is entirely missing: Combat Reflexes and temporary HP have implementations elsewhere. |
| High | Two feats retain manual prerequisite clauses: Improved Familiar and Familiar Spell. Some feat choices also require eligibility facts from outside the feat catalog. | Flag unresolved facts for review. Selection and repeatability metadata and benefit text are now present on all 124 feats. |
| Medium | 581 of 611 spells and 95 of 124 feats have no typed effect catalog entry; covered entries may be partial. | Convert unambiguous sheet effects from `SPELLBOOK.txt`, `FEATS.txt`, and `EPIC FEATS.txt`. Missing types are not missing descriptions. |
| Needs adjudication | The ranged modifier for a prone attacker is printed `—3` in `COMBAT MODIFIERS.txt`. | Confirm what that cell means before encoding it as a numeric modifier or rule. |

## Reproduce

```sh
python tools/audit_core.py
python tools/organize_core.py --check
python -m unittest discover -s tools
```

The audit currently finds no issues in the checked rule, spell, condition,
and feat-effect references and no blank spell descriptions. It reports named
coverage gaps separately from structural errors. It does not check every
record's interpretation against its source or imply that every `.txt` rule
is executable.
