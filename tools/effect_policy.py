"""Default application boundary; typed resolution helpers are opt-in DM tools."""

POLICY = dict(scope='all-core-effects', automaticallyApply='recipient-sheet-numbers-only',
              otherwise='player-dm-adjudication', preserveSourceText=True,
              typedReferenceIsNotAuthorization=True, dmMayOverride=True)


def application_mode(effect):
    """Fail closed: a numeric DC, duration or die does not make an effect a sheet modifier."""
    operation = effect.get('operation')
    if effect.get('target', 'recipient') not in ('recipient', 'self'):
        return 'adjudicate'
    if operation == 'modifier' and isinstance(effect.get('statId'), str) and 'amount' in effect:
        return 'recipient-sheet'
    if operation in ('size-change', 'movement-enhancement', 'temporary-hp'):
        return 'recipient-sheet'
    return 'adjudicate'


def annotate(effects):
    for effect in effects:
        effect['applicationMode'] = application_mode(effect)
