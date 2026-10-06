SETTLEMENT GENERATOR SPECIFICATION (PATCHED, v3)
================================================

Skeleton: SRD 3.5 mechanics. Flavour: medieval English aesthetics without naming England, Forgotten Realms pantheon for deities.
Values marked "(approximation)" are not defined by the SRD or the original spec and belong in one constants file.
A Change Log is at the end.


INPUTS
------
- Size: thorpe, hamlet, village, small town, large town, city, metropolis
- Terrain: one or more tags from: farmland, forest, mountain, hills, marsh, coast, river; access tags: major road, minor road, isolated; modifier tag: border
- Wealth: destitute, poor, modest, prosperous, rich
- Racial makeup: percentage per race (must sum to 100)
- Ruling race(s): optional
- Seed: required
- Start season: optional, defaults to a value derived from the seed
- Toggles: magic level, law level, trade route, monster threat, castle chance, war, looting

Thorpe: smaller than a hamlet. A few households, often one extended family or a cluster of farmsteads. No market, guild, watch, or permanent clergy (a shrine-keeper or itinerant priest may visit).

Destitute: recently looted, razed, or stripped by war, raid, or disaster. Damaged establishments, depleted stores, broken supply chains, unpaid levies, absent ruling class. In shock, not merely poorer than poor. A destitute input means a looting event has already occurred at tick 0 and is recorded in recentEvents.

Metropolis: greater than a city. A capital or trade hub of 50,000 or more, multiple districts, a cathedral or grand temple complex, a university or scholarly college, a permanent garrison, foreign quarters, national guilds. Aggregates and re-exports surrounding settlements' surplus.


CORE PRINCIPLES
---------------
1. Population before everything except environment. Phase 2 sets environment only and creates no entities. Races, sexes, ages, households, clans come next.
2. Dependency-first order. No backtracking, no rewriting. Every entity is split into GENESIS fields (immutable once its phase completes) and STATE fields (mutable, owned by the simulation). Phase 11 and later ticks write only to state fields. Fields added by later phases are appended, never edited.
3. Two-pass economy. Pass 1 sets resources, trade, demand, supply-chain structure. Pass 2 simulates prices, stock, wages, taxes, upkeep, coffers.
4. SRD 3.5 skeleton: classes, levels, feats, skills, equipment, prices, spells, magic items, stat blocks. Setting flavour on top: Forgotten Realms deity names (with SRD domains mapped to them), medieval English naming and institutions.
5. Medieval English flavour without naming England. Anglo-Saxon, Norman, guild, manor, parish aesthetics for mundane things.
6. Race affects profession propensity. Dwarven smith in a human village; elven fletcher in a dwarven village.
7. Single-screen establishment interaction. Stats, hiring, buying, haggling, spell and item commissioning on one screen.
8. Integrated defense economy. Equipment, upkeep, fortifications, siege stores, levies flow through the economy.
9. Entity graph. Stable id, type, tags. Phases append fields. Entities reference each other by id only; each fact is stored in exactly one place.
10. Separate RNG streams. Every random draw is keyed: seed + phase + entityId. Draws that recur add a further component: tick for simulation, eventType + seasonIndex for events, attemptIndex for haggling. Naming is keyed on entityId, never on call order.
11. Lazy naming, lazy materialisation, lazy UI. Names are generated when identity is complete. Commoners are materialised on demand from their household id (see Scale). UI renders summaries first.
12. JSON for all application output. Every export, copy action, and interchange payload from the app is JSON. Documentation (README), tests, and source code are exempt. The schema deliverable is a real JSON Schema file.


SIZE AND POPULATION (Table AB)
------------------------------
  Thorpe        5-29
  Hamlet        30-99
  Village       100-500
  Small town    501-2,000
  Large town    2,001-10,000
  City          10,001-50,000
  Metropolis    50,001 and above

Exact population is drawn from the band by the seed, nudged by wealth and terrain, and may be overridden by a slider. Households approximate population / 4.5.


WEALTH TIERS (Table AA, single source of truth)
-----------------------------------------------
  Tier         NPC gear x   Import x   Luxury share of import spend   Class level mod
  Destitute    0.25         0.1        0%                             -1 (min 1)
  Poor         0.5          0.5        5%                             0
  Modest       1            1          10%                            0
  Prosperous   1.5          1.5        20%                            0
  Rich         2            2.5        35%                            0

Every other table that scales by wealth refers to this table. Wealth distribution within a settlement is Table S.
The luxury share is a CAP on luxury import spend. Actual luxury imports = min(luxury demand from Tables AG, AE, and X, the cap).


ORDER OF OPERATIONS
-------------------
Each phase lists the fields it OWNS. A field has exactly one owning phase.

1. Inputs and Seed
   Establish RNG streams. Owns: seed, inputs, startSeason.

2. Physical and External Context
   Terrain tags, climate (cold, temperate, warm; seed-drawn, nudged by terrain), trade access (Table AC), isolation, threat, natural resource endowment (Table AF), external demand. Creates no entities.
   Owns: settlement.context, climate, tradeRoutes, resourceBase, externalDemand, threatLevel.

3. Demographics
   Table A and Table AB. Owns: population, racialBreakdown, sexDistribution, ageBands, labourPool.

4. Kinship and Households
   Households, multigenerational families, clans, dependents, servants, apprentices. Female-headed households follow Table H3.
   Owns (genesis): households.id, members, dependents, families, clans, dependencyGraph.
   Fields wealth, profession, householdProduction, supplyChainIds are APPENDED by phases 7, 8, 11.

5. Culture and Identity
   Alignment (birth alignment from race and clan only, Table D), faith (race -> clan -> alignment, Table F), naming profile, social class (Table G, with Table H3 for women).
   Owns: alignment, faith, namingProfile, socialClass.

6. Power and Law
   Government, ruling race(s), law level, watch mandate, and charter POLICY (which trades may form guilds, sex restrictions, fees). Guild charter INSTANCES are created in phase 9.
   Owns: government (offices, law, charterPolicy), lawLevel, watchMandate.

7. Economic Skeleton (Pass 1)
   Baseline import and export categories from the gap between resourceBase (phase 2) and what the population and social classes consume (Tables AE, AG). Luxury demand comes from Table AG and Table AE, is capped by the wealth tier luxury share (Table AA), and is supplied per trade route (Table AC). Per-establishment inputs are finalised in phase 9 and reconciled in phase 11.
   Owns: imports, exports, initialDemand, supplyChainStructure.

8. Labour and Professions
   Hard-coded sex division (Table H), racial propensity, faith, economy. Fill government offices.
   Owns: professions, labourAllocation, government.officials (by id).

9. Establishments
   Derived from professions and supply-chain needs (Table AE). Varied names referencing settlement, geography, patron, monster, heraldry, or family. Each has a proprietor id with race, sex, class, level assigned here. Stat blocks are filled in phase 12. Guild charter instances are created here.
   Owns: establishments, guildCharters.

10. Defense and Levies
    Walls, gates, towers, ditches, palisades, castle chance, garrison, levy size, training, equipment quality, morale, siege stores.
    Owns: defenses.

11. Economy Simulation (Pass 2)
    Supply chains, exports of surplus, prices, stock, wages, taxes, tithes, guild fees, household production, child labour, defense upkeep, coffers. Daily ticks, weekly aggregation, events rolled at season start (Table N). Effects ripple to family coffers, merchant profits, guard equipment, lord's treasury, poor relief, public works. All effects land in STATE fields only.
    Includes a 13-week warm-up before the first user-visible state (approximation); for destitute settlements warm-up starts from the post-looting state.
    Owns: prices, stock, coffers, taxes, upkeep, supplyChainState, tradeBalance, and all state fields.

12. NPCs and Proprietors
    SRD 3.5 stat blocks for notable NPCs only (see Scale). Equipped using final economy wealth. Each notable NPC receives a base disposition (Table R) and an alignment drift (Table D).
    Owns: npcs, stats, equipment, dailyIncome, haggleStats, baseDisposition.

13. Services and Costs
    Hirelings, spellcasting, item creation, establishment services (Table O).
    Owns: serviceCatalog.

14. UI and JSON Export
    Responsive UI, seed control, sliders, tabs, filters, search, tooltips. App output is a single JSON document. Flavour text varies and never repeats base data.


RULES AND TABLES
================

A. Demographic Priors
---------------------
Mean household 4.5 (3-8). Age: 0-14 35%, 15-44 45%, 45-64 15%, 65+ 5%. Infant mortality 25% before age 5. Birth sex ratio 105 M : 100 F; adult 98 M : 100 F. Child labour productive from about age 7.

Racial counts are rounded with the largest-remainder method so they sum exactly to the total at genesis.


B. Class vs Profession
----------------------
Every NPC has both a class (SRD) and a profession (medieval flavour).

  Class       Typical professions
  Commoner    ploughman, alewife, goose girl, porter, laundress
  Expert      smith, fletcher, miller, scribe, apothecary, merchant
  Warrior     watchman, man-at-arms, levy, gatekeeper
  Aristocrat  lord, lady, sheriff, reeve, knight, bishop
  Adept       cunning man, wise woman, hedge priest
  Cleric      parish priest, abbess, prior, canon, archdeacon, abbot
  Wizard      scholar-mage, alchemist
  Sorcerer    hedge-sorcerer, bloodline mage
  Rogue       chapman, cutpurse, huckster, fence
  Fighter     man-at-arms, knight, mercenary, captain
  Ranger      forester, huntsman, verderer
  Bard        minstrel, herald, crier
  Druid       circle-keeper, grove-tender
  Paladin     knight of a militant order
  Monk        cloistered brother/sister, ascetic


C. Class Levels by Settlement Type
----------------------------------
  Role               Class              Thorpe Hamlet Village Sm.town Lg.town City   Metropolis
  Labourer           Commoner           1      1      1-2     1-3     1-3     1-4    1-5
  Tradesman          Expert             2-3    2-4    2-5     3-6     4-7     5-8    6-10
  Guild master       Expert             -      -      4-6     5-7     6-9     8-11   10-14
  Watchman           Warrior            -      1      1-2     1-3     2-4     2-5    3-6
  Man-at-arms        Fighter            -      -      2-3     2-4     3-5     4-6    5-8
  Knight             Fighter/Aristocrat -      -      3-5     4-6     5-7     6-9    8-12
  Priest             Cleric/Adept       1-2    2      2-3     3-4     4-5     5-7    6-9
  Senior cleric      Cleric             -      -      -       5-6     6-8     8-10   10-13
    (archdeacon, abbot, abbess, prior, dean)
  Bishop/Archbishop  Cleric             -      -      -       -       -       9-12   12-17
  Cunning man/woman  Adept/Wizard       1-2    2      2-3     3-5     4-6     5-8    7-11
  Lord/lady          Aristocrat         -      5      6-7     7-9     8-11    10-14  13-18
  Castle captain     Fighter            -      -      4-6     6-8     7-9     9-12   12-16

The listed ranges are the only source of level. Destitute settlements apply the level modifier in Table AA. Thorpe has no permanent watch, man-at-arms, knight, guild master, or resident lord; clergy is itinerant or a single shrine-keeper. Metropolis has multiple watch companies, knightly households, a permanent garrison, an archbishop or equivalent, a university, and national guilds. Bishops and archbishops exist only where a cathedral exists (Table L); lesser settlements use the senior cleric row. Non-parish churches use their own equivalent titles (Table F). Wives of lords are Aristocrats at the lord's level minus 2 (minimum 1); see Table H1.


D. Alignment
------------
Birth alignment is rolled in phase 5 from race and clan only. No profession or wealth term is used at genesis.

Step 1, good-evil axis, by race (approximation):
  Default (human, dwarf, elf, halfling, gnome, half-elf): Good 55%, Neutral 44%, Evil 1%
  Half-orc: Good 30%, Neutral 70%, Evil 0%. A half-orc living in civilisation is never Evil: no evil half-orc stays free of a bounty for long, so the worst case is chaotic neutral. Any Evil result is rerolled as Neutral.
  Orc: Good 15%, Neutral 45%, Evil 40%

Step 2, law-chaos axis, by race:
  Race                  Lawful  Neutral  Chaotic
  Human agrarian        45%     40%      15%
  Human border/trade    25%     50%      25%
  Dwarf                 70%     25%      5%
  Elf                   20%     55%      25%
  Halfling              50%     45%      5%
  Gnome                 30%     50%      20%
  Orc                   15%     30%      55%
  Half-elf              25%     55%      20%
  Half-orc              20%     40%      40%

The two axes are rolled independently and combined into one of nine alignments. Human subtype: "border/trade" if the settlement has a border tag, a major road, a coast or river tag, or trade route is major; otherwise "agrarian". Clan reputation shifts the bias of either axis by up to 10 points (never producing an Evil half-orc).

Alignment drift, applied only to notable NPCs in phase 12 and stored as alignmentCurrent (birth alignment is never edited):
  Wealth: middle tiers lean Good; destitute leans toward Evil; very rich leans Neutral-to-Evil by self-interest.
  Profession: clergy lean Good; rogue and assassin lean Evil.
Drift moves at most one step on one axis and never makes a half-orc Evil. Faith always derives from birth alignment.


E. Ability Scores, Feats, Skills, Equipment
-------------------------------------------
- Scores: 4d6 drop lowest. PC classes assign highest rolls to preferred stats; NPC classes assign in order.
- Feats: 1 at level 1, then every 3 levels, plus racial and class bonus feats per SRD. Priors: Skill Focus (profession), Negotiator (merchants), Persuasive (innkeepers), Power Attack (warriors), Weapon Focus (soldiers), Brew Potion / Craft Magic Arms and Armor / Craft Wondrous Item (spellcasters).
- Skills: (class skill points + Int mod) x (level + 3), max rank = level + 3, with the SRD human bonus. Prioritise profession skills first, then class skills. Emphasise Appraise, Bluff, Diplomacy, Gather Information, Intimidate, Sense Motive, Profession, relevant Craft.
- Equipment: NPC wealth by level (SRD DMG Table 4-23, reference to be confirmed against the SRD NPC gear table) x the gear multiplier in Table AA, split into arms and armour, outfit and kit, and valuables by Table AH.


F. Pantheon (Forgotten Realms)
------------------------------
Deity names are Forgotten Realms; clerical domains are mapped to SRD domains (approximation). Settlements shun evil gods publicly; evil deities are worshipped covertly, except in orc-majority settlements where Gruumsh may be open.

Church templates (each defines clergy titles, sex restrictions, celibacy, magical services):

- Parish: parishes, bishops, archdeacons, monasteries and nunneries, tithes, canon law. Parish clergy male share 95%; nunneries are led by abbesses (Cleric or Monk).
- Nature: druidic circles, grove-tenders, no fixed hierarchy. Male share 60%.
- War: militant orders, grandmaster -> knight-captain -> brother/sister-at-arms. Male share 98%.
- Trickster: secret societies, cell structure. Male share 55%.
- Death: funerary guilds, arch-funerary -> mortician -> acolyte. Male share 60%.
- Craft and Trade: guild-temple hybrid, master -> journeyman -> apprentice. Sex per guild rules (Table P) and racial overrides (Table H).
- Scholar: collegiate chapters under a provost. Male share 85%.
- Evil (covert): covert shrines, no public buildings, disguised clergy.

Deities (alignment; SRD domains; template):
  Lathander    NG  Good, Protection, Sun                 Parish
  Chauntea     NG  Good, Plant, Protection               Parish
  Mielikki     NG  Animal, Good, Plant                   Nature
  Silvanus     N   Animal, Plant, Water                  Nature
  Tyr          LG  Good, Law, War                        War
  Helm         LN  Law, Protection, War                  War
  Torm         LG  Good, Law, Protection, War            War
  Tymora       CG  Chaos, Good, Luck, Travel             Trickster
  Kelemvor     LN  Death, Law, Protection                Death
  Moradin      LG  Earth, Good, Law, Protection          Craft and Trade (dwarves)
  Gond         N   Earth, Fire, Knowledge                 Craft and Trade (gnomes)
  Waukeen      N   Knowledge, Luck, Travel                Craft and Trade (merchants)
  Oghma        N   Knowledge, Luck, Travel                Scholar
  Mystra       NG  Good, Knowledge, Magic, Protection    Scholar
  Corellon Larethian  CG  Chaos, Good, Protection, War   Nature (elven circles)
  Yondalla     LG  Good, Law, Protection                 Parish (halfling hearth-shrines)
  Evil, covert:
  Bane LE (Evil, Law, Destruction, War); Bhaal LE (Death, Evil, Destruction); Myrkul LE (Death, Evil, Law); Shar NE (Evil, Knowledge, Trickery); Cyric CE (Chaos, Destruction, Evil, Trickery); Talos CE (Air, Chaos, Destruction, Evil, Fire); Loviatar LE (Evil, Law, Strength); Malar CE (Animal, Chaos, Evil, Strength); Gruumsh CE (Chaos, Evil, Strength, War; orc template: Evil, open in orc-majority settlements).

Race to pantheon (approximation), primary first:
  Human:     Lathander, Chauntea, Mielikki, Silvanus, Tyr, Helm, Torm, Tymora, Kelemvor, Waukeen, Oghma, Mystra, Gond
  Dwarf:     Moradin, Tyr, Helm
  Elf:       Corellon Larethian, Mielikki, Silvanus
  Halfling:  Yondalla, Chauntea, Tymora
  Gnome:     Gond, Oghma, Mystra
  Orc:       Gruumsh
  Half-elf, half-orc: parent pantheon chosen by upbringing (Table W); a half-orc never takes an evil deity in civilisation. If the upbringing pantheon leaves no permitted deity (an orc-raised half-orc), fall back to the settlement's parish deity (Table L).
Evil deities are drawn only when the alignment-compatible roll lands on Evil. A deity is alignment-compatible if its alignment is within one step on each axis of the worshipper's birth alignment.

Metropolises may host a grand cathedral, allied temples, and hidden shrines.


G. Social Class
---------------
  Class              Share     Markers
  Gentry             2-5%      titles, heraldry, elite names
  Clergy             3-8%      rank titles, vestments
  Merchants/guild    8-15%     occupational surnames, fees
  Artisans           15-25%    guild membership, trade names
  Free peasantry     40-55%    yeoman, goodman, goodwife
  Unfree/servile     10-20%    no surname, obligatory labour
  Outcasts           1-3%      no guild, no parish standing

Shares are drawn within range and normalised to 100.

Per-size overrides:
  Thorpe: gentry 0, clergy 0-1 (itinerant or shrine-keeper), merchants 0, artisans 5-10, free peasantry 55-70, unfree 15-30, outcasts 0-3.
  Hamlet: gentry 0-2, merchants 0-3.
Destitute: gentry absent, dead, or fled; unfree and outcast shares rise; artisan and merchant shares fall. Metropolis: merchant/guild share rises, a small scholarly and bureaucratic class emerges, foreign quarters as distinct enclaves.
Women's social class follows Table H3.


H. Sex-Based Division of Labour and Class Status (medieval standard)
--------------------------------------------------------------------
Not optional and not a seed-variable input. Every class and profession has a fixed MALE SHARE constant in one constants file. Assignment draws against that share from the seeded stream, so the same seed always gives the same result. Shares cannot be changed by inputs or toggles.

Precedence, applied in this order (first matching rule wins):
1. Widow/heiress exception: a widow may inherit and operate a deceased husband's trade, guild membership, and establishment as full proprietor, and may act as regent for a lordship; daughters inherit in the absence of sons. Applies only to inherited positions. Social penalties possible in restrictive guilds.
2. Racial override (below): replaces the baseline share and lifts guild sex restrictions inside that race's own guilds.
3. Church restriction (Table F) for clergy; guild restriction (Table P) for guild membership.
4. Baseline male share from H1 (class) and H2 (profession).

H1. Class availability by sex (male share):
  Commoner     per profession (H2)
  Expert       per profession (H2)
  Warrior      98
  Fighter      99   (knights, men-at-arms, captains, mercenaries)
  Paladin      100  (militant orders)
  Ranger       90   (foresters, huntsmen, verderers)
  Rogue        65
  Bard         75   (minstrels; female entertainers exist but are the minority)
  Aristocrat   lords, sheriffs, reeves, knights, bishops: male. Ladies: the wife, widow, or daughter of an Aristocrat takes class Aristocrat at the lord's level minus 2 (minimum 1). A woman holds a lordship in her own right only via the widow/heiress exception.
  Cleric       per church template (Table F): parish and secular clergy male; abbesses and prioresses head nunneries
  Monk         by house: male houses and female houses in equal number
  Druid        60
  Adept        35   (wise women and cunning men; the female share is larger than any other magical class)
  Wizard       90
  Sorcerer     90

H2. Profession male share:
  Male 98: soldier, man-at-arms, knight, watchman, gatekeeper, sheriff, constable, bailiff, miner, quarryman, mason, carpenter, joiner, cooper, wheelwright, smith (blacksmith, farrier, armourer), carter, waggoner, drover, deep-water fisherman, sailor, ferryman, tanner, slaughterer, butcher, ploughman, husbandman.
  Male 90-98 (stated per profession): thatcher 95, tiler 95, yeoman farmer 95, reeve 95, lay scribe 95, clerk 95, notary 95, alchemist 95, master apothecary 95, fletcher 90, bowyer 90, miller 90, master baker 90, draper 90, goldsmith/jeweller 90, glassmaker 90, chirurgeon 90, scholar 92, physician 98.
  Female 98: spinner, seamstress, embroiderer, dairywoman, butter-maker, midwife, laundress, washerwoman, wet-nurse, goose girl (male share 2).
  Female 90-95: alewife (5), brewster (5), cheesemaker (5), wise woman (5), herbalist (10), poultry keeper (5), nurse (5), market woman (5), regrater (10), huckster (10), household cook (10), domestic baker (5), domestic servant (15), haberdasher and seller of small cloth wares, shop-front (25 male share), domestic candle-maker (10), charm-seller and petty diviner (15).
  Mixed (explicit male share): weaver 55, smallholding farmer 70, orchard-keeper 70, gardener 60, merchant 85, shopkeeper 60, pedlar 65, innkeeper, taverner, hostelry keeper 65, healer 35, scribe in a nunnery 15, minstrel, bard, entertainer 75, rogue, thief, cutpurse 65, potter 70, teacher, tutor 70.
  Fletcher and bowyer among elves: male share 40.

Each profession appears in exactly one group. Alewives and brewsters (victualling) are female-dominated; innkeepers and taverners are mixed. Draper (shop-front sale of bulk cloth) is a male guild trade; haberdashers and sellers of small wares are female-leaning.

H3. Social class status of women:
- A woman takes the social class of her father; on marriage she takes her husband's; a widow keeps her husband's.
- Unfree status passes from the father.
- Households are male-headed. Female-headed households are limited to widows, plus unmarried women of property at 1-3% of households (higher in destitute settlements, where men are lost).
- Gentry women are always class Aristocrat (H1) with no profession other than managing the household, except via the widow/heiress exception.
- Women outside the gentry and clergy hold Commoner or Expert class according to H2.

Racial overrides: dwarven women smith and work stone openly (male share 55); elven women fletch, bowyer, and practise magic openly (male share 40, including Wizard and Sorcerer); halfling women innkeep, farm, and handle pipe-weed openly (male share 40); gnome women tinker, alchemise, and cut gems openly (male share 40); orc women butcher, raid, and mercenary openly (male share 50, including Warrior and Fighter).

Enforcement: the labour engine checks sex before assignment; establishments reflect proprietor sex unless an exception applies; household composition reflects the division; women's unwaged work is modelled as household production (Table V). Metropolises soften enforcement at the margins (female religious houses, women's guilds, widow communities) by widening the minority draw by up to 10 points, but never override the baseline.


I. Faith Derivation
-------------------
Faith = race pantheon (Table F) -> clan patron -> alignment-compatible deity, using birth alignment. Half-race upbringing (Table W) determines which parent's pantheon applies.


J. Naming
---------
- Humans: Anglo-Saxon, sex-appropriate
- Elves: Romantic-language feel, sex-appropriate
- Halflings: Biblical first names + plain English surnames
- Gnomes: Celtic
- Dwarves: approximated Mongol
- Orcs: guttural first names + violent Native American epithet-style surnames
- Half-races: mix, decided by upbringing
- Ruling race(s) influence elite names and titles
- Class-conscious; marital status affects address (widow, wife, maid, master, goodman, goodwife)
- Generated lazily once identity is complete, keyed on entityId (Principle 10)
- Metropolises include foreign quarters with names from the appropriate parent cultures


K. Defense, Levy, Castle
------------------------
Definitions:
  Garrison: standing professional soldiers under the lord or crown.
  Watch: civil police (Table Q).
  Militia: peacetime muster of able-bodied adult males (Table Q).
  Levy: wartime call-up ceiling, drawn from the range below and capped at 50% of able-bodied adult males.

Historical baseline, exaggerated for a world of inhuman monsters.

  Size        Wall                   Castle  Garrison  Levy       Siege stores
  Thorpe      none/ditch             0%      -         0-5        1 day
  Hamlet      ditch/palisade         2%      -         10-30      3 days
  Village     palisade               5%      5-15      30-80      7 days
  Small town  stone wall + gates     15%     20-60     80-200     14 days
  Large town  wall + towers          40%     60-150    200-500    30 days
  City        curtain wall + keep    70%     150-500   500-2000   60 days
  Metropolis  multiple walls,        90%     500-2000  2000-8000  90-180 days
              citadel, harbour chain

Castle chance modifiers: +10% on border or high threat; +10% if rich; then multiplied by the castle chance toggle (low x0.5, normal x1, high x1.5), capped at 95%.
Destitute: walls and stores halved, garrison halved, levy halved until next harvest or event tick.

Upkeep:
  Garrison pay is the standard skilled-work rate: the SRD trained hireling rate of 3 sp per day for every garrison soldier and sergeant, plus provisions of 2 sp per soldier per day, plus 5% of fortification value per year. Knights and the castle captain are retained by fief or by the lord's treasury, not on the garrison wage line.
  Destitute: garrison pay accrues as arrears in coffers.debt until recovery.
Siege stores: food, arrows (1,000 per 100 archers per day), fuel, pitch, stone. Metropolises maintain multiple depots and naval supply where applicable.


L. Religious Buildings
----------------------
Historical population-to-church ratios, adjusted for deity distribution. Bands match Table AB.
- Thorpe (<30): no building; shrine stone, wayside cross, or itinerant priest.
- Hamlet (30-99): 1 shrine
- Village (100-500): 1-2 shrines, 1 chapel
- Small town (501-2,000): 2-4 shrines, 1-3 chapels, 1-2 churches
- Large town (2,001-10,000): 4-8 shrines, 3-6 chapels, 2-4 churches, 1-2 temples, 1-3 monasteries (male and female houses in equal number)
- City (10,001-50,000): 8+ shrines, 6+ chapels, 4+ churches, 2+ temples, 3+ monasteries, 1 cathedral
- Metropolis (50,001+): 15+ shrines, 10+ chapels, 8+ churches, 4+ temples, 5+ monasteries, 1 grand cathedral, 1+ university or scholarly college, foreign temples

Distribution follows faith demographics. The parish deity (Lathander or Chauntea in most human settlements) holds the parish church; minority gods hold shrines or shared temples; evil gods hold covert shrines only. Destitute: one religious building may be damaged, desecrated, or abandoned.


M. Supply Chains and External Trade
-----------------------------------
Each establishment declares inputs and outputs from the goods in Tables AD and AE. Examples:
- Smithy: iron ingot + charcoal -> tools, weapons, nails
- Bowyer: yew stave + sinew -> bows
- Fletcher: shafts + feathers + heads -> arrows
- Miller: grain -> flour
- Baker: flour + yeast + fuel -> bread
- Tanner: hides + tannin -> leather
- Weaver: wool -> cloth
- Apothecary: herbs + glass + alcohol -> remedies

Desired imports by wealth: Table AA (import multiplier, luxury share).
Import cost by location and trade route: Table AC.

Import budget (trade balance rule):
  importBudget = exportIncome + permitted coffer draw + credit
  Credit by tier: destitute 0, poor 0, modest 5% of annual exports, prosperous 10%, rich 15%.
  Actual imports = min(desired imports, importBudget). Luxury imports are cut first when the budget falls short. Shortfall is recorded as unmet demand. tradeBalance = exportIncome - importSpend is explicit in the output and reconciles with coffers.

Thorpe: no market; trade via pedlars, fairs, or a nearby larger settlement. Destitute: broken supply chains, relief, foraging, and barter until restored. Metropolis: regional trade hub, import multiplier x1.5 above its wealth tier, luxury share doubled, supplies surrounding settlements as an export node.


TRADE ACCESS AND TRADE ROUTE (Table AC)
---------------------------------------
Trade access by tag (location). Applies to crude goods:
  Tag          Access     Crude import cost x   Export capacity x
  coast        high       0.8                   1.5
  river        high       0.9                   1.3
  major road   medium     1.0                   1.0
  minor road   low        1.2                   0.7
  isolated     very low   1.5                   0.3
Multiple tags: use the best single tag; no stacking. No road, coast, or river tag means isolated.

Trade route toggle (approximation). It acts mostly on luxury goods:
  Toggle   Luxury catalogue available   Luxury import cost x    Crude import cost
  none     25% of imported luxuries     location x 1.5          +10%
  minor    50%                          location x 1.2          unchanged
  major    100%                         location x 1.0          -10%
  "Location x" is the crude import multiplier above. The available subset is drawn by the seed and is a subset of the imported-only luxuries (Table AD); locally producible luxuries are unaffected by the toggle.
The toggle also scales luxury export demand: a major route raises external demand for local luxuries by 20%, none lowers it by 20%.


GOODS: CRUDE AND LUXURY (Table AD)
----------------------------------
PRICE ANCHORS (SRD Trade Goods table, per pound unless stated):
  1 cp wheat; 2 cp flour; 1 sp iron; 5 sp tobacco (use for halfling pipe-weed) or copper; 1 gp cinnamon; 2 gp ginger or pepper; 5 gp salt or silver; 15 gp saffron or cloves; 50 gp gold; 500 gp platinum (metropolis and dwarven trade only, approximation).
  Per square yard: linen 4 gp; silk 10 gp.
  Livestock, each: chicken 2 cp; goat 1 gp; sheep 2 gp; pig 3 gp; cow 10 gp; ox 15 gp.
  Not in the SRD table (approximation): cloth of gold at 100 gp per square yard; all other goods are priced by comparison to the nearest anchor.
Classification: a non-livestock good priced at 1 gp or more per unit is a luxury, with two named staples exempt: salt and linen. Staples are crude by category (necessary inputs, never removed by the trade route toggle, imported at the crude multiplier) but are priced at their SRD anchors, so inland they are expensive. Everything below 1 gp per unit is crude.

CRUDE GOODS (everyday inputs; local where terrain allows, otherwise imported at the crude import cost):
  Food: grain (wheat, barley, oats, rye), vegetables, fruit, nuts, mushrooms, honey, fish, shellfish, game, livestock (cattle, sheep, pigs, goats, poultry, draught animals), milk, eggs, hops
  Fibre and hides: wool, flax, hemp, hides, sinew, horn, feathers, tallow, beeswax, fleeces
  Wood and plant: timber, firewood, charcoal, tannin bark, pitch and resin, osiers, reeds and thatch, yew staves, ash shafts, herbs, madder, woad, weld
  Earth and mineral: stone, lime, sand, clay, peat, flint, iron ore, copper and tin ore, lead ore, potash (wood ash), alum
  Staples (crude by category, priced at anchor): salt, linen
  Worked crude goods: iron ingot, nails and tools, rope, cloth (wool), leather, flour, ale, bread, parchment, ink, candles, glass vials, pottery, barrels, planks

LUXURY GOODS:
  Imported-only (subject to the trade route toggle):
    spices (pepper, cinnamon, ginger), rare spices (saffron, cloves), sugar, silk, cloth of gold, incense and perfume, ivory, exotic dyes (indigo, scarlet), exotic hardwoods, carpets and tapestries, cut gems
  Locally producible if conditions are met (not affected by the trade route toggle):
    fine wine (warm climate, farmland or hills), olive oil (warm climate), fine woollen broadcloth (hills or farmland with sheep and weavers), fine furs (forest, cold or temperate), silver and gold bullion, plate and jewellery (mountain with precious ore and a goldsmith), fine glass (sand, potash, fuel, glassmaker), illuminated books and manuscripts (parchment, pigments, scribes in a monastery or scriptorium), fine steel and masterwork arms and armour (iron ore, charcoal, master smith or armourer), aqua vitae and strong spirits (grain or grapes, alchemist or apothecary)

Luxury demand has two parts: apparel from Table AG, and non-apparel luxuries (wine, spices, plate, books, incense) from the Table AE consumer lines, scaled by class: gentry 100% of their household demand, clergy 30%, merchants 40%, artisans 10%, free peasantry and below 0%. Luxury import spend is the lesser of total demand and the wealth-tier cap (Table AA), allocated across consumers pro rata to demand. Item-creation materials (Table X) are an additional luxury consumer.

MASTERWORK
  SRD premium over the normal item: weapon +300 gp, armour +150 gp, tool +50 gp (a masterwork artisan's tool kit totals 55 gp). Only an establishment whose proprietor is an Expert with the matching Craft who passes the SRD masterwork Craft check, and which holds fine steel (weapons, armour) or fine hardwood and fine metal (tools) in stock, may sell masterwork. The premium is luxury spend, paid against that stock. A normal item is never sold at the premium.

OUTFIT TIERS AND LUXURY DEMAND (Table AG, approximation)
  Outfit prices are SRD: peasant's 1 sp, artisan's 1 gp, scholar's 5 gp, monk's 5 gp, courtier's 30 gp, noble's 75 gp, royal 200 gp. A noble's outfit also needs a signet ring and jewellery worth at least 100 gp, and a courtier's outfit 50 gp of jewellery; jewellery lasts a lifetime and counts as stored valuables (Table S), not annual demand.
  Social class         Outfit tier                                           Replaced every   Luxury share of outfit price
  Unfree, outcasts     peasant's                                             2 years          0%
  Free peasantry       peasant's                                             2 years          0%
  Artisans             artisan's                                             3 years          0%
  Merchants/guild      80% artisan's, 20% courtier's                         2 years          30% (courtier's only)
  Clergy               scholar's (secular) or monk's (monastic)              3 years          0% (ritual luxuries via Table AE)
  Gentry               courtier's (household, knights); noble's (lord, lady, heir)   1 year   30% courtier's, 50% noble's
  Ruler                royal (ruler and consort only; metropolis or royal-blood lord) 1 year  70%
  annualApparelLuxuryDemandGp(class) = sum over persons of outfitPrice x luxuryShare / replaceYears (children count half).
  Apparel luxuries are silk, fine furs, gems, precious metal, and exotic dyes (Table AD).

NPC GEAR SPLIT (Table AH, approximation)
  The gear gp of each notable NPC (Table E) is split:
  Class group                                  Arms and armour   Outfit, kit, tools   Valuables
  Commoner                                     5%                75%                  20%
  Expert                                       5%                55%                  40% (includes masterwork tools)
  Warrior, Fighter, Ranger, Paladin            65%               20%                  15%
  Aristocrat                                   20%               25%                  55%
  Cleric, Monk, Druid, Adept                   15%               35%                  50%
  Wizard, Sorcerer, Bard, Rogue                10%               40%                  50%
  Valuables are gems, plate, jewellery, bullion, and fine cloth at full anchor price. They draw on and count toward settlement luxury stock; an NPC whose valuables exceed available stock holds coin instead.


PROFESSION INPUTS (Table AE)
----------------------------
For every profession: crude inputs | luxury inputs. "-" means none. These feed establishments (phase 9) and supply chains (phase 11). A profession that cannot source its crude inputs locally or by import stays dormant or substitutes.

Agriculture
  ploughman, husbandman, yeoman farmer, smallholding farmer | seed grain, draught oxen, iron tools, firewood | -
  gardener, orchard-keeper | seed, saplings, iron tools | -
  dairywoman, cheesemaker, butter-maker | milk, salt, firewood, barrels | -
  poultry keeper, goose girl | grain, feed | -
  drover | livestock, fodder | -
Food and drink
  miller | grain, millstones (stone), water or wind power | -
  master baker, domestic baker | flour, ale barm, firewood | sugar, spice (fine bakes)
  alewife, brewster | barley, hops or gruit herbs, water, firewood, barrels | spice (spiced ale, rich settlements only)
  butcher, slaughterer | livestock, salt, firewood | spice (cured fine meats)
  deep-water fisherman | boats (timber, pitch), hemp nets, salt | -
  household cook | food stuffs, firewood | spice, sugar
  innkeeper, taverner | food, ale, bedding, firewood | wine, spice
Metal
  smith (blacksmith, farrier, armourer) | iron ingot, charcoal, hides (bellows), water | masterwork steel (armourer, fine work)
  miner, quarryman | iron tools, timber props, tallow (lamps) | -
  goldsmith, jeweller | silver or gold, charcoal | gems, gold and silver bullion
Wood
  carpenter, joiner, wheelwright, cooper | timber, iron nails and bands, tools | exotic hardwoods (fine joinery)
  fletcher | ash shafts, goose feathers, iron or steel heads, glue (hides) | -
  bowyer | yew staves, sinew, horn, beeswax | -
Building
  mason | quarried stone, lime, sand, timber (scaffold) | -
  thatcher | reeds or straw | -
  tiler | clay, firewood | -
Textiles and clothing
  spinner | wool, flax, hemp | -
  weaver | yarn, dye (madder, woad, weld) | exotic dyes (fine cloth)
  seamstress, embroiderer | cloth, thread | silk thread, gold thread
  draper | wool and linen cloth | silk, cloth of gold
  haberdasher (small wares) | ribbon, pins, buttons (horn, bone) | silk ribbon
  tanner | hides, tannin bark, lime, water | -
  laundress, washerwoman | water, wood ash lye, tallow soap | -
  domestic candle-maker | tallow, beeswax | -
Medicine
  apothecary, herbalist, wise woman | herbs, honey, alcohol, glass vials | spices, rare spices, incense (compounds)
  midwife, healer, nurse, wet-nurse | herbs, linen bandages, clean water | -
  chirurgeon, physician | herbs, iron instruments, alcohol, linen | spices, rare spices
  alchemist | glass, firewood, salt, metals, reagents | gems, quicksilver (approximation)
Church and learning
  cleric (parish priest), druid, monk, abbess, prior | tithe grain, candles (beeswax), wine for rites, firewood | incense, silk vestments, illuminated books
  lay scribe, clerk, notary | parchment, ink (oak gall, iron), quills | pigments, gold leaf
  scholar, teacher, tutor | parchment, ink | books
  wizard, sorcerer, scholar-mage, adept, cunning man | herbs, metals, ink, candles | gems, fine ink, rare books
Commerce
  merchant, shopkeeper, pedlar | stock goods, carts, pack mules, fodder | whichever luxuries traded
  huckster, regrater, market woman | foodstuffs, baskets | -
Transport
  carter, waggoner | carts (wheelwright), draught animals, fodder, iron tyres | -
  ferryman | boat (timber, pitch), rope (hemp) | -
  sailor | ship, hemp rope, linen canvas, pitch | -
Pottery and glass
  potter | clay, firewood | -
  glassmaker | sand, potash, firewood | cobalt and other pigments (coloured glass)
Military and law
  soldier, man-at-arms, mercenary | iron arms, leather or iron armour, rations | masterwork steel (officers)
  knight | iron and leather arms and armour, warhorse, fodder | plate (masterwork steel)
  watchman, gatekeeper | club or spear, lantern oil (tallow), whistle | -
  sheriff, reeve, constable, bailiff | parchment, ink, horses | -
  forester, huntsman, verderer, ranger | bows, hounds, snares | -
Gentry and entertainment
  lord, lady, aristocrat | household provisions, fuel, servants | wine, spices, silk, fine furs, plate, books (primary luxury consumers)
  bard, minstrel, herald, crier | instruments (wood, gut) | silk costume (rich settlements)
Shadow trades
  rogue, cutpurse, fence | stolen goods | luxuries (fence handles them)
  charm-seller, petty diviner | trinkets, herbs, bones | incense

Terrain resource tables (Table AF). Abundance A = abundant, S = some, - = none. Climate gates are in notes. These set resourceBase (phase 2); anything an establishment needs that is "-" must be imported.

  Resource           farmland  forest  mountain  hills  marsh  coast  river
  grain              A         -       -         S      -      -      S
  vegetables, fruit  A         S       -         S      -      -      S
  livestock          A         S       S         A      S      -      S
  milk, eggs         A         -       S         S      -      -      -
  wool               S         -       S         A      -      -      -
  flax, hemp         S         -       -         S      S      -      S
  hides, sinew       S         S       S         S      -      -      -
  honey, beeswax     S         S       -         S      -      -      -
  hops, barley       S         -       -         S      -      -      -
  timber             -         A       S         -      -      -      -
  firewood           S         A       S         S      S      S      -
  charcoal           -         A       -         -      -      -      -
  tannin bark, pitch -         A       -         -      -      -      -
  yew, ash shafts    -         S       -         S      -      -      -
  herbs              S         S       S         S      S      S      S
  game               S         A       S         S      S      -      -
  furs               -         S       S         -      -      -      -
  reeds, osiers      -         -       -         -      A      -      S
  peat               -         -       -         -      A      -      -
  fish, shellfish    -         -       -         -      S      A      A
  salt               -         -       -         -      -      A      -
  sand, potash       -         S       -         -      -      S      S
  clay               S         -       -         S      S      -      S
  stone, lime        -         -       A         S      -      -      -
  iron ore           -         -       A         S      -      -      -
  copper, tin, lead  -         -       S         S      -      -      -
  precious ore       -         -       S         -      -      -      -   (rare: seed roll, 15% on mountain)
  mill power         -         -       -         -      -      -      A
Notes: border adds no resource; it raises threat one step and castle chance (Table K). Climate gates: fine wine and olive oil only in warm climate on farmland or hills; fine furs need cold or temperate forest; cold climate halves grain output and doubles firewood demand.
Abundant resources are exported as surplus (Table Z); absent resources needed by a profession are imported.


N. Events
---------
Events are rolled at the start of each season, one roll per event type per settlement, using the event stream (seed + phase + eventType + seasonIndex). Daily ticks apply their effects.

  Event                  Frequency                      Effect
  Harvest                1 per agrarian settlement      +20% grain, -10% bread
                         per season
  Fair                   1 per town per season          +30% trade volume for 1 week
  Banditry               10% per season on trade routes -20% imports, +levy cost
  Monster raid           5-25% by threat                -stock, +defense spend
  Plague                 2-5% per season (city or       -5-20% population, -trade
                         metropolis 5-25%)
  War                    toggle                         +levy, +taxes, -imports
  Trade disruption       10% per season                 +50% import cost (luxuries first)
  Looting                toggle                         Sets wealth to destitute; seizes luxury stock and stored valuables first; damages establishments,
                                                        walls, stores; recovery over subsequent ticks
  Fire                   3% per season in towns/cities, 1-3 districts damaged or destroyed; -stock,
                         5% in metropolises             -housing, +recovery cost
  Plague riot            10% during plague in city or   +law temporarily, -guild power, -trade
                         metropolis
  Foreign demand spike   5% per season                  +30% export price for one good
  Trade embargo          5% per season                  Exports blocked; surplus spoils
  Pirate/raider attack   10% per season on coast/river  -export volume, +insurance cost
  Merchant caravan       15% per season in towns+       +import variety (luxury subset widens by one
                                                        draw), -import prices

Population changes after genesis are logged in a ledger. The racial-makeup sum rule applies at genesis only.


O. Services and Costs
---------------------
Use SRD formulas exactly where the SRD defines them.
- Hireling: SRD daily rates: untrained 1 sp, trained (skilled) 3 sp. Specialists (sages, translators, master artisans) start at the trained rate and are priced upward by skill (approximation).
- Spellcasting by an NPC: spell level x caster level x 10 gp, with minimum caster level per SRD (a 0-level spell uses 5 gp x caster level). Material components and XP costs are added at full price.
- Item creation: SRD formulas. Raw materials cost half the market price; time is 1 day per 1,000 gp of market price (minimum 1 day); XP cost is 1/25 of base price, paid by the crafter. The commission fee converts XP to gold at 5 gp per XP (approximation). At least half of the raw-material gp is drawn from luxury stock (Table X). Prerequisites per Table X.
- Spell level ceiling is DERIVED, not input: the highest spell level castable by the highest-level caster present, using SRD spell progressions (adept: 2nd at caster level 3, 3rd at 7, 4th at 11, 5th at 15). The magic level toggle shifts caster levels by -2 (low), 0 (normal), +2 (high), clamped to Table C.
  Typical outcome (informational): thorpe 1, hamlet 1, village 2, small town 3, large town 4, city 6, metropolis 6-9 (9th level needs caster level 17, high magic only).
- Hireling availability follows the sex-based labour rules. Metropolises add specialist hirelings.


P. Guilds
---------
  Trade                       Guild?          Sex restriction  Political power
  Smiths, masons, carpenters  yes             male             high
  Weavers, brewers            yes (often mixed) mixed          medium
  Mercers (wholesale cloth),  yes             male             high
    drapers, vintners
  Chandlers, laundresses      no formal guild female           low
  Scribes, apothecaries       yes             male             medium

Racial overrides (Table H) lift the restriction inside that race's own guilds. Widow/heiress rule per Table H.
Fees: 1-5 gp entry, 1-10 sp monthly. Membership gates establishment rights and price floors. Thorpes: none. Destitute: suspended or powerless. Metropolis: great guilds with national charters, political representation, internal hierarchy (master -> warden -> guildmaster).
Charter policy comes from phase 6; charter instances are created in phase 9.


Q. Watch and Militia
--------------------
- Watch size is about population / 100, x2 in towns, x3 in cities, x4 in metropolises; minimum 1 from hamlet upward.
- Watch: Warrior, level per Table C, chain shirt, club or spear, lantern, whistle. Pay 2 sp/day (part-time civic duty, below the garrison rate).
- Garrison: skilled rate per Table K (3 sp/day plus provisions).
- Militia (peacetime muster): 1 in 4 able-bodied adult males. Poor = spear + leather; rich = spear + shield + leather. Unpaid except on call-up (1 sp/day).
- Jurisdiction: watch inside walls, militia outside, sheriff commands both.
- Thorpe: no watch; adult residents form an ad hoc levy.
- Destitute: no paid watch; militia unpaid, under-equipped, half-strength; garrison per Table K (halved, pay in arrears).
- Metropolis: organised watch companies, permanent city garrison, harbour watch (if coastal or riverine), gate wards, each with captains and lieutenants.


R. Disposition and Haggling
---------------------------
Haggling is driven by DISPOSITION, using the SRD Diplomacy attitude scale: Hostile, Unfriendly, Indifferent, Friendly, Helpful. Disposition is a stat the DM can see on every notable NPC and every proprietor card.

R1. Base disposition (genesis, phase 12). Each notable NPC has baseDisposition toward strangers, rolled once on d100 plus modifiers:
  Result (after modifiers)   Disposition
  1-5 or less                Hostile
  6-25                       Unfriendly
  26-75                      Indifferent
  76-95                      Friendly
  96 or more                 Helpful
Modifiers to the roll (approximation): NPC Charisma modifier x 2; same race as the buyer +10; same clan or faith +10; ruling race member dealing with a non-ruling race -10; alignment opposed on the good-evil axis -10, on the law-chaos axis -5; settlement under plague or raid event -10; destitute settlement stranger -10.

R2. Current attitude (state). The first meeting between a given buyer and a given NPC rolls the base disposition with buyer-specific modifiers (race, clan, faith, alignment, reputation). Current attitude then changes by play. It is stored in state keyed by seed + establishmentId + buyerId.

R3. Changing attitude. A buyer makes a Diplomacy check against the SRD DC for the desired shift:
  Starting attitude   To Unfriendly  To Indifferent  To Friendly  To Helpful
  Hostile             20             25              35           50
  Unfriendly          -              15              25           40
  Indifferent         -              -               15           30
  Friendly            -              -               -            20
One attempt per NPC per day. Failure by 5 or more drops the attitude one step. The proprietor adds +2 to the DC if they have Negotiator or Skill Focus (Profession) (approximation). Intimidate: opposed by 1d20 + proprietor level + Wis modifier; success treats the proprietor as Friendly for that transaction only, after which attitude drops to Unfriendly for 7 days; under high law level a reputation penalty also applies (approximation).

R4. Price by current attitude:
  Hostile        refuses to trade
  Unfriendly     +10% over list
  Indifferent    list price
  Friendly       -5% from list
  Helpful        -10% from list
Guild price floors (Table P) always apply as a minimum. Scarcity can add up to +25%. A relationship (repeat custom, 5 or more purchases) lifts attitude one step for pricing only.
Destitute: sellers may accept goods in kind at 50% value. Metropolis: haggling is impersonal; race, clan, and faith modifiers are halved; reputation modifiers doubled; guild floors stronger.
RNG for each roll is keyed seed + "disposition" or "diplomacy" + establishmentId + buyerId + attemptIndex.


S. Wealth Distribution
----------------------
- Bottom 60% of households: 20% of wealth
- Middle 30%: 35%
- Top 10%: 45%
Within each band, log-normal sigma = 0.8, scaled by wealth tier (Table AA) and profession income. Destitute: top band shifted down, distribution compressed toward subsistence, higher share at zero. Metropolis: bottom 60% = 15%, middle 30% = 30%, top 10% = 55%, with a small ultra-wealthy elite.
Stored wealth: part of each household's wealth is held as valuables (plate, gems, bullion, jewellery, fine cloth) valued at full anchor price: bottom band 5%, middle 20%, top 40% (approximation). The lord's treasury holds 30% of its coffers as valuables. Valuables count as luxury stock and are seized first by the Looting event and by raids.


T. Clannishness
---------------
Ordered ranking with numeric clannishness (0-1) (approximation):
  dwarf 0.9, elf 0.8, orc 0.75, gnome 0.7, halfling 0.6, half-orc 0.5, border human 0.45, half-elf 0.3, agrarian human 0.25.
Clan share, reputation, and influence on naming, patron deity, profession bias, and marriage scale with it. Metropolis fragments clans into neighbourhoods and guilds, reducing clannishness by 0.15. Clans dominating an export trade (dwarven metal, halfling pipe-weed, elven bows) gain outsized political weight.


U. Toggles
----------
  Toggle         Effect
  Magic level    low/normal/high; shifts caster levels -2/0/+2, derived spell ceiling (Table O); item supply is also limited by luxury stock (Table X)
  Law level      low/normal/high; shifts watch size, fines, guild power, rogue presence
  Trade route    none/minor/major; acts mostly on luxury goods availability, price, and export demand (Table AC), minor effect on crude import cost
  Monster threat low/normal/high; shifts castle chance, levy, watch, adventurers
  Castle chance  low/normal/high; multiplies castle chance by 0.5/1/1.5 (Table K)
  War            off/on; applies the War event (Table N) from tick 0
  Looting        off/on; applies the Looting event at tick 0 (equivalent to destitute input)


V. Household Production
-----------------------
Track householdProduction per household. Value brewing, spinning, dairying, and victualling at SRD craft rates x hours per week. Include child labour from about age 7. Contributes to household income, taxable wealth, and supply-chain inputs (ale, cloth, cheese, bread). Mainstay in thorpes and destitute settlements; largely displaced by workshops and guild production in metropolises but persists in poor quarters.

No double counting: hours worked for wages in an establishment (or unpaid in a household-owned establishment) count toward that establishment's production only. Household production covers only goods made outside establishment hours and consumed by the household or sold directly by it.


W. Half-Race Upbringing
-----------------------
upbringing = weighted choice: 60% majority household race, 30% clan race, 10% settlement race. Determines naming convention, faith inheritance, profession propensity. Half-races may use either parent race's override, chosen by upbringing.


X. Magic Item Prerequisites
---------------------------
Before offering a commission, verify: crafter has feat, required spell known/prepared, caster level >= item CL, establishment has tools, materials available via supply chain, settlement magic level permits.
At least half of the raw-material gp must come from luxury stock, priced at the Table AD anchors, by item type:
  weapons, armour: fine steel, precious metal, gems
  wands, rods, staffs: fine hardwood, precious metal, gems
  scrolls, potions: fine ink and pigments, gems, rare spices or incense
  rings, wondrous items: gems, precious metal, silk
If the luxury stock is short, the commission is refused or delayed until a caravan or route restock. A low trade route setting therefore limits magic item supply without a separate rule.


Y. Toggle Independence
----------------------
Toggles modify generation but never break determinism. Changes re-derive dependent outputs from the same seed.


Z. Exports of Surplus
---------------------
Surplus is what remains after local demand, seed stock, and defense stores are satisfied.

  surplus(good) = localProduction - localDemand - seedStock - defenseStores

Local demand includes household consumption, establishment inputs (Table AE), and government/defense needs. Seed stock is a reserve proportional to size and threat level.

Export capacity by size:
  Thorpe      negligible       pedlars or nearby market only; one or two goods
  Hamlet      low              local fair, occasional caravan
  Village     low-medium       weekly market, pedlar traffic
  Small town  medium           regional market, merchant guild
  Large town  medium-high      multiple routes, warehousing
  City        high             trade hub, foreign merchants
  Metropolis  very high        aggregates and re-exports surrounding settlements

Modify by trade access (Table AC export capacity multiplier). Locally producible luxuries (Table AD) are exportable and follow the trade route demand effect.

Wholesale price: SRD trade goods (Table AD anchors) are the exception to the half-price rule and export at full anchor value; transport, risk, and merchant profit come out of the export income split below, not out of the price. Goods not on the SRD trade goods table export at local retail x export factor (0.5-0.8; worse access = worse terms), always below local retail. Local retail of a locally abundant trade good is anchor x 0.5-0.8; of a scarce one, anchor x 1.0; an imported one costs anchor x import multiplier (Table AC).

Export income split (normalised to 100%):
  Producing households and establishments: 60-70%
  Merchant/transporter: 10-15%
  Guild fees: 5-8%
  Taxes and tithes: 5-8%
  Loss (spoilage, tolls, shrinkage): remainder, floor of 2%
If the four named shares sum above 98%, scale them proportionally so loss equals 2%.

External demand: set in phase 2 from context. Mining exports ore and imports grain; farming exports grain and imports iron; a coastal metropolis exports manufactures and imports raw materials. Premiums swing +/-30% with events.

Strategic controls: by law level and war/siege risk, the lord may forbid export of grain, weapons, horses, or naval stores. Forbidden exports become smuggling or black-market trade.

Unsold surplus: becomes stock, spoils at a rate set by the good (grain fast, metal not, silk slow), or is dumped locally, depressing local prices.

Special cases:
- Thorpe: minimal surplus, exported via pedlars or nearby fairs. May specialise in one good (charcoal, wool, fish); no merchant class.
- Destitute: no surplus; may export assets (livestock, tools, heirlooms) at distress prices (50% of wholesale, overriding the full-price rule). One-way drain until recovery.
- Metropolis: re-export formula applies in addition to the surplus formula:
    reExport(good) = hinterlandPurchases(good) - metropolisLocalDemand(good)
  Hinterland purchases are bought at hinterland wholesale and resold at that price x 1.10-1.25 (approximation), with income split as above. surplus() is still computed on own production only.

Export income concentrates in merchant households. Thriving export trade raises the merchant share and widens wealth spread; blocked trade compresses it and pushes artisans toward destitution.


SCALE
-----
Full individual stat blocks (npcs) are generated only for notable NPCs: proprietors, government officials, clergy heads, watch and garrison officers, guild masters, and a seeded sample of others. Commoners are represented as counts in households and labourAllocation, and are materialised on demand by a deterministic function of household id and seed. Export detail levels: summary, notable (default), full. The full level is allowed only for populations up to 2,000.


JSON OUTPUT STRUCTURE
---------------------
App output is a single JSON document. The outline below is for human reading and is not itself JSON. The shipped JSON Schema file (draft 2020-12) is authoritative. Each fact lives in one place; cross-references are by id.

  seed, inputs { size, terrain[], wealth, racialMakeup, rulingRaces, startSeason, toggles }
  settlement { id, size, wealth, population, context, climate, recentEvents[], recoveryState, districts[] (metropolis only) }
  demographics { racialBreakdown[], sexDistribution, ageBands, labourPool }
  households[]  { id, memberIds or memberSummary, wealth, professionId, dependents, householdProduction, supplyChainIds }
  families[], clans[], dependencyGraph
  culture { faith, alignment, namingProfile, socialClass }
  government { offices[], officialIds[], law, lawLevel, charterPolicy, watchMandate }
  guildCharters[]
  economy { resourceBase, externalDemand, imports[], exports[], initialDemand, supplyChainStructure, tradeBalance, prices, stock, coffers, taxes, upkeep, supplyChainState }
  professions[], labourAllocation
  establishments[] { id, type, name, ownerId (npc id), inventory, services, prices, supplyChainIds, srdRef }
  npcs[] { id, name, race, sex, class, level, profession, faith, alignmentBirth, alignmentCurrent, stats, equipment, dailyIncome, haggleStats { baseDisposition, negotiator, skills }, attitudeState, isProprietor, srdRef }
  defenses { garrison, levyIds or levyCount, equipment, upkeep, siegeStores }
  religion[] { id, deity, structure, clergy, buildings, services }
  catalogs { goods (category, price anchor, source rules), outfitTiers, gearSplit, professionInputs, services, hirelingCosts, itemCreationCosts }
  uiState

Common fields: id, type, name, tags, location, ownerId.
  Persons (npc) add: race, sex.
  Household: members, wealth, professionId, dependents, householdProduction, supplyChainIds. Households carry raceMix, not a single race or sex.
  Establishment: inventory, services, prices, supplyChainIds.
  Defense: garrison, levy, equipment, upkeep, siegeStores.
  Religion: deity, structure, clergy, buildings, services.
  Government: offices, officials, law, charters.
  Settlement: size, wealth, recentEvents, recoveryState, districts (metropolis only).
srdRef appears only on entities that map to SRD content: npcs (class), items, goods, services, spells, professions with an SRD equivalent. It does not appear on households, clans, or the settlement.
Entities have a genesis block and a state block (Principle 2). JSON must be stable, pretty-printable, and directly consumable by other tools. No trailing prose, no mixed formats.


RENAMING RULE
-------------
Keep SRD class, spell, magic item, and magical names verbatim. Rename only mundane items, goods, services, and professions to medieval English equivalents based on description (for example, longsword -> arming sword, chain shirt -> haubergeon, hemp rope -> hempen rope, inn -> hostelry). Keep the SRD name in hidden srdRef. Forgotten Realms deity names are kept verbatim.


UI
--
Single-screen establishment view:

  +--------------------+-----------------------------+
  | Proprietor card    | Tabs:                       |
  | Name, race, sex    | [Inventory][Services]       |
  | Class, level       | [Haggle][Hire]              |
  | Stat block         | [Spellcasting][Crafting]    |
  | Feats, skills      | Shared cart/session state   |
  | Disposition        |                             |
  +--------------------+-----------------------------+

The Haggle tab shows base disposition, current attitude, the Diplomacy DC for each possible shift, and the resulting price. Tabs share a session cart: buy items, hire NPCs, commission spells, commission items, negotiate price, all against the same proprietor. Flavour text varies and never repeats base data. Destitute establishments may show damage, depleted stock, or barter-only trade. Thorpes show no establishment screen for absent trades. Metropolises add a district filter and directory view by trade.

Export and copy actions produce JSON only (document or subtree), with the detail level selectable (see Scale).


ACCEPTANCE CRITERIA
-------------------
- Same seed + same inputs = same settlement, including the same names regardless of generation order.
- At genesis, population sums match racial makeup input exactly (largest-remainder rounding). Later changes are explained by the ledger.
- No phase requires backtracking; no genesis field is written after its phase completes. Every field has exactly one owning phase.
- Sex division of labour and class status are hard-coded as fixed male-share constants per class and profession, enforced via the stated precedence, with widow, heiress, and racial exceptions.
- Women's social class follows father, then husband; households are male-headed except per Table H3.
- Class and profession are separate attributes for every NPC.
- Birth alignment depends on race and clan only; faith derives from race -> clan -> alignment. No half-orc in civilisation is Evil.
- Every deity is from the Forgotten Realms pantheon list, has an alignment and SRD domains, and maps to a church template with distinct clergy nomenclature.
- SRD class, spell, magic item names preserved.
- Spell ceiling is derived from the highest caster level present and is reachable by the generated NPCs.
- Defense equipment, upkeep, fortifications, siege stores are part of the economy. Garrison pay is the SRD trained hireling rate.
- Every profession has crude and luxury inputs defined (Table AE); every good has a source rule (Tables AD, AF); a profession with unavailable crude inputs is dormant or substitutes, never silently supplied.
- Trade route toggle changes luxury availability, price, and demand far more than crude goods.
- Goods on the SRD trade goods table use SRD anchor prices and export at full value; luxury demand derives from outfit tiers (Table AG) and Table AE consumers, capped by Table AA.
- Masterwork is sold only by qualified establishments holding fine steel or fine hardwood; item creation draws at least half its raw materials from luxury stock.
- NPC gear is split per Table AH; valuables never exceed available luxury stock.
- Establishment screen combines stats, hiring, buying, disposition-based haggling, spell/item commissioning.
- Disposition is generated for every notable NPC, visible on its card, and drives price through attitude.
- Import and export flows vary by wealth, location, and external demand. Imports are capped by the import budget; tradeBalance is explicit and reconciles with coffers.
- Export income split sums to 100% in every case.
- Supply chains connect logically and affect prices and availability.
- All app output and export is JSON; the shipped schema is valid JSON Schema.
- SRD mechanics only for rules content; Forgotten Realms proper nouns appear only as deity names and flavour.
- Generated text never names England or real historical places.
- UI pleasant, searchable, non-repetitive.
- Separate RNG streams preserve determinism when phases, events, or UI actions are added.
- Thorpes generate without market, guild, watch, or permanent clergy unless a shrine-keeper is present, and with no merchant social class.
- Destitute settlements reflect recent looting: damaged establishments, depleted stores, halved defenses, broken trade, barter economy, recovery trajectory.
- Metropolises generate districts, grand temples or cathedrals, a university or scholarly college, national guilds, a permanent garrison, multiple watch companies, foreign quarters, and a wider wealth spread; clans fragment into neighbourhoods and guilds.
- Bishops appear only where a cathedral exists.
- Large populations export at notable level without exceeding practical document size.


DELIVERABLES
------------
- Working web app or generator script.
- Source code with README, and a single constants file holding all approximated values (male shares, disposition modifiers, luxury tables, terrain resources).
- JSON Schema (draft 2020-12) for all entities.
- Sample seeds and JSON outputs.
- Tests for: determinism (including generation-order independence of names), population sums at genesis, stat block validity, sex-labour and class enforcement and precedence, half-orc never Evil, phase dependency order and field ownership, genesis immutability, JSON schema conformance, trade balance and import budget, luxury-only effect of the trade route toggle, profession input coverage, export split normalisation, derived spell ceiling, garrison pay consistency, disposition and attitude-shift DCs, thorpe generation, metropolis district generation, destitute recovery, price anchor fidelity, full-price export of SRD trade goods, outfit-tier luxury demand, masterwork gating, item-creation luxury draw, and NPC gear split.

If a rule is ambiguous, choose a consistent 3.5-compatible approximation, document it in the constants file, and keep the simulation coherent.
