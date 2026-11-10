import { SKILLS, type Ability, type Modifier, type Target } from "./types";

export interface ConditionDef {
  key: string;
  label: string;
  /** Rules reminder shown on the sheet. */
  text: string;
  bad: boolean;
  /** Conditions in a group overlap: only the highest rank applies its numbers. */
  group?: string;
  rank?: number;
  mods?: Modifier[];
  loseDex?: boolean;
  speedMult?: number;
  overrides?: Partial<Record<Ability, number>>;
}

const P = (target: Target, value: number): Modifier => ({ target, type: "penalty", value });

const strDexSkills: Modifier[] = SKILLS.filter((s) => s.ability === "str" || s.ability === "dex").map((s) =>
  P(`skill:${s.key}`, -4),
);
const fearMods: Modifier[] = [P("attack", -2), P("saves", -2), P("skills", -2)];

const list: ConditionDef[] = [
  {
    key: "blinded",
    label: "Blinded",
    bad: true,
    text: "\u22122 AC, loses Dex bonus to AC, half speed, \u22124 on Search and most Str/Dex skills. 50% miss chance on attacks; sight-based checks fail.",
    mods: [P("ac", -2), P("skill:search", -4), ...strDexSkills],
    loseDex: true,
    speedMult: 0.5,
  },
  {
    key: "dazzled",
    label: "Dazzled",
    bad: true,
    text: "\u22121 on attack rolls, Search checks, and Spot checks.",
    mods: [P("attack", -1), P("skill:search", -1), P("skill:spot", -1)],
  },
  {
    key: "deafened",
    label: "Deafened",
    bad: true,
    text: "\u22124 initiative. Automatically fails Listen checks; 20% failure chance on spells with verbal components.",
    mods: [P("initiative", -4)],
  },
  {
    key: "entangled",
    label: "Entangled",
    bad: true,
    text: "\u22122 attack, \u22124 Dexterity, half speed. Can't run or charge; Concentration DC 15 to cast.",
    mods: [P("attack", -2), P("dex", -4)],
    speedMult: 0.5,
  },
  {
    key: "fatigued",
    label: "Fatigued",
    bad: true,
    group: "fatigue",
    rank: 1,
    text: "\u22122 Strength and Dexterity. Can't run or charge. Removed by 8 hours of rest.",
    mods: [P("str", -2), P("dex", -2)],
  },
  {
    key: "exhausted",
    label: "Exhausted",
    bad: true,
    group: "fatigue",
    rank: 2,
    text: "\u22126 Strength and Dexterity, half speed.",
    mods: [P("str", -6), P("dex", -6)],
    speedMult: 0.5,
  },
  {
    key: "shaken",
    label: "Shaken",
    bad: true,
    group: "fear",
    rank: 1,
    text: "\u22122 on attack rolls, saving throws, skill checks, and ability checks.",
    mods: fearMods,
  },
  {
    key: "frightened",
    label: "Frightened",
    bad: true,
    group: "fear",
    rank: 2,
    text: "Flees from the source of fear as best it can. \u22122 on attack rolls, saves, skill checks, and ability checks.",
    mods: fearMods,
  },
  {
    key: "panicked",
    label: "Panicked",
    bad: true,
    group: "fear",
    rank: 3,
    text: "Drops anything held and flees at top speed. \u22122 on saves, skill checks, and ability checks; cowers if cornered.",
    mods: fearMods,
  },
  {
    key: "sickened",
    label: "Sickened",
    bad: true,
    text: "\u22122 on attack rolls, weapon damage, saving throws, skill checks, and ability checks.",
    mods: [P("attack", -2), P("damage", -2), P("saves", -2), P("skills", -2)],
  },
  {
    key: "nauseated",
    label: "Nauseated",
    bad: true,
    text: "Can't attack, cast spells, or concentrate. Only a single move action each turn.",
  },
  {
    key: "stunned",
    label: "Stunned",
    bad: true,
    text: "Drops everything held, can't act, \u22122 AC, loses Dex bonus to AC.",
    mods: [P("ac", -2)],
    loseDex: true,
  },
  {
    key: "dazed",
    label: "Dazed",
    bad: true,
    text: "Can take no actions, but has no penalty to AC.",
  },
  {
    key: "paralyzed",
    label: "Paralyzed",
    bad: true,
    text: "Helpless: can't move or act. Strength and Dexterity are treated as 0. Melee attackers get +4 and may coup de grace.",
    overrides: { str: 0, dex: 0 },
    loseDex: true,
  },
  {
    key: "asleep",
    label: "Asleep",
    bad: true,
    text: "Helpless: Dexterity treated as 0. Wakes if wounded, or if an ally spends a standard action.",
    overrides: { dex: 0 },
    loseDex: true,
  },
  {
    key: "helpless",
    label: "Helpless",
    bad: true,
    text: "Dexterity treated as 0. Melee attackers get +4 and may coup de grace.",
    overrides: { dex: 0 },
    loseDex: true,
  },
  {
    key: "petrified",
    label: "Petrified",
    bad: true,
    text: "Turned to stone and considered unconscious. Dexterity treated as 0.",
    overrides: { dex: 0 },
    loseDex: true,
  },
  {
    key: "prone",
    label: "Prone",
    bad: true,
    text: "\u22124 on melee attacks. +4 AC against ranged attacks but \u22124 AC against melee attacks.",
    mods: [P("melee_attack", -4)],
  },
  {
    key: "confused",
    label: "Confused",
    bad: true,
    text: "Roll d% each round: 01\u201310 attack caster, 11\u201320 act normally, 21\u201350 babble, 51\u201370 flee, 71\u2013100 attack nearest creature.",
  },
  {
    key: "fascinated",
    label: "Fascinated",
    bad: true,
    text: "Stands or sits quietly. \u22124 on skill checks made as reactions, such as Listen and Spot.",
    mods: [P("skill:listen", -4), P("skill:spot", -4)],
  },
  {
    key: "charmed",
    label: "Charmed",
    bad: true,
    text: "Regards the caster as a trusted friend and ally (attitude: friendly).",
  },
  {
    key: "dominated",
    label: "Dominated",
    bad: true,
    text: "The caster controls your actions through a telepathic link.",
  },
  {
    key: "ethereal",
    label: "Ethereal",
    bad: false,
    text: "On the Ethereal Plane: unseen and insubstantial, moving in any direction (even through solid objects) at half speed. You can't affect the Material Plane, and only force effects and other ethereal creatures can affect you.",
    speedMult: 0.5,
  },
  {
    key: "invisible",
    label: "Invisible",
    bad: false,
    text: "+2 on attack rolls against sighted opponents, who lose their Dex bonus to AC. +20 on Hide checks while moving (+40 if immobile).",
    mods: [{ target: "skill:hide", type: "untyped", value: 20 }],
  },
];

export const CONDITIONS: Record<string, ConditionDef> = Object.fromEntries(list.map((c) => [c.key, c]));
export const CONDITION_LIST: ConditionDef[] = list;
