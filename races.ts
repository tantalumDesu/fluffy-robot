// What a race does to a character. Pure helpers shared by the server, the
// sheet engine and the race picker.

import {
  ABILITIES,
  ENERGIES,
  SIZE_NAMES,
  SKILLS,
  capitalize,
  describeMod,
  signed,
  type Ability,
  type CharacterData,
  type Modifier,
  type Race,
  type RacialTraits,
  type SaveBonus,
} from "./types";

const ABILITY_SHORT: Record<Ability, string> = { str: "Str", dex: "Dex", con: "Con", int: "Int", wis: "Wis", cha: "Cha" };

/** "+2 Con, −2 Cha", or "" when the race changes no ability score. */
export function describeAdjustments(a: Partial<Record<Ability, number>>): string {
  return ABILITIES.flatMap((k) => (a[k] ? [`${signed(a[k] ?? 0)} ${ABILITY_SHORT[k]}`] : [])).join(", ");
}

/** "Humanoid (dwarf)" */
export function typeLine(creatureType: string, subtypes: string[]): string {
  return `${capitalize(creatureType)}${subtypes.length ? ` (${subtypes.join(", ")})` : ""}`;
}

export function sizeIndexOf(name: string): number {
  const i = (SIZE_NAMES as readonly string[]).indexOf(name);
  return i < 0 ? 4 : i;
}

/** Total Hit Dice: class levels plus any racial Hit Dice. */
export function hitDiceOf(d: Pick<CharacterData, "level" | "racial">): number {
  return d.level + (d.racial?.hitDice?.count ?? 0);
}

/** Everything a race adds to a character, in the form the sheet engine reads. */
export function racialTraitsOf(race: Race): RacialTraits {
  const mods: Modifier[] = [];
  for (const a of ABILITIES) {
    const value = race.abilityAdjustments[a];
    if (value) mods.push({ target: a, type: "racial", value });
  }
  if (race.naturalArmor > 0) mods.push({ target: "ac", type: "natural", value: race.naturalArmor });
  for (const [skill, value] of Object.entries(race.skillBonuses)) {
    if (value) mods.push({ target: `skill:${skill}`, type: "racial", value });
  }
  mods.push(...race.modifiers);
  return {
    slug: race.slug,
    name: race.name,
    subtypes: race.subtypes,
    levelAdjustment: race.levelAdjustment,
    hitDice: race.racialHitDice
      ? {
          count: race.racialHitDice.count,
          die: race.racialHitDice.die,
          baseAttack: race.racialHitDice.baseAttack,
          fort: race.racialHitDice.fort,
          ref: race.racialHitDice.ref,
          will: race.racialHitDice.will,
        }
      : null,
    mods,
    saveBonuses: race.saveBonuses,
    senses: race.senses,
    resist: race.resistances,
    spellResistance: race.spellResistance,
    immunities: race.immunities,
    reminders: race.reminders,
  };
}

/** The fields a race sets on a character when it is chosen. */
export function withRace(data: CharacterData, race: Race): CharacterData {
  return {
    ...data,
    race: race.name,
    racial: racialTraitsOf(race),
    size: sizeIndexOf(race.size),
    speed: race.speed,
    creatureType: race.creatureType,
  };
}

/**
 * A racial saving throw bonus that only counts against some spells: a dwarf's
 * +2 against spells, an elf's +2 against enchantments, a halfling's +2 morale
 * bonus against fear. Bonuses of a type already on the save don't stack with it.
 */
export function racialSaveBonus(
  racial: RacialTraits | null,
  stat: { parts: { type: string; value: number; applied: boolean }[] },
  save: "fort" | "ref" | "will",
  spell: { school: string; descriptors: string },
): { value: number; reason: string } {
  if (!racial) return { value: 0, reason: "" };
  const best = new Map<string, { value: number; against: string }>();
  const descriptors = spell.descriptors.toLowerCase().split(/,\s*/);
  for (const b of racial.saveBonuses) {
    if (b.saves && !b.saves.includes(save)) continue;
    const [kind, name = ""] = b.against.split(":");
    const applies =
      kind === "spells" ||
      (kind === "school" && spell.school.toLowerCase() === name.toLowerCase()) ||
      (kind === "descriptor" && descriptors.includes(name.toLowerCase()));
    if (!applies) continue;
    const against = kind === "spells" ? "spells" : `${name.toLowerCase()} ${kind === "school" ? "spells" : "effects"}`;
    const current = best.get(b.type);
    if (!current || b.value > current.value) best.set(b.type, { value: b.value, against });
  }
  let value = 0;
  const reasons: string[] = [];
  for (const [type, b] of best) {
    const already = Math.max(0, ...stat.parts.filter((p) => p.applied && p.type === type && p.value > 0).map((p) => p.value));
    if (b.value > already) {
      value += b.value - already;
      reasons.push(`${signed(b.value - already)} ${type} against ${b.against}`);
    }
  }
  return { value, reason: reasons.join(", ") };
}

// ---------------------------------------------------------------- descriptions

const SAVE_WORD = { fort: "Fortitude", ref: "Reflex", will: "Will" } as const;
const listOf = (items: string[]): string =>
  items.length <= 1 ? (items[0] ?? "") : `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;

/** "+2 racial bonus on saving throws against spells and spell-like effects" */
export function describeSaveBonus(b: SaveBonus): string {
  const [kind, name = ""] = b.against.split(":");
  const what = kind === "spells" ? "spells and spell-like effects" : kind === "school" ? `${name.toLowerCase()} spells and effects` : `${name.toLowerCase()} effects`;
  const saves = b.saves?.length ? `${listOf(b.saves.map((s) => SAVE_WORD[s]))} saves` : "saving throws";
  return `${signed(b.value)} ${b.type} bonus on ${saves} against ${what}`;
}

/** What a race gives besides plain modifiers: Hit Dice, senses, resistances, immunities. */
export function traitLines(r: RacialTraits): string[] {
  const lines: string[] = [];
  if (r.hitDice) {
    const h = r.hitDice;
    lines.push(`${h.count}d${h.die} racial Hit Dice: base attack ${signed(h.baseAttack)}, Fort ${signed(h.fort)}, Ref ${signed(h.ref)}, Will ${signed(h.will)}`);
  }
  for (const b of r.saveBonuses) lines.push(`${describeSaveBonus(b)} (counted when a spell is cast on you)`);
  const resist = ENERGIES.flatMap((e) => (r.resist[e] ? [`${e} ${r.resist[e]}`] : []));
  if (resist.length) lines.push(`Resist ${listOf(resist)}`);
  if (r.spellResistance) lines.push(`Spell resistance ${r.spellResistance.base}${r.spellResistance.perLevel ? " + character level" : ""}`);
  for (const i of r.immunities) lines.push(`Immune to magic ${i} effects`);
  if (r.senses.length) lines.push(r.senses.join(", "));
  return lines;
}

/** Everything a race puts on the sheet by itself, for the race picker. */
export function raceLines(race: Race): string[] {
  const lines: string[] = [];
  const adjustments = describeAdjustments(race.abilityAdjustments);
  if (adjustments) lines.push(`${adjustments} to your ability scores`);
  lines.push(`${race.size} size, speed ${race.speed} ft., ${typeLine(race.creatureType, race.subtypes).toLowerCase()}`);
  if (race.naturalArmor) lines.push(`${signed(race.naturalArmor)} natural armor`);
  const byValue = new Map<number, string[]>();
  for (const s of SKILLS) {
    const value = race.skillBonuses[s.key];
    if (value) byValue.set(value, [...(byValue.get(value) ?? []), s.name]);
  }
  for (const [value, names] of byValue) lines.push(`${signed(value)} racial bonus on ${listOf(names)} checks`);
  for (const m of race.modifiers) lines.push(describeMod(m));
  lines.push(...traitLines(racialTraitsOf(race)));
  return lines;
}
