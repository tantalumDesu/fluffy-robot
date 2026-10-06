## Inputs
- Size: **thorpe**, hamlet, village, small town, large town, city, **metropolis**
- Terrain/location: river, coast, road, forest, mountain, border, farmland, etc.
- Wealth: **destitute**, poor, modest, prosperous, rich
- Racial makeup: percentage per race (humans, elves, dwarves, halflings, gnomes, half-elves, half-orcs, orcs, etc.)
- Ruling race(s): optional
- Seed: required
- Toggles: magic level, law level, trade route, monster threat, castle chance

**Destitute** represents a settlement recently looted, razed, or stripped by war, raid, or disaster. It implies a recent catastrophic event flag, damaged or destroyed establishments, depleted stores, disrupted supply chains, unpaid levies, and a depleted or absent ruling class. It is not merely poorer than poor — it is a settlement in shock.

**Thorpe** is smaller than a hamlet: a few households, often a single extended family or a small cluster of farmsteads, with no formal market, no guild, and no permanent clergy unless a shrine or itinerant priest serves the area.

**Metropolis** is larger than a city: a great capital or trade hub with a population in the tens of thousands, multiple districts, a cathedral or grand temple complex, a university or scholarly institution, a permanent garrison, foreign quarters, and guilds of national importance. It draws immigrants, luxuries, and specialists from far beyond its region.

## Core Principles
1. Population first. Households, clans, races, sexes, ages before anything else.
2. Dependency-first order. Each phase consumes only earlier outputs. No backtracking, no rewriting.
3. Two-pass economy. Pass 1 sets resources, trade, demand, supply-chain structure. Pass 2 simulates prices, stock, wages, taxes, upkeep, coffers.
4. Stochastic but consistent. Weighted tables, coherent sums and supply chains.
5. SRD 3.5 mechanics. Classes, levels, feats, skills, equipment, prices, stat blocks.
6. Medieval English flavour without naming England. Anglo-Saxon, Norman, guild, manor, parish aesthetics for mundane things.
7. Race affects profession propensity. Dwarven smith in a human village; elven fletcher in a dwarven village; and so on.
8. Single-screen establishment interaction. Proprietor stats, hiring, buying, haggling, spell commissioning, item commissioning all on one screen.
9. Integrated defense economy. Equipment, upkeep, fortifications, siege stores, levies flow through the economy.
10. Entity graph. Stable `id`, `type`, `tags`. Phases append fields.
11. Separate RNG streams. `seed + phase + entityId` so adding phases preserves determinism.
12. Lazy naming and UI. Names generated when identity is complete. UI renders summaries first.
13. Exportable and filterable. JSON for everything.

## Order of Operations
1. **Inputs & Seed** — accept inputs, establish RNG streams.
2. **Physical & External Context** — trade access, resource base, climate, isolation, threat level. Outputs: `settlement.context`, `tradeRoutes`, `externalDemand`, `threatLevel`.
3. **Demographics** — medieval priors (Table A). Outputs: `population`, `racialBreakdown`, `sexDistribution`, `ageBands`, `labourPool`.
4. **Kinship & Households** — households, multigenerational families, clans, dependents, servants, apprentices. Outputs: `households`, `families`, `clans`, `dependencyGraph`.
5. **Culture & Identity** — alignment, faith (race → clan → alignment), naming profile, social class. Naming is callable, not a phase. Outputs: `faith`, `alignment`, `namingProfile`, `socialClass`.
6. **Power & Law** — government, ruling race(s), guild charters, watch mandate, legal restrictions, class-conscious titles. Outputs: `government`, `lawLevel`, `guildCharters`, `watchMandate`.
7. **Economic Skeleton (Pass 1)** — resource base, external trade scaled by wealth and location, initial demand, supply-chain structure. Outputs: `resourceBase`, `imports`, `exports`, `initialDemand`, `supplyChainStructure`.
8. **Labour & Professions** — assign professions using hard-coded sex division, racial propensity, faith, economy. Fill government offices. Outputs: `professions`, `labourAllocation`, `governmentOfficials`.
9. **Establishments** — derived from professions and supply-chain needs; varied names referencing settlement, geography, patron, monster, heraldry, or family. Each with named proprietor (race, sex, class, level, stats). Outputs: `establishments`, `proprietors`, `inventory`, `services`.
10. **Defense & Levies** — walls, gates, towers, ditches, palisades, castle chance, garrison, levy size, training, equipment quality, morale, siege stores. Outputs: `defenses`, `levies`, `garrison`, `siegeStores`.
11. **Economy Simulation (Pass 2)** — supply chains, prices, stock, demand, wages, taxes, tithes, guild fees, household production, child labour, defense upkeep, siege stores, coffers. Daily/weekly ticks. Events (Table N). Effects ripple to family coffers, merchant profits, guard equipment, lord's treasury, poor relief, public works. Outputs: `prices`, `stock`, `coffers`, `taxes`, `upkeep`, `supplyChainState`.
12. **NPCs & Proprietors** — 3.5 stat blocks from class/level/race/sex/faith/alignment; equipped using final economy wealth. Outputs: `npcStats`, `equipment`, `dailyIncome`, `haggleStats`.
13. **Services & Costs** — hirelings, spellcasting, magic item creation, establishment services (SRD formulas). Outputs: `serviceCatalog`, `hirelingCosts`, `itemCreationCosts`.
14. **UI & Exports** — responsive UI, seed control, sliders, tabs (Overview, Population, Households, Professions, Establishments, NPCs, Government, Defense, Religion, Economy, Exports), filters, search, tooltips. Flavour text varies; never repeats base data. Outputs: `json`, `uiState`.

## Rules & Tables

### Table A: Demographic Priors
- Mean household size 4.5 (range 3–8)
- Age: 0–14 = 35%, 15–44 = 45%, 45–64 = 15%, 65+ = 5%
- Infant mortality 25% before age 5
- Birth sex ratio 105 M : 100 F; adult 98 M : 100 F
- Child labour counted as economically productive from ~age 7

### Table B: Class vs Profession
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

### Table C: Class Levels by Settlement Type
| Role | Class | Thorpe | Hamlet | Village | Small town | Large town | City | Metropolis |
|---|---|---|---|---|---|---|---|---|
| Common labourer | Commoner | 1 | 1 | 1–2 | 1–3 | 1–3 | 1–4 | 1–5 |
| Skilled tradesman | Expert | 2–3 | 2–4 | 2–5 | 3–6 | 4–7 | 5–8 | 6–10 |
| Guild master | Expert | — | — | 4–6 | 5–7 | 6–9 | 8–11 | 10–14 |
| Watchman | Warrior | — | 1 | 1–2 | 1–3 | 2–4 | 2–5 | 3–6 |
| Man-at-arms | Fighter | — | — | 2–3 | 2–4 | 3–5 | 4–6 | 5–8 |
| Knight | Fighter/Aristocrat | — | — | 3–5 | 4–6 | 5–7 | 6–9 | 8–12 |
| Parish priest | Cleric/Adept | 1–2 | 2 | 2–3 | 3–4 | 4–5 | 5–7 | 6–9 |
| Bishop/Archbishop | Cleric | — | — | — | 6–8 | 7–10 | 9–12 | 12–16 |
| Cunning man/woman | Adept/Wizard | 1–2 | 2 | 2–3 | 3–5 | 4–6 | 5–8 | 7–11 |
| Lord/lady | Aristocrat | — | 5 | 6–7 | 7–9 | 8–11 | 10–14 | 13–18 |
| Castle captain | Fighter | — | — | 4–6 | 6–8 | 7–9 | 9–12 | 12–16 |

A thorpe has no permanent watch, no man-at-arms, no knight, no guild master, and no lord or lady resident. Any clergy is itinerant or a single shrine-keeper.
A metropolis has multiple watch companies, multiple knightly orders or noble households, a permanent garrison, an archbishop or equivalent, a university or scholarly college, and guilds of national importance. Level ranges rise by 1 in a metropolis above city baseline. Level ranges drop by 1 in destitute settlements (minimum 1).

### Table D: Alignment
Base: Good 55%, Neutral 44%, Evil 1%.

Law/chaos by race/clan:
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

Wealth modifier: middle wealth bands grant a Good bonus; the destitute bend toward Evil; the very rich are neutral-to-Evil by self-interest. Profession modifier: clergy +Good, rogue/assassin +Evil. Clan reputation shifts alignment bias.

### Table E: Ability Scores, Feats, Skills, Equipment
- Ability scores: 4d6 drop lowest for everyone. PC classes assign highest rolls to preferred stats; NPC classes assign in order.
- Feats: 1 at level 1, then every 3 levels. Priors: Skill Focus (profession), Negotiator (merchants), Persuasive (innkeepers), Power Attack (warriors), Weapon Focus (soldiers), Brew Potion / Craft Magic Arms and Armor / Craft Wondrous Item (spellcasters).
- Skill ranks: `(class skill points + Int mod) × (level + 3)`, max rank = level + 3. Prioritise profession skills first, then class skills. Emphasise Appraise, Bluff, Diplomacy, Gather Information, Intimidate, Sense Motive, Profession, relevant Craft.
- Equipment: NPC wealth by level (SRD DMG Table 4-23) × settlement wealth tier: destitute ×0.25, poor ×0.5, modest ×1, prosperous ×1.5, rich ×2.

### Table F: Pantheon
Use the classic Forgotten Realms pantheon. Settlements shun evil gods in public worship; evil deities are still worshipped covertly. Each deity has a distinct church structure:
- Sun deity (Lathander/Pelor): parishes, bishops, archdeacons, monasteries, tithes, canon law.
- Nature deity (Mielikki/Silvanus): druidic circles, grove-tenders, mixed sexes, no fixed hierarchy.
- War deity (Tyr/Helm): militant orders, grandmaster → knight-captain → brother/sister-at-arms, male-dominated.
- Trickster (Tymora/Olidammara): secret societies, cell structure, mixed.
- Death deity (Kelemvor/Wee Jas): funerary guilds, arch-funerary → mortician → acolyte, mixed.
- Craft deity (Moradin for dwarves, Gond for gnomes): guild-temple hybrid, master → journeyman → apprentice.
- Evil deities: covert shrines, no public buildings, clergy disguised or hidden.

Each church defines clergy titles, sex restrictions, celibacy, and available magical services. Metropolises may host a grand temple or cathedral for the dominant deity, plus significant temples to allied faiths and hidden shrines to forbidden ones.

### Table G: Social Class
| Class | Share | Markers |
|---|---|---|
| Gentry | 2–5% | titles, heraldry, elite names |
| Clergy | 3–8% | rank titles, vestments |
| Merchants/guild | 8–15% | occupational surnames, fees |
| Artisans | 15–25% | guild membership, trade names |
| Free peasantry | 40–55% | yeoman, goodman, goodwife |
| Unfree/servile | 10–20% | no surname, obligatory labour |
| Outcasts | 1–3% | no guild, no parish standing |

In destitute settlements, gentry may be absent, dead, or fled; the unfree and outcast shares rise; the artisan and merchant shares fall.
In metropolises, the merchant/guild share rises, a small scholarly and bureaucratic class emerges, and foreign quarters may exist as distinct social enclaves.

Class affects naming, profession ceiling, wealth, marriage.

### Table H: Hard-Coded Sex-Based Division of Labour
Not optional, not randomised. Baseline approximates medieval English practice. Precedence: baseline → racial override → widow/heiress exception → mixed/flexible fallback.

**Male-dominated (≥80% male):** ploughman, husbandman, yeoman farmer; smith (blacksmith, farrier, armourer); carpenter, joiner, cooper, wheelwright; mason, thatcher, tiler; tanner, butcher, slaughterer; miller, master baker; deep-water fisherman, sailor, ferryman; carter, waggoner, drover; miner, quarryman; soldier, man-at-arms, watchman, gatekeeper; sheriff, reeve, constable, bailiff; scribe, clerk, notary (where literacy is male-dominated); alchemist, apothecary (master); wizard, sorcerer, warlock (unless race/culture says otherwise); fletcher, bowyer (unless elven, where mixed).

**Female-dominated (≥80% female):** alewife, brewster, innkeeper (victualling); spinner, weaver, seamstress, embroiderer; dairywoman, cheesemaker, butter-maker; midwife, wise woman, herbalist; poultry keeper, goose girl; laundress, washerwoman; nurse, wet-nurse, domestic servant; market woman, huckster, regrater; domestic baker, household cook; clothier, draper (shop-front); domestic candle-maker; charm-seller, petty diviner; cleric, druid, adept (where the deity's church permits).

**Mixed / flexible (20–80%):** smallholding farmer, gardener, orchard-keeper; merchant, shopkeeper, pedlar; innkeeper, taverner, hostelry keeper; healer, physician, chirurgeon; scribe (where female religious houses exist); cleric, druid, monk (varies by deity and order); bard, minstrel, entertainer; rogue, thief, cutpurse; fletcher, bowyer (especially elven); potter, glassmaker, jeweller (varies by guild); teacher, tutor, scholar.

**Widow/heiress exception:** a widow or heiress may inherit and operate her husband's/father's trade, guild membership, and establishment as a full proprietor. Social penalties may apply in restrictive guilds. Daughters inherit in the absence of sons.

**Racial overrides:** dwarven women may smith and work stone openly; elven women may fletch, bowyer, and practise magic openly; halfling women may innkeep, farm, and handle pipe-weed openly; gnome women may tinker, alchemise, and cut gems openly; orc women may butcher, raid, and mercenary openly.

**Enforcement:** labour engine checks sex against tables before assignment; establishments reflect proprietor sex unless exception applies; household composition reflects division; women's unwaged work modelled as household production (Table V). Metropolises may host female religious houses, women's guilds, and larger communities of widows operating trades, softening enforcement at the margins but not overriding the baseline.

### Table I: Faith Derivation
Faith = race pantheon → clan patron → alignment-compatible deity. Half-race upbringing (Table W) determines which parent's pantheon applies.

### Table J: Naming
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
- Metropolises include foreign quarters with names drawn from the appropriate parent cultures

### Table K: Defense, Levy, Castle
Use historical data as baseline, exaggerated for a world of inhuman monsters.
| Size | Wall | Castle chance | Garrison | Levy | Siege stores |
|---|---|---|---|---|---|
| Thorpe | none or ditch | 0% | — | 0–5 | 1 day |
| Hamlet | ditch/palisade | 2% | — | 10–30 | 3 days |
| Village | palisade | 5% | 5–15 | 30–80 | 7 days |
| Small town | stone wall + gates | 15% | 20–60 | 80–200 | 14 days |
| Large town | stone wall + towers | 40% | 60–150 | 200–500 | 30 days |
| City | curtain wall + keep | 70% | 150–500 | 500–2000 | 60 days |
| Metropolis | multiple walls, citadel, harbour chain | 90% | 500–2000 | 2000–8000 | 90–180 days |

Modifiers: +10% castle chance on border or high monster threat; +10% if rich. Destitute settlements have walls and stores reduced by 50%, garrison halved, and levy halved until the next harvest or event tick restores them.
Upkeep: 1 gp per soldier per day; 5% of fortification value per year.
Siege stores: food, arrows (1,000 per 100 archers per day of siege), fuel, pitch, stone. Metropolises maintain multiple store depots and naval supply where applicable.

### Table L: Religious Buildings
Use historical population-to-church ratios, adjusted for deity distribution.
- Thorpe (<30): no building; a shrine stone, wayside cross, or itinerant priest visits.
- <100: 1 shrine
- 100–500: 1–2 shrines, 1 chapel
- 500–2,000: 2–4 shrines, 1–3 chapels, 1–2 churches
- 2,000–10,000: 4–8 shrines, 3–6 chapels, 2–4 churches, 1–2 temples, 1–3 monasteries
- 10,000–50,000 (city): 8+ shrines, 6+ chapels, 4+ churches, 2+ temples, 3+ monasteries, 1 cathedral
- 50,000+ (metropolis): 15+ shrines, 10+ chapels, 8+ churches, 4+ temples, 5+ monasteries, 1 grand cathedral, 1+ university or scholarly college, foreign temples

Distribution follows faith demographics. The sun deity holds the parish church; minority gods hold shrines or shared temples; evil gods hold covert shrines only. In destitute settlements, one religious building may be damaged, desecrated, or abandoned.

### Table M: Supply Chains
Each establishment declares inputs and outputs. Examples:
- Smithy: iron ingot + charcoal → tools, weapons, nails
- Bowyer: yew stave + sinew → bows
- Fletcher: shafts + feathers + heads → arrows
- Miller: grain → flour
- Baker: flour + yeast + fuel → bread
- Tanner: hides + tannin → leather
- Weaver: wool → cloth
- Apothecary: herbs + glass + alcohol → remedies

External trade scaled by wealth and location:
| Wealth | Import multiplier | Luxury share |
|---|---|---|
| Destitute | 0.1× | 0% |
| Poor | 0.5× | 5% |
| Modest | 1× | 10% |
| Prosperous | 1.5× | 20% |
| Rich | 2.5× | 35% |

| Location | Trade access | Import cost |
|---|---|---|
| Coast | high | ×0.8 |
| River | high | ×0.9 |
| Major road | medium | ×1.0 |
| Minor road | low | ×1.2 |
| Isolated | very low | ×1.5 |

A thorpe has no market; trade occurs through pedlars, fairs, or a nearby larger settlement. Destitute settlements have broken supply chains and depend on relief, foraging, and barter until restored. A metropolis is a regional trade hub: import multiplier ×1.5 above its wealth tier, luxury share doubled, and it supplies surrounding settlements as an export node.

### Table N: Events
| Event | Frequency | Effect |
|---|---|---|
| Harvest | 1 per agrarian settlement per season | +20% grain, −10% bread |
| Fair | 1 per town per season | +30% trade volume for 1 week |
| Banditry | 10% per season on trade routes | −20% imports, +levy cost |
| Monster raid | 5–25% by threat | −stock, +defense spend |
| Plague | 2–5% per season | −5–20% population, −trade. Metropolises: −5–25% population, severe trade disruption. |
| War | toggle/plot | +levy, +taxes, −imports |
| Trade disruption | 10% per season | +50% import cost |
| **Looting** | plot/toggle | Sets wealth to destitute; damages establishments, walls, stores; triggers recovery over subsequent ticks |
| **Fire** | 3% per season in towns and cities, 5% in metropolises | Damages or destroys 1–3 districts; −stock, −housing, +recovery cost |
| **Plague riot** | 10% during plague in cities and metropolises | +law level temporarily, −guild power, −trade |

### Table O: Services & Costs
Use SRD formulas exactly.
- Hireling: SRD daily rates (untrained 1 sp, trained 3 sp, skilled 5 sp–2 gp, spellcaster 1 gp × caster level per spell).
- Spellcasting: `caster level × spell level × 10 gp`.
- Magic item creation: SRD formulas; require crafter prerequisites (feat, spell, caster level, appropriate establishment — Table X). Cost = half market price in materials; time = 1 day per 1,000 gp market price.
- Spell level ceiling by settlement: thorpe 1, hamlet 2, village 3, small town 5, large town 7, city 9, metropolis 9+ (with multiple high-level casters; modified by magic level toggle).
- Hireling availability follows sex-based labour rules. Metropolises have specialist hirelings (sages, translators, foreign mercenaries, master artisans) unavailable elsewhere.

### Table P: Guilds
| Trade | Guild? | Sex restriction | Political power |
|---|---|---|---|
| Smiths, masons, carpenters | yes | male | high |
| Weavers, brewers | yes (often mixed) | mixed | medium |
| Mercers, vintners | yes | male | high |
| Chandlers, laundresses | no formal guild | female | low |
| Scribes, apothecaries | yes | male | medium |

Fees: 1–5 gp entry, 1–10 sp monthly. Membership gates establishment rights and price floors. Thorpes have no guilds. Destitute settlements have suspended or powerless guilds. Metropolises have great guilds with national charters, political representation, and internal hierarchies (master → warden → guildmaster).

### Table Q: Watch and Militia
Use historical data.
- Watch size ≈ population / 100, ×2 in towns, ×3 in cities, ×4 in metropolises.
- Watch: Warrior 1–3, chain shirt, club or spear, lantern, whistle. Pay 2 sp/day.
- Militia: 1 in 4 able-bodied adult males. Poor = spear + leather; rich = spear + shield + leather.
- Jurisdiction: watch inside walls, militia outside, sheriff commands both.
- Thorpes have no watch; adult residents form an ad hoc levy.
- Destitute settlements have no paid watch; militia is unpaid, under-equipped, and half-strength.
- Metropolises have organised watch companies, a permanent city garrison, a harbour watch (if coastal or riverine), and gate wards, each with captains and lieutenants.

### Table R: Haggling
Contested check: proprietor Diplomacy or Intimidate vs buyer Diplomacy or Appraise.
- Buyer wins by 10+: 10% discount
- Buyer wins by 5–9: 5% discount
- Tie: list price
- Proprietor wins by 5–9: 5% markup
- Proprietor wins by 10+: 10% markup
Modifiers: reputation, guild price floors, scarcity, relationship. In destitute settlements, sellers may accept goods in kind at 50% value. In metropolises, haggling is more impersonal: guild price floors are stronger, and reputation matters more than relationship.

### Table S: Wealth Distribution
- Bottom 60% of households: 20% of wealth
- Middle 30%: 35%
- Top 10%: 45%
Within each band, log-normal σ = 0.8, scaled by wealth tier and profession income. Destitute settlements shift the top band down and compress the distribution toward subsistence, with a higher share at zero. Metropolises have a wider spread: bottom 60% = 15%, middle 30% = 30%, top 10% = 55%, with a small ultra-wealthy elite.

### Table T: Clannishness
Dwarves > elves > gnomes > halflings > humans. Clan share of population, clan reputation, and clan influence on naming, patron deity, profession bias, and marriage scale accordingly. Orcs and border humans also cluster. Metropolises fragment clans into neighbourhoods and guilds, reducing clannishness by one step.

### Table U: Toggles
| Toggle | Effect |
|---|---|
| Magic level | low/normal/high; shifts caster availability, item supply, spell ceiling |
| Law level | low/normal/high; shifts watch size, fines, guild power, rogue presence |
| Trade route | none/minor/major; shifts imports, prices, wealth |
| Monster threat | low/normal/high; shifts castle chance, levy, watch, adventurers |

### Table V: Household Production
Track `householdProduction` per household. Value brewing, spinning, dairying, and victualling at SRD craft rates × hours per week. Include child labour from ~age 7. Contributes to household income, taxable wealth, and supply-chain inputs (ale, cloth, cheese, bread). In thorpes and destitute settlements, household production is the mainstay of the economy. In metropolises, it is largely displaced by workshops and guild production, but persists in poor quarters.

### Table W: Half-Race Upbringing
`upbringing` = weighted choice: 60% majority household race, 30% clan race, 10% settlement race. Upbringing determines naming convention, faith inheritance, and profession propensity. Half-races may use either parent race's override, chosen by upbringing.

### Table X: Magic Item Prerequisites
Before offering a commission, verify: crafter has feat, required spell known/prepared, caster level ≥ item CL, establishment has tools, materials available via supply chain, settlement magic level permits.

### Table Y: Toggle Independence
Toggles modify generation but never break determinism. Changes to toggles re-derive dependent outputs from the same seed.

## Entity Data Model
Common fields: `id`, `type`, `name`, `race`, `sex`, `tags`, `location`, `ownerId`, `srdRef`.
Type-specific:
- Household: `members`, `wealth`, `profession`, `dependents`, `householdProduction`, `supplyChainIds`
- NPC: `class`, `level`, `profession`, `faith`, `alignment`, `stats`, `equipment`
- Establishment: `inventory`, `services`, `prices`, `supplyChainIds`
- Defense: `garrison`, `levy`, `equipment`, `upkeep`, `siegeStores`
- Religion: `deity`, `structure`, `clergy`, `buildings`, `services`
- Government: `offices`, `officials`, `law`, `charters`
- Settlement: `size`, `wealth`, `recentEvents`, `recoveryState`, `districts` (metropolis only)

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

Tabs share a session cart: buy items, hire NPCs, commission spells, commission items, negotiate price — all against the same proprietor. Flavour text varies; never repeats base data. Destitute establishments may show damage, depleted stock, or barter-only trade. Thorpes show no establishment screen for absent trades. Metropolises add a district filter and a directory view of establishments by trade.

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
- External trade inputs vary by wealth and location.
- Supply chains connect logically and affect prices and availability.
- Exports valid JSON, easy to filter.
- No non-SRD D&D content required.
- Generated text never names England or real historical places.
- UI pleasant, searchable, non-repetitive.
- Separate RNG streams preserve determinism when phases are added.
- Thorpes generate without market, guild, watch, or permanent clergy unless a shrine-keeper is present.
- Destitute settlements reflect recent looting: damaged establishments, depleted stores, halved defenses, broken trade, barter economy, and a recovery trajectory over subsequent event ticks.
- Metropolises generate districts, grand temples or cathedrals, a university or scholarly college, national guilds, a permanent garrison, multiple watch companies, foreign quarters, and a wider wealth spread; clans fragment into neighbourhoods and guilds.

## Deliverables
- Working web app or generator script.
- Source code with README.
- JSON schema for all entities.
- Sample seeds and outputs.Tabs share a session cart: buy items, hire NPCs, commission spells, commission items, negotiate price — all against the same proprietor. Flavour text varies; never repeats base data. Destitute establishments may show damage, depleted stock, or barter-only trade. Thorpes show no establishment screen for absent trades. Metropolises add a district filter and a directory view of establishments by trade.

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
- External trade inputs vary by wealth and location.
- Supply chains connect logically and affect prices and availability.
- Exports valid JSON, easy to filter.
- No non-SRD D&D content required.
- Generated text never names England or real historical places.
- UI pleasant, searchable, non-repetitive.
- Separate RNG streams preserve determinism when phases are added.
- Thorpes generate without market, guild, watch, or permanent clergy unless a shrine-keeper is present.
- Destitute settlements reflect recent looting: damaged establishments, depleted stores, halved defenses, broken trade, barter economy, and a recovery trajectory over subsequent event ticks.
- Metropolises generate districts, grand temples or cathedrals, a university or scholarly college, national guilds, a permanent garrison, multiple watch companies, foreign quarters, and a wider wealth spread; clans fragment into neighbourhoods and guilds.

## Deliverables
- Working web app or generator script.
- Source code with README.
- JSON schema for all entities.
- Sample seeds and outputs.
- Tests for determinism, population sums, stat block validity, sex-labour enforcement, phase dependency order, export parsing, thorpe generation, metropolis district generation, and destitute recovery.

If a rule is ambiguous, choose a consistent 3.5-compatible approximation, document it, and keep the simulation coherent.
- Tests for determinism, population sums, stat block validity, sex-labour enforcement, phase dependency order, export parsing, thorpe generation, metropolis district generation, and destitute recovery.

If a rule is ambiguous, choose a consistent 3.5-compatible approximation, document it, and keep the simulation coherent.
