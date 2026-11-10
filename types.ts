// Shared vocabulary for the D&D 3.5 rules engine. Pure data + tiny helpers:
// safe to import from both server and client code.

export type Ability = "str" | "dex" | "con" | "int" | "wis" | "cha";
export const ABILITIES: readonly Ability[] = ["str", "dex", "con", "int", "wis", "cha"];
export const ABILITY_NAME: Record<Ability, string> = {
  str: "Strength",
  dex: "Dexterity",
  con: "Constitution",
  int: "Intelligence",
  wis: "Wisdom",
  cha: "Charisma",
};

export const BONUS_TYPES = [
  "enhancement",
  "morale",
  "luck",
  "insight",
  "sacred",
  "profane",
  "competence",
  "resistance",
  "deflection",
  "dodge",
  "armor",
  "armor_enh",
  "shield",
  "shield_enh",
  "natural",
  "natural_enh",
  "size",
  "circumstance",
  "alchemical",
  "racial",
  "untyped",
  "penalty",
] as const;
export type BonusType = (typeof BONUS_TYPES)[number];

export const BONUS_LABEL: Record<BonusType, string> = {
  enhancement: "enhancement",
  morale: "morale",
  luck: "luck",
  insight: "insight",
  sacred: "sacred",
  profane: "profane",
  competence: "competence",
  resistance: "resistance",
  deflection: "deflection",
  dodge: "dodge",
  armor: "armor",
  armor_enh: "armor enhancement",
  shield: "shield",
  shield_enh: "shield enhancement",
  natural: "natural armor",
  natural_enh: "natural armor enhancement",
  size: "size",
  circumstance: "circumstance",
  alchemical: "alchemical",
  racial: "racial",
  untyped: "untyped",
  penalty: "penalty",
};

export type Energy = "acid" | "cold" | "electricity" | "fire" | "sonic";
export const ENERGIES: readonly Energy[] = ["acid", "cold", "electricity", "fire", "sonic"];

export const CREATURE_TYPES = [
  "aberration",
  "animal",
  "construct",
  "dragon",
  "elemental",
  "fey",
  "giant",
  "humanoid",
  "magical beast",
  "monstrous humanoid",
  "ooze",
  "outsider",
  "plant",
  "undead",
  "vermin",
] as const;
export type CreatureType = (typeof CREATURE_TYPES)[number];
export const isCreatureType = (v: unknown): v is CreatureType => (CREATURE_TYPES as readonly unknown[]).includes(v);
/** "humanoids", "undead", "fey"... */
export const pluralType = (t: string): string => (t === "undead" || t === "vermin" || t === "fey" ? t : `${t}s`);

/** Subtypes that spells check for. */
export const SUBTYPES = ["extraplanar"] as const;

export const ALIGNMENTS = {
  LG: "Lawful Good",
  NG: "Neutral Good",
  CG: "Chaotic Good",
  LN: "Lawful Neutral",
  N: "Neutral",
  CN: "Chaotic Neutral",
  LE: "Lawful Evil",
  NE: "Neutral Evil",
  CE: "Chaotic Evil",
} as const;
export type Alignment = keyof typeof ALIGNMENTS;
export type AlignComponent = "good" | "evil" | "lawful" | "chaotic";
export const ALIGN_COMPONENTS: readonly AlignComponent[] = ["good", "evil", "lawful", "chaotic"];

export function alignmentParts(a: Alignment): AlignComponent[] {
  const out: AlignComponent[] = [];
  if (a.startsWith("L")) out.push("lawful");
  if (a.startsWith("C")) out.push("chaotic");
  if (a.endsWith("G")) out.push("good");
  if (a.endsWith("E")) out.push("evil");
  return out;
}

/** Accepts "NG", "Neutral Good", "chaotic evil", "True Neutral"... */
export function parseAlignment(value: unknown): Alignment {
  if (typeof value !== "string") return "N";
  const v = value.trim();
  if (v.toUpperCase() in ALIGNMENTS) return v.toUpperCase() as Alignment;
  const t = v.toLowerCase();
  const order = t.includes("lawful") ? "L" : t.includes("chaotic") ? "C" : "N";
  const moral = t.includes("good") ? "G" : t.includes("evil") ? "E" : "N";
  return (order === "N" && moral === "N" ? "N" : `${order}${moral}`) as Alignment;
}

/** Who a spell can affect. Comes from `targetRequirements` in the spell data. */
export interface TargetRequirements {
  creatureTypes?: CreatureType[];
  /** Not undead and not a construct. */
  living?: boolean;
  subtypes?: string[];
  /** Creatures with any of these alignment components are unaffected. */
  alignmentNot?: AlignComponent[];
  maxHitDice?: number;
}

/** "Humanoids only", "Living creatures with 4 HD or less"... */
export function describeRequirements(r: TargetRequirements): string {
  const who = r.creatureTypes?.length
    ? r.creatureTypes.map(pluralType).join(" or ")
    : r.subtypes?.length
      ? `${r.subtypes.join(" or ")} creatures`
      : "creatures";
  let s = `${r.living ? "living " : ""}${who}`;
  if (r.alignmentNot?.length) s += ` that are not ${r.alignmentNot.join(" or ")}`;
  if (r.maxHitDice != null) s += ` with ${r.maxHitDice} HD or less`;
  if (!r.alignmentNot?.length && r.maxHitDice == null) s += " only";
  return capitalize(s);
}

export const SIZE_NAMES = ["Fine", "Diminutive", "Tiny", "Small", "Medium", "Large", "Huge", "Gargantuan", "Colossal"] as const;

export interface SkillDef {
  key: string;
  name: string;
  ability: Ability;
  trained?: boolean;
  /** Armor check penalty multiplier (Swim takes it twice). */
  acp?: 1 | 2;
}

export const SKILLS: SkillDef[] = [
  { key: "appraise", name: "Appraise", ability: "int" },
  { key: "balance", name: "Balance", ability: "dex", acp: 1 },
  { key: "bluff", name: "Bluff", ability: "cha" },
  { key: "climb", name: "Climb", ability: "str", acp: 1 },
  { key: "concentration", name: "Concentration", ability: "con" },
  { key: "craft", name: "Craft", ability: "int" },
  { key: "decipher_script", name: "Decipher Script", ability: "int", trained: true },
  { key: "diplomacy", name: "Diplomacy", ability: "cha" },
  { key: "disable_device", name: "Disable Device", ability: "int", trained: true },
  { key: "disguise", name: "Disguise", ability: "cha" },
  { key: "escape_artist", name: "Escape Artist", ability: "dex", acp: 1 },
  { key: "forgery", name: "Forgery", ability: "int" },
  { key: "gather_information", name: "Gather Information", ability: "cha" },
  { key: "handle_animal", name: "Handle Animal", ability: "cha", trained: true },
  { key: "heal", name: "Heal", ability: "wis" },
  { key: "hide", name: "Hide", ability: "dex", acp: 1 },
  { key: "intimidate", name: "Intimidate", ability: "cha" },
  { key: "jump", name: "Jump", ability: "str", acp: 1 },
  { key: "knowledge_arcana", name: "Knowledge (arcana)", ability: "int", trained: true },
  { key: "knowledge_dungeoneering", name: "Knowledge (dungeoneering)", ability: "int", trained: true },
  { key: "knowledge_nature", name: "Knowledge (nature)", ability: "int", trained: true },
  { key: "knowledge_religion", name: "Knowledge (religion)", ability: "int", trained: true },
  { key: "knowledge_planes", name: "Knowledge (the planes)", ability: "int", trained: true },
  { key: "listen", name: "Listen", ability: "wis" },
  { key: "move_silently", name: "Move Silently", ability: "dex", acp: 1 },
  { key: "open_lock", name: "Open Lock", ability: "dex", trained: true },
  { key: "perform", name: "Perform", ability: "cha" },
  { key: "profession", name: "Profession", ability: "wis", trained: true },
  { key: "ride", name: "Ride", ability: "dex" },
  { key: "search", name: "Search", ability: "int" },
  { key: "sense_motive", name: "Sense Motive", ability: "wis" },
  { key: "sleight_of_hand", name: "Sleight of Hand", ability: "dex", trained: true, acp: 1 },
  { key: "spellcraft", name: "Spellcraft", ability: "int", trained: true },
  { key: "spot", name: "Spot", ability: "wis" },
  { key: "survival", name: "Survival", ability: "wis" },
  { key: "swim", name: "Swim", ability: "str", acp: 2 },
  { key: "tumble", name: "Tumble", ability: "dex", trained: true, acp: 1 },
  { key: "use_magic_device", name: "Use Magic Device", ability: "cha", trained: true },
  { key: "use_rope", name: "Use Rope", ability: "dex" },
];

export type Target =
  | Ability
  | "ac"
  | "attack"
  | "melee_attack"
  | "ranged_attack"
  | "damage"
  | "melee_damage"
  | "ranged_damage"
  | "saves"
  | "fort"
  | "ref"
  | "will"
  | "skills"
  | "initiative"
  | "speed"
  | "hp_max"
  | "caster_level"
  | "spell_dc"
  | "size"
  | "grapple"
  | `skill:${string}`;

const TARGET_LABELS: Record<string, string> = {
  str: "Strength",
  dex: "Dexterity",
  con: "Constitution",
  int: "Intelligence",
  wis: "Wisdom",
  cha: "Charisma",
  ac: "Armor Class",
  attack: "attack rolls",
  melee_attack: "melee attack rolls",
  ranged_attack: "ranged attack rolls",
  damage: "weapon damage",
  melee_damage: "melee damage",
  ranged_damage: "ranged damage",
  saves: "all saving throws",
  fort: "Fortitude saves",
  ref: "Reflex saves",
  will: "Will saves",
  skills: "all skill checks",
  initiative: "initiative",
  speed: "speed",
  hp_max: "maximum hit points",
  caster_level: "caster level",
  spell_dc: "spell save DCs",
  grapple: "grapple checks",
  size: "size category",
};

export function targetLabel(t: string): string {
  if (t.startsWith("skill:")) {
    const key = t.slice(6);
    return `${SKILLS.find((s) => s.key === key)?.name ?? key} checks`;
  }
  return TARGET_LABELS[t] ?? t;
}

export function isTarget(t: unknown): t is Target {
  if (typeof t !== "string") return false;
  if (t.startsWith("skill:")) return SKILLS.some((s) => s.key === t.slice(6));
  return t in TARGET_LABELS;
}

export const TARGET_OPTIONS: { value: Target; label: string }[] = [
  ...Object.keys(TARGET_LABELS).map((k) => ({ value: k as Target, label: capitalize(TARGET_LABELS[k]) })),
  ...SKILLS.map((s) => ({ value: `skill:${s.key}` as Target, label: `Skill: ${s.name}` })),
];

export interface Modifier {
  target: Target;
  type: BonusType;
  value: number;
  /** Size rolled when the effect is applied ("1d6"). `value` then only carries the sign. */
  dice?: string;
}

/** Everything a lasting effect does to a sheet, fully resolved at cast time. */
export interface EffectPayload {
  mods: Modifier[];
  conditions: string[];
  notes: string[];
  defenses: string[];
  tempHp?: { remaining: number; max: number };
  resist?: Partial<Record<Energy, number>>;
  absorb?: { energy: Energy; remaining: number; max: number };
  /** Ability scores forced down to a value (paralysis, feeblemind...). */
  overrides?: Partial<Record<Ability, number>>;
  speedMult?: number;
  loseDex?: boolean;
  babFull?: boolean;
  extraAttack?: boolean;
  sr?: number;
  /** Ability damage / negative levels accumulate instead of overlapping. */
  stacksWithSelf?: boolean;
}

export type EffectKind = "buff" | "debuff" | "neutral";
export type Tier = "curated" | "dataset" | "none";

export interface ActiveEffect {
  id: number;
  slug: string | null;
  name: string;
  origin: "self" | "other" | "custom";
  casterName: string;
  casterLevel: number;
  kind: EffectKind;
  tier: Tier | "custom";
  school: string;
  payload: EffectPayload;
  remainingRounds: number | null;
  totalRounds: number | null;
  durationLabel: string;
  suppressed: boolean;
  summary: string;
  /** Which version of the spell this is, when the spell has several. */
  variant: string | null;
}

export interface ArmorPiece {
  name: string;
  bonus: number;
  enh: number;
  maxDex: number | null;
  checkPenalty: number;
}

export interface GearItem {
  id: string;
  name: string;
  mods: Modifier[];
}

export interface Weapon {
  id: string;
  name: string;
  kind: "melee" | "ranged";
  enh: number;
  misc: number;
  dice: string;
  crit: string;
  twoHanded: boolean;
  strToDamage: boolean;
}

export type CastingStyle = "prepared" | "spontaneous" | "none";

export type SaveKey = "fort" | "ref" | "will";

/** Monster levels a race starts with (a bugbear's 3d8) and what they give. */
export interface RacialHitDice {
  count: number;
  die: number;
  baseAttack: number;
  fort: number;
  ref: number;
  will: number;
  skillPoints?: string;
  feats?: number;
}

/** A saving throw bonus against some spells only. `against`: "spells", "school:Illusion", "descriptor:Fear". */
export interface SaveBonus {
  against: string;
  value: number;
  type: BonusType;
  saves?: SaveKey[];
}

/** One entry of data/races.json. */
export interface Race {
  slug: string;
  name: string;
  /** "core" = on the Core (3.5) listing; "other" = added by name. */
  group: "core" | "other";
  edition: string | null;
  source: { book: string; abbreviation: string; page: number | null };
  url: string;
  alsoAppearsIn: string[];
  creatureType: CreatureType;
  subtypes: string[];
  size: string;
  speed: number;
  levelAdjustment: number;
  abilityAdjustments: Partial<Record<Ability, number>>;
  racialHitDice: RacialHitDice | null;
  naturalArmor: number;
  /** Racial bonuses that always apply, by skill key. */
  skillBonuses: Record<string, number>;
  modifiers: Modifier[];
  saveBonuses: SaveBonus[];
  senses: string[];
  resistances: Partial<Record<Energy, number>>;
  /** `perLevel` is added once per character level (total Hit Dice). */
  spellResistance: { base: number; perLevel: number } | null;
  /** Effect categories the race ignores ("sleep"). */
  immunities: string[];
  favoredClass: string;
  languages: { automatic: string[]; bonus: string[] };
  /** Situational traits: shown on the sheet, never added to a number. */
  reminders: string[];
  /** The page this entry was chosen in place of, when it isn't the one the listing links to. */
  replaces: string | null;
  /** A second source that fills gaps in the page: another page, or pasted text (data/races.supplements.json). */
  supplement: { from: string; kind: string; title: string; traits: string[] } | null;
  /** Values the page leaves out that come from the supplement. */
  fromSupplement: string[];
  /** Values no source states, entered from memory. */
  unverified: string[];
  differsFromPage: { field: string; page: string; used: string; reason: string }[];
  /** The racial traits and description exactly as the source page gives them. */
  traits: string[];
  traitsText: string;
  description: string;
}

/** What a chosen race adds to a character. Kept on the character and refreshed from the race file. */
export interface RacialTraits {
  slug: string;
  name: string;
  subtypes: string[];
  levelAdjustment: number;
  hitDice: RacialHitDice | null;
  /** Ability adjustments, natural armor and skill bonuses, as typed modifiers. */
  mods: Modifier[];
  saveBonuses: SaveBonus[];
  senses: string[];
  resist: Partial<Record<Energy, number>>;
  /** `perLevel` is added once per character level (total Hit Dice). */
  spellResistance: { base: number; perLevel: number } | null;
  immunities: string[];
  reminders: string[];
}

/** One level of a class, as its advancement table gives it. */
export interface ClassLevelRow {
  level: number;
  /** The level as the table words it ("7th"; "23rd" in an epic progression). */
  label: string;
  bab: number;
  fort: number;
  ref: number;
  will: number;
  special: string;
  /** Spells per day by spell level (index 0 = 0-level); null = cannot cast that level yet. */
  spells: (number | null)[] | null;
  spellsKnown?: (number | null)[];
  /** 1 when this level also counts as a level of an existing spellcasting class. */
  advance: number;
  /** Other columns of the table (a monk's unarmed damage, a dwarven defender's AC bonus). */
  other?: Record<string, string>;
}

export interface ClassCasting {
  ability: Ability;
  style: "prepared" | "spontaneous";
  type: "arcane" | "divine";
  /** Key of the class's spell list in the spell file. */
  list: string;
  casterLevel: "full" | "half";
  domainSlots: boolean;
}

/** One entry of data/classes.json. */
export interface GameClass {
  slug: string;
  name: string;
  /** phb = Player's Handbook; npc = NPC classes; prestige; epic = levels 21 and up. */
  group: "phb" | "npc" | "prestige" | "epic";
  prestige: boolean;
  source: { book: string; abbreviation: string; page: number | null };
  url: string;
  alsoAppearsIn: string[];
  /** The page a class was taken from when the listing does not have it. */
  addedFrom: string | null;
  hitDie: number;
  skillPoints: number;
  classSkills: string[];
  requirements: string | null;
  /** For an epic progression: the class it continues past 20th level. */
  continues: string | null;
  baseAttack: string;
  saves: { fort: string; ref: string; will: string };
  casting: ClassCasting | null;
  /** For a prestige class: which kind of existing spellcasting class its levels advance. */
  spellAdvance: { types: string[]; both: boolean; text: string } | null;
  levels: ClassLevelRow[];
  footnotes: string[];
  differsFromPage: { column: string; level: string; page: number; used: number; progression: string }[];
  unverified: string[];
  /** The class features as written on the source page. */
  features: string;
}

/** A class a character has levels in, with what those levels give. */
export interface ClassLevels {
  slug: string;
  name: string;
  level: number;
  hitDie: number;
  bab: number;
  fort: number;
  ref: number;
  will: number;
}

/** One requirement of a feat, in a form that can be checked against a character. */
export interface FeatPrerequisite {
  /** The requirement as written ("Dex 13", "base attack bonus +4"). */
  text: string;
  /** "other" = cannot be checked by the app (a fly speed, a class feature). */
  kind: "ability" | "bab" | "casterLevel" | "level" | "classLevel" | "skill" | "feat" | "other";
  ability?: Ability;
  value?: number;
  className?: string;
  skill?: string;
  /** Slug of the feat that is required. */
  feat?: string;
}

/** What a feat asks you to choose when you take it. */
export interface FeatChoice {
  kind: "skill" | "weapon" | "school" | "text";
  label: string;
  /** Added to the chosen skill (Skill Focus). */
  skillBonus: number;
  /** Added to a weapon of the chosen name on the sheet (Weapon Focus, Weapon Specialization). */
  weaponAttack: number;
  weaponDamage: number;
}

/** One entry of data/feats.json. */
export interface Feat {
  slug: string;
  name: string;
  type: string;
  group: "general" | "fighter" | "metamagic" | "item" | "special" | "monster" | "epic";
  source: { book: string; abbreviation: string; page: number | null };
  url: string;
  alsoAppearsIn: string[];
  /** The one-line description from the listing. */
  summary: string;
  prerequisite: string;
  /** "srd" = checked against the System Reference Document; "listing" = only the listing gives it. */
  prerequisiteFrom: "srd" | "listing" | "none";
  prerequisites: FeatPrerequisite[];
  /** What the listing's own Prerequisite field says, when it differs from the SRD. */
  listingPrerequisite: string | null;
  supplement: string | null;
  benefit: string;
  normal: string;
  special: string;
  description: string;
  /** Bonuses the feat always gives, added to the sheet. */
  modifiers: Modifier[];
  choice: FeatChoice | null;
  repeatable: boolean;
}

/** A feat a character has, with what it adds to the sheet. */
export interface FeatTaken {
  slug: string;
  name: string;
  /** What was chosen for it: a skill key, a weapon name, a school. Empty when the feat has no choice. */
  choice: string;
  mods: Modifier[];
  weaponAttack: number;
  weaponDamage: number;
  benefit: string;
}

export interface CharacterData {
  /** Feats chosen from the feat list. */
  feats: FeatTaken[];
  /** Classes chosen from the class list. Empty when class, level, base attack and saves are typed in by hand. */
  classes: ClassLevels[];
  /** Caster level worked out from the classes; null = use the character level. */
  casterLevel: number | null;
  race: string;
  /** Set when the race was chosen from the race list; null for a race typed in by hand. */
  racial: RacialTraits | null;
  className: string;
  /** Key used to look up spell levels in the spell list, e.g. "wizard". */
  classKey: string;
  level: number;
  alignment: Alignment;
  creatureType: CreatureType;
  subtypes: string[];
  size: number;
  abilities: Record<Ability, number>;
  hpMax: number;
  bab: number;
  baseSaves: { fort: number; ref: number; will: number };
  speed: number;
  armor: ArmorPiece;
  shield: ArmorPiece;
  naturalArmor: number;
  gear: GearItem[];
  weapons: Weapon[];
  skills: Record<string, number>;
  castingAbility: Ability | null;
  castingStyle: CastingStyle;
  slots: number[];
}

export interface CharacterState {
  id: number;
  name: string;
  data: CharacterData;
  damage: number;
  clock: number;
  slotsUsed: number[];
}

export interface SpellbookEntry {
  id: number;
  slug: string;
  name: string;
  level: number;
  prepared: number;
  used: number;
  school: string;
  tier: Tier;
  duration: string;
  range: string;
  save: string;
}

export interface LogEntry {
  id: number;
  clock: number;
  kind: string;
  text: string;
}

export interface AppState {
  character: CharacterState;
  effects: ActiveEffect[];
  spellbook: SpellbookEntry[];
  log: LogEntry[];
}

export interface CharacterSummary {
  id: number;
  name: string;
  summary: string;
}

/** Editable effect suggestion (from the data file, or typed in by hand). */
export interface Suggestion {
  mods: Modifier[];
  conditions: string[];
  /** Duration hint from the data file, in rounds. */
  rounds?: number;
  damage?: DamageSpec;
}

/** Damage defined in the spell file: "8d6" flat, or "1d8" per 2 levels up to 5 dice. */
export interface DamageSpec {
  /** "8d6", "20", or the dice gained at each step when `perLevels` is set. */
  dice: string;
  perLevels?: number;
  maxDice?: number;
  bonusPerLevel?: number;
  energy?: Energy;
}

/** One of several forms a spell can be cast in ("Fireworks" or "Smoke Cloud"). */
export interface SpellVariant {
  key: string;
  name: string;
  /** This version's paragraph of the spell description. */
  text: string;
  /** Only set where the version differs from the spell's own line. */
  save: string | null;
  sr: string | null;
  duration: string | null;
  suggestion: Suggestion | null;
  note: string;
  /** Checked by hand against the spell text (false = parser output only). */
  reviewed: boolean;
}

export interface CustomEffect {
  mods: Modifier[];
  conditions: string[];
  note: string;
  /** undefined = use the spell's own duration; null = until dismissed. */
  rounds?: number | null;
  damage?: DamageSpec;
}

export interface SpellListItem {
  slug: string;
  name: string;
  source: string;
  school: string;
  subschool: string;
  minLevel: number;
  levels: Record<string, number>;
  castingTime: string;
  range: string;
  duration: string;
  save: string;
  sr: string;
  tier: Tier;
  descriptors: string;
  requires: TargetRequirements | null;
  /** Names of the versions the spell file offers ("Fireworks", "Smoke Cloud"). */
  versions: string[];
}

export interface SpellDetail extends SpellListItem {
  sourcePage: string;
  classNames: Record<string, string>;
  components: string;
  target: string;
  targetKind: string;
  description: string;
  suggestion: Suggestion | null;
  variants: SpellVariant[];
}

export interface SpellMetaInfo {
  total: number;
  tiers: Record<Tier, number>;
  schools: string[];
  classes: { key: string; name: string; count: number }[];
}

export type SaveMode = "roll" | "fail" | "pass";

export type Action =
  | {
      type: "cast";
      slug: string | null;
      name?: string;
      /** Spellbook entry being cast (consumes a slot). */
      entryId?: number | null;
      targetSelf: boolean;
      origin: "self" | "other" | "custom";
      casterName?: string;
      cl: number;
      options?: Record<string, string>;
      saveMode: SaveMode;
      dc?: number;
      custom?: CustomEffect | null;
      /** Key of the chosen version, for spells that have several. */
      variant?: string | null;
    }
  | { type: "dismiss"; effectId: number }
  | { type: "toggle"; effectId: number }
  | { type: "clear" }
  | { type: "advance"; rounds: number }
  | { type: "rest" }
  | { type: "hp"; mode: "damage" | "heal"; amount: number; energy?: Energy | null }
  | { type: "book.add"; slug: string }
  | { type: "book.remove"; entryId: number }
  | { type: "book.prepare"; entryId: number; delta: number };

export interface ActionResult {
  state: AppState;
  events: { tone: "good" | "bad" | "info"; text: string }[];
}

// ---------------------------------------------------------------- helpers

export function capitalize(s: string): string {
  return s ? s[0].toUpperCase() + s.slice(1) : s;
}

/** +3 / −2 with a real minus sign. */
export function signed(n: number): string {
  return n >= 0 ? `+${n}` : `\u2212${Math.abs(n)}`;
}

export function ordinal(n: number): string {
  if (n === 0) return "0";
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return `${n}${s[(v - 20) % 10] ?? s[v] ?? s[0]}`;
}

/** A round is 6 seconds: 10 rounds per minute, 600 per hour. */
export function formatRounds(n: number): string {
  if (n < 10) return `${n} round${n === 1 ? "" : "s"}`;
  if (n < 600) {
    const m = Math.floor(n / 10);
    const r = n % 10;
    return r && m < 10 ? `${m} min ${r} rd` : `${m} min`;
  }
  if (n < 14400) {
    const h = Math.floor(n / 600);
    const m = Math.floor((n % 600) / 10);
    return m ? `${h} hr ${m} min` : `${h} hr`;
  }
  const d = Math.floor(n / 14400);
  const h = Math.floor((n % 14400) / 600);
  return h ? `${d} d ${h} hr` : `${d} day${d === 1 ? "" : "s"}`;
}

export function formatClock(rounds: number): string {
  const day = Math.floor(rounds / 14400) + 1;
  const secs = (rounds % 14400) * 6;
  const pad = (v: number) => String(v).padStart(2, "0");
  return `Day ${day} \u00b7 ${pad(Math.floor(secs / 3600))}:${pad(Math.floor((secs % 3600) / 60))}:${pad(secs % 60)}`;
}

export function describeMod(m: Modifier): string {
  if (m.target === "size") {
    const n = Math.abs(m.value);
    return `Size ${m.value > 0 ? "increases" : "decreases"} by ${n} categor${n === 1 ? "y" : "ies"}`;
  }
  const unit = m.target === "speed" ? " ft." : "";
  const tgt = targetLabel(m.target);
  if (m.value < 0 || m.type === "penalty") return `${signed(m.value)}${unit} penalty to ${tgt}`;
  const kind = m.type === "untyped" ? "" : `${BONUS_LABEL[m.type]} `;
  return `${signed(m.value)}${unit} ${kind}bonus to ${tgt}`;
}

/** "8d6" → 8 dice of 6; "1d4+1"; "20" → a flat 20 (sides 0). */
export function parseDice(text: string): { count: number; sides: number; bonus: number } | null {
  const m = /^\s*(\d{1,3})\s*(?:d\s*(\d{1,3}))?\s*(?:([+-])\s*(\d{1,4}))?\s*$/i.exec(text);
  if (!m) return null;
  return { count: Number(m[1]), sides: m[2] ? Number(m[2]) : 0, bonus: m[4] ? (m[3] === "-" ? -1 : 1) * Number(m[4]) : 0 };
}

/** "8d6", "1d8 per 2 levels (max 5d8)", "1d8 +1 per level fire" */
export function describeDamage(d: DamageSpec): string {
  const sides = parseDice(d.dice)?.sides ?? 0;
  let s = d.dice;
  if (d.perLevels) s += ` per ${d.perLevels === 1 ? "level" : `${d.perLevels} levels`}`;
  if (d.maxDice && sides) s += ` (max ${d.maxDice}d${sides})`;
  if (d.bonusPerLevel) s += ` +${d.bonusPerLevel} per level`;
  return d.energy ? `${s} ${d.energy}` : s;
}
