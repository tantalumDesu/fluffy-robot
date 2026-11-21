"""Source-backed effects and a resolver for numeric sheet modifiers."""
import re


def modifier(stat, amount, bonus=None, stacking=None, **qualifiers):
    return dict(operation='modifier', statId=stat, amount=amount, bonusType=bonus,
                stacking=stacking or ('highest-same-type' if bonus and bonus not in ('dodge', 'circumstance') else 'once-per-effect'), **qualifiers)


def catalogs(spells, feats, skills):
    spell_by_id = {s['id']: s for s in spells}
    skill_by_name = {s['name'].casefold(): s['id'] for s in skills}
    spell_effects, feat_effects = {}, {}

    def spell(key, unit, per_level, effects, **extra):
        record = spell_by_id[key]
        duration = {'unit': unit, 'perCasterLevel' if per_level else 'amount': 1}
        if record['duration'].get('dismissible'):
            duration['dismissible'] = True
        spell_effects[key] = [dict(effect, id=f'{key}:{i}', target='recipient',
                                   application='confirmed-by-player', duration=duration,
                                   source={'file': record['file'], 'heading': record['name']}, **extra)
                              for i, effect in enumerate(effects, 1)]

    def feat(key, *effects):
        feat_effects[key] = [dict(effect, id=f'{key}:{i}', source=feats[key]['source'])
                             for i, effect in enumerate(effects, 1)]

    spell('mage-armor', 'hour', True, [dict(modifier('ac', 4, 'armor'), appliesAgainstIncorporeal=True)])
    # Retain the published ID for saved effect references.
    spell_effects['mage-armor'][0]['id'] = 'mage-armor:armor-bonus'
    spell('shield', 'minute', True, [dict(modifier('ac', 4, 'shield'), appliesAgainstIncorporeal=True),
                                    {'operation': 'spell-defense', 'negatesSpellId': 'magic-missile'}])
    spell('shield-of-faith', 'minute', True, [modifier('ac', {'kind': 'caster-level-steps',
          'base': 2, 'start': 0, 'every': 6, 'max': 5}, 'deflection')])
    spell('false-life', 'hour', True, [{'operation': 'temporary-hp', 'dice': '1d10',
          'casterLevelBonusMax': 10, 'endsWhenPoolDepleted': True}])
    for alignment in ('chaos', 'evil', 'good', 'law'):
        spell('protection-from-' + alignment, 'minute', True,
              [modifier(stat, 2, bonus, requires={'sourceAlignmentTag': alignment})
               for stat, bonus in (('ac', 'deflection'), ('save', 'resistance'))])
    spell('resistance', 'minute', False, [modifier('save', 1, 'resistance')])
    for key, amount in [('bless', 1), ('bane', -1), ('aid', 1)]:
        bonus = 'morale' if amount > 0 else None
        effects = [modifier('attack', amount, bonus), modifier('save', amount, bonus, requires={'saveAgainst': 'fear'})]
        if key == 'aid':
            effects.append({'operation': 'temporary-hp', 'dice': '1d8', 'casterLevelBonusMax': 10})
        spell(key, 'minute', True, effects, **({'countersAndDispels': ['bane' if key == 'bless' else 'bless']} if key != 'aid' else {}))
    spell('virtue', 'minute', False, [{'operation': 'temporary-hp', 'amount': 1}])
    spell('heroism', 'minute', True, [modifier(stat, 2, 'morale') for stat in ('attack', 'save', 'skill')])
    for effect in spell_effects['heroism']:
        effect['duration'] = {'unit': 'minute', 'perCasterLevel': 10}
    spell('heroism-greater', 'minute', True,
          [modifier(stat, 4, 'morale') for stat in ('attack', 'save', 'skill')] +
          [{'operation': 'immunity', 'effectTag': 'fear'},
           {'operation': 'temporary-hp', 'casterLevelBonusMax': 20}])
    for key, ability in [('bulls-strength', 'str'), ('cats-grace', 'dex'), ('bears-endurance', 'con'),
                         ('eagles-splendor', 'cha'), ('foxs-cunning', 'int'), ('owls-wisdom', 'wis')]:
        for variant in (key, key + '-mass'):
            qualifiers = {'recalculateDerivedStats': True}
            if ability in ('int', 'wis', 'cha'):
                qualifiers.update(grantsBonusSpellSlots=False, affectsSpellSaveDc=True)
            if ability == 'int':
                qualifiers['grantsSkillPoints'] = False
            if ability == 'con':
                qualifiers['hpPolicy'] = 'adjust-current-and-max-by-hd-not-temporary-hp'
            spell(variant, 'minute', True, [dict(modifier('ability:' + ability, 4, 'enhancement'), **qualifiers)])
    spell('barkskin', 'minute', True, [modifier('natural-armor', {'kind': 'caster-level-steps', 'base': 2,
           'start': 3, 'every': 3, 'max': 5}, 'enhancement')])
    spell_effects['barkskin'][0]['duration'] = {'unit': 'minute', 'perCasterLevel': 10}
    spell('divine-favor', 'minute', False, [modifier(stat, {'kind': 'caster-level-steps', 'base': 0,
          'start': 0, 'every': 3, 'min': 1, 'max': 3}, 'luck') for stat in ('attack', 'weapon-damage')])

    spell('haste', 'round', True, [modifier('attack', 1), modifier('ac', 1, 'dodge'),
          modifier('save:ref', 1, 'dodge', suppressedWhen='denied-dex-to-ac'),
          {'operation': 'extra-full-attack-attack', 'amount': 1, 'atFullBab': True, 'stacking': 'noncumulative'},
          {'operation': 'movement-enhancement', 'amountFt': 30, 'maxSpeedMultiplier': 2, 'modes': 'all'}],
          countersAndDispels=['slow'])

    for key, record in feats.items():
        match = re.search(r'^Benefit:\s*You get a \+2 bonus on all (.+?) checks and (.+?) checks\.$', record['text'], re.M)
        if match and all(name.casefold() in skill_by_name for name in match.groups()):
            feat(key, *(modifier('skill:' + skill_by_name[name.casefold()], 2) for name in match.groups()))
    for key, stat, amount in [('improved-initiative', 'initiative', 4), ('great-fortitude', 'save:fort', 2),
                              ('lightning-reflexes', 'save:ref', 2), ('iron-will', 'save:will', 2),
                              ('toughness', 'max-hp', 3)]:
        feat(key, modifier(stat, amount, stacking='sum' if key == 'toughness' else None))
    feat('skill-focus', modifier('skill', 3, requires={'skillId': '$skillId'}))
    for key, stat, amount in [('weapon-focus', 'attack', 1), ('greater-weapon-focus', 'attack', 1),
                              ('weapon-specialization', 'weapon-damage', 2), ('greater-weapon-specialization', 'weapon-damage', 2)]:
        feat(key, modifier(stat, amount, requires={'weaponId': '$weaponId'}))
    feat('dodge', modifier('ac', 1, 'dodge', 'once-per-effect', requires={'attackerId': '$opponentId'},
                           suppressedWhen='denied-dex-to-ac'))
    feat('point-blank-shot', *(modifier(stat, 1, requires={'attackKind': 'ranged'}, maxDistanceFt=30)
                              for stat in ('attack', 'weapon-damage')))
    feat('two-weapon-defense', modifier('ac', 1, 'shield', requires={'qualifiesForTwoWeaponDefense': True}),
         modifier('ac', 2, 'shield', requires={'qualifiesForTwoWeaponDefense': True, 'defensiveStance': True}))
    feat('combat-reflexes', {'operation': 'opportunity-attacks', 'extraFrom': 'positive-dexterity-modifier',
                             'allowedWhileFlatFooted': True})
    return spell_effects, feat_effects


def modifier_total(stat_id, instances, context=None):
    """Total matching modifiers from active (effect, instance parameters) pairs for one stat.

    Caller resolves active durations, conditions and derived stats. Unknown choices fail closed.
    """
    context = context or {}
    best, worst, seen, total = {}, {}, set(), 0
    family, _, member = stat_id.partition(':')
    context = dict(context)
    if family == 'skill' and member:
        context['skillId'] = member
    for effect, params in instances:
        if effect['operation'] != 'modifier' or effect['statId'] not in (stat_id, family):
            continue
        if stat_id == 'ac' and effect.get('bonusType') in ('armor', 'shield', 'natural-armor'):
            if context.get('attackMode') == 'touch':
                continue
            if context.get('attackMode') == 'incorporeal-touch' and not effect.get('appliesAgainstIncorporeal'):
                continue
        if (effect.get('suppressedWhen') in context.get('flags', ())
                or (stat_id == 'ac' and effect.get('bonusType') == 'dodge'
                    and 'denied-dex-to-ac' in context.get('flags', ()))):
            continue
        required = effect.get('requires', {})
        resolved = {k: params.get(v[1:]) if isinstance(v, str) and v.startswith('$') else v for k, v in required.items()}
        if any(v is None or (v not in context.get('sourceAlignmentTags', ()) if k == 'sourceAlignmentTag'
                             else context.get(k) != v) for k, v in resolved.items()):
            continue
        if 'maxDistanceFt' in effect:
            distance = context.get('distanceFt')
            if not isinstance(distance, (float, int)) or not 0 <= distance <= effect['maxDistanceFt']:
                continue
        amount = effect['amount']
        if isinstance(amount, dict):
            level = params.get('casterLevel')
            if isinstance(level, bool) or not isinstance(level, int) or level < 1:
                continue
            amount = min(amount['max'], max(amount.get('min', amount['base']),
                         amount['base'] + (level - amount['start']) // amount['every']))
        if effect['stacking'] == 'highest-same-type':
            key = effect['bonusType']
            if amount < 0:
                worst[key] = min(worst.get(key, 0), amount)
            else:
                best[key] = max(best.get(key, 0), amount)
        elif effect['stacking'] == 'once-per-effect':
            if effect['id'] not in seen:
                total += amount
                seen.add(effect['id'])
        elif effect['stacking'] == 'sum':
            total += amount
    return total + sum(best.values()) + sum(worst.values())
