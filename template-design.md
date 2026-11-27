# Creature template design

The [standalone catalogue](dnd35_templates.json) is available for pruning and is not consumed by core generation or automatically applied to character sheets. Lycanthropy and undead are the first planned integrations. The [integration guide](integration-guide.md) describes the existing sheet interfaces, including typed attack rosters for caller-supplied forms.

## Standalone catalogue

`dnd35_templates.json` now includes normalized `acquisitionModes` (`null` means unspecified), `formOf` links for lycanthrope form records, and `requiresTemplateId` links for the Ghost, Skeleton, Vampire and Zombie variant families. A parent link is not the full eligibility rule; read the original entry for additional restrictions.

`coreV2Reference.effectiveContributions` uses the field names and value shapes of `progression.races[].effective` in `dnd-core.json`: `abilityAdjustments`, `darkvisionFeet`, `energyResistance`, and `levelAdjustment`. These are contributions, not a complete replacement race profile. When integration is enabled, sum adjustments and LA, use the greater darkvision range and resistance per damage type, and never treat LA as Hit Dice. `sourceLines` points to one-based lines in `stats.raw` (arrays track the corresponding array entries).

Fixed and absent ability scores have no equivalent in the current race model. They remain explicit under `unsupportedAbilityChanges`, not disguised as adjustments or zeros. Conditional effects, HD tables and transformation costs remain reference-only. Run `python tools/normalize_templates.py` after editing source stat lines and `python tools/normalize_templates.py --check` to check for stale derived data.

## Template implementation checklist

| Area | Requirement | Catalogue example |
| --- | --- | --- |
| Hit Dice and progression | Distinguish adding racial HD, changing die size, and recalculating BAB or saves. Keep HD, class levels, LA, and CR independent. A type change alone must not recalculate everything. | Lycanthropy adds the animal's HD, BAB, and base saves; Arachnoid changes type but keeps BAB and base saves. |
| Forms versus persistent changes | Layer persistent template overrides over the base creature, then apply the active form's overrides. Keep original creature and base-animal inputs available. A form switch must not reapply persistent grants or reset HP, equipment, or ability uses. Apply any explicit form-specific gear or HP rules separately. | Lycanthrope animal and hybrid forms read the base animal's physical scores; Ghost's AC depends on manifestation. |
| Replacing or suppressing features | Target specific grants by source, so losing one grant doesn't erase a feature independently granted elsewhere. Preserve the original build in history even if all or part of it is currently unusable. | Psychic Vampire replaces Energy Drain; Zombie loses class levels, skills, and feats in the catalogue. |
| Acquisition and removal | Check eligibility and costs at the right time and record them once. Rebuilding the sheet must not re-charge XP or reroll choices. Removal can have its own consequences instead of simply undoing acquisition. | Necropolitan's ritual costs one level and XP; Mirage Mullah can lose its template after leaving the oasis. |
| Conditional rules and traits | Distinguish unconditional changes from effects that depend on current context, and identify what they override. | Ghost retains natural armor on the Ethereal Plane but changes defenses when manifesting; Vampire sunlight exposure has consequences across rounds. |
| Multiple templates and order | Evaluate eligibility at application time against the appropriate creature state. Represent dependencies, repeatability, and removal explicitly; don't assume overrides commute. | Evolved can repeat; Sanctified removes Fiendish if present. |

**Proposed override model:** base creature → persistent template overrides → active form overrides → temporary effects for the current situation. An override can add, replace, or suppress; it need not be a numeric bonus. For mutually exclusive forms, store one active form ID per form group, not independent switches that can activate incompatible forms. Derive the current sheet from the active layers; switching forms changes the selection, not the base record. Store acquisition and removal events, choices, current form, HP, equipment, and spent uses in character state, not in the canon definition. Costs and other one-time consequences belong in those events, not in the recalculation.

**Table decisions before implementation:**

1. **Lycanthropy:** Decide what happens to gear, spellcasting, and character control when switching forms, and what persists after switching back or curing the affliction.
2. **Undead:** Decide whether the player keeps control after a transformation that removes class levels or features, and which parts of the original build return if the creature is restored to life.
3. **Mid-play transformations:** Decide what requires DM confirmation, especially changes to XP, alignment, class abilities, or player control.

The catalogue records this distinction in `overrideModel` and each entry's `overrideLayer`. The three lycanthrope forms share one `formGroupId`; the common template is persistent. Listing-only entries have no assigned layer. Some persistent templates describe form changes in prose; those forms are not separate typed records yet.

The catalogue audit splits template-specific alternate shapes, manifestations, and possession modes into reference-only `formProfiles`; their owning templates remain persistent. `sourceEffectIndexes` are zero-based indices into the owning entry's `other_effects`. Vampire, Swarmform patches the Vampire shape group and replaces its four animal choices, not its gaseous profile. Movement-triggered incorporeality, Wind Walk-dependent behavior, and feature suppression are `contextualModes`, not independently selectable forms. Ordinary spell grants, lasting transformations, and fixed creature traits are not split into form profiles.

`effects.stateChangesById` uses the same transition format for rage, progressive fatigue, cumulative fear, and reference-only Vampire sunlight. `tools.state_changes` applies transitions to caller-owned state; the caller supplies rage eligibility and expiry, rest, and encounter events, and passes the resulting condition IDs to sheet derivation. Fear durations and recovery, rage use limits and combat modifiers, and Vampire exposure detection and turn enforcement are not managed by this helper. The sunlight profile is not automatically attached to any creature or form.

`environmentStatesById` holds independent, toggleable environment profiles. Each profile uses the core transition shape; store its current state per actor and send `exposure-on` / `exposure-off` when the table resolves the exposure. Round, hour, and day events are explicit; the catalogue does not start a clock. A `resolve-source-effect` event points back to the original prose for adjudication, not executable damage or healing. This does not add profiles to core or attach them to play automatically. Complex conditions (such as Shadow Blend availability and whether water shields a Drowned One) are resolved by the caller before toggling. Daylight spell exposure and natural sunlight are separate facts.
