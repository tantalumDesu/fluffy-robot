// What a character's feats do. Pure helpers shared by the server, the sheet
// engine and the feat picker.

import type { Sheet } from "./engine";
import { hitDiceOf } from "./races";
import { ABILITY_NAME, SKILLS, describeMod, signed, type CharacterData, type Feat, type FeatTaken, type GameClass, type Modifier } from "./types";

/** A feat and what was chosen for it. */
export interface FeatPick {
  slug: string;
  choice: string;
}

export const FEAT_GROUPS: { key: Feat["group"]; label: string }[] = [
  { key: "general", label: "General feats" },
  { key: "fighter", label: "Fighter bonus feats" },
  { key: "metamagic", label: "Metamagic feats" },
  { key: "item", label: "Item creation feats" },
  { key: "special", label: "Special feats" },
  { key: "monster", label: "Monster feats" },
  { key: "epic", label: "Epic feats" },
];

export const SCHOOLS = ["Abjuration", "Conjuration", "Divination", "Enchantment", "Evocation", "Illusion", "Necromancy", "Transmutation"];

const skillName = (key: string): string => SKILLS.find((s) => s.key === key)?.name ?? key;

/** "Skill Focus (Spellcraft)", "Weapon Focus (Greatsword)", "Power Attack" */
export function featLabel(f: Pick<FeatTaken, "name" | "choice">): string {
  if (!f.choice) return f.name;
  return `${f.name} (${SKILLS.some((s) => s.key === f.choice) ? skillName(f.choice) : f.choice})`;
}

/** Does a feat taken for "greatsword" apply to the weapon called "+1 Greatsword"? */
export function weaponMatches(choice: string, weaponName: string): boolean {
  const norm = (s: string) => s.toLowerCase().replace(/[^a-z]+/g, "");
  const a = norm(choice);
  const b = norm(weaponName);
  return a.length > 2 && b.length > 2 && (a.includes(b) || b.includes(a));
}

/** What taking a feat (with a choice, if it asks for one) adds to a character. */
export function featTakenOf(feat: Feat, choice: string): FeatTaken {
  const picked = feat.choice ? choice.trim().slice(0, 40) : "";
  const mods: Modifier[] = [...feat.modifiers];
  if (feat.choice?.kind === "skill" && feat.choice.skillBonus && SKILLS.some((s) => s.key === picked)) {
    mods.push({ target: `skill:${picked}`, type: "untyped", value: feat.choice.skillBonus });
  }
  return {
    slug: feat.slug,
    name: feat.name,
    choice: picked,
    mods,
    weaponAttack: feat.choice?.kind === "weapon" ? feat.choice.weaponAttack : 0,
    weaponDamage: feat.choice?.kind === "weapon" ? feat.choice.weaponDamage : 0,
    benefit: feat.benefit,
  };
}

/** The chosen feats, as they are stored on a character. Feats not in the list are left out. */
export function applyFeats(data: CharacterData, picks: FeatPick[], all: Feat[]): CharacterData {
  const feats: FeatTaken[] = [];
  for (const p of picks) {
    const feat = all.find((f) => f.slug === p.slug);
    if (feat) feats.push(featTakenOf(feat, p.choice));
  }
  return { ...data, feats };
}

/** What a feat puts on the sheet by itself, in words; "" when it is only a reminder. */
export function featEffect(f: FeatTaken): string {
  const parts = f.mods.map(describeMod);
  if (f.weaponAttack) parts.push(`${signed(f.weaponAttack)} on attack rolls with ${f.choice || "the chosen weapon"}`);
  if (f.weaponDamage) parts.push(`${signed(f.weaponDamage)} on damage rolls with ${f.choice || "the chosen weapon"}`);
  return parts.join(", ");
}

export interface PrerequisiteCheck {
  text: string;
  /** true = met, false = not met, null = the app can't tell. */
  met: boolean | null;
  /** What the character has, when that helps ("you have 12"). */
  have: string;
}

/**
 * Checks a feat's prerequisites against a character. `sheet` is the sheet
 * without spell effects, so a temporary bonus doesn't qualify anyone.
 */
export function checkPrerequisites(feat: Feat, data: CharacterData, sheet: Sheet, taken: FeatPick[]): PrerequisiteCheck[] {
  return feat.prerequisites.map((p) => {
    const need = p.value ?? 0;
    switch (p.kind) {
      case "ability": {
        const score = p.ability ? sheet.abilities[p.ability].value : 0;
        return { text: p.ability ? `${ABILITY_NAME[p.ability]} ${need}` : p.text, met: score >= need, have: `you have ${score}` };
      }
      case "bab":
        return { text: p.text, met: sheet.bab.value >= need, have: `yours is ${signed(sheet.bab.value)}` };
      case "casterLevel": {
        const cl = data.castingStyle === "none" ? 0 : sheet.casterLevel.value;
        return { text: p.text, met: cl >= need, have: cl ? `yours is ${cl}` : "you don't cast spells" };
      }
      case "level": {
        const hd = hitDiceOf(data);
        return { text: p.text, met: hd >= need, have: `you are level ${hd}` };
      }
      case "classLevel": {
        // Known for certain only when classes were chosen from the list.
        if (data.classes.length) {
          const have = data.classes.find((c) => c.slug === p.className)?.level ?? 0;
          return { text: p.text, met: have >= need, have: have ? `you have ${have}` : `you have no ${p.className} levels` };
        }
        if (data.className.trim().toLowerCase() === p.className) return { text: p.text, met: data.level >= need, have: `you are level ${data.level}` };
        return { text: p.text, met: null, have: "choose your classes from the list to check this" };
      }
      case "skill": {
        const ranks = p.skill ? (data.skills[p.skill] ?? 0) : 0;
        return { text: p.text, met: ranks >= need, have: `you have ${ranks}` };
      }
      case "feat":
        return { text: p.text, met: taken.some((t) => t.slug === p.feat), have: "not taken" };
      default:
        return { text: p.text, met: null, have: "check this yourself" };
    }
  });
}

/**
 * How many feats a character of this level normally has: one, plus one per
 * three Hit Dice, plus a human's extra feat and the feats in the class
 * tables, whether a free choice ("Bonus feat") or a named feat (a wizard's
 * Scribe Scroll). A guide, not a limit.
 */
export function featsExpected(data: CharacterData, classes: GameClass[], feats: Feat[]): { total: number; parts: string[] } {
  const known = new Map(feats.map((f) => [f.name.toLowerCase(), f.name]));
  const hd = hitDiceOf(data);
  const parts = [`${1 + Math.floor(hd / 3)} for ${hd} Hit ${hd === 1 ? "Die" : "Dice"}`];
  let total = 1 + Math.floor(hd / 3);
  if (data.racial?.reminders.some((r) => /extra feat/i.test(r))) {
    total += 1;
    parts.push(`1 ${data.racial.name.toLowerCase()} bonus feat`);
  }
  for (const c of data.classes) {
    const cls = classes.find((k) => k.slug === c.slug);
    const rows = cls ? cls.levels.slice(0, c.level) : [];
    const bonus = rows.reduce((n, row) => n + (row.special.match(/\bbonus feat\b/gi)?.length ?? 0), 0);
    // Abilities in the table that are feats by name.
    const named = rows.flatMap((row) => row.special.split(/,\s*/).flatMap((item) => known.get(item.trim().toLowerCase()) ?? []));
    if (bonus) {
      total += bonus;
      parts.push(`${bonus} ${c.name.toLowerCase()} bonus feat${bonus === 1 ? "" : "s"}`);
    }
    if (named.length) {
      total += named.length;
      parts.push(`${named.join(" and ")} from ${c.name.toLowerCase()}`);
    }
  }
  return { total, parts };
}
