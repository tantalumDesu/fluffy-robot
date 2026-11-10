// Turns "spell X cast at caster level N on this character" into a concrete,
// fully resolved result. Used twice: on the client with an averaging roller
// (to preview what a spell will do) and on the server with real dice.

import { CONDITIONS } from "./conditions";
import { hitDiceOf } from "./races";
import {
  ABILITIES,
  ABILITY_NAME,
  ALIGNMENTS,
  ENERGIES,
  alignmentParts,
  describeMod,
  formatRounds,
  parseDice,
  pluralType,
  type Ability,
  type DamageSpec,
  type ActiveEffect,
  type Alignment,
  type CharacterState,
  type CreatureType,
  type CustomEffect,
  type EffectKind,
  type EffectPayload,
  type Energy,
  type Modifier,
  type TargetRequirements,
} from "./types";

export interface TargetInfo {
  hd: number;
  hp: number;
  speed: number;
  /** Slugs of spells currently affecting the target (for wards & counters). */
  activeSlugs: string[];
  type: CreatureType;
  subtypes: string[];
  alignment: Alignment;
  /** Not undead and not a construct. */
  living: boolean;
  /** Effect categories this creature type ignores ("mind", "sleep", "poison"...). */
  immunities: string[];
  /** Effect categories the character's race ignores (an elf and "sleep"). */
  racialImmunities: string[];
  raceName: string;
}

export interface OptionDef {
  key: string;
  label: string;
  choices: { value: string; label: string }[];
}

export interface SaveInfo {
  type: "fort" | "ref" | "will";
  on: "negates" | "half" | "partial";
}

/** A fixed save, no save (null), or one that depends on who is targeted. */
export type SaveRule = SaveInfo | null | ((t: TargetInfo) => SaveInfo | null);

export interface Ctx {
  cl: number;
  /** True when the target made its saving throw (only matters for "partial"). */
  saved: boolean;
  target: TargetInfo;
  opt: (key: string) => string;
  /** Roll `count` dice with `sides` sides and return the total. */
  d: (count: number, sides: number) => number;
}

export interface Out {
  mods?: Modifier[];
  conditions?: string[];
  notes?: string[];
  defenses?: string[];
  tempHp?: number;
  resist?: Partial<Record<Energy, number>>;
  absorb?: { energy: Energy; amount: number };
  overrides?: Partial<Record<Ability, number>>;
  speedMult?: number;
  loseDex?: boolean;
  babFull?: boolean;
  extraAttack?: boolean;
  sr?: number;
  stacksWithSelf?: boolean;
  heal?: number;
  damage?: { amount: number; energy?: Energy; minHp?: number };
  /** Duration override in rounds (null = until removed). Default: the spell's own duration. */
  rounds?: number | null;
  durationLabel?: string;
  /** Ends other effects on the target. */
  removes?: { slugs?: string[]; conditions?: string[] };
  /** Dispel check: 1d20 + caster level (capped at this value) vs 11 + each effect's caster level. */
  dispel?: number;
  /** Area dispel: strongest spell first, and stop after the first one that ends. */
  dispelOne?: boolean;
  /** Spells this one counters and dispels (haste vs slow...). */
  counters?: string[];
  noEffect?: string;
}

export interface SpellDef {
  kind: "buff" | "debuff" | "heal" | "damage" | "utility";
  summary: string;
  options?: OptionDef[];
  /** undefined = read it from the spell's data. */
  save?: SaveRule;
  /** Matched against wards on the target and against creature-type immunities. */
  tags?: string[];
  /** Overrides `kind` when a spell helps some creatures and harms others (cure spells vs undead). */
  hostileTo?: (t: TargetInfo) => boolean;
  build: (c: Ctx) => Out;
}

export interface SpellMeta {
  slug: string | null;
  name: string;
  duration: string;
  save: string;
  sr: string;
  /** "Fear, Mind-Affecting" */
  descriptors?: string;
  school?: string;
  requires?: TargetRequirements | null;
}

export interface Resolution {
  kind: EffectKind;
  noEffect: string | null;
  lines: string[];
  rolls: string[];
  payload: EffectPayload;
  /** Leaves a lasting effect on the sheet. */
  ongoing: boolean;
  rounds: number | null;
  durationLabel: string;
  heal: number;
  damage: { amount: number; energy: Energy | null; minHp: number | null } | null;
  removes: { slugs: string[]; conditions: string[] } | null;
  dispel: number | null;
  dispelOne: boolean;
  counters: string[];
}

export type Roller = (count: number, sides: number) => number;
export const averageRoller: Roller = (count, sides) => Math.floor((count * (sides + 1)) / 2);

// ------------------------------------------------------------ who can be affected

/**
 * Whole categories of effect that a creature type ignores (SRD creature type
 * traits). Spells are matched by their tags and by their descriptors.
 */
export const TYPE_IMMUNITIES: Partial<Record<CreatureType, string[]>> = {
  undead: ["mind", "sleep", "paralysis", "stun", "poison", "death", "fatigue"],
  construct: ["mind", "sleep", "paralysis", "stun", "poison", "death", "fatigue", "drain"],
  plant: ["mind", "sleep", "paralysis", "stun", "poison"],
  ooze: ["mind", "sleep", "paralysis", "stun", "poison"],
  vermin: ["mind"],
  elemental: ["sleep", "paralysis", "stun", "poison"],
  dragon: ["sleep", "paralysis"],
};

const IMMUNITY_LABEL: Record<string, string> = {
  mind: "mind-affecting effects",
  sleep: "sleep effects",
  paralysis: "paralysis",
  stun: "stunning",
  poison: "poison",
  death: "death effects",
  fatigue: "fatigue and exhaustion",
  drain: "energy drain",
};

/** Protective spells that make the target ignore whole categories of magic. */
export const WARDS: Record<string, { tags: string[]; text: string }> = {
  "death-ward": {
    tags: ["death", "drain", "negative"],
    text: "Death Ward makes you immune to death spells, energy drain and negative energy effects.",
  },
  "freedom-of-movement": { tags: ["movement"], text: "Freedom of Movement lets you ignore magic that impedes movement." },
  "mind-blank": { tags: ["mind"], text: "Mind Blank protects you from all mind-affecting spells and effects." },
  shield: { tags: ["magic-missile"], text: "Your Shield spell negates magic missile." },
};

const aCreature = (type: CreatureType): string => (type === "undead" ? "undead" : `${/^[aeiou]/.test(type) ? "an" : "a"} ${type}`);

export function targetInfoFor(c: CharacterState, hp: number, effects: ActiveEffect[]): TargetInfo {
  const d = c.data;
  return {
    hd: hitDiceOf(d),
    hp,
    speed: d.speed,
    activeSlugs: effects.flatMap((e) => (!e.suppressed && e.slug ? [e.slug] : [])),
    type: d.creatureType,
    subtypes: d.subtypes,
    alignment: d.alignment,
    living: d.creatureType !== "undead" && d.creatureType !== "construct",
    immunities: TYPE_IMMUNITIES[d.creatureType] ?? [],
    racialImmunities: d.racial?.immunities ?? [],
    raceName: d.racial?.name ?? "",
  };
}

/** Why this creature is not a legal target, or null when it is. */
export function checkRequirements(name: string, r: TargetRequirements | null | undefined, t: TargetInfo): string | null {
  if (!r) return null;
  const spell = name || "This spell";
  if (r.creatureTypes?.length && !r.creatureTypes.includes(t.type)) {
    return `${spell} only affects ${r.creatureTypes.map(pluralType).join(" and ")}, and you are ${aCreature(t.type)}.`;
  }
  if (r.living && !t.living) return `${spell} only affects living creatures, and you are ${aCreature(t.type)}.`;
  if (r.subtypes?.length && !r.subtypes.some((s) => t.subtypes.includes(s))) {
    return `${spell} only affects ${r.subtypes.join(" or ")} creatures.`;
  }
  if (r.alignmentNot?.length) {
    const parts = alignmentParts(t.alignment);
    const match = r.alignmentNot.find((a) => parts.includes(a));
    if (match) return `${spell} doesn't affect ${match} creatures, and you are ${ALIGNMENTS[t.alignment]}.`;
  }
  if (r.maxHitDice != null && t.hd > r.maxHitDice) {
    return `${spell} only affects creatures with ${r.maxHitDice} or fewer Hit Dice, and you have ${t.hd}.`;
  }
  return null;
}

/** Tags from the curated definition plus the ones implied by the spell's descriptors. */
export function spellTags(def: SpellDef | undefined, meta: Pick<SpellMeta, "descriptors">): string[] {
  const tags = new Set(def?.tags ?? []);
  const d = (meta.descriptors ?? "").toLowerCase();
  if (d.includes("mind-affecting")) tags.add("mind");
  if (d.includes("death")) tags.add("death");
  return [...tags];
}

/** A requirement, immunity or ward that stops the spell before it does anything. */
export function blockedReason(meta: SpellMeta, def: SpellDef | undefined, t: TargetInfo): string | null {
  const unmet = checkRequirements(meta.name, meta.requires, t);
  if (unmet) return unmet;
  const tags = spellTags(def, meta);
  const immune = tags.find((tag) => t.immunities.includes(tag));
  if (immune) return `As ${aCreature(t.type)}, you are immune to ${IMMUNITY_LABEL[immune] ?? immune}.`;
  const racial = tags.find((tag) => t.racialImmunities.includes(tag));
  if (racial) {
    const race = t.raceName.toLowerCase();
    return `As ${/^[aeiou]/.test(race) ? "an" : "a"} ${race}, you are immune to magic ${IMMUNITY_LABEL[racial] ?? racial}.`;
  }
  for (const slug of t.activeSlugs) {
    const ward = WARDS[slug];
    if (ward && ward.tags.some((tag) => tags.includes(tag))) return ward.text;
  }
  return null;
}

export function isHostile(def: SpellDef, t: TargetInfo): boolean {
  return def.hostileTo ? def.hostileTo(t) : def.kind === "debuff" || def.kind === "damage";
}

// ------------------------------------------------------------ durations & saves

const UNIT: Record<string, number> = { round: 1, minute: 10, hour: 600, day: 14400 };

export function parseDuration(
  text: string,
  cl: number,
  d: Roller,
): { rounds: number | null; instant: boolean; label: string } {
  const t = (text || "").toLowerCase().trim();
  if (!t) return { rounds: null, instant: false, label: "Until dismissed" };
  if (t.startsWith("instantaneous")) return { rounds: null, instant: true, label: "Instantaneous" };
  const timed = (n: number) => ({ rounds: Math.max(1, n), instant: false, label: formatRounds(Math.max(1, n)) });

  const per = /(\d+)\s*(round|minute|hour|day)s?\s*(?:\/|per)\s*(\d+)?\s*(?:caster\s+)?levels?/.exec(t);
  if (per) {
    const every = per[3] ? Number(per[3]) : 1;
    return timed(Number(per[1]) * UNIT[per[2]] * Math.max(1, Math.floor(cl / every)));
  }
  const dice = /(\d+)d(\d+)(?:\s*\+\s*(\d+))?\s*(round|minute|hour|day)s?/.exec(t);
  if (dice) {
    return timed((d(Number(dice[1]), Number(dice[2])) + Number(dice[3] ?? 0)) * UNIT[dice[4]]);
  }
  const fixed = /(\d+)\s*(round|minute|hour|day)s?/.exec(t);
  if (fixed) return timed(Number(fixed[1]) * UNIT[fixed[2]]);
  if (t.startsWith("permanent")) return { rounds: null, instant: false, label: "Permanent" };
  if (t.includes("concentration")) return { rounds: null, instant: false, label: "Concentration" };
  return { rounds: null, instant: false, label: text };
}

export function parseSave(text: string): SaveInfo | null {
  const m = /(will|fort|ref)\w*\s+(negates|half|partial|disbelief)/i.exec(text || "");
  if (!m) return null;
  const type = m[1].toLowerCase() as SaveInfo["type"];
  const word = m[2].toLowerCase();
  return { type, on: word === "half" ? "half" : word === "partial" ? "partial" : "negates" };
}

export const isHarmless = (meta: Pick<SpellMeta, "save" | "sr">): boolean =>
  /harmless/i.test(meta.save) || /harmless/i.test(meta.sr);

export const allowsSr = (meta: Pick<SpellMeta, "save" | "sr">): boolean =>
  /^\s*yes/i.test(meta.sr) && !isHarmless(meta);

export function saveFor(meta: SpellMeta, def: SpellDef | undefined, target: TargetInfo): SaveInfo | null {
  if (def && def.save !== undefined) return typeof def.save === "function" ? def.save(target) : def.save;
  return parseSave(meta.save);
}

// ------------------------------------------------------------ descriptions

/** Everything in a payload except its numeric modifiers, as readable lines. */
export function describeExtras(p: EffectPayload): string[] {
  const lines: string[] = [];
  for (const c of p.conditions) {
    const def = CONDITIONS[c];
    lines.push(def ? `${def.label}: ${def.text}` : c);
  }
  if (p.tempHp) {
    lines.push(
      p.tempHp.remaining === p.tempHp.max
        ? `${p.tempHp.max} temporary hit points`
        : `${p.tempHp.remaining} of ${p.tempHp.max} temporary hit points left`,
    );
  }
  if (p.babFull) lines.push("Base attack bonus equals your character level");
  if (p.extraAttack) lines.push("One extra attack at your highest bonus when making a full attack");
  if (p.sr) lines.push(`Spell resistance ${p.sr}`);
  if (p.speedMult && p.speedMult < 1) lines.push("Speed is halved");
  if (p.loseDex) lines.push("Loses Dexterity bonus to AC");
  if (p.overrides) {
    for (const a of ABILITIES) {
      const v = p.overrides[a];
      if (v != null) lines.push(`${ABILITY_NAME[a]} is treated as ${v}`);
    }
  }
  if (p.resist) {
    for (const en of ENERGIES) if (p.resist[en]) lines.push(`Resist ${en} ${p.resist[en]}`);
  }
  if (p.absorb) lines.push(`Absorbs the next ${p.absorb.remaining} points of ${p.absorb.energy} damage`);
  lines.push(...p.defenses, ...p.notes);
  return lines;
}

export function describePayload(p: EffectPayload): string[] {
  return [...p.mods.map(describeMod), ...describeExtras(p)];
}

/** One-line summary for logs and toasts (no rules text or notes). */
export function briefPayload(p: EffectPayload): string {
  const items: string[] = p.mods.map(describeMod);
  for (const c of p.conditions) items.push(CONDITIONS[c]?.label.toLowerCase() ?? c);
  if (p.tempHp) items.push(`${p.tempHp.max} temporary HP`);
  if (p.babFull) items.push("base attack equals character level");
  if (p.sr) items.push(`spell resistance ${p.sr}`);
  if (p.speedMult && p.speedMult < 1) items.push("half speed");
  if (p.overrides) {
    for (const a of ABILITIES) if (p.overrides[a] != null) items.push(`${ABILITY_NAME[a]} treated as ${p.overrides[a]}`);
  }
  if (p.resist) {
    for (const en of ENERGIES) if (p.resist[en]) items.push(`resist ${en} ${p.resist[en]}`);
  }
  if (p.absorb) items.push(`absorbs ${p.absorb.remaining} ${p.absorb.energy} damage`);
  items.push(...p.defenses);
  if (!items.length && p.notes.length) items.push(p.notes[0]);
  return items.length > 5 ? `${items.slice(0, 5).join(", ")} and ${items.length - 5} more` : items.join(", ");
}

function inferKind(p: EffectPayload): EffectKind {
  const bad =
    p.mods.some((m) => m.value < 0) ||
    p.conditions.some((c) => CONDITIONS[c]?.bad ?? true) ||
    !!p.overrides ||
    !!p.loseDex ||
    ((p.speedMult ?? 1) < 1 && p.conditions.length === 0);
  const good =
    p.mods.some((m) => m.value > 0) ||
    p.conditions.some((c) => CONDITIONS[c] && !CONDITIONS[c].bad) ||
    !!p.tempHp ||
    !!p.sr ||
    !!p.resist ||
    !!p.absorb ||
    p.defenses.length > 0;
  return bad && !good ? "debuff" : good && !bad ? "buff" : "neutral";
}

const KIND: Record<SpellDef["kind"], EffectKind> = {
  buff: "buff",
  debuff: "debuff",
  heal: "buff",
  damage: "debuff",
  utility: "neutral",
};

// ------------------------------------------------------------ resolution

export interface CastInput {
  cl: number;
  options: Record<string, string>;
  saved: boolean;
  custom?: CustomEffect | null;
}

/** A modifier written as dice ("-1d6 Strength") gets its size rolled now. */
function rollMod(m: Modifier, d: Roller): Modifier {
  const dice = m.dice ? parseDice(m.dice) : null;
  if (!dice || !dice.sides) return { target: m.target, type: m.type, value: m.value };
  const total = Math.max(1, d(dice.count, dice.sides) + dice.bonus);
  return { target: m.target, type: m.type, value: m.value < 0 ? -total : total };
}

/** Damage defined in the spell file: flat dice, or dice that grow with caster level. */
function rollDamage(spec: DamageSpec, cl: number, d: Roller): { amount: number; energy?: Energy } {
  const dice = parseDice(spec.dice);
  if (!dice) return { amount: 0 };
  let count = dice.count;
  if (spec.perLevels) count *= Math.max(1, Math.floor(cl / spec.perLevels));
  if (spec.maxDice) count = Math.min(count, spec.maxDice);
  const rolled = dice.sides ? d(count, dice.sides) : count;
  const amount = Math.max(0, rolled + dice.bonus + (spec.bonusPerLevel ?? 0) * cl);
  return spec.energy ? { amount, energy: spec.energy } : { amount };
}

export function resolveSpell(
  meta: SpellMeta,
  def: SpellDef | undefined,
  input: CastInput,
  target: TargetInfo,
  roll: Roller,
): Resolution {
  const rolls: string[] = [];
  const d: Roller = (count, sides) => {
    const total = roll(count, sides);
    rolls.push(`${count}d${sides} = ${total}`);
    return total;
  };
  const cl = Math.max(1, Math.floor(input.cl) || 1);
  const empty: EffectPayload = { mods: [], conditions: [], notes: [], defenses: [] };
  const result: Resolution = {
    kind: def ? KIND[def.kind] : "neutral",
    noEffect: null,
    lines: [],
    rolls,
    payload: empty,
    ongoing: false,
    rounds: null,
    durationLabel: "",
    heal: 0,
    damage: null,
    removes: null,
    dispel: null,
    dispelOne: false,
    counters: [],
  };

  // Not a legal target, immune by creature type, or protected by a ward.
  const blocked = blockedReason(meta, def, target);
  if (blocked) return { ...result, noEffect: blocked };

  const save = saveFor(meta, def, target);
  if (input.saved && save?.on === "negates") {
    return { ...result, noEffect: "The saving throw succeeded: the spell is negated." };
  }

  let out: Out;
  if (def) {
    out = def.build({
      cl,
      saved: input.saved,
      target,
      d,
      opt: (key) => input.options[key] ?? def.options?.find((o) => o.key === key)?.choices[0]?.value ?? "",
    });
  } else {
    const custom = input.custom;
    out = {
      mods: (custom?.mods ?? []).map((m) => rollMod(m, d)),
      conditions: custom?.conditions ?? [],
      notes: custom?.note ? [custom.note] : [],
    };
    if (custom?.damage) out.damage = rollDamage(custom.damage, cl, d);
    if (custom && custom.rounds !== undefined) out.rounds = custom.rounds;
  }
  if (out.noEffect) return { ...result, noEffect: out.noEffect };

  const payload: EffectPayload = {
    mods: (out.mods ?? []).filter((m) => m.value !== 0),
    conditions: out.conditions ?? [],
    notes: out.notes ?? [],
    defenses: out.defenses ?? [],
  };
  if (out.tempHp && out.tempHp > 0) payload.tempHp = { remaining: out.tempHp, max: out.tempHp };
  if (out.resist) payload.resist = out.resist;
  if (out.absorb) payload.absorb = { energy: out.absorb.energy, remaining: out.absorb.amount, max: out.absorb.amount };
  if (out.overrides) payload.overrides = out.overrides;
  if (out.speedMult) payload.speedMult = out.speedMult;
  if (out.loseDex) payload.loseDex = true;
  if (out.babFull) payload.babFull = true;
  if (out.extraAttack) payload.extraAttack = true;
  if (out.sr) payload.sr = out.sr;
  if (out.stacksWithSelf) payload.stacksWithSelf = true;

  const hasPayload =
    payload.mods.length > 0 ||
    payload.conditions.length > 0 ||
    payload.notes.length > 0 ||
    payload.defenses.length > 0 ||
    !!payload.tempHp ||
    !!payload.resist ||
    !!payload.absorb ||
    !!payload.overrides ||
    !!payload.speedMult ||
    !!payload.loseDex ||
    !!payload.babFull ||
    !!payload.sr;

  const parsed = parseDuration(meta.duration, cl, d);
  let rounds = parsed.rounds;
  let instant = parsed.instant;
  let label = parsed.label;
  if (out.rounds !== undefined) {
    rounds = out.rounds;
    instant = false;
    label = out.rounds === null ? "Until removed" : formatRounds(out.rounds);
  } else if (instant && hasPayload) {
    // An instantaneous spell with lasting consequences (ability damage...).
    instant = false;
    label = "Until removed";
  }
  if (out.durationLabel) label = out.durationLabel;

  const lines = describePayload(payload);

  let damage: Resolution["damage"] = null;
  if (out.damage && out.damage.amount > 0) {
    let amount = out.damage.amount;
    if (input.saved && save?.on === "half") amount = Math.floor(amount / 2);
    damage = { amount, energy: out.damage.energy ?? null, minHp: out.damage.minHp ?? null };
    lines.unshift(
      `${amount} ${out.damage.energy ? `${out.damage.energy} ` : ""}damage${input.saved && save?.on === "half" ? " (halved by the save)" : ""}`,
    );
  }
  const heal = Math.max(0, out.heal ?? 0);
  if (heal) lines.unshift(`Heals ${heal} hit points`);
  if (out.dispel) {
    lines.push(out.dispelOne ? "Dispel checks against the spells on you, strongest first, until one of them ends" : "Dispel check against every spell affecting you");
  }
  const removes =
    out.removes && ((out.removes.slugs?.length ?? 0) > 0 || (out.removes.conditions?.length ?? 0) > 0)
      ? { slugs: out.removes.slugs ?? [], conditions: out.removes.conditions ?? [] }
      : null;

  // What the spell turned out to be for this target: a cure spell is a
  // "heal", but it damages undead.
  let kind: EffectKind = def ? KIND[def.kind] : inferKind(payload);
  if (def?.kind === "utility") kind = inferKind(payload);
  if (!def && damage && !heal) kind = "debuff";
  if (def && (def.kind === "heal" || def.kind === "damage")) {
    if (damage && !heal) kind = "debuff";
    else if (heal && !damage) kind = "buff";
  }
  if (def?.hostileTo) kind = def.hostileTo(target) ? "debuff" : "buff";

  return {
    kind,
    noEffect: null,
    lines,
    rolls,
    payload,
    ongoing: !instant,
    rounds,
    durationLabel: label,
    heal,
    damage,
    removes,
    dispel: out.dispel ?? null,
    dispelOne: out.dispelOne === true,
    counters: out.counters ?? [],
  };
}
