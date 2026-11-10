// D&D 3.5 sheet calculator. Pure function of (character, active effects):
// it applies bonus-type stacking rules and returns every number together with
// the list of parts that built it, so the UI can explain any value.

import { CONDITIONS } from "./conditions";
import { featLabel, weaponMatches } from "./feats";
import { hitDiceOf } from "./races";
import {
  ABILITIES,
  ABILITY_NAME,
  BONUS_LABEL,
  ENERGIES,
  SIZE_NAMES,
  SKILLS,
  type Ability,
  type ActiveEffect,
  type BonusType,
  type CharacterState,
  type Energy,
  type Modifier,
  type Target,
  type Weapon,
  signed,
} from "./types";

export interface Part {
  label: string;
  type: BonusType | "base";
  value: number;
  applied: boolean;
  reason?: string;
  effectId?: number;
  /** Effects that influenced this part indirectly (e.g. through an ability score). */
  via?: number[];
  cls?: "armor" | "shield" | "natural" | "dex" | "dodge";
  source?: string;
  modKey?: string;
  /** Stacking already decided elsewhere; leave untouched. */
  fixed?: boolean;
}

export interface Stat {
  key: string;
  label: string;
  value: number;
  /** Value with no spell effects active (gear still counts). */
  base: number;
  parts: Part[];
  effectIds: number[];
}

export interface AbilityStat extends Stat {
  mod: number;
  baseMod: number;
}

export interface SkillStat extends Stat {
  skill: string;
  ability: Ability;
  ranks: number;
  usable: boolean;
}

export interface WeaponLine {
  id: string;
  name: string;
  kind: "melee" | "ranged";
  attack: Stat;
  damage: Stat;
  attackText: string;
  damageText: string;
  crit: string;
}

export interface ActiveCondition {
  key: string;
  label: string;
  text: string;
  bad: boolean;
  sources: string[];
  effectIds: number[];
}

export interface SheetLine {
  text: string;
  source: string;
  effectId: number;
}

export interface Sheet {
  abilities: Record<Ability, AbilityStat>;
  hpMax: Stat;
  hp: number;
  tempHp: number;
  hpStatus: "ok" | "disabled" | "dying" | "dead";
  ac: Stat;
  touch: Stat;
  flat: Stat;
  initiative: Stat;
  speed: Stat;
  bab: Stat;
  grapple: Stat;
  melee: Stat;
  ranged: Stat;
  damage: Stat;
  fort: Stat;
  ref: Stat;
  will: Stat;
  casterLevel: Stat;
  spellDc: Stat | null;
  sr: Stat;
  weapons: WeaponLine[];
  skills: SkillStat[];
  size: { index: number; name: string; base: number; effectIds: number[] };
  conditions: ActiveCondition[];
  defenses: SheetLine[];
  notes: SheetLine[];
  resist: Partial<Record<Energy, number>>;
  /** Per effect modifier ("effectId:index"): did it actually count? */
  report: Record<string, { applied: boolean; reason?: string }>;
}

const SIZE_MOD = [8, 4, 2, 1, 0, -1, -2, -4, -8];
const SIZE_GRAPPLE = [-16, -12, -8, -4, 0, 4, 8, 12, 16];
const SIZE_HIDE = [16, 12, 8, 4, 0, -4, -8, -12, -16];

/** Bonus types that always stack with themselves (from different sources). */
const ALWAYS_STACK = new Set<string>(["dodge", "untyped", "circumstance"]);

export const abilityMod = (score: number): number => Math.floor((score - 10) / 2);

type Report = Map<string, { applied: boolean; reason?: string }>;

interface SrcMod extends Modifier {
  label: string;
  source: string;
  effectId?: number;
  modKey?: string;
  via?: number[];
}

/**
 * The heart of 3.5 stacking:
 *  - typed bonuses of the same type don't stack: the highest wins
 *  - dodge, circumstance and untyped bonuses stack
 *  - penalties stack, but the same source never stacks with itself
 */
function stackParts(parts: Part[]): Part[] {
  const bySource = new Map<string, Part>();
  const bestOfType = new Map<string, Part>();
  for (const p of parts) {
    if (p.type === "base" || p.fixed || p.value === 0) continue;
    if (p.value < 0 || p.type === "penalty" || ALWAYS_STACK.has(p.type)) {
      const key = `${p.source ?? p.label}|${p.value < 0 ? "neg" : p.type}`;
      const prev = bySource.get(key);
      if (!prev) {
        bySource.set(key, p);
      } else if (Math.abs(p.value) > Math.abs(prev.value)) {
        prev.applied = false;
        prev.reason = "The same effect doesn't stack with itself; only the strongest applies";
        bySource.set(key, p);
      } else {
        p.applied = false;
        p.reason = "The same effect doesn't stack with itself; only the strongest applies";
      }
      continue;
    }
    const prev = bestOfType.get(p.type);
    const kind = BONUS_LABEL[p.type];
    if (!prev) {
      bestOfType.set(p.type, p);
    } else if (p.value > prev.value) {
      prev.applied = false;
      prev.reason = `Doesn't stack: ${p.label} gives a higher ${kind} bonus (${signed(p.value)})`;
      bestOfType.set(p.type, p);
    } else {
      p.applied = false;
      p.reason = `Doesn't stack with ${prev.label} (${signed(prev.value)} ${kind} bonus)`;
    }
  }
  return parts;
}

function finish(key: string, label: string, input: Part[], report: Report): Stat {
  const parts = stackParts(input);
  let value = 0;
  const ids = new Set<number>();
  for (const p of parts) {
    if (p.modKey) {
      const prev = report.get(p.modKey);
      if (!prev || !prev.applied) {
        report.set(p.modKey, p.applied ? { applied: true } : { applied: false, reason: p.reason });
      }
    }
    if (!p.applied) continue;
    value += p.value;
    if (p.effectId != null) ids.add(p.effectId);
    p.via?.forEach((i) => ids.add(i));
  }
  return { key, label, value, base: value, parts: parts.filter((p, i) => i === 0 || p.value !== 0), effectIds: [...ids] };
}

/** Re-total an already stacked stat with some parts excluded (touch / flat-footed AC). */
function derive(key: string, label: string, from: Stat, exclude: (p: Part) => boolean, reason: string): Stat {
  const parts = from.parts.map((p) => (p.applied && exclude(p) ? { ...p, applied: false, reason } : { ...p }));
  let value = 0;
  const ids = new Set<number>();
  for (const p of parts) {
    if (!p.applied) continue;
    value += p.value;
    if (p.effectId != null) ids.add(p.effectId);
    p.via?.forEach((i) => ids.add(i));
  }
  return { key, label, value, base: value, parts, effectIds: [...ids] };
}

/** Highest candidate wins, the rest are marked as not stacking. */
function chooseBest(cands: Part[], kind: string): Part | null {
  let best: Part | null = null;
  for (const p of cands) {
    p.fixed = true;
    if (p.value <= 0) {
      p.applied = false;
      continue;
    }
    if (!best) {
      best = p;
    } else if (p.value > best.value) {
      best.applied = false;
      best.reason = `Doesn't stack: ${p.label} gives a higher ${kind} (${signed(p.value)})`;
      best = p;
    } else {
      p.applied = false;
      p.reason = `Doesn't stack with ${best.label} (${signed(best.value)} ${kind})`;
    }
  }
  return best;
}

const base = (label: string, value: number, extra: Partial<Part> = {}): Part => ({
  label,
  type: "base",
  value,
  applied: true,
  ...extra,
});

function run(c: CharacterState, effects: ActiveEffect[], conRef: number | null): Sheet {
  const d = c.data;
  const report: Report = new Map();
  const live = effects.filter((e) => !e.suppressed);

  // ---- gather every modifier source -------------------------------------
  const mods: SrcMod[] = [];
  for (const g of d.gear) {
    for (const m of g.mods) mods.push({ ...m, label: g.name || "Gear", source: `gear:${g.id}` });
  }
  // The chosen race: ability adjustments, natural armor and skill bonuses.
  const racial = d.racial;
  const raceLabel = racial ? `${racial.name} (race)` : "";
  if (racial) for (const m of racial.mods) mods.push({ ...m, label: raceLabel, source: "race" });
  // Feats: untyped bonuses, so each feat stacks with everything else.
  d.feats.forEach((f, i) => {
    for (const m of f.mods) mods.push({ ...m, label: featLabel(f), source: `feat:${i}` });
  });
  const racialHd = racial?.hitDice ?? null;
  const totalHd = hitDiceOf(d);
  const racialHdLabel = racialHd ? `${racial?.name}: ${racialHd.count}d${racialHd.die} racial Hit Dice` : "";

  let loseDex: { label: string; id: number } | null = null;
  let speedMult: { value: number; label: string; id: number } = { value: 1, label: "", id: 0 };
  let babFull: { label: string; id: number } | null = null;
  let extraAttack = false;
  let sr: { value: number; label: string; id: number } | null = null;
  const overrides: Partial<Record<Ability, { value: number; label: string; id: number }>> = {};
  const setOverride = (a: Ability, value: number, label: string, id: number) => {
    const cur = overrides[a];
    if (!cur || value < cur.value) overrides[a] = { value, label, id };
  };

  const condMap = new Map<string, { sources: string[]; ids: number[] }>();
  for (const e of live) {
    const p = e.payload;
    const source = p.stacksWithSelf || !e.slug ? `fx:${e.id}` : `spell:${e.slug}`;
    p.mods.forEach((m, i) => mods.push({ ...m, label: e.name, source, effectId: e.id, modKey: `${e.id}:${i}` }));
    for (const k of p.conditions) {
      const entry = condMap.get(k) ?? { sources: [], ids: [] };
      entry.sources.push(e.name);
      entry.ids.push(e.id);
      condMap.set(k, entry);
    }
    if (p.loseDex && !loseDex) loseDex = { label: e.name, id: e.id };
    if (p.speedMult && p.speedMult < speedMult.value) speedMult = { value: p.speedMult, label: e.name, id: e.id };
    if (p.babFull && !babFull) babFull = { label: e.name, id: e.id };
    if (p.extraAttack) extraAttack = true;
    if (p.sr && (!sr || p.sr > sr.value)) sr = { value: p.sr, label: e.name, id: e.id };
    if (p.overrides) {
      for (const a of ABILITIES) {
        const v = p.overrides[a];
        if (v != null) setOverride(a, v, e.name, e.id);
      }
    }
  }

  // Conditions: overlapping ones (shaken / frightened / panicked) apply once.
  const groupTop = new Map<string, string>();
  for (const k of condMap.keys()) {
    const def = CONDITIONS[k];
    if (!def?.group) continue;
    const cur = groupTop.get(def.group);
    if (!cur || (CONDITIONS[cur].rank ?? 0) < (def.rank ?? 0)) groupTop.set(def.group, k);
  }
  const conditions: ActiveCondition[] = [];
  for (const [k, src] of condMap) {
    const def = CONDITIONS[k];
    conditions.push({
      key: k,
      label: def?.label ?? k,
      text: def?.text ?? "",
      bad: def?.bad ?? true,
      sources: src.sources,
      effectIds: src.ids,
    });
    if (!def) continue;
    const id = src.ids[0];
    if ((!def.group || groupTop.get(def.group) === k) && def.mods) {
      for (const m of def.mods) {
        mods.push({ ...m, label: `${def.label} (${src.sources[0]})`, source: `cond:${def.group ?? k}`, effectId: id, via: src.ids });
      }
    }
    if (def.loseDex && !loseDex) loseDex = { label: def.label, id };
    if (def.speedMult && def.speedMult < speedMult.value) speedMult = { value: def.speedMult, label: def.label, id };
    if (def.overrides) {
      for (const a of ABILITIES) {
        const v = def.overrides[a];
        if (v != null) setOverride(a, v, def.label, id);
      }
    }
  }

  const pick = (...targets: Target[]): Part[] =>
    mods
      .filter((m) => targets.includes(m.target))
      .map((m) => ({
        label: m.label,
        type: m.type,
        value: m.value,
        applied: true,
        source: m.source,
        effectId: m.effectId,
        modKey: m.modKey,
        via: m.via,
      }));

  // ---- ability scores ----------------------------------------------------
  const abilities = {} as Record<Ability, AbilityStat>;
  for (const a of ABILITIES) {
    const st = finish(a, ABILITY_NAME[a], [base("Base score", d.abilities[a]), ...pick(a)], report);
    if (st.value < 1) {
      st.parts.push(base("Penalties can't reduce a score below 1", 1 - st.value));
      st.value = 1;
    }
    const ov = overrides[a];
    if (ov && st.value > ov.value) {
      st.parts.push(base(`${ov.label}: treated as ${ov.value}`, ov.value - st.value, { effectId: ov.id }));
      st.value = ov.value;
      if (!st.effectIds.includes(ov.id)) st.effectIds.push(ov.id);
    }
    abilities[a] = { ...st, mod: abilityMod(st.value), baseMod: abilityMod(st.value) };
  }
  const abPart = (a: Ability): Part =>
    base(`${ABILITY_NAME[a]} modifier`, abilities[a].mod, { via: abilities[a].effectIds });

  // ---- size ---------------------------------------------------------------
  const sizeMods = mods.filter((m) => m.target === "size");
  const grow = Math.max(0, ...sizeMods.map((m) => m.value));
  const shrink = Math.min(0, ...sizeMods.map((m) => m.value));
  const sizeIndex = Math.max(0, Math.min(8, d.size + grow + shrink));
  const sizeIds = sizeMods.flatMap((m) => (m.effectId != null ? [m.effectId] : []));
  for (const m of sizeMods) if (m.modKey) report.set(m.modKey, { applied: true });
  const sizePart = (table: number[]): Part => base(`Size (${SIZE_NAMES[sizeIndex]})`, table[sizeIndex], { via: sizeIds });

  // ---- base attack --------------------------------------------------------
  // Chosen classes each contribute their own line; otherwise the typed total is used.
  const classParts = (key: "bab" | "fort" | "ref" | "will", label: string, typed: number): Part[] =>
    d.classes.length ? d.classes.map((c) => base(`${c.name} ${c.level}`, c[key])) : [base(label, typed)];
  const babParts: Part[] = classParts("bab", racialHd ? "Base attack bonus from class levels" : "Base attack bonus", d.bab);
  if (racialHd) babParts.push(base(racialHdLabel, racialHd.baseAttack));
  const ownBab = d.bab + (racialHd?.baseAttack ?? 0);
  if (babFull && totalHd > ownBab) {
    babParts.push(base(`${babFull.label}: equals character level`, totalHd - ownBab, { effectId: babFull.id }));
  }
  const bab = finish("bab", "Base attack bonus", babParts, report);
  const babPart = (): Part => base("Base attack bonus", bab.value, { via: bab.effectIds });

  // ---- armor class --------------------------------------------------------
  const acMods = pick("ac");
  const ofType = (t: BonusType, cls?: Part["cls"]) =>
    acMods.filter((p) => p.type === t).map((p) => ({ ...p, cls }));
  const acParts: Part[] = [base("Base", 10)];

  // Worn armor/shield (+ the best enhancement on it) competes with spells that
  // grant an armor/shield bonus outright (mage armor, shield): highest wins.
  const wornGroup = (
    worn: { name: string; bonus: number; enh: number },
    fallback: string,
    baseType: "armor" | "shield",
    enhType: "armor_enh" | "shield_enh",
  ) => {
    const name = worn.name || fallback;
    const wornPart: Part = { label: name, type: baseType, value: worn.bonus, applied: true, cls: baseType, fixed: true };
    const enh: Part[] = [];
    if (worn.enh > 0) {
      enh.push({ label: `${name} (magic ${signed(worn.enh)})`, type: enhType, value: worn.enh, applied: true, cls: baseType });
    }
    enh.push(...ofType(enhType, baseType));
    // Clothing counts as armor for magic vestment, but a shield has to exist.
    if (baseType === "shield" && worn.bonus <= 0) {
      for (const p of enh) {
        p.value = 0;
        p.reason = "No shield equipped";
      }
    }
    const bestEnh = chooseBest(enh, `enhancement bonus to ${baseType}`);
    const wornTotal = Math.max(0, worn.bonus) + (bestEnh?.value ?? 0);
    const others = ofType(baseType, baseType);
    const bestOther = chooseBest(others, `${baseType} bonus`);
    if (bestOther && bestOther.value > wornTotal) {
      for (const p of [wornPart, ...enh]) {
        if (p.applied && p.value > 0) {
          p.applied = false;
          p.reason = `Doesn't stack: ${bestOther.label} gives a higher ${baseType} bonus (${signed(bestOther.value)})`;
        }
      }
    } else if (bestOther) {
      bestOther.applied = false;
      bestOther.reason = `Doesn't stack with your worn ${baseType} (${signed(wornTotal)} ${baseType} bonus)`;
    }
    acParts.push(wornPart, ...enh, ...others);
  };
  wornGroup(d.armor, "Armor", "armor", "armor_enh");
  wornGroup(d.shield, "Shield", "shield", "shield_enh");

  const natural: Part[] = [];
  if (d.naturalArmor > 0) {
    natural.push({ label: "Natural armor", type: "natural", value: d.naturalArmor, applied: true, cls: "natural" });
  }
  natural.push(...ofType("natural", "natural"));
  chooseBest(natural, "natural armor bonus");
  const naturalEnh = ofType("natural_enh", "natural");
  chooseBest(naturalEnh, "enhancement bonus to natural armor");
  acParts.push(...natural, ...naturalEnh);

  let dexToAc = abilities.dex.mod;
  let dexLabel = "Dexterity modifier";
  if (d.armor.maxDex != null && dexToAc > d.armor.maxDex) {
    dexToAc = d.armor.maxDex;
    dexLabel = `Dexterity modifier (armor caps it at ${signed(d.armor.maxDex)})`;
  }
  const dexPart = base(dexLabel, dexToAc, { via: abilities.dex.effectIds, cls: "dex" });
  const dexDenied = loseDex !== null && dexToAc > 0;
  if (loseDex && dexDenied) {
    dexPart.applied = false;
    dexPart.reason = `Dexterity bonus to AC is lost (${loseDex.label})`;
  }
  acParts.push(dexPart, sizePart(SIZE_MOD));

  const special = new Set<string>(["armor", "armor_enh", "shield", "shield_enh", "natural", "natural_enh"]);
  for (const p of acMods) {
    if (special.has(p.type)) continue;
    if (p.type === "dodge" && p.value > 0) {
      p.cls = "dodge";
      if (loseDex) {
        p.applied = false;
        p.fixed = true;
        p.reason = `Dodge bonuses are lost with your Dexterity bonus (${loseDex.label})`;
      }
    }
    acParts.push(p);
  }
  const ac = finish("ac", "Armor Class", acParts, report);
  if (loseDex && (dexDenied || acParts.some((p) => p.cls === "dodge")) && !ac.effectIds.includes(loseDex.id)) {
    ac.effectIds.push(loseDex.id);
  }
  const touch = derive(
    "touch",
    "Touch AC",
    ac,
    (p) => p.cls === "armor" || p.cls === "shield" || p.cls === "natural",
    "Armor, shield and natural armor don't apply against touch attacks",
  );
  const flat = derive(
    "flat",
    "Flat-footed AC",
    ac,
    (p) => p.cls === "dodge" || (p.cls === "dex" && p.value > 0),
    "Lost while flat-footed",
  );

  // ---- saves, initiative, speed --------------------------------------------
  const save = (k: "fort" | "ref" | "will", label: string, a: Ability) =>
    finish(
      k,
      label,
      [...classParts(k, racialHd ? "Base save from class levels" : "Base save", d.baseSaves[k]), ...(racialHd ? [base(racialHdLabel, racialHd[k])] : []), abPart(a), ...pick("saves", k)],
      report,
    );
  const fort = save("fort", "Fortitude", "con");
  const ref = save("ref", "Reflex", "dex");
  const will = save("will", "Will", "wis");

  const initiative = finish("initiative", "Initiative", [abPart("dex"), ...pick("initiative")], report);

  const speed = finish("speed", "Speed", [base("Base speed", d.speed), ...pick("speed")], report);
  if (speedMult.value < 1) {
    const next = Math.max(5, Math.floor((speed.value * speedMult.value) / 5) * 5);
    speed.parts.push(base(`Reduced (${speedMult.label})`, next - speed.value, { effectId: speedMult.id }));
    speed.value = next;
    if (!speed.effectIds.includes(speedMult.id)) speed.effectIds.push(speedMult.id);
  }

  // ---- attacks -------------------------------------------------------------
  const attackParts = (melee: boolean, w?: Weapon): Part[] => {
    const ps: Part[] = [babPart(), abPart(melee ? "str" : "dex"), sizePart(SIZE_MOD)];
    if (w && w.enh) {
      ps.push({ label: `${w.name} (magic ${signed(w.enh)})`, type: "enhancement", value: w.enh, applied: true, source: `weapon:${w.id}` });
    }
    if (w && w.misc) {
      ps.push({ label: `${w.name} (focus / masterwork)`, type: "untyped", value: w.misc, applied: true, source: `weapon-misc:${w.id}` });
    }
    // Weapon Focus and the like, taken for a weapon of this name.
    if (w) {
      for (const f of d.feats) {
        if (f.weaponAttack && weaponMatches(f.choice, w.name)) ps.push({ label: featLabel(f), type: "untyped", value: f.weaponAttack, applied: true, source: `feat-weapon:${f.slug}` });
      }
    }
    ps.push(...pick("attack", melee ? "melee_attack" : "ranged_attack"));
    return ps;
  };
  const damageParts = (melee: boolean, w?: Weapon): Part[] => {
    const ps: Part[] = [];
    const strMod = abilities.str.mod;
    if (melee) {
      const two = w?.twoHanded && strMod > 0;
      ps.push(
        base(two ? "Strength modifier \u00d71\u00bd (two-handed)" : "Strength modifier", two ? Math.floor(strMod * 1.5) : strMod, {
          via: abilities.str.effectIds,
        }),
      );
    } else {
      ps.push(base("Strength modifier", w?.strToDamage ? strMod : 0, { via: w?.strToDamage ? abilities.str.effectIds : [] }));
    }
    if (w && w.enh) {
      ps.push({ label: `${w.name} (magic ${signed(w.enh)})`, type: "enhancement", value: w.enh, applied: true, source: `weapon:${w.id}` });
    }
    if (w) {
      for (const f of d.feats) {
        if (f.weaponDamage && weaponMatches(f.choice, w.name)) ps.push({ label: featLabel(f), type: "untyped", value: f.weaponDamage, applied: true, source: `feat-weapon:${f.slug}` });
      }
    }
    ps.push(...pick("damage", melee ? "melee_damage" : "ranged_damage"));
    return ps;
  };

  const melee = finish("melee", "Melee attack", attackParts(true), report);
  const ranged = finish("ranged", "Ranged attack", attackParts(false), report);
  const damage = finish("damage", "Melee damage bonus", damageParts(true), report);
  const grapple = finish("grapple", "Grapple", [babPart(), abPart("str"), sizePart(SIZE_GRAPPLE), ...pick("grapple")], report);

  const iteratives = Math.min(4, bab.value >= 1 ? Math.floor((bab.value - 1) / 5) + 1 : 1);
  const weapons: WeaponLine[] = d.weapons.map((w) => {
    const isMelee = w.kind === "melee";
    const attack = finish(`weapon:${w.id}:attack`, `${w.name} attack`, attackParts(isMelee, w), report);
    const dmg = finish(`weapon:${w.id}:damage`, `${w.name} damage`, damageParts(isMelee, w), report);
    const seq = Array.from({ length: iteratives }, (_, i) => attack.value - 5 * i);
    if (extraAttack) seq.unshift(attack.value);
    return {
      id: w.id,
      name: w.name,
      kind: w.kind,
      attack,
      damage: dmg,
      attackText: seq.map(signed).join("/"),
      damageText: `${w.dice}${dmg.value ? signed(dmg.value) : ""}`,
      crit: w.crit,
    };
  });

  // ---- skills ----------------------------------------------------------------
  const acp = -Math.abs(d.armor.checkPenalty || 0) - Math.abs(d.shield.checkPenalty || 0);
  const skills: SkillStat[] = SKILLS.map((s) => {
    const ranks = d.skills[s.key] ?? 0;
    const ps: Part[] = [base("Ranks", ranks), abPart(s.ability)];
    if (s.acp && acp) ps.push(base(s.acp === 2 ? "Armor check penalty \u00d72" : "Armor check penalty", acp * s.acp));
    if (s.key === "hide") ps.push(sizePart(SIZE_HIDE));
    if (s.key === "jump") {
      const steps = Math.floor((speed.value - 30) / 10);
      ps.push(base(`Speed ${speed.value} ft.`, steps > 0 ? steps * 4 : steps * 6, { via: speed.effectIds }));
    }
    ps.push(...pick("skills", `skill:${s.key}`));
    const st = finish(`skill:${s.key}`, s.name, ps, report);
    return { ...st, skill: s.key, ability: s.ability, ranks, usable: !s.trained || ranks > 0 };
  });

  // ---- hit points ------------------------------------------------------------
  const conMod = abilities.con.mod;
  const refCon = conRef ?? conMod;
  const hpParts: Part[] = [base("Hit points on your sheet", d.hpMax)];
  if (conMod !== refCon) {
    hpParts.push(
      base(`Constitution modifier ${signed(conMod - refCon)} \u00d7 ${totalHd} Hit Dice`, (conMod - refCon) * totalHd, {
        via: abilities.con.effectIds,
      }),
    );
  }
  hpParts.push(...pick("hp_max"));
  const hpMax = finish("hp_max", "Maximum hit points", hpParts, report);
  if (hpMax.value < 1) hpMax.value = 1;
  const hp = hpMax.value - c.damage;
  let tempHp = 0;
  for (const e of live) tempHp += e.payload.tempHp?.remaining ?? 0;
  const hpStatus = hp <= -10 ? "dead" : hp < 0 ? "dying" : hp === 0 ? "disabled" : "ok";

  // ---- spellcasting ------------------------------------------------------------
  const casterLevel = finish(
    "caster_level",
    "Caster level",
    [base(d.casterLevel != null ? "Caster level from your classes" : `${d.className || "Class"} level`, d.casterLevel ?? d.level), ...pick("caster_level")],
    report,
  );
  if (casterLevel.value < 0) casterLevel.value = 0;
  const spellDc = d.castingAbility
    ? finish("spell_dc", "Spell save DC", [base("Base", 10), abPart(d.castingAbility), ...pick("spell_dc")], report)
    : null;

  // Spell resistance from different sources doesn't stack: the highest applies.
  const racialSr = racial?.spellResistance ? racial.spellResistance.base + racial.spellResistance.perLevel * totalHd : 0;
  const srParts: Part[] = [];
  if (racial?.spellResistance) {
    const rule = `${racial.spellResistance.base}${racial.spellResistance.perLevel ? " + character level" : ""}`;
    srParts.push(base(`${raceLabel}: ${rule}`, racialSr));
  }
  if (sr) srParts.push(base(sr.label, sr.value, { effectId: sr.id }));
  const srValue = Math.max(racialSr, sr?.value ?? 0);
  for (const p of srParts) {
    if (p.value < srValue || (p.effectId == null && sr && sr.value === srValue && racialSr === srValue)) {
      p.applied = false;
      p.reason = "Spell resistance doesn't stack: the highest applies";
    }
  }
  const srStat: Stat = {
    key: "sr",
    label: "Spell resistance",
    value: srValue,
    base: 0,
    parts: srParts.length ? srParts : [base("None", 0)],
    effectIds: sr && sr.value === srValue ? [sr.id] : [],
  };

  // ---- text lines ----------------------------------------------------------------
  const defenses: SheetLine[] = [];
  const notes: SheetLine[] = [];
  const resist: Partial<Record<Energy, number>> = {};
  for (const e of live) {
    const p = e.payload;
    for (const text of p.defenses) defenses.push({ text, source: e.name, effectId: e.id });
    for (const text of p.notes) notes.push({ text, source: e.name, effectId: e.id });
    if (p.absorb && p.absorb.remaining > 0) {
      defenses.push({
        text: `Absorbs the next ${p.absorb.remaining} points of ${p.absorb.energy} damage`,
        source: e.name,
        effectId: e.id,
      });
    }
    if (p.resist) {
      for (const en of ENERGIES) {
        const v = p.resist[en];
        if (!v) continue;
        defenses.push({ text: `Resist ${en} ${v}`, source: e.name, effectId: e.id });
        if (v > (resist[en] ?? 0)) resist[en] = v;
      }
    }
  }

  return {
    abilities,
    hpMax,
    hp,
    tempHp,
    hpStatus,
    ac,
    touch,
    flat,
    initiative,
    speed,
    bab,
    grapple,
    melee,
    ranged,
    damage,
    fort,
    ref,
    will,
    casterLevel,
    spellDc,
    sr: srStat,
    weapons,
    skills,
    size: { index: sizeIndex, name: SIZE_NAMES[sizeIndex], base: d.size, effectIds: sizeIds },
    conditions,
    defenses,
    notes,
    resist,
    report: Object.fromEntries(report),
  };
}

/** Every numeric stat on a sheet, for diffing two sheets against each other. */
export function allStats(s: Sheet): Stat[] {
  const out: Stat[] = [
    ...ABILITIES.map((a) => s.abilities[a]),
    s.hpMax,
    s.ac,
    s.touch,
    s.flat,
    s.fort,
    s.ref,
    s.will,
    s.initiative,
    s.speed,
    s.bab,
    s.grapple,
    s.melee,
    s.ranged,
    s.damage,
    s.casterLevel,
    s.sr,
  ];
  if (s.spellDc) out.push(s.spellDc);
  for (const w of s.weapons) out.push(w.attack, w.damage);
  out.push(...s.skills);
  return out;
}

export function computeSheet(c: CharacterState, effects: ActiveEffect[]): Sheet {
  const baseline = run(c, [], null);
  const sheet = effects.length ? run(c, effects, baseline.abilities.con.mod) : baseline;
  const baseValues = new Map(allStats(baseline).map((s) => [s.key, s.value]));
  for (const st of allStats(sheet)) st.base = baseValues.get(st.key) ?? st.value;
  for (const a of ABILITIES) sheet.abilities[a].baseMod = baseline.abilities[a].mod;
  return sheet;
}
