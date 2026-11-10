// Hand-curated sheet effects for D&D 3.5 spells, keyed by the slug used in the
// spell list. Numbers follow the Player's Handbook v3.5. Anything situational
// ("+2 AC against evil creatures") is recorded as a note instead of being
// silently added to a total.
//
// Who a spell can affect at all (creature type, alignment, Hit Dice limits)
// is NOT decided here: it is data, in `targetRequirements` of the spell file.
// These definitions only decide what happens to a legal target.

import type { Ctx, OptionDef, Out, SaveInfo, SpellDef, TargetInfo } from "./cast";
import { ABILITY_NAME, alignmentParts, type Ability, type AlignComponent, type BonusType, type Energy, type Modifier, type Target } from "./types";

const M = (target: Target, type: BonusType, value: number): Modifier => ({ target, type, value });
const pen = (target: Target, value: number): Modifier => ({ target, type: "penalty", value: -Math.abs(value) });
const clamp = (n: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, n));

type Build = (c: Ctx) => Out;
type Extra = Partial<Pick<SpellDef, "options" | "save" | "tags" | "hostileTo">>;

const DEFS: Record<string, SpellDef> = {};
const add = (slugs: string | string[], def: SpellDef) => {
  for (const s of Array.isArray(slugs) ? slugs : [slugs]) DEFS[s] = def;
};
const make = (kind: SpellDef["kind"]) => (summary: string, build: Build, extra: Extra = {}): SpellDef => ({
  kind,
  summary,
  build,
  ...extra,
});
const buff = make("buff");
const debuff = make("debuff");
const healing = make("heal");
const attack = make("damage");
const utility = make("utility");

const WILL: SaveInfo = { type: "will", on: "negates" };
const FORT: SaveInfo = { type: "fort", on: "negates" };
const REF: SaveInfo = { type: "ref", on: "negates" };
const half = (type: SaveInfo["type"]): SaveInfo => ({ type, on: "half" });
const partial = (type: SaveInfo["type"]): SaveInfo => ({ type, on: "partial" });
const isUndead = (t: TargetInfo): boolean => t.type === "undead";

const ENERGY_OPT: OptionDef = {
  key: "energy",
  label: "Energy type",
  choices: [
    { value: "fire", label: "Fire" },
    { value: "cold", label: "Cold" },
    { value: "acid", label: "Acid" },
    { value: "electricity", label: "Electricity" },
    { value: "sonic", label: "Sonic" },
  ],
};

// ============================================================ ability buffs
const enhancer = (a: Ability) =>
  buff(`+4 enhancement bonus to ${ABILITY_NAME[a]}`, () => ({ mods: [M(a, "enhancement", 4)] }));
add(["bulls-strength", "bulls-strength-mass"], enhancer("str"));
add(["cats-grace", "cats-grace-mass"], enhancer("dex"));
add(["bears-endurance", "bears-endurance-mass"], enhancer("con"));
add(["foxs-cunning", "foxs-cunning-mass"], enhancer("int"));
add(["owls-wisdom", "owls-wisdom-mass"], enhancer("wis"));
add(["eagles-splendor", "eagles-splendor-mass"], enhancer("cha"));

// ============================================================ armor class
add(
  "mage-armor",
  buff("+4 armor bonus to AC", () => ({
    mods: [M("ac", "armor", 4)],
    notes: ["Force effect: this armor bonus also works against incorporeal touch attacks."],
  })),
);
add(
  "shield",
  buff("+4 shield bonus to AC; negates magic missile", () => ({
    mods: [M("ac", "shield", 4)],
    notes: ["Negates magic missile attacks directed at you."],
  })),
);
add(
  "shield-of-faith",
  buff("+2 deflection bonus to AC, +1 per 6 caster levels (max +5)", (c) => ({
    mods: [M("ac", "deflection", clamp(2 + Math.floor(c.cl / 6), 2, 5))],
  })),
);
add(
  "barkskin",
  buff("+2 enhancement bonus to natural armor, +1 per 3 levels above 3rd (max +5)", (c) => ({
    mods: [M("ac", "natural_enh", clamp(2 + Math.floor((c.cl - 3) / 3), 2, 5))],
  })),
);
add(
  "magic-vestment",
  buff(
    "+1 enhancement bonus per 4 caster levels on armor or shield (max +5)",
    (c) => ({
      mods: [M("ac", c.opt("item") === "shield" ? "shield_enh" : "armor_enh", clamp(Math.floor(c.cl / 4), 1, 5))],
    }),
    {
      options: [
        {
          key: "item",
          label: "Cast on",
          choices: [
            { value: "armor", label: "Armor (or clothing)" },
            { value: "shield", label: "Shield" },
          ],
        },
      ],
    },
  ),
);
const protection = (vs: string) =>
  buff(`+2 AC and saves against ${vs} creatures (situational)`, () => ({
    notes: [
      `+2 deflection bonus to AC and +2 resistance bonus on saves against attacks made by ${vs} creatures (situational, so not added to your totals).`,
      "Blocks possession and mental control, and bodily contact by summoned creatures.",
    ],
  }));
add(["protection-from-evil", "magic-circle-against-evil"], protection("evil"));
add(["protection-from-good", "magic-circle-against-good"], protection("good"));
add(["protection-from-law", "magic-circle-against-law"], protection("lawful"));
add(["protection-from-chaos", "magic-circle-against-chaos"], protection("chaotic"));

const aura = (vs: string, rider: string) =>
  buff("+4 deflection bonus to AC and +4 resistance bonus on saves", () => ({
    mods: [M("ac", "deflection", 4), M("saves", "resistance", 4)],
    notes: [`Spell resistance 25 against ${vs} spells and spells cast by ${vs} creatures.`, rider],
  }));
add("holy-aura", aura("evil", "Evil creatures that strike you in melee may be blinded (Fortitude negates)."));
add("unholy-aura", aura("good", "Good creatures that strike you in melee take 1d6 Strength damage (Fortitude negates)."));
add("cloak-of-chaos", aura("lawful", "Lawful creatures that strike you in melee are confused for 1 round (Will negates)."));
add("shield-of-law", aura("chaotic", "Chaotic creatures that strike you in melee are slowed (Will negates)."));
add(
  "shield-other",
  buff("+1 deflection bonus to AC and +1 resistance bonus on saves", () => ({
    mods: [M("ac", "deflection", 1), M("saves", "resistance", 1)],
    notes: ["You take only half damage from wounds; the caster takes the other half."],
  })),
);
add(
  "foresight",
  buff("+2 insight bonus to AC and Reflex saves", () => ({
    mods: [M("ac", "insight", 2), M("ref", "insight", 2)],
    notes: ["You are never surprised or flat-footed."],
  })),
);

// ============================================================ miss chances & damage soaks
const defense = (summary: string, lines: (c: Ctx) => string[], notes: string[] = []) =>
  buff(summary, (c) => ({ defenses: lines(c), notes }));
add("blur", defense("20% miss chance (concealment)", () => ["Attacks against you have a 20% miss chance (concealment)"]));
add("displacement", defense("50% miss chance", () => ["Attacks against you have a 50% miss chance (as total concealment)"]));
add(
  "blink",
  defense(
    "50% miss chance against physical attacks; your own attacks may miss",
    () => ["Physical attacks against you have a 50% miss chance", "Half damage from area attacks and falling"],
    ["Your own attacks have a 20% miss chance, and your spells have a 20% chance to fail."],
  ),
);
add("entropic-shield", defense("20% miss chance against ranged attacks", () => ["Ranged attacks against you have a 20% miss chance"]));
add(
  "mirror-image",
  buff("1d4 images + 1 per 3 caster levels (max 8)", (c) => ({
    defenses: [`${Math.min(8, c.d(1, 4) + Math.floor(c.cl / 3))} mirror images (attackers may hit an image instead of you)`],
  })),
);
add(
  "stoneskin",
  defense("Damage reduction 10/adamantine", (c) => [`DR 10/adamantine (ends after absorbing ${Math.min(150, 10 * c.cl)} points of damage)`]),
);
add(
  "protection-from-arrows",
  defense("Damage reduction 10/magic against ranged weapons", (c) => [
    `DR 10/magic against ranged weapons (ends after absorbing ${Math.min(100, 10 * c.cl)} points of damage)`,
  ]),
);
add(
  "resist-energy",
  buff("Energy resistance 10 (20 at caster level 7, 30 at 11)", (c) => ({
    resist: { [c.opt("energy") as Energy]: c.cl >= 11 ? 30 : c.cl >= 7 ? 20 : 10 },
  }), { options: [ENERGY_OPT] }),
);
add(
  "protection-from-energy",
  buff("Absorbs 12 points of one energy type per caster level (max 120)", (c) => ({
    absorb: { energy: c.opt("energy") as Energy, amount: Math.min(120, 12 * c.cl) },
  }), { options: [ENERGY_OPT] }),
);
add("spell-resistance", buff("Spell resistance 12 + caster level", (c) => ({ sr: 12 + c.cl })));
add(
  "spell-turning",
  buff("Turns 1d4+6 spell levels back on their casters", (c) => ({
    defenses: [`Turns ${c.d(1, 4) + 6} levels of targeted spells back on their casters`],
  })),
);
add(
  "fire-shield",
  buff(
    "Attackers take 1d6 + caster level damage; half damage from the opposed element",
    (c) => {
      const warm = c.opt("shield") !== "chill";
      return {
        defenses: [
          `Creatures striking you in melee take 1d6+${Math.min(15, c.cl)} ${warm ? "fire" : "cold"} damage`,
          `Half damage from ${warm ? "cold" : "fire"}-based attacks (none on a successful Reflex save)`,
        ],
      };
    },
    {
      options: [
        {
          key: "shield",
          label: "Version",
          choices: [
            { value: "warm", label: "Warm shield (protects from cold)" },
            { value: "chill", label: "Chill shield (protects from fire)" },
          ],
        },
      ],
    },
  ),
);
add(
  "iron-body",
  buff("+6 Strength, \u22126 Dexterity, DR 15/adamantine, half speed", () => ({
    mods: [M("str", "enhancement", 6), pen("dex", 6)],
    speedMult: 0.5,
    defenses: [
      "DR 15/adamantine",
      "Half damage from acid and fire",
      "Immune to blindness, critical hits, ability damage, deafness, disease, drowning, electricity, poison and stunning",
    ],
    notes: ["50% arcane spell failure chance and a \u22128 armor check penalty, as if wearing full plate."],
  })),
);
add(
  "gaseous-form",
  buff("Damage reduction 10/magic; can't attack or cast", () => ({
    defenses: ["DR 10/magic", "Immune to poison and critical hits"],
    notes: ["Fly speed 10 ft. (perfect). You can't attack or cast spells with verbal, somatic, material or focus components."],
  })),
);
add(
  ["globe-of-invulnerability-lesser", "globe-of-invulnerability"],
  buff("Blocks low-level spell effects", () => ({
    defenses: ["Spell effects of 3rd level or lower can't reach you (4th level or lower for the full globe)"],
  })),
);
add(
  "protection-from-spells",
  buff("+8 resistance bonus on saves against spells (situational)", () => ({
    notes: ["+8 resistance bonus on saving throws against spells and spell-like abilities (not other effects, so not added to your totals)."],
  })),
);
add(
  "moment-of-prescience",
  buff("One-time insight bonus equal to caster level (max +25)", (c) => ({
    notes: [`Once: +${Math.min(25, c.cl)} insight bonus on a single attack roll, opposed check, saving throw, or to AC against one attack. Then the spell ends.`],
  })),
);

// ============================================================ combat buffs
add(
  "bless",
  buff("+1 morale bonus on attack rolls (and saves against fear)", () => ({
    mods: [M("attack", "morale", 1)],
    notes: ["+1 morale bonus on saving throws against fear effects."],
    counters: ["bane"],
  })),
);
add(
  "aid",
  buff("+1 morale bonus on attack rolls, 1d8 + caster level temporary HP (max +10)", (c) => ({
    mods: [M("attack", "morale", 1)],
    tempHp: c.d(1, 8) + Math.min(10, c.cl),
    notes: ["+1 morale bonus on saving throws against fear effects."],
  })),
);
add(
  "divine-favor",
  buff("+1 luck bonus on attack and weapon damage per 3 caster levels (max +3)", (c) => {
    const n = clamp(Math.floor(c.cl / 3), 1, 3);
    return { mods: [M("attack", "luck", n), M("damage", "luck", n)] };
  }),
);
add(
  "divine-power",
  buff("Base attack equals character level, +6 enhancement to Strength, 1 temp HP per caster level", (c) => ({
    mods: [M("str", "enhancement", 6)],
    babFull: true,
    tempHp: c.cl,
  })),
);
add(
  "righteous-might",
  buff("Grow one size: +4 Strength, +2 Constitution, +2 natural armor, damage reduction", (c) => ({
    mods: [M("str", "size", 4), M("con", "size", 2), M("ac", "natural_enh", 2), M("size", "size", 1)],
    defenses: [`DR ${c.cl >= 15 ? 9 : c.cl >= 12 ? 6 : 3}/evil (or /good if you channel negative energy)`],
    notes: ["Reach increases to 10 ft. and your weapons deal damage as if one size larger."],
  })),
);
add(
  "tensers-transformation",
  buff("+4 Str/Dex/Con, +4 natural armor, +5 Fortitude, fighter's base attack", () => ({
    mods: [
      M("str", "enhancement", 4),
      M("dex", "enhancement", 4),
      M("con", "enhancement", 4),
      M("ac", "natural", 4),
      M("fort", "competence", 5),
    ],
    babFull: true,
    notes: ["You can't cast spells for the duration. Proficient with all simple and martial weapons."],
  })),
);
add(
  "heroism",
  buff("+2 morale bonus on attack rolls, saves and skill checks", () => ({
    mods: [M("attack", "morale", 2), M("saves", "morale", 2), M("skills", "morale", 2)],
  })),
);
add(
  "heroism-greater",
  buff("+4 morale bonus on attacks, saves and skills; temp HP; immune to fear", (c) => ({
    mods: [M("attack", "morale", 4), M("saves", "morale", 4), M("skills", "morale", 4)],
    tempHp: Math.min(20, c.cl),
    defenses: ["Immune to fear effects"],
    removes: { conditions: ["shaken", "frightened", "panicked"] },
  })),
);
add(
  "good-hope",
  buff("+2 morale bonus on saves, attacks, skill checks and weapon damage", () => ({
    mods: [M("saves", "morale", 2), M("attack", "morale", 2), M("skills", "morale", 2), M("damage", "morale", 2)],
    notes: ["Also +2 morale bonus on ability checks."],
    counters: ["crushing-despair"],
  })),
);
add(
  "prayer",
  utility(
    "Allies: +1 luck on attacks, damage, saves, skills. Foes: \u22121 on the same",
    (c) =>
      c.opt("side") === "foe"
        ? { mods: [pen("attack", 1), pen("damage", 1), pen("saves", 1), pen("skills", 1)] }
        : { mods: [M("attack", "luck", 1), M("damage", "luck", 1), M("saves", "luck", 1), M("skills", "luck", 1)] },
    {
      save: null,
      options: [
        {
          key: "side",
          label: "You are the caster's",
          choices: [
            { value: "ally", label: "Ally (+1 luck bonus)" },
            { value: "foe", label: "Foe (\u22121 penalty)" },
          ],
        },
      ],
    },
  ),
);
add(
  "haste",
  buff("+1 attack, +1 dodge to AC and Reflex, +30 ft. speed, one extra attack", (c) => ({
    mods: [
      M("attack", "untyped", 1),
      M("ac", "dodge", 1),
      M("ref", "dodge", 1),
      M("speed", "enhancement", Math.min(30, c.target.speed)),
    ],
    extraAttack: true,
    counters: ["slow"],
  })),
);
add(
  "rage",
  buff("+2 morale to Strength and Constitution, +1 Will, \u22122 AC", () => ({
    mods: [M("str", "morale", 2), M("con", "morale", 2), M("will", "morale", 1), pen("ac", 2)],
    notes: ["Compelled to fight heedless of danger; can't use skills or abilities that require patience or concentration."],
  })),
);
add(
  "true-strike",
  buff("+20 insight bonus on your next attack roll", () => ({
    mods: [M("attack", "insight", 20)],
    notes: ["Applies to your next single attack roll only, and that attack ignores concealment miss chances."],
    rounds: 1,
  })),
);
add(
  "enlarge-person",
  buff("Grow one size: +2 Strength, \u22122 Dexterity, \u22121 attack and AC", () => ({
    mods: [M("str", "size", 2), M("dex", "size", -2), M("size", "size", 1)],
    notes: ["Reach increases to 10 ft. and your weapons deal damage as if one size larger."],
    counters: ["reduce-person"],
  })),
);
add("enlarge-person-mass", DEFS["enlarge-person"]);
add(
  "reduce-person",
  utility("Shrink one size: +2 Dexterity, \u22122 Strength, +1 attack and AC", () => ({
    mods: [M("dex", "size", 2), M("str", "size", -2), M("size", "size", -1)],
    notes: ["Your weapons deal damage as if one size smaller."],
    counters: ["enlarge-person"],
  })),
);
add("reduce-person-mass", DEFS["reduce-person"]);

const weaponBuff = (scaled: boolean, note: string) =>
  buff(
    scaled ? "+1 enhancement bonus on attack and damage per 4 caster levels (max +5)" : "+1 enhancement bonus on attack and damage",
    (c) => {
      const n = scaled ? clamp(Math.floor(c.cl / 4), 1, 5) : 1;
      return { mods: [M("attack", "enhancement", n), M("damage", "enhancement", n)], notes: [note] };
    },
  );
const ONE_WEAPON = "Affects one weapon; this prototype applies it to every weapon on the sheet. It doesn't stack with a weapon's own magic bonus.";
add("magic-weapon", weaponBuff(false, ONE_WEAPON));
add("magic-weapon-greater", weaponBuff(true, ONE_WEAPON));
add("magic-fang", weaponBuff(false, "Affects one natural weapon or unarmed strike; shown here on every listed weapon."));
add("magic-fang-greater", weaponBuff(true, "Affects natural weapons or unarmed strikes; shown here on every listed weapon."));
add(
  "shillelagh",
  buff("Club or quarterstaff: +1 enhancement on attack and damage, deals 2d6", () => ({
    mods: [M("attack", "enhancement", 1), M("damage", "enhancement", 1)],
    notes: ["Only your own nonmagical club or quarterstaff: it deals damage as if two sizes larger (2d6 for Medium)."],
  })),
);

// ============================================================ small buffs & temp HP
add("resistance", buff("+1 resistance bonus on saves", () => ({ mods: [M("saves", "resistance", 1)] })));
add(
  "guidance",
  buff("+1 competence bonus on one roll", () => ({
    notes: ["Once: +1 competence bonus on a single attack roll, saving throw or skill check. Then the spell ends."],
  })),
);
add("virtue", buff("1 temporary hit point", () => ({ tempHp: 1 })));
add(
  "false-life",
  buff("1d10 + caster level temporary hit points (max +10)", (c) => ({ tempHp: c.d(1, 10) + Math.min(10, c.cl) })),
);
add(
  "heroes-feast",
  buff("+1 morale on attacks and Will saves, temporary HP, immune to poison and fear for 12 hours", (c) => ({
    mods: [M("attack", "morale", 1), M("will", "morale", 1)],
    tempHp: c.d(1, 8) + Math.min(10, Math.floor(c.cl / 2)),
    defenses: ["Immune to poison and fear effects"],
    rounds: 7200,
  })),
);
add("longstrider", buff("+10 ft. enhancement bonus to speed", () => ({ mods: [M("speed", "enhancement", 10)] })));
add("expeditious-retreat", buff("+30 ft. enhancement bonus to speed", () => ({ mods: [M("speed", "enhancement", 30)] })));
add(
  "jump",
  buff("+10 enhancement bonus on Jump checks (+20 at caster level 5, +30 at 9)", (c) => ({
    mods: [M("skill:jump", "enhancement", c.cl >= 9 ? 30 : c.cl >= 5 ? 20 : 10)],
  })),
);
add(
  "glibness",
  buff("+30 bonus on Bluff checks", () => ({
    mods: [M("skill:bluff", "untyped", 30)],
    notes: ["Only for Bluff checks made to convince others you speak the truth. Magical lie detection must beat a DC 15 + caster level check."],
  })),
);
add(
  ["invisibility", "invisibility-sphere", "invisibility-mass"],
  buff("Invisible until you attack", () => ({ conditions: ["invisible"], notes: ["Ends as soon as you attack any creature."] })),
);
add("invisibility-greater", buff("Invisible, even while attacking", () => ({ conditions: ["invisible"] })));
add(
  "remove-fear",
  buff("Ends fear; +4 morale bonus on saves against fear", () => ({
    notes: ["+4 morale bonus on saving throws against fear effects."],
    removes: { conditions: ["shaken", "frightened", "panicked"] },
    rounds: 100,
  })),
);

// ============================================================ notes-only utility
const note = (summary: string, ...notes: string[]) => buff(summary, () => ({ notes }));
add("fly", note("Fly speed 60 ft.", "Fly speed 60 ft. (40 ft. in medium or heavy armor) with good maneuverability."));
add("overland-flight", note("Fly speed 40 ft.", "Fly speed 40 ft. (30 ft. in medium or heavy armor) with average maneuverability."));
add("air-walk", note("Walk on air", "You can tread on air as if it were solid ground."));
add("levitate", note("Float up or down 20 ft. per round", "Move up or down 20 ft. per round. Attacking while levitating gives cumulative \u22121 penalties on attack rolls (max \u22125)."));
add("spider-climb", note("Climb speed 20 ft.", "Climb speed 20 ft. on walls and ceilings; no Climb checks needed. You keep your Dex bonus to AC while climbing."));
add("feather-fall", note("Fall slowly", "You fall at 60 ft. per round and take no damage on landing."));
add("water-breathing", note("Breathe water", "You can breathe water freely."));
add("water-walk", note("Walk on liquid", "You can walk on any liquid as if it were firm ground."));
add("darkvision", note("Darkvision 60 ft.", "You can see 60 ft. in total darkness (black and white only)."));
add("see-invisibility", note("See invisible creatures", "You see invisible and ethereal creatures and objects within your range of vision."));
add("true-seeing", note("See things as they really are", "Out to 120 ft.: see through darkness, illusions, invisibility, displacement and polymorph effects."));
add("tongues", note("Speak any language", "You can speak and understand the language of any intelligent creature."));
add("comprehend-languages", note("Understand any language", "You understand spoken and written languages (you can't speak them)."));
add("endure-elements", note("Comfortable from \u221250\u00b0 to 140\u00b0F", "No harm from hot or cold environments between \u221250 and 140 degrees Fahrenheit."));
add("pass-without-trace", note("Leave no tracks", "You leave neither footprints nor scent; tracking you is impossible by nonmagical means."));
add("nondetection", note("Hard to detect by divination", "Divinations against you require a caster level check (DC 11 + caster level, or 15 + your level if self-cast)."));
add("delay-poison", note("Poison has no effect for now", "You are temporarily immune to poison; effects are postponed until the spell ends."));
add("death-ward", buff("Immune to death spells and negative energy", () => ({ defenses: ["Immune to death spells, magical death effects, energy drain and negative energy effects"] })));
add("freedom-of-movement", buff("Ignore paralysis, slow, web and grappling", () => ({ defenses: ["Moves and attacks normally despite paralysis, slow, web, solid fog and grapples"], removes: { slugs: ["slow", "web", "entangle", "hold-person", "hold-monster", "hold-person-mass", "hold-monster-mass"] } })));
add("mind-blank", buff("Immune to mind-affecting magic and divination", () => ({ defenses: ["Immune to mind-affecting spells and to information gathering by divination"] })));
add("sanctuary", note("Opponents must save to attack you", "Opponents must make a Will save to attack you directly. Ends if you attack."));
add("bless-weapon", note("Weapon is good-aligned", "Your weapon strikes true against evil foes: it counts as good-aligned and automatically confirms critical threats against evil creatures."));
add("align-weapon", note("Weapon gains an alignment", "Your weapon counts as good, evil, lawful or chaotic for overcoming damage reduction."));
add("keen-edge", note("Doubles threat range", "Doubles the critical threat range of one slashing or piercing weapon."));
add("flame-arrow", note("Ammunition deals +1d6 fire", "Up to 50 projectiles deal an extra 1d6 fire damage on a hit."));

// ============================================================ debuffs
add(
  "bane",
  debuff("\u22121 on attack rolls (and saves against fear)", () => ({
    mods: [pen("attack", 1)],
    notes: ["\u22121 penalty on saving throws against fear effects."],
    counters: ["bless"],
  }), { save: WILL, tags: ["mind"] }),
);
add("doom", debuff("Shaken", () => ({ conditions: ["shaken"] }), { save: WILL, tags: ["mind"] }));
add(
  "cause-fear",
  debuff("Frightened for 1d4 rounds (shaken for 1 round on a save)", (c) =>
    c.saved ? { conditions: ["shaken"], rounds: 1 } : { conditions: ["frightened"], rounds: c.d(1, 4) },
  { save: partial("will"), tags: ["mind"] }),
);
add(
  "scare",
  debuff("Frightened for 1 round per level (shaken for 1 round on a save)", (c) =>
    c.saved ? { conditions: ["shaken"], rounds: 1 } : { conditions: ["frightened"], rounds: c.cl },
  { save: partial("will"), tags: ["mind"] }),
);
add(
  "fear",
  debuff("Panicked for 1 round per level (shaken for 1 round on a save)", (c) =>
    c.saved ? { conditions: ["shaken"], rounds: 1 } : { conditions: ["panicked"], rounds: c.cl },
  { save: partial("will"), tags: ["mind"] }),
);
add(
  "crushing-despair",
  debuff("\u22122 on attack rolls, saves, skill checks and weapon damage", () => ({
    mods: [pen("attack", 2), pen("saves", 2), pen("skills", 2), pen("damage", 2)],
    notes: ["Also \u22122 on ability checks."],
    counters: ["good-hope"],
  }), { save: WILL, tags: ["mind"] }),
);
add(
  "slow",
  debuff("\u22121 on attack rolls, AC and Reflex saves; half speed", () => ({
    mods: [pen("attack", 1), pen("ac", 1), pen("ref", 1)],
    speedMult: 0.5,
    notes: ["You can take only a single move action or standard action each turn."],
    counters: ["haste"],
  }), { save: WILL, tags: ["movement"] }),
);
add(
  "ray-of-enfeeblement",
  debuff("Strength penalty of 1d6 + 1 per 2 caster levels (max +5)", (c) => ({
    mods: [pen("str", c.d(1, 6) + Math.min(5, Math.floor(c.cl / 2)))],
  }), { save: null }),
);
add(
  "ray-of-exhaustion",
  debuff("Exhausted (fatigued on a successful save)", (c) => ({ conditions: [c.saved ? "fatigued" : "exhausted"] }), {
    save: partial("fort"),
    tags: ["fatigue"],
  }),
);
add("touch-of-fatigue", debuff("Fatigued", () => ({ conditions: ["fatigued"] }), { save: FORT, tags: ["fatigue"] }));
add(
  "waves-of-fatigue",
  debuff("Fatigued until you rest", () => ({ conditions: ["fatigued"], rounds: null, durationLabel: "Until you rest" }), { save: null, tags: ["fatigue"] }),
);
add(
  "waves-of-exhaustion",
  debuff("Exhausted until you rest", () => ({ conditions: ["exhausted"], rounds: null, durationLabel: "Until you rest" }), { save: null, tags: ["fatigue"] }),
);
add(
  "touch-of-idiocy",
  debuff("1d6 penalty to Intelligence, Wisdom and Charisma", (c) => {
    const n = c.d(1, 6);
    return { mods: [pen("int", n), pen("wis", n), pen("cha", n)], notes: ["May reduce the spells you can cast while it lasts."] };
  }, { save: null, tags: ["mind"] }),
);
add(
  "bestow-curse",
  debuff(
    "\u22126 to an ability score, or \u22124 on attacks, saves and checks",
    (c) => {
      const curse = c.opt("curse");
      if (curse === "rolls") {
        return { mods: [pen("attack", 4), pen("saves", 4), pen("skills", 4)], notes: ["Also \u22124 on ability checks."] };
      }
      if (curse === "actions") return { notes: ["Each turn you have a 50% chance to act normally; otherwise you take no action."] };
      return { mods: [pen(curse as Ability, 6)] };
    },
    {
      save: WILL,
      options: [
        {
          key: "curse",
          label: "Curse",
          choices: [
            { value: "rolls", label: "\u22124 on attack rolls, saves and checks" },
            { value: "str", label: "\u22126 Strength" },
            { value: "dex", label: "\u22126 Dexterity" },
            { value: "con", label: "\u22126 Constitution" },
            { value: "int", label: "\u22126 Intelligence" },
            { value: "wis", label: "\u22126 Wisdom" },
            { value: "cha", label: "\u22126 Charisma" },
            { value: "actions", label: "50% chance to lose each turn" },
          ],
        },
      ],
    },
  ),
);
add(
  "blindnessdeafness",
  debuff("Permanently blinded or deafened", (c) => ({ conditions: [c.opt("sense") === "deaf" ? "deafened" : "blinded"] }), {
    save: FORT,
    options: [
      {
        key: "sense",
        label: "Effect",
        choices: [
          { value: "blind", label: "Blindness" },
          { value: "deaf", label: "Deafness" },
        ],
      },
    ],
  }),
);
add(
  "glitterdust",
  debuff("Blinded (Will negates the blindness); \u221240 on Hide checks", (c) => ({
    conditions: c.saved ? [] : ["blinded"],
    mods: [pen("skill:hide", 40)],
    notes: ["Outlined in glittering dust: invisibility doesn't hide you."],
  }), { save: partial("will") }),
);
const hold = debuff("Paralyzed", () => ({
  conditions: ["paralyzed"],
  notes: ["Each round on your turn you may attempt a new Will save (a full-round action) to end the effect."],
}), { save: WILL, tags: ["movement", "mind", "paralysis"] });
add(["hold-person", "hold-monster", "hold-person-mass", "hold-monster-mass", "hold-animal"], hold);
add(["sleep", "deep-slumber"], debuff("Asleep", () => ({ conditions: ["asleep"] }), { save: WILL, tags: ["mind", "sleep"] }));

add(["daze", "daze-monster"], debuff("Dazed for 1 round", () => ({ conditions: ["dazed"], rounds: 1 }), { save: WILL, tags: ["mind"] }));

add(
  "color-spray",
  debuff("Stunned, blinded or unconscious depending on your Hit Dice", (c) => {
    const hd = c.target.hd;
    if (hd >= 5) return { conditions: ["stunned"], rounds: 1 };
    if (hd >= 3) return { conditions: ["blinded", "stunned"], rounds: c.d(1, 4), notes: ["Stays stunned for 1 more round after this ends."] };
    return {
      conditions: ["helpless", "blinded", "stunned"],
      rounds: c.d(2, 4),
      notes: ["Unconscious. Afterwards: blinded and stunned for 1d4 rounds, then stunned for 1 round."],
    };
  }, { save: WILL, tags: ["mind", "stun"] }),
);
add(
  "tashas-hideous-laughter",
  debuff("Prone and helpless with laughter", () => ({ conditions: ["prone"], notes: ["You can take no actions while laughing, but you are not considered helpless."] }), {
    save: WILL,
    tags: ["mind"],
  }),
);
add(
  ["web", "entangle"],
  debuff("Entangled", () => ({ conditions: ["entangled"], notes: ["Break free with a DC 20 Strength check or DC 25 Escape Artist check."] }), {
    save: REF,
    tags: ["movement"],
  }),
);
add("grease", debuff("Fall prone", () => ({ conditions: ["prone"], rounds: 1 }), { save: REF }));
add("stinking-cloud", debuff("Nauseated", () => ({ conditions: ["nauseated"], notes: ["Lasts while you stay in the cloud and for 1d4+1 rounds after leaving."] }), { save: FORT }));
add(
  "ghoul-touch",
  debuff("Paralyzed for 1d6+2 rounds", (c) => ({ conditions: ["paralyzed"], rounds: c.d(1, 6) + 2, notes: ["You exude a stench that sickens living creatures within 10 ft."] }), {
    save: FORT,
    tags: ["movement", "paralysis"],
  }),
);
add("flare", debuff("Dazzled for 1 minute", () => ({ conditions: ["dazzled"], rounds: 10 }), { save: FORT }));
add(
  "feeblemind",
  debuff("Intelligence and Charisma drop to 1", () => ({
    overrides: { int: 1, cha: 1 },
    notes: ["Can't cast spells, use Int- or Cha-based skills, or communicate coherently. Removed by heal, limited wish, miracle or wish."],
    rounds: null,
  }), { save: WILL, tags: ["mind"] }),
);
const negativeLevels = (dice: number, sides: number, hours: (cl: number) => number) =>
  debuff(`${dice}d${sides} negative levels (undead gain temporary hit points instead)`, (c) => {
    const n = c.d(dice, sides);
    if (isUndead(c.target)) {
      return { tempHp: n * 5, rounds: 600, notes: ["Negative energy strengthens undead: temporary hit points instead of negative levels."] };
    }
    return {
      mods: [pen("attack", n), pen("saves", n), pen("skills", n), pen("hp_max", 5 * n), pen("caster_level", n)],
      notes: [`${n} negative level${n === 1 ? "" : "s"}: also \u2212${n} on ability checks and effective level, and you lose ${n} of your highest-level spell slots.`],
      rounds: hours(c.cl) * 600,
      stacksWithSelf: true,
    };
  }, { save: null, tags: ["negative", "drain"], hostileTo: (t) => !isUndead(t) });
add("enervation", negativeLevels(1, 4, (cl) => Math.min(15, cl)));
add("energy-drain", negativeLevels(2, 4, () => 24));
add(
  "mind-fog",
  debuff("\u221210 on Will saves and Wisdom checks", (c) => ({
    mods: [M("will", "competence", -10)],
    notes: ["Also \u221210 on Wisdom checks. Lasts while in the fog and 2d6 rounds after leaving."],
    rounds: 300 + c.d(2, 6),
  }), { save: WILL, tags: ["mind"] }),
);
add(
  "ottos-irresistible-dance",
  debuff("\u22124 AC and \u221210 Reflex while dancing", (c) => ({
    mods: [pen("ac", 4), pen("ref", 10)],
    notes: ["You can do nothing but dance in place, you provoke attacks of opportunity each round, and you lose any shield bonus."],
    rounds: c.d(1, 4) + 1,
  }), { save: null, tags: ["mind"] }),
);
add(
  "symbol-of-pain",
  debuff("\u22124 on attack rolls, skill checks and ability checks", () => ({ mods: [pen("attack", 4), pen("skills", 4)], notes: ["Also \u22124 on ability checks."], rounds: 600 }), {
    save: FORT,
  }),
);
add(
  "eyebite",
  debuff("Sickened, panicked or comatose depending on your Hit Dice", (c) => {
    const hd = c.target.hd;
    const conditions = hd >= 10 ? ["sickened"] : hd >= 5 ? ["sickened", "panicked"] : ["sickened", "panicked", "helpless"];
    return { conditions, rounds: 100 * c.cl, notes: hd < 10 ? ["Panic lasts 1d4 rounds, then you are shaken; sickened for the full duration."] : [] };
  }, { save: FORT }),
);
add(
  "power-word-stun",
  debuff("Stunned, duration based on your current hit points", (c) => {
    const hp = c.target.hp;
    if (hp > 150) return { noEffect: "Power Word Stun has no effect on a creature with 151 or more hit points." };
    return { conditions: ["stunned"], rounds: hp <= 50 ? c.d(4, 4) : hp <= 100 ? c.d(2, 4) : c.d(1, 4) };
  }, { save: null, tags: ["mind", "stun"] }),
);
add(
  "power-word-blind",
  debuff("Blinded, duration based on your current hit points", (c) => {
    const hp = c.target.hp;
    if (hp > 200) return { noEffect: "Power Word Blind has no effect on a creature with 201 or more hit points." };
    return { conditions: ["blinded"], rounds: hp <= 50 ? null : hp <= 100 ? (c.d(1, 4) + 1) * 10 : c.d(1, 4) + 1 };
  }, { save: null, tags: ["mind"] }),
);
add(
  "poison",
  debuff("1d10 Constitution damage", (c) => ({
    mods: [pen("con", c.d(1, 10))],
    notes: ["Ability damage: heals 1 point per day. A second save is due 1 minute later; apply the spell again if it fails."],
    rounds: null,
    stacksWithSelf: true,
  }), { save: FORT, tags: ["poison"] }),
);
const mental = (condition: string, summary: string) => debuff(summary, () => ({ conditions: [condition] }), { save: WILL, tags: ["mind"] });
add(["confusion", "confusion-lesser"], mental("confused", "Confused"));
add("insanity", debuff("Permanently confused", () => ({ conditions: ["confused"], rounds: null }), { save: WILL, tags: ["mind"] }));
add(["charm-person", "charm-monster"], mental("charmed", "Charmed"));
add(["dominate-person", "dominate-monster"], mental("dominated", "Dominated"));
add(["hypnotism", "hypnotic-pattern"], mental("fascinated", "Fascinated"));
add(
  "faerie-fire",
  debuff("Outlined in light", () => ({ notes: ["Outlined: you gain no concealment from darkness, blur, displacement or invisibility."] }), { save: null }),
);
add("silence", debuff("No sound", () => ({ notes: ["No sound: you can't cast spells with verbal components. Immune to sonic and language-based attacks."] }), { save: WILL }));
add("dimensional-anchor", debuff("Can't teleport or travel between planes", () => ({ notes: ["Blocks teleportation, plane shifting, ethereal and astral travel."] }), { save: null }));
add(
  "lullaby",
  debuff("\u22125 on Listen and Spot, \u22122 on Will saves against sleep", () => ({
    mods: [pen("skill:listen", 5), pen("skill:spot", 5)],
    notes: ["\u22122 penalty on Will saves against sleep effects."],
  }), { save: WILL, tags: ["mind"] }),
);
add("flesh-to-stone", debuff("Turned to stone", () => ({ conditions: ["petrified"], rounds: null }), { save: FORT }));

// ============================================================ healing
const NOT_ALIVE = "Positive energy only mends living creatures: it does nothing to a construct.";
/** Positive energy heals the living, burns undead (Will save for half) and ignores constructs. */
const positive = (summary: string, amount: (c: Ctx) => number, onLiving: Out = {}, undeadFloor?: number) =>
  healing(summary, (c) => {
    if (c.target.type === "construct") return { noEffect: NOT_ALIVE };
    const n = amount(c);
    if (isUndead(c.target)) return { damage: undeadFloor != null ? { amount: n, minHp: undeadFloor } : { amount: n } };
    return { heal: n, ...onLiving };
  }, { save: (t) => (isUndead(t) ? half("will") : null), hostileTo: isUndead });
const cure = (dice: number, cap: number) =>
  positive(`Heals ${dice}d8 + caster level (max +${cap}); damages undead instead`, (c) => c.d(dice, 8) + Math.min(cap, c.cl));
add("cure-minor-wounds", positive("Heals 1 hit point; damages undead instead", () => 1));
add("cure-light-wounds", cure(1, 5));
add("cure-moderate-wounds", cure(2, 10));
add("cure-serious-wounds", cure(3, 15));
add("cure-critical-wounds", cure(4, 20));
add("cure-light-wounds-mass", cure(1, 25));
add("cure-moderate-wounds-mass", cure(2, 30));
add("cure-serious-wounds-mass", cure(3, 35));
add("cure-critical-wounds-mass", cure(4, 40));
const HEAL_ENDS = {
  conditions: ["blinded", "confused", "dazed", "dazzled", "deafened", "exhausted", "fatigued", "nauseated", "sickened", "stunned"],
  slugs: ["feeblemind", "insanity", "poison", "chill-touch", "touch-of-idiocy"],
};
add("heal", positive("Heals 10 HP per caster level (max 150) and ends most afflictions; harms undead", (c) => Math.min(150, 10 * c.cl), { removes: HEAL_ENDS }, 1));
add("heal-mass", positive("Heals 10 HP per caster level (max 250) and ends most afflictions; harms undead", (c) => Math.min(250, 10 * c.cl), { removes: HEAL_ENDS }, 1));

// ============================================================ removal & dispelling
const ABILITY_DRAINS = ["ray-of-enfeeblement", "touch-of-idiocy", "chill-touch", "poison"];
add("remove-paralysis", healing("Ends paralysis and slow", () => ({ removes: { conditions: ["paralyzed"], slugs: ["slow"] } }), { save: null }));
add("remove-curse", healing("Ends curses", () => ({ removes: { slugs: ["bestow-curse"] } }), { save: null }));
add("remove-blindnessdeafness", healing("Cures blindness and deafness", () => ({ removes: { conditions: ["blinded", "deafened"] } }), { save: null }));
add("neutralize-poison", healing("Ends poison", () => ({ removes: { slugs: ["poison"] } }), { save: null }));
add("stone-to-flesh", healing("Restores a petrified creature", () => ({ removes: { conditions: ["petrified"] } }), { save: null }));
add("restoration-lesser", healing("Ends ability penalties and fatigue", () => ({ removes: { slugs: ABILITY_DRAINS, conditions: ["fatigued", "exhausted"] } }), { save: null }));
add("restoration", healing("Ends ability penalties, fatigue and negative levels", () => ({ removes: { slugs: [...ABILITY_DRAINS, "enervation", "energy-drain"], conditions: ["fatigued", "exhausted"] } }), { save: null }));
add(
  "restoration-greater",
  healing("Ends ability penalties, negative levels, fatigue, confusion and insanity", () => ({
    removes: { slugs: [...ABILITY_DRAINS, "enervation", "energy-drain", "feeblemind", "insanity"], conditions: ["fatigued", "exhausted", "confused"] },
  }), { save: null }),
);
const DISPEL_MODE: OptionDef = {
  key: "mode",
  label: "Version",
  choices: [
    { value: "targeted", label: "Targeted dispel (a check against every spell on you)" },
    { value: "area", label: "Area dispel (strongest spell first, ends at most one)" },
  ],
};
const dispelling = (cap: number) =>
  utility(
    `Dispel check (1d20 + caster level, max +${cap}) against the spells on you`,
    (c) => ({ dispel: cap, dispelOne: c.opt("mode") === "area" }),
    { save: null, options: [DISPEL_MODE] },
  );
add("dispel-magic", dispelling(10));
add("dispel-magic-greater", dispelling(20));

// ============================================================ damage
const NEG = ["negative"];
/** Negative energy harms the living (Will save for half), heals undead and ignores constructs. */
const negative = (summary: string, amount: (c: Ctx) => number, floor?: number) =>
  attack(summary, (c) => {
    if (c.target.type === "construct") return { noEffect: "Constructs are immune to necromancy effects." };
    const n = amount(c);
    if (isUndead(c.target)) return { heal: n };
    return { damage: floor != null ? { amount: n, minHp: floor } : { amount: n } };
  }, { save: (t) => (isUndead(t) ? null : half("will")), tags: NEG, hostileTo: (t) => !isUndead(t) });
const inflict = (dice: number, cap: number) =>
  negative(`${dice}d8 + caster level (max +${cap}) negative energy damage; heals undead instead`, (c) => c.d(dice, 8) + Math.min(cap, c.cl));
add("inflict-minor-wounds", negative("1 point of damage; heals undead instead", () => 1));
add("inflict-light-wounds", inflict(1, 5));
add("inflict-moderate-wounds", inflict(2, 10));
add("inflict-serious-wounds", inflict(3, 15));
add("inflict-critical-wounds", inflict(4, 20));
add("inflict-light-wounds-mass", inflict(1, 25));
add("inflict-moderate-wounds-mass", inflict(2, 30));
add("inflict-serious-wounds-mass", inflict(3, 35));
add("inflict-critical-wounds-mass", inflict(4, 40));
add("harm", negative("10 damage per caster level (max 150), never below 1 HP; heals undead instead", (c) => Math.min(150, 10 * c.cl), 1));

const blast = (summary: string, maxDice: number, sides: number, energy: Energy | undefined, save: SaveInfo | null, perLevels = 1) =>
  attack(summary, (c) => ({ damage: { amount: c.d(clamp(Math.floor(c.cl / perLevels), 1, maxDice), sides), energy } }), { save });
add("burning-hands", blast("1d4 fire damage per caster level (max 5d4)", 5, 4, "fire", half("ref")));
add("shocking-grasp", blast("1d6 electricity damage per caster level (max 5d6)", 5, 6, "electricity", null));
add("fireball", blast("1d6 fire damage per caster level (max 10d6)", 10, 6, "fire", half("ref")));
add("lightning-bolt", blast("1d6 electricity damage per caster level (max 10d6)", 10, 6, "electricity", half("ref")));
add("cone-of-cold", blast("1d6 cold damage per caster level (max 15d6)", 15, 6, "cold", half("ref")));
add("flame-strike", blast("1d6 damage per caster level (max 15d6), half fire and half divine", 15, 6, undefined, half("ref")));
add("fire-storm", blast("1d6 fire damage per caster level (max 20d6)", 20, 6, "fire", half("ref")));
add("chain-lightning", blast("1d6 electricity damage per caster level (max 20d6)", 20, 6, "electricity", half("ref")));
add("delayed-blast-fireball", blast("1d6 fire damage per caster level (max 20d6)", 20, 6, "fire", half("ref")));
add("horrid-wilting", blast("1d6 damage per caster level (max 20d6)", 20, 6, undefined, half("fort")));
add("polar-ray", blast("1d6 cold damage per caster level (max 25d6)", 25, 6, "cold", null));
add(
  "searing-light",
  attack("1d8 damage per 2 caster levels (max 5d8); undead take 1d6 per level (max 10d6), constructs 1d6 per 2 levels", (c) => {
    const halfLevel = clamp(Math.floor(c.cl / 2), 1, 5);
    const amount = isUndead(c.target) ? c.d(Math.min(10, c.cl), 6) : c.target.type === "construct" ? c.d(halfLevel, 6) : c.d(halfLevel, 8);
    return { damage: { amount } };
  }, { save: null }),
);
add("vampiric-touch", blast("1d6 damage per 2 caster levels (max 10d6)", 10, 6, undefined, null, 2));
add("acid-splash", attack("1d3 acid damage", (c) => ({ damage: { amount: c.d(1, 3), energy: "acid" } }), { save: null }));
add("ray-of-frost", attack("1d3 cold damage", (c) => ({ damage: { amount: c.d(1, 3), energy: "cold" } }), { save: null }));
add("call-lightning", attack("3d6 electricity damage", (c) => ({ damage: { amount: c.d(3, 6), energy: "electricity" } }), { save: half("ref") }));
add("flaming-sphere", attack("2d6 fire damage", (c) => ({ damage: { amount: c.d(2, 6), energy: "fire" } }), { save: REF }));
add("produce-flame", attack("1d6 + caster level fire damage (max +5)", (c) => ({ damage: { amount: c.d(1, 6) + Math.min(5, c.cl), energy: "fire" } }), { save: null }));
add("ice-storm", attack("5d6 damage (3d6 bludgeoning + 2d6 cold)", (c) => ({ damage: { amount: c.d(5, 6) } }), { save: null }));
add(
  "melfs-acid-arrow",
  attack("2d4 acid damage, repeating for extra rounds", (c) => ({
    damage: { amount: c.d(2, 4), energy: "acid" },
    notes: [`Takes another 2d4 acid damage at the start of each of the next ${Math.min(6, Math.floor(c.cl / 3))} round(s): apply it with the damage control.`],
    rounds: Math.min(6, Math.floor(c.cl / 3)) || undefined,
  }), { save: null }),
);
add(
  "scorching-ray",
  attack("4d6 fire damage per ray (1 ray, 2 at caster level 7, 3 at 11)", (c) => ({ damage: { amount: c.d(4 * (c.cl >= 11 ? 3 : c.cl >= 7 ? 2 : 1), 6), energy: "fire" } }), { save: null }),
);
add(
  "magic-missile",
  attack("1d4+1 force damage per missile (1 missile, +1 per 2 levels above 1st, max 5)", (c) => {
    const missiles = Math.min(5, 1 + Math.floor((c.cl - 1) / 2));
    return { damage: { amount: c.d(missiles, 4) + missiles } };
  }, { save: null, tags: ["magic-missile"] }),
);
add(
  "sound-burst",
  attack("1d8 sonic damage and stunned for 1 round (Fortitude negates the stun)", (c) => {
    const stunned = !c.saved && !c.target.immunities.includes("stun");
    return { damage: { amount: c.d(1, 8), energy: "sonic" }, conditions: stunned ? ["stunned"] : [], rounds: stunned ? 1 : undefined };
  }, { save: partial("fort") }),
);
add(
  "shout",
  attack("5d6 sonic damage and deafened for 2d6 rounds (Fortitude: half damage, no deafness)", (c) => {
    const amount = c.d(5, 6);
    return c.saved
      ? { damage: { amount: Math.floor(amount / 2), energy: "sonic" } }
      : { damage: { amount, energy: "sonic" }, conditions: ["deafened"], rounds: c.d(2, 6) };
  }, { save: partial("fort") }),
);
add(
  "chill-touch",
  attack("1d6 damage and 1 Strength damage (Fortitude negates the Strength damage); undead flee instead", (c) => {
    if (isUndead(c.target)) {
      return { conditions: ["panicked"], rounds: c.d(1, 4) + c.cl, notes: ["Undead take no damage but flee as if panicked."] };
    }
    return {
      damage: { amount: c.d(1, 6) },
      mods: c.saved ? [] : [pen("str", 1)],
      notes: c.saved ? [] : ["Ability damage: heals 1 point per day."],
      rounds: c.saved ? undefined : null,
      stacksWithSelf: true,
    };
  }, { save: (t) => (isUndead(t) ? WILL : partial("fort")), tags: NEG }),
);
add(
  "disintegrate",
  attack("2d6 damage per caster level (max 40d6); 5d6 on a successful Fortitude save", (c) => ({
    damage: { amount: c.saved ? c.d(5, 6) : c.d(Math.min(40, 2 * c.cl), 6) },
  }), { save: partial("fort") }),
);
const slay = (summary: string, onSave: (c: Ctx) => number) =>
  attack(summary, (c) => ({ damage: { amount: c.saved ? onSave(c) : c.target.hp + 10 } }), { save: partial("fort"), tags: ["death"] });
add("finger-of-death", slay("Death; 3d6 + caster level damage (max +25) on a successful Fortitude save", (c) => c.d(3, 6) + Math.min(25, c.cl)));
add("slay-living", slay("Death; 3d6 + caster level damage on a successful Fortitude save", (c) => c.d(3, 6) + c.cl));
add(
  "power-word-kill",
  attack("Kills a creature with 100 or fewer hit points", (c) =>
    c.target.hp > 100
      ? { noEffect: "Power Word Kill has no effect on a creature with 101 or more hit points." }
      : { damage: { amount: c.target.hp + 10 } },
  { save: null, tags: ["death", "mind"] }),
);

// ============================================================ undead-only spells
add("disrupt-undead", attack("1d6 damage to an undead creature", (c) => ({ damage: { amount: c.d(1, 6) } }), { save: null }));
add(
  "halt-undead",
  debuff("Held immobile", () => ({
    conditions: ["paralyzed"],
    notes: ["Ends if you are attacked or take damage. Mindless undead get no saving throw."],
  }), { save: WILL }),
);

// ============================================================ ethereal travel
// Ethereal is its own state, not invisibility: you are on another plane.
add(["ethereal-jaunt", "etherealness"], buff("Ethereal: on the Ethereal Plane, not merely unseen", () => ({ conditions: ["ethereal"] })));
add(
  "mislead",
  buff("Invisible while an illusory double takes your place", () => ({
    conditions: ["invisible"],
    notes: ["As greater invisibility, so attacking doesn't end it. The double lasts while you concentrate, plus 3 rounds."],
  })),
);

// ============================================================ alignment spells
// The data file says who is untouched (targetRequirements.alignmentNot);
// these decide how hard everyone else is hit.
const SLOWED: Out = {
  mods: [pen("attack", 1), pen("ac", 1), pen("ref", 1)],
  speedMult: 0.5,
  notes: ["Slowed: only a single move or standard action each turn."],
};
const OPPOSITE: Record<AlignComponent, AlignComponent> = { good: "evil", evil: "good", lawful: "chaotic", chaotic: "lawful" };
const smite = (hated: AlignComponent, riderText: string, rider: (c: Ctx) => Out) =>
  attack(
    `${hated[0].toUpperCase()}${hated.slice(1)} creatures take 1d8 damage per 2 caster levels (max 5d8; ${hated} outsiders 1d6 per level, max 10d6) and are ${riderText}. Creatures that are neither ${hated} nor ${OPPOSITE[hated]} take half damage and nothing more`,
    (c) => {
      const full = alignmentParts(c.target.alignment).includes(hated);
      let amount = full && c.target.type === "outsider" ? c.d(Math.min(10, c.cl), 6) : c.d(clamp(Math.floor(c.cl / 2), 1, 5), 8);
      if (!full) amount = Math.floor(amount / 2);
      if (c.saved) amount = Math.floor(amount / 2);
      return { damage: { amount }, ...(full && !c.saved ? rider(c) : {}) };
    },
    { save: partial("will") },
  );
add("holy-smite", smite("evil", "blinded for 1 round", () => ({ conditions: ["blinded"], rounds: 1 })));
add("unholy-blight", smite("good", "sickened for 1d4 rounds", (c) => ({ conditions: ["sickened"], rounds: c.d(1, 4) })));
add("chaos-hammer", smite("lawful", "slowed for 1d6 rounds", (c) => ({ ...SLOWED, rounds: c.d(1, 6) })));
add("orders-wrath", smite("chaotic", "dazed for 1 round", () => ({ conditions: ["dazed"], rounds: 1 })));

/** Holy Word and its kin: the result depends on how far your Hit Dice fall below the caster level. */
const word = (summary: string, equal: Build, lower: Build, farLower: Build) =>
  debuff(summary, (c) => {
    const gap = c.cl - c.target.hd;
    if (gap < 0) return { noEffect: `You have more Hit Dice (${c.target.hd}) than the caster level (${c.cl}), so you are unaffected.` };
    if (gap >= 10) return { damage: { amount: c.target.hp + 10 } };
    const out = gap >= 5 ? farLower(c) : gap >= 1 ? lower(c) : equal(c);
    const notes = [...(out.notes ?? [])];
    if (c.target.subtypes.includes("extraplanar")) notes.push("As an extraplanar creature you are also banished to your home plane unless you make a Will save at \u22124.");
    return { ...out, notes };
  }, { save: null });
const BY_HD = "By your Hit Dice against the caster level:";
add(
  "holy-word",
  word(
    `${BY_HD} deafened, blinded, paralyzed, or killed`,
    (c) => ({ conditions: ["deafened"], rounds: c.d(1, 4) }),
    (c) => ({ conditions: ["blinded", "deafened"], rounds: c.d(2, 4), notes: ["The deafness ends sooner (1d4 rounds)."] }),
    (c) => ({ conditions: ["paralyzed", "blinded", "deafened"], rounds: c.d(1, 10) * 10, notes: ["Paralyzed for the full time; the blindness lasts 2d4 rounds and the deafness 1d4 rounds."] }),
  ),
);
add(
  "blasphemy",
  word(
    `${BY_HD} dazed, weakened, paralyzed, or killed`,
    () => ({ conditions: ["dazed"], rounds: 1 }),
    (c) => ({ mods: [pen("str", c.d(2, 6))], rounds: c.d(2, 4), notes: ["Also dazed for the first round."] }),
    (c) => ({ conditions: ["paralyzed"], mods: [pen("str", c.d(2, 6))], rounds: c.d(1, 10) * 10, notes: ["Paralyzed for the full time; the Strength loss lasts 2d4 rounds. Also dazed for the first round."] }),
  ),
);
add(
  "dictum",
  word(
    `${BY_HD} deafened, slowed, paralyzed, or killed`,
    (c) => ({ conditions: ["deafened"], rounds: c.d(1, 4) }),
    (c) => ({ ...SLOWED, conditions: ["deafened"], rounds: c.d(2, 4), notes: [...(SLOWED.notes ?? []), "The deafness ends sooner (1d4 rounds)."] }),
    (c) => ({ ...SLOWED, conditions: ["paralyzed", "deafened"], rounds: c.d(1, 10) * 10, notes: ["Paralyzed for the full time; slowed for 2d4 rounds and deafened for 1d4 rounds."] }),
  ),
);
add(
  "word-of-chaos",
  word(
    `${BY_HD} deafened, stunned, confused, or killed`,
    (c) => ({ conditions: ["deafened"], rounds: c.d(1, 4) }),
    (c) => ({ conditions: ["deafened"], rounds: c.d(1, 4), notes: ["Also stunned for the first round."] }),
    (c) => ({ conditions: ["confused", "deafened"], rounds: c.d(1, 10) * 10, notes: ["Confused for the full time; deafened for 1d4 rounds and stunned for the first round."] }),
  ),
);

export function getDef(slug: string | null | undefined): SpellDef | undefined {
  return slug ? DEFS[slug] : undefined;
}

export const CURATED_SLUGS: string[] = Object.keys(DEFS);
/** Curated spells that ask which version or option was cast. */
export const OPTION_SLUGS: string[] = CURATED_SLUGS.filter((slug) => (DEFS[slug].options?.length ?? 0) > 0);
