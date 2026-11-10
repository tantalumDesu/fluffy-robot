// What a character's classes give: level, base attack, base saves and
// spellcasting. Pure helpers shared by the server, the sheet editor and the
// class picker.

import { abilityMod, computeSheet } from "./engine";
import { signed, type Ability, type CharacterData, type ClassLevels, type GameClass } from "./types";

/** A class and the number of levels taken in it. */
export interface ClassPick {
  slug: string;
  level: number;
}

const SAVE_NAME = { fort: "Fort", ref: "Ref", will: "Will" } as const;

/** "Wizard 7", or "Fighter 4 / Wizard 3" for a multiclass character. */
export function classLine(d: Pick<CharacterData, "className" | "level" | "classes">): string {
  if (d.classes.length > 1) return d.classes.map((c) => `${c.name} ${c.level}`).join(" / ");
  return `${d.className} ${d.level}`.trim();
}

/** "4d10 + 3d4" */
export function hitDiceLine(classes: ClassLevels[]): string {
  return classes.map((c) => `${c.level}d${c.hitDie}`).join(" + ");
}

/** "d4 · poor attack · good Will · arcane spells" */
export function describeClass(c: GameClass): string {
  const good = (["fort", "ref", "will"] as const).filter((k) => c.saves[k] === "good").map((k) => SAVE_NAME[k]);
  const parts = [`d${c.hitDie}`];
  if (c.group === "epic") parts.push("epic bonuses");
  else parts.push(`${c.baseAttack} attack`, good.length ? `good ${good.join(", ")}` : "no good save");
  if (c.casting) parts.push(`${c.casting.type} spells`);
  else if (c.spellAdvance) parts.push("advances spellcasting");
  return parts.join(" \u00b7 ");
}

/** What the chosen levels of each class give, read from the class tables. */
export function classLevelsOf(picks: ClassPick[], all: GameClass[]): ClassLevels[] {
  const out: ClassLevels[] = [];
  for (const p of picks) {
    const cls = all.find((c) => c.slug === p.slug);
    if (!cls || out.some((o) => o.slug === cls.slug)) continue;
    const level = Math.max(1, Math.min(cls.levels.length, Math.round(p.level) || 1));
    const row = cls.levels[level - 1];
    out.push({ slug: cls.slug, name: cls.name, level, hitDie: cls.hitDie, bab: row.bab, fort: row.fort, ref: row.ref, will: row.will });
  }
  return out;
}

export interface Spellcasting {
  cls: GameClass;
  /** Level used to read spells per day from the class table: own levels plus levels gained through prestige classes. */
  tableLevel: number;
  casterLevel: number;
  /** Prestige and epic classes whose levels count toward this class's spellcasting. */
  advancedBy: string[];
}

/**
 * The class a character casts spells as. The sheet tracks one spell list, so
 * with several casting classes the one with the most levels is used; prestige
 * classes that advance "an existing spellcasting class" add to it.
 */
export function spellcastingOf(levels: ClassLevels[], all: GameClass[]): Spellcasting | null {
  const find = (slug: string) => all.find((c) => c.slug === slug);
  let best: { cls: GameClass; own: number } | null = null;
  for (const l of levels) {
    const cls = find(l.slug);
    // A paladin below 4th level has no spells yet.
    if (!cls?.casting || !cls.levels[l.level - 1].spells?.some((n) => n != null)) continue;
    if (!best || l.level > best.own) best = { cls, own: l.level };
  }
  if (!best) return null;
  const casting = best.cls.casting;
  if (!casting) return null;
  let gained = 0;
  let epic = 0;
  const advancedBy: string[] = [];
  for (const l of levels) {
    const cls = find(l.slug);
    if (!cls || cls.slug === best.cls.slug) continue;
    if (cls.continues === best.cls.slug) {
      // Past 20th level the caster level keeps rising; spells per day do not.
      epic += l.level;
      advancedBy.push(cls.name);
    } else if (cls.spellAdvance?.types.includes(casting.type)) {
      const n = cls.levels.slice(0, l.level).reduce((sum, row) => sum + row.advance, 0);
      if (n) advancedBy.push(cls.name);
      gained += n;
    }
  }
  const own = casting.casterLevel === "half" ? Math.floor(best.own / 2) : best.own;
  return { cls: best.cls, tableLevel: Math.min(best.cls.levels.length, best.own + gained), casterLevel: own + gained + epic, advancedBy };
}

/**
 * Spells per day by spell level: the class table plus bonus spells for a high
 * ability score. A spell level needs a score of at least 10 + its level.
 */
export function slotsFor(cls: GameClass, tableLevel: number, score: number): number[] {
  const row = cls.levels[Math.max(1, Math.min(cls.levels.length, tableLevel)) - 1].spells ?? [];
  const mod = abilityMod(score);
  const slots = row.map((base, level) => {
    if (base == null || score < 10 + level) return 0;
    const bonus = level >= 1 && mod >= level ? 1 + Math.floor((mod - level) / 4) : 0;
    return base + bonus;
  });
  while (slots.length && !slots[slots.length - 1]) slots.pop();
  return slots;
}

/** The ability score spells are based on, with race and gear but without spell effects. */
function restingScore(data: CharacterData, ability: Ability): number {
  return computeSheet({ id: 0, name: "", data, damage: 0, clock: 0, slotsUsed: [] }, []).abilities[ability].value;
}

/**
 * Sets everything the chosen classes decide: level, class name, base attack
 * and base saves. With `fillSpellcasting` it also fills in how the character
 * casts and the spells per day, which stay editable afterwards (a specialist
 * wizard's extra slot, for example).
 */
export function applyClasses(data: CharacterData, picks: ClassPick[], all: GameClass[], fillSpellcasting: boolean): CharacterData {
  const classes = classLevelsOf(picks, all);
  if (!classes.length) return { ...data, classes: [], casterLevel: null };
  const sum = (key: "level" | "bab" | "fort" | "ref" | "will") => classes.reduce((n, c) => n + c[key], 0);
  const casting = spellcastingOf(classes, all);
  const next: CharacterData = {
    ...data,
    classes,
    level: sum("level"),
    className: classes.length === 1 ? classes[0].name : classes.map((c) => c.name).join(" / "),
    bab: sum("bab"),
    baseSaves: { fort: sum("fort"), ref: sum("ref"), will: sum("will") },
    casterLevel: casting ? casting.casterLevel : null,
  };
  if (!fillSpellcasting) return next;
  const how = casting?.cls.casting;
  if (!casting || !how) return { ...next, castingStyle: "none", castingAbility: null, slots: [] };
  return {
    ...next,
    castingStyle: how.style,
    castingAbility: how.ability,
    classKey: how.list,
    slots: slotsFor(casting.cls, casting.tableLevel, restingScore(next, how.ability)),
  };
}

/**
 * What a character's levels in a class have granted so far: the special
 * abilities from the class table, each with the level it came at, and the
 * current value of any other column (a monk's unarmed damage).
 */
export function featuresGained(level: ClassLevels, all: GameClass[]): { specials: string[]; now: string[] } {
  const cls = all.find((c) => c.slug === level.slug);
  if (!cls) return { specials: [], now: [] };
  const rows = cls.levels.slice(0, level.level);
  const current = rows[rows.length - 1];
  return {
    specials: rows.filter((r) => r.special).map((r) => `${r.special} (${r.label})`),
    now: Object.entries(current?.other ?? {}).map(([label, value]) => `${label} ${value}`),
  };
}

/** Why a class can't be added yet, for the one requirement that can be checked: epic progressions. */
export function unmetRequirement(cls: GameClass, picks: ClassPick[], all: GameClass[]): string | null {
  if (!cls.continues) return null;
  const base = all.find((c) => c.slug === cls.continues);
  const have = picks.find((p) => p.slug === cls.continues)?.level ?? 0;
  return have >= 20 ? null : `Needs 20 levels of ${base?.name ?? cls.continues} first${have ? ` (you have ${have})` : ""}.`;
}

/** "Base attack +5 · Fort +4, Ref +1, Will +5" */
export function totalsLine(classes: ClassLevels[]): string {
  const sum = (key: "bab" | "fort" | "ref" | "will") => classes.reduce((n, c) => n + c[key], 0);
  return `Base attack ${signed(sum("bab"))} \u00b7 Fort ${signed(sum("fort"))}, Ref ${signed(sum("ref"))}, Will ${signed(sum("will"))}`;
}
