# D&D 3.5 core canon audit

The repository’s TXT files, including explicit table rulings, are the baseline. This audit distinguishes source retention, structured data, and executable behavior. None implies the others.

## Current coverage

- The structural audit finds no missing IDs from the `RULES.txt` index and no errors in its checked references or adjudication text fields.
- The source audit compares spell summaries and descriptions, condition descriptions, and feat bodies against source blocks. It checks race traits, class abilities, and special-ability paragraphs against their source files. It does not verify every numeric rule or parser against every source.
- Typed spell and feat coverage is partial. The structural report gives live counts; an effect entry can cover only part of a description. Only confirmed recipient-sheet numeric effects are applied automatically.

## Open findings

| Area | What remains |
| --- | --- |
| Class ability prose | 15 descriptions do not match a contiguous source passage. `tools/source_audit.py` lists the records; a paraphrase or joined passage is not necessarily a rules discrepancy. |
| Feat eligibility | Improved Familiar uses the dedicated acquisition catalog; unlisted candidates remain a DM ruling. Familiar Spell’s chosen spell still requires eligibility confirmation. Some other choices need facts supplied by the player or DM. |
| Combat context | The caller supplies cover, concealment, flanking, and opportunity triggers. There is no map geometry or automatic reaction engine. Exposed-item damage on a natural 1 and concentration after taking damage during casting remain manual. |
| Effect stacking | The sheet uses the highest bonus and most negative penalty per named type. Same-source overlap is a DM ruling. |
| Damage and drain | The sheet projects class DR and confirmed external grants; aligned weapon properties supply bypass tags, not automatic extra damage. The caller coordinates spell pools, condition transitions, permanent level loss, and restoration with actor state. |

## Run the checks

```sh
python tools/organize_core.py --check
python tools/audit_core.py
python tools/source_audit.py
python -m unittest discover -s tools
```
