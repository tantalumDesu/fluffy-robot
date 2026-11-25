"""Physical weapon damage types, distinct from alignment and energy."""
import re

PHYSICAL = ('bludgeoning', 'piercing', 'slashing')


def physical_profile(raw):
    text = raw.strip().lower()
    if text in ('—', '-', ''):
        return None
    ids = re.split(r' and | or ', text)
    if not set(ids) <= set(PHYSICAL) or (' and ' in text and ' or ' in text):
        raise ValueError(f'Unknown physical damage type expression: {raw!r}')
    return {'typeIds': ids, 'mode': 'choose-one' if ' or ' in text else 'all'}


def resolve_physical_types(profile, choice=None):
    if not profile:
        if choice is not None:
            raise ValueError('No physical damage type choice is available')
        return ()
    types = profile['typeIds']
    if not types or not set(types) <= set(PHYSICAL):
        raise ValueError('Invalid physical damage type profile')
    if profile['mode'] == 'choose-one':
        if choice not in types:
            raise ValueError('Choose one listed physical damage type for this hit')
        return (choice,)
    if profile['mode'] != 'all' or choice is not None:
        raise ValueError('This hit uses all listed physical damage types')
    return tuple(types)


def equipment_attack_damage(core, host_item_id, attack_item_id, *, addition_ids=()):
    """Resolve damage type for a declared attack with a confirmed equipped host."""
    items = core['inventory']['itemsById']
    host, attack = items[host_item_id], items[attack_item_id]
    profile = attack.get('attackProfile', {})
    if profile.get('kind') != 'equipment-attack':
        raise ValueError('Not a host equipment attack')
    if ('hostKind' in profile and host['kind'] != profile['hostKind'] or
            'hostItemIds' in profile and host_item_id not in profile['hostItemIds']):
        raise ValueError('Incompatible equipped host')
    required = profile.get('requiredAdditionId')
    if required:
        if required not in addition_ids:
            raise ValueError('Required spikes are not installed')
        return items[required]['physicalDamage']
    if 'armor:shield-spikes' in addition_ids:
        raise ValueError('Use the spiked shield bash profile')
    return attack['physicalDamage']
