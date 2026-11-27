# D&D 3.5 rules core

This is a personal project to put my D&D 3.5 table rules into a form that software can use. I’m developing the rules data and testing the calculations before putting them together into an application. There’s no released app, finished character sheet UI, or end-to-end combat engine yet.

## Capabilities and implementation

These are callable data and Python tools, not screens in a finished app. The [integration guide](integration-guide.md) explains how to use them together.

| Capability | What it supports | Where to look |
| --- | --- | --- |
| Rules data and source checks | Shared rules, source descriptions, typed records, and audits for broken references and text differences. The TXT files are the rules baseline, including table rulings. | [`dnd-core.json`](dnd-core.json), [`organize_core.py`](tools/organize_core.py), [`audit_core.py`](tools/audit_core.py), [`source_audit.py`](tools/source_audit.py) |
| Character advancement | XP thresholds, ordered class levels, multiclass and epic progression, feat selection, and alignment eligibility checks, and exact per-level HP, ability, skill, and feat records for loss and restoration. | [`character_advancement.py`](tools/character_advancement.py), [`level_history.py`](tools/level_history.py), [`level_choices.py`](tools/level_choices.py), [`feat_selection.py`](tools/feat_selection.py), [`alignment.py`](tools/alignment.py) |
| Character-sheet totals | Ability modifiers, AC, attacks, saves, skills, equipment fit, load, and type-based modifier stacking. | [`derived_stats.py`](tools/derived_stats.py), [`creature_size.py`](tools/creature_size.py), [`sheet_effects.py`](tools/sheet_effects.py) |
| Equipment and transport | Equipment slots, hand allocation, two-weapon routines, physical damage types, shield bashes and spikes, locked gauntlets, pack loads, vehicle payloads, and animal training. | [`equipment_slots.py`](tools/equipment_slots.py), [`damage_types.py`](tools/damage_types.py), [`locked_gauntlet.py`](tools/locked_gauntlet.py), [`pack_animals.py`](tools/pack_animals.py), [`vehicle_load.py`](tools/vehicle_load.py), [`animal_training.py`](tools/animal_training.py) |
| Familiars and animal companions | Full source stat blocks alongside level-adjusted numbers, Improved Familiar eligibility, and familiar dismissal or death XP loss. | [`companion_sheet.py`](tools/companion_sheet.py), [`improved_familiars.py`](tools/improved_familiars.py) |
| Spellcasting | Per-class slots, preparation and recovery, metamagic, casting plans, and arcane spell failure from worn armor and shields. | [`spellcasting.py`](tools/spellcasting.py), [`effect_state.py`](tools/effect_state.py) |
| Encounters and conditions | Turn budgets, cast timing, removable condition overrides, condition transitions, and supported spell cures. | [`game_time.py`](tools/game_time.py), [`encounter_conditions.py`](tools/encounter_conditions.py), [`condition_rules.py`](tools/condition_rules.py), [`condition_cures.py`](tools/condition_cures.py) |
| Damage, healing, and drain | HP and temporary HP, typed DR and bypass, energy defenses, nonlethal damage, stabilization, and negative-level or restoration bookkeeping. | [`injury.py`](tools/injury.py), [`damage_reduction.py`](tools/damage_reduction.py), [`negative_levels.py`](tools/negative_levels.py), [`drain_history.py`](tools/drain_history.py) |

## Where it goes next

The next step is to put these pieces together around a working character sheet: keep build choices, equipment, companion links, and other actor state separate from shared rules, then connect the sheet to encounter updates. Use actual table examples to decide which gaps are worth filling. When a rule changes, record it in the relevant TXT source, refresh the JSON, and test the behavior.

**The DM has the final say.** Automatically apply only confirmed numeric effects on the recipient’s sheet. Effects beyond the recipient or without a sheet-number change keep their source text for player and DM adjudication. Explicit helpers can calculate outcomes from facts the table supplies; typed data alone doesn’t authorize an effect. Record one-off rulings in character or encounter state, not in shared canon.

`dnd35_templates.json` stays a standalone catalogue for case-by-case review. Templates aren’t applied to characters by the current core. Lycanthropy and undead are priorities for later integration once their persistent changes and toggleable forms are understood.

## Refresh and verify

From the repository root, with Python 3.9 or later:

```sh
python tools/organize_core.py                    # Refresh generated data
python tools/organize_core.py --check            # Check that it is up to date
python tools/audit_core.py                       # Check structure and references
python tools/source_audit.py                     # Compare retained text against TXT sources
python -m unittest discover -s tools             # Run the tests
```

The generator refreshes source-backed catalogs, descriptions, and source anchors. Some class, spell, and skill fields still come from the existing JSON; the generator does not rebuild every record from scratch.

## When changing generated core data

Before adding a field to `dnd-core.json`, check whether another record already owns the same mechanical fact. Prefer a stable ID reference or a lookup derived by the consumer over a serialized copy. Keep source prose, distinct variants, and intentional overrides; do not treat their resemblance as duplication. Update the generator and affected consumers together, add a regression check when consolidating a shared fact, and note other duplicates you discover in `CANON-AUDIT.md`.

## More detail

- [Integration guide](integration-guide.md) — data layout, sheet effects, progression, equipment, spellcasting, and encounter state.
- [Creature template design](template-design.md) — standalone catalogue, form and persistence model, and open template rulings.
- [Canon audit](CANON-AUDIT.md) — source coverage and extraction notes.
