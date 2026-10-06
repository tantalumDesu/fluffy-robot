## Inputs
- **Size:** thorpe, hamlet, village, small town, large town, city, metropolis
- **Terrain:** river, coast, road, forest, mountain, border, farmland, etc.
- **Wealth:** destitute, poor, modest, prosperous, rich
- **Racial makeup:** percentage per race
- **Ruling race(s):** optional
- **Seed:** required
- **Toggles:** magic level, law level, trade route, monster threat, castle chance

**Thorpe** — smaller than a hamlet: a few households, often one extended family or a cluster of farmsteads. No market, guild, watch, or permanent clergy (a shrine-keeper or itinerant priest may visit).
**Destitute** — recently looted, razed, or stripped by war, raid, or disaster. Damaged establishments, depleted stores, broken supply chains, unpaid levies, absent ruling class. In shock, not merely poorer than poor.
**Metropolis** — greater than a city: a capital or trade hub of tens of thousands, multiple districts, a cathedral or grand temple complex, a university or scholarly college, a permanent garrison, foreign quarters, national guilds. Aggregates and re-exports surrounding settlements' surplus.

## Core Principles
1. Population first. Races, sexes, ages, households, clans before anything else.
2. Dependency-first order. No backtracking, no rewriting.
3. Two-pass economy. Pass 1 sets resources, trade, demand, supply-chain structure. Pass 2 simulates prices, stock, wages, taxes, upkeep, coffers.
4. SRD 3.5 mechanics. Classes, levels, feats, skills, equipment, prices, stat blocks.
5. Medieval English flavour without naming England. Anglo-Saxon, Norman, guild, manor, parish aesthetics for mundane things.
6. Race affects profession propensity. Dwarven smith in a human village; elven fletcher in a dwarven village.
7. Single-screen establishment interaction. Stats, hiring, buying, haggling, spell and item commissioning on one screen.
8. Integrated defense economy. Equipment, upkeep, fortifications, siege stores, levies flow through the economy.
9. Entity graph. Stable `id`, `type`, `tags`. Phases append fields.
10. Separate RNG streams. `seed + phase + entityId` preserves determinism as phases are added.
11. Lazy naming and UI. Names generated when identity is complete; UI renders summaries first.
12. JSON only. All export, formatting, and interchange is JSON. No CSV, no Markdown, no other serialisation format.

## Order of Operations
1. **Inputs & Seed** — establish RNG streams.
2. **Physical & External Context** — trade access, resource base, climate, isolation, threat, external demand. Outputs: `settlement.context`, `tradeRoutes`, `externalDemand`, `threatLevel`.
3. **Demographics** — Table A. Outputs: `population`, `racialBreakdown`, `sexDistribution`, `ageBands`, `labourPool`.
4. **Kinship & Households** — households, multigenerational families, clans, dependents, servants, apprentices. Outputs: `households`, `families`, `clans`, `dependencyGraph`.
5. **Culture & Identity** — alignment, faith (race → clan → alignment), naming profile, social class. Naming is callable, not a phase.
6. **Power & Law** — government, ruling race(s), guild charters, watch mandate, legal restrictions. Outputs: `government`, `lawLevel`, `guildCharters`, `watchMandate`.
7. **Economic Skeleton (Pass 1)** — resource base, import and export flows scaled by wealth and location, initial demand, supply-chain structure. Outputs: `resourceBase`, `imports`, `exports`, `initialDemand`, `supplyChainStructure`.
8. **Labour & Professions** — hard-coded sex division, racial propensity, faith, economy. Fill government offices. Outputs: `professions`, `labourAllocation`, `governmentOfficials`.
9. **Establishments** — derived from professions and supply-chain needs; varied names referencing settlement, geography, patron, monster, heraldry, or family. Each with named proprietor (race, sex, class, level, stats).
10. **Defense & Levies** — walls, gates, towers, ditches, palisades, castle chance, garrison, levy size, training, equipment quality, morale, siege stores.
11. **Economy Simulation (Pass 2)** — supply chains, exports of surplus, prices, stock, wages, taxes, tithes, guild fees, household production, child labour, defense upkeep, coffers. Daily/weekly ticks. Events (Table N). Effects ripple to family coffers, merchant profits, guard equipment, lord's treasury, poor relief, public works.
12. **NPCs & Proprietors** — 3.5 stat blocks from class/level/race/sex/faith/alignment; equipped using final economy wealth.
13. **Services & Costs** — hirelings, spellcasting, item creation, establishment services (SRD formulas).
14. **UI & JSON Export** — responsive UI, seed control, sliders, tabs, filters, search, tooltips. All output is a single JSON document. Flavour text varies; never repeats base data.

## Rules & Tables

### A. Demographic Priors
Mean household 4.5 (3–8). Age: 0–14 35%, 15–44 45%, 45–64 15%, 65+ 5%. Infant mortality 25% before age 5. Birth sex ratio 105 M : 100 F; adult 98 M : 100 F. Child labour productive from ~age 7.

### B. Class vs Profession
Every NPC has both a `class` (SRD) and a `profession` (medieval flavour).

| Class | Typical professions |
|---|---|
| Commoner | ploughman, alewife, goose girl, porter, laundress |
| Expert | smith, fletcher, miller, scribe, apothecary, merchant |
| Warrior | watchman, man-at-arms, levy, gatekeeper |
| Aristocrat | lord, sheriff, reeve, knight, bishop |
| Adept | cunning man, wise woman, hedge priest |
| Cleric | parish priest, prior, canon, druid |
| Wizard | scholar-mage, alchemist |
| Rogue | chapman, cutpurse, huckster, fence |
| Fighter | man-at-arms, knight, mercenary, captain |
| Ranger | forester, huntsman, verderer |
| Bard | minstrel, herald, crier |
| Druid | circle-keeper, grove-tender |
| Paladin | knight of a militant order |
| Monk | cloistered brother/sister, ascetic |

### C. Class Levels by Settlement Type
| Role | Class | Thorpe | Hamlet | Village | Small town | Large town | City | Metropolis |
|---|---|---|---|---|---|---|---|---|
| Labourer | Commoner | 1 | 1 | 1–2 | 1–3 | 1–3 | 1–4 | 1–5 |
| Tradesman | Expert | 2–3 | 2–4 | 2–5 | 3–6 | 4–7 | 5–8 | 6–10 |
| Guild master | Expert | — | — | 4–6 | 5–7 | 6–9 | 8–11 | 10–14 |
| Watchman | Warrior | — | 1 | 1–2 | 1–3 | 2–4 | 2–5 | 3–6 |
| Man-at-arms | Fighter | — | — | 2–3 | 2–4 | 3–5 | 4–6 | 5–8 |
| Knight | Fighter/Aristocrat | — | — | 3–5 | 4–6 | 5–7 | 6–9 | 8–12 |
| Priest | Cleric/Adept | 1–2 | 2 | 2–3 | 3–4 | 4–5 | 5–7 | 6–9 |
| Bishop/Archbishop | Cleric | — | — | — | 6–8 | 7–10 | 9–12 | 12–16 |
| Cunning man/woman | Adept/Wizard | 1–2 | 2 | 2–3 | 3–5 | 4–6 | 5–8 | 7–11 |
| Lord/lady | Aristocrat | — | 5 | 6–7 | 7–9 | 8–11 | 10–14 | 13–18 |
| Castle captain | Fighter | — | — | 4–6 | 6–8 | 7–9 | 9–12 | 12–16 |

Thorpe has no permanent watch, man-at-arms, knight, guild master, or resident lord; clergy is itinerant or a single shrine-keeper. Metropolis has multiple watch companies, knightly households, a permanent garrison, an archbishop or equivalent, a university, and national guilds. Metropolis levels +1 above city. Destitute settlements −1 (minimum 1).

### D. Alignment
Base: Good 55%, Neutral 44%, Evil 1%.

| Race | Lawful | Neutral | Chaotic |
|---|---|---|---|
| Human agrarian | 45% | 40% | 15% |
| Human border/trade | 25% | 50% | 25% |
| Dwarf | 70% | 25% | 5% |
| Elf | 20% | 55% | 25% |
| Halfling | 50% | 45% | 5% |
| Gnome | 30% | 50% | 20% |
| Orc | 15% | 30% | 55% |
| Half-elf | 25% | 55% | 20% |
| Half-orc | 20% | 40% | 40% |

Wealth modifier: middle bands +Good; destitute bends toward Evil; very rich neutral-to-Evil by self-interest. Profession modifier: clergy +Good, rogue/assassin +Evil. Clan reputation shifts bias.

### E. Ability Scores, Feats, Skills, Equipment
- Scores: 4d6 drop lowest. PC classes assign highest rolls to preferred stats; NPC classes assign in order.
- Feats: 1 at level 1, then every 3 levels. Priors: Skill Focus (profession), Negotiator (merchants), Persuasive (innkeepers), Power Attack (warriors), Weapon Focus (soldiers), Brew Potion / Craft Magic Arms and Armor / Craft Wondrous Item (spellcasters).
- Skills: `(class skill points + Int mod) × (level + 3)`, max rank = level + 3. Prioritise profession skills first, then class skills. Emphasise Appraise, Bluff, Diplomacy, Gather Information, Intimidate, Sense Motive, Profession, relevant Craft.
- Equipment: NPC wealth by level (SRD DMG Table 4-23) × wealth tier: destitute ×0.25, poor ×0.5, modest ×1, prosperous ×1.5, rich ×2.

### F. Pantheon
Classic Forgotten Realms pantheon. Settlements shun evil gods publicly; evil deities are worshipped covertly. Each deity has a distinct church structure:
- **Sun** (Lathander/Pelor): parishes, bishops, archdeacons, monasteries, tithes, canon law.
- **Nature** (Mielikki/Silvanus): druidic circles, grove-tenders, mixed sexes, no fixed hierarchy.
- **War** (Tyr/Helm): militant orders, grandmaster → knight-captain → brother/sister-at-arms, male-dominated.
- **Trickster** (Tymora/Olidammara): secret societies, cell structure, mixed.
- **Death** (Kelemvor/Wee Jas): funerary guilds, arch-funerary → mortician → acolyte, mixed.
- **Craft** (Moradin for dwarves, Gond for gnomes): guild-temple hybrid, master → journeyman → apprentice.
- **Evil deities:** covert shrines, no public buildings, disguised clergy.

Each church defines clergy titles, sex restrictions, celibacy, and magical services. Metropolises may host a grand cathedral, allied temples, and hidden shrines.

### G. Social Class
| Class | Share | Markers |
|---|---|---|
| Gentry | 2–5% | titles, heraldry, elite names |
| Clergy | 3–8% | rank titles, vestments |
| Merchants/guild | 8–15% | occupational surnames, fees |
| Artisans | 15–25% | guild membership, trade names |
| Free peasantry | 40–55% | yeoman, goodman, goodwife |
| Unfree/servile | 10–20% | no surname, obligatory labour |
| Outcasts | 1–3% | no guild, no parish standing |

Destitute: gentry absent, dead, or fled; unfree and outcast shares rise; artisan and merchant shares fall. Metropolis: merchant/guild share rises, small scholarly and bureaucratic class emerges, foreign quarters as distinct enclaves.

### H. Hard-Coded Sex-Based Division of Labour
Not optional, not randomised. Baseline approximates medieval English practice. Precedence: baseline → racial override → widow/heiress exception → mixed/flexible fallback.

**Male-dominated (≥80% M):** ploughman, husbandman, yeoman farmer; smith (blacksmith, farrier, armourer); carpenter, joiner, cooper, wheelwright; mason, thatcher, tiler; tanner, butcher, slaughterer; miller, master baker; deep-water fisherman, sailor, ferryman; carter, waggoner, drover; miner, quarryman; soldier, man-at-arms, watchman, gatekeeper; sheriff, reeve, constable, bailiff; scribe, clerk, notary; alchemist, apothecary (master); wizard, sorcerer, warlock; fletcher, bowyer (unless elven).

**Female-dominated (≥80% F):** alewife, brewster, innkeeper (victualling); spinner, weaver, seamstress, embroiderer; dairywoman, cheesemaker, butter-maker; midwife, wise woman, herbalist; poultry keeper, goose girl; laundress, washerwoman; nurse, wet-nurse, domestic servant; market woman, huckster, regrater; domestic baker, household cook; clothier, draper (shop-front); domestic candle-maker; charm-seller, petty diviner; cleric, druid, adept (where the deity permits).

**Mixed (20–80%):** smallholding farmer, gardener, orchard-keeper; merchant, shopkeeper, pedlar; innkeeper, taverner, hostelry keeper; healer, physician, chirurgeon; scribe (female religious houses); cleric, druid, monk (by order); bard, minstrel, entertainer; rogue, thief, cutpurse; fletcher, bowyer (especially elven); potter, glassmaker, jeweller; teacher, tutor, scholar.

**Widow/heiress exception:** may inherit and operate a deceased husband's/father's trade, guild membership, and establishment as a full proprietor. Social penalties possible in restrictive guilds. Daughters inherit in the absence of sons.

**Racial overrides:** dwarven women smith and work stone openly; elven women fletch, bowyer, and practise magic openly; halfling women innkeep, farm, and handle pipe-weed openly; gnome women tinker, alchemise, and cut gems openly; orc women butcher, raid, and mercenary openly.

**Enforcement:** labour engine checks sex before assignment; establishments reflect proprietor sex unless exception applies; household composition reflects division; women's unwaged work modelled as household production (Table V). Metropolises soften enforcement at the margins (female religious houses, women's guilds, widow communities) but do not override the baseline.

### I. Faith Derivation
Faith = race pantheon → clan patron → alignment-compatible deity. Half-race upbringing (Table W) determines which parent's pantheon applies.

### J. Naming
- Humans: Anglo-Saxon, sex-appropriate
- Elves: Romantic-language feel, sex-appropriate
- Halflings: Biblical first names + plain English surnames
- Gnomes: Celtic
- Dwarves: approximated Mongol
- Orcs: guttural first names + violent Native American epithet-style surnames
- Half-races: mix, decided by upbringing
- Ruling race(s) influence elite names and titles
- Class-conscious; marital status affects address (widow, wife, maid, master, goodman, goodwife)
- Generated lazily once identity is complete
- Metropolises include foreign quarters with names from the appropriate parent cultures

### K. Defense, Levy, Castle
Historical baseline, exaggerated for a world of inhuman monsters.
| Size | Wall | Castle | Garrison | Levy | Siege stores |
|---|---|---|---|---|---|
| Thorpe | none/ditch | 0% | — | 0–5 | 1 day |
| Hamlet | ditch/palisade | 2% | — | 10–30 | 3 days |
| Village | palisade | 5% | 5–15 | 30–80 | 7 days |
| Small town | stone wall + gates | 15% | 20–60 | 80–200 | 14 days |
| Large town | wall + towers | 40% | 60–150 | 200–500 | 30 days |
| City | curtain wall + keep | 70% | 150–500 | 500–2000 | 60 days |
| Metropolis | multiple walls, citadel, harbour chain | 90% | 500–2000 | 2000–8000 | 90–180 days |

Modifiers: +10% castle on border or high threat; +10% if rich. Destitute: walls and stores halved, garrison halved, levy halved until next harvest or event tick.
Upkeep: 1 gp per soldier per day; 5% of fortification value per year.
Siege stores: food, arrows (1,000 per 100 archers per day), fuel, pitch, stone. Metropolises maintain multiple depots and naval supply where applicable.

### L. Religious Buildings
Historical population-to-church ratios, adjusted for deity distribution.
- Thorpe (<30): no building; shrine stone, wayside cross, or itinerant priest.
- <100: 1 shrine
- 100–500: 1–2 shrines, 1 chapel
- 500–2,000: 2–4 shrines, 1–3 chapels, 1–2 churches
- 2,000–10,000: 4–8 shrines, 3–6 chapels, 2–4 churches, 1–2 temples, 1–3 monasteries
- City (10k–50k): 8+ shrines, 6+ chapels, 4+ churches, 2+ temples, 3+ monasteries, 1 cathedral
- Metropolis (50k+): 15+ shrines, 10+ chapels, 8+ churches, 4+ temples, 5+ monasteries, 1 grand cathedral, 1+ university or scholarly college, foreign temples

Distribution follows faith demographics. Sun deity holds the parish church; minority gods hold shrines or shared temples; evil gods hold covert shrines only. Destitute: one religious building may be damaged, desecrated, or abandoned.

### M. Supply Chains and External Trade
Each establishment declares inputs and outputs:
- Smithy: iron ingot + charcoal → tools, weapons, nails
- Bowyer: yew stave + sinew → bows
- Fletcher: shafts + feathers + heads → arrows
- Miller: grain → flour
- Baker: flour + yeast + fuel → bread
- Tanner: hides + tannin → leather
- Weaver: wool → cloth
- Apothecary: herbs + glass + alcohol → remedies

**Imports by wealth:**
| Wealth | Import multiplier | Luxury share |
|---|---|---|
| Destitute | 0.1× | 0% |
| Poor | 0.5× | 5% |
| Modest | 1× | 10% |
| Prosperous | 1.5× | 20% |
| Rich | 2.5× | 35% |

**Import cost by location:**
| Location | Trade access | Import cost |
|---|---|---|
| Coast | high | ×0.8 |
| River | high | ×0.9 |
| Major road | medium | ×1.0 |
| Minor road | low | ×1.2 |
| Isolated | very low | ×1.5 |

Thorpe: no market; trade via pedlars, fairs, or a nearby larger settlement. Destitute: broken supply chains, relief/foraging/barter until restored. Metropolis: regional trade hub, import multiplier ×1.5 above wealth tier, luxury share doubled, supplies surrounding settlements as an export node.

### N. Events
| Event | Frequency | Effect |
|---|---|---|
| Harvest | 1 per agrarian settlement per season | +20% grain, −10% bread |
| Fair | 1 per town per season | +30% trade volume for 1 week |
| Banditry | 10% per season on trade routes | −20% imports, +levy cost |
| Monster raid | 5–25% by threat | −stock, +defense spend |
| Plague | 2–5% per season (city/metropolis 5–25%) | −5–20% population, −trade |
| War | toggle/plot | +levy, +taxes, −imports |
| Trade disruption | 10% per season | +50% import cost |
| Looting | plot/toggle | Sets wealth to destitute; damages establishments, walls, stores; recovery over subsequent ticks |
| Fire | 3% per season in towns/cities, 5% in metropolises | 1–3 districts damaged or destroyed; −stock, −housing, +recovery cost |
| Plague riot | 10% during plague in city/metropolis | +law temporarily, −guild power, −trade |
| Foreign demand spike | 5% per season | +30% export price for one good |
| Trade embargo | 5% per season | Exports blocked; surplus spoils |
| Pirate/raider attack | 10% per season on coast/river | −export volume, +insurance cost |
| Merchant caravan | 15% per season in towns+ | +import variety, −import prices |

### O. Services & Costs
Use SRD formulas exactly.
- Hireling: SRD daily rates (untrained 1 sp, trained 3 sp, skilled 5 sp–2 gp, spellcaster 1 gp × caster level per spell).
- Spellcasting: `caster level × spell level × 10 gp`.
- Item creation: SRD formulas; prerequisites checked per Table X. Cost = half market price in materials; time = 1 day per 1,000 gp market price.
- Spell level ceiling: thorpe 1, hamlet 2, village 3, small town 5, large town 7, city 9, metropolis 9+ (multiple high-level casters; modified by magic level toggle).
- Hireling availability follows sex-based labour rules. Metropolises add specialist hirelings (sages, translators, foreign mercenaries, master artisans).

### P. Guilds
| Trade | Guild? | Sex restriction | Political power |
|---|---|---|---|
| Smiths, masons, carpenters | yes | male | high |
| Weavers, brewers | yes (often mixed) | mixed | medium |
| Mercers, vintners | yes | male | high |
| Chandlers, laundresses | no formal guild | female | low |
| Scribes, apothecaries | yes | male | medium |

Fees: 1–5 gp entry, 1–10 sp monthly. Membership gates establishment rights and price floors. Thorpes: none. Destitute: suspended or powerless. Metropolis: great guilds with national charters, political representation, internal hierarchy (master → warden → guildmaster).

### Q. Watch and Militia
- Watch size ≈ population / 100, ×2 in towns, ×3 in cities, ×4 in metropolises.
- Watch: Warrior 1–3, chain shirt, club or spear, lantern, whistle. Pay 2 sp/day.
- Militia: 1 in 4 able-bodied adult males. Poor = spear + leather; rich = spear + shield + leather.
- Jurisdiction: watch inside walls, militia outside, sheriff commands both.
- Thorpe: no watch; adult residents form an ad hoc levy.
- Destitute: no paid watch; militia unpaid, under-equipped, half-strength.
- Metropolis: organised watch companies, permanent city garrison, harbour watch (if coastal/riverine), gate wards, each with captains and lieutenants.

### R. Haggling
Contested check: proprietor Diplomacy or Intimidate vs buyer Diplomacy or Appraise.
- Buyer wins by 10+: 10% discount
- Buyer wins by 5–9: 5% discount
- Tie: list price
- Proprietor wins by 5–9: 5% markup
- Proprietor wins by 10+: 10% markup

Modifiers: reputation, guild price floors, scarcity, relationship. Destitute: sellers may accept goods in kind at 50% value. Metropolis: haggling more impersonal; guild price floors stronger; reputation matters more than relationship.

### S. Wealth Distribution
- Bottom 60% of households: 20% of wealth
- Middle 30%: 35%
- Top 10%: 45%
Within each band, log-normal σ = 0.8, scaled by wealth tier and profession income. Destitute: top band shifted down, distribution compressed toward subsistence, higher share at zero. Metropolis: bottom 60% = 15%, middle 30% = 30%, top 10% = 55%, with a small ultra-wealthy elite.

### T. Clannishness
Dwarves > elves > gnomes > halflings > humans. Clan share, reputation, and influence on naming, patron deity, profession bias, and marriage scale accordingly. Orcs and border humans also cluster. Metropolis fragments clans into neighbourhoods and guilds, reducing clannishness by one step. Clans dominating an export trade (dwarven metal, halfling pipe-weed, elven bows) gain outsized political weight.

### U. Toggles
| Toggle | Effect |
|---|---|
| Magic level | low/normal/high; shifts caster availability, item supply, spell ceiling |
| Law level | low/normal/high; shifts watch size, fines, guild power, rogue presence |
| Trade route | none/minor/major; shifts imports, exports, prices, wealth |
| Monster threat | low/normal/high; shifts castle chance, levy, watch, adventurers |

### V. Household Production
Track `householdProduction` per household. Value brewing, spinning, dairying, and victualling at SRD craft rates × hours per week. Include child labour from ~age 7. Contributes to household income, taxable wealth, and supply-chain inputs (ale, cloth, cheese, bread). Mainstay in thorpes and destitute settlements; largely displaced by workshops and guild production in metropolises but persists in poor quarters.

### W. Half-Race Upbringing
`upbringing` = weighted choice: 60% majority household race, 30% clan race, 10% settlement race. Determines naming convention, faith inheritance, profession propensity. Half-races may use either parent race's override, chosen by upbringing.

### X. Magic Item Prerequisites
Before offering a commission, verify: crafter has feat, required spell known/prepared, caster level ≥ item CL, establishment has tools, materials available via supply chain, settlement magic level permits.

### Y. Toggle Independence
Toggles modify generation but never break determinism. Changes re-derive dependent outputs from the same seed.

### Z. Exports of Surplus
Surplus is what remains after local demand, seed stock, and defense stores are satisfied.

`surplus(good) = localProduction − localDemand − seedStock − defenseStores`

Local demand includes household consumption, establishment inputs, and government/defense needs. Seed stock is a reserve proportional to size and threat level.

**Export capacity by size:**
| Size | Capacity | Notes |
|---|---|---|
| Thorpe | negligible | Pedlars or nearby market only; one or two goods |
| Hamlet | low | Local fair, occasional caravan |
| Village | low–medium | Weekly market, pedlar traffic |
| Small town | medium | Regional market, merchant guild |
| Large town | medium–high | Multiple routes, warehousing |
| City | high | Trade hub, foreign merchants |
| Metropolis | very high | Aggregates and re-exports surrounding settlements |

Modify by trade access: coast ×1.5, river ×1.3, major road ×1.0, minor road ×0.7, isolated ×0.3.

**Wholesale price:** `local retail × export factor` (0.5–0.8, worse access = worse terms). Wholesale always below local retail; the margin funds transport, risk, and merchant profit.

**Export income split:** 60–75% to producing households and establishments; 10–20% to merchant/transporter; 5–10% guild fees; 5–10% taxes and tithes; remainder lost to spoilage, tolls, shrinkage.

**External demand:** specified per settlement by context. Mining exports ore and imports grain; farming exports grain and imports iron; coastal metropolis exports manufactures and imports raw materials. Premiums swing ±30% with events.

**Strategic controls:** by law level and war/siege risk, the lord may forbid export of grain, weapons, horses, or naval stores. Forbidden exports become smuggling or black-market trade.

**Unsold surplus:** becomes stock, spoils at a rate set by the good (grain fast, metal not), or is dumped locally, depressing local prices.

**Special cases:**
- Thorpe: minimal surplus, exported via pedlars or nearby fairs. May specialise in one good (charcoal, wool, fish); no merchant class.
- Destitute: no surplus; may export assets (livestock, tools, heirlooms) at distress prices (50% wholesale). One-way drain until recovery.
- Metropolis: aggregates surrounding surplus, re-exports finished goods, hosts foreign merchants, sets regional prices. Export capacity not limited to own production.

**Export income concentrates in merchant households.** Thriving export trade raises the merchant share and widens wealth spread; blocked trade compresses it and pushes artisans toward destitution.

## JSON Schema
All output is a single JSON document. No CSV, no Markdown, no other serialisation format.

{
"seed": string,
"inputs": { size, terrain, wealth, racialMakeup, rulingRaces, toggles },
"settlement": {
"context": {...},
"size": string,
"wealth": string,
"recentEvents": [...],
"recoveryState": {...},
"districts": [...] // metropolis only
},
"population": {...},
"racialBreakdown": [...],
"sexDistribution": {...},
"ageBands": {...},
"labourPool": {...},
"households": [ { id, members, wealth, profession, dependents, householdProduction, supplyChainIds } ],
"families": [...],
"clans": [...],
"dependencyGraph": {...},
"faith": {...},
"alignment": {...},
"namingProfile": {...},
"socialClass": {...},
"government": { offices, officials, law, charters },
"lawLevel": string,
"guildCharters": [...],
"watchMandate": {...},
"resourceBase": {...},
"imports": [...],
"exports": [...],
"initialDemand": {...},
"supplyChainStructure": {...},
"professions": [...],
"labourAllocation": {...},
"governmentOfficials": [...],
"establishments": [ { id, type, name, ownerId, race, sex, class, level, inventory, services, prices, supplyChainIds, stats, srdRef } ],
"proprietors": [...],
"defenses": { garrison, levy, equipment, upkeep, siegeStores },
"levies": [...],
"siegeStores": {...},
"prices": {...},
"stock": {...},
"coffers": {...},
"taxes": {...},
"upkeep": {...},
"supplyChainState": {...},
"npcStats": [ { id, name, race, sex, class, level, profession, faith, alignment, stats, equipment, dailyIncome, haggleStats, srdRef } ],
"equipment": {...},
"dailyIncome": {...},
"haggleStats": {...},
"serviceCatalog": {...},
"hirelingCosts": {...},
"itemCreationCosts": {...},
"religion": [ { id, deity, structure, clergy, buildings, services } ],
"uiState": {...}
}


Common fields on every entity: `id`, `type`, `name`, `race`, `sex`, `tags`, `location`, `ownerId`, `srdRef`.
- **Household:** `members`, `wealth`, `profession`, `dependents`, `householdProduction`, `supplyChainIds`
- **NPC:** `class`, `level`, `profession`, `faith`, `alignment`, `stats`, `equipment`
- **Establishment:** `inventory`, `services`, `prices`, `supplyChainIds`
- **Defense:** `garrison`, `levy`, `equipment`, `upkeep`, `siegeStores`
- **Religion:** `deity`, `structure`, `clergy`, `buildings`, `services`
- **Government:** `offices`, `officials`, `law`, `charters`
- **Settlement:** `size`, `wealth`, `recentEvents`, `recoveryState`, `districts` (metropolis only)

JSON must be stable, pretty-printable, and directly consumable by other tools. No trailing prose, no mixed formats.

## Renaming Rule
Keep SRD class, spell, magic item, and magical names verbatim. Rename only mundane items, goods, services, and professions to medieval English equivalents based on description (e.g., longsword → arming sword, chain shirt → haubergeon, hemp rope → hempen rope, inn → hostelry). Keep the SRD name in hidden `srdRef`.

## UI
Single-screen establishment view:
┌────────────────────┬─────────────────────────────┐
│ Proprietor card │ Tabs: │
│ Name, race, sex │ [Inventory][Services] │
│ Class, level │ [Haggle][Hire] │
│ Stat block │ [Spellcasting][Crafting] │
│ Feats, skills │ Shared cart/session state │
└────────────────────┴─────────────────────────────┘

Tabs share a session cart: buy items, hire NPCs, commission spells, commission items, negotiate price — all against the same proprietor. Flavour text varies; never repeats base data. Destitute establishments may show damage, depleted stock, or barter-only trade. Thorpes show no establishment screen for absent trades. Metropolises add a district filter and directory view by trade.

Export and copy actions produce JSON only. Copy buttons copy the JSON document or a JSON subtree. No CSV, no Markdown, no other serialisation.

## Acceptance Criteria
- Same seed + same inputs = same settlement.
- Population sums match racial makeup input.
- No phase requires backtracking.
- Sex-based labour division hard-coded and enforced, with widow and racial exception rules.
- Class and profession are separate attributes for every NPC.
- Faith derived from race → clan → alignment.
- Each deity has a distinct church structure and clergy nomenclature.
- SRD class, spell, magic item names preserved.
- Defense equipment, upkeep, fortifications, siege stores are part of the economy.
- Establishment screen combines stats, hiring, buying, haggling, spell/item commissioning.
- Import and export flows vary by wealth, location, and external demand.
- Exports of surplus fund imports; trade balance is explicit.
- Supply chains connect logically and affect prices and availability.
- **All output and export is JSON only. No CSV, no Markdown, no other serialisation.**
- No non-SRD D&D content required.
- Generated text never names England or real historical places.
- UI pleasant, searchable, non-repetitive.
- Separate RNG streams preserve determinism when phases are added.
- Thorpes generate without market, guild, watch, or permanent clergy unless a shrine-keeper is present.
- Destitute settlements reflect recent looting: damaged establishments, depleted stores, halved defenses, broken trade, barter economy, recovery trajectory over subsequent ticks.
- Metropolises generate districts, grand temples or cathedrals, a university or scholarly college, national guilds, a permanent garrison, multiple watch companies, foreign quarters, and a wider wealth spread; clans fragment into neighbourhoods and guilds.

## Deliverables
- Working web app or generator script.
- Source code with README.
- JSON schema for all entities.
- Sample seeds and JSON outputs.
- Tests for determinism, population sums, stat block validity, sex-labour enforcement, phase dependency order, JSON schema conformance, trade balance, thorpe generation, metropolis district generation, and destitute recovery.

If a rule is ambiguous, choose a consistent 3.5-compatible approximation, document it, and keep the simulation coherent.
