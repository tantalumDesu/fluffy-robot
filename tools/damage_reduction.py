"""Shared DR profiles and projection of confirmed sheet grants."""


def catalog(lines, source):
    def anchor(file, prefix):
        return source(file, line=next(i for i, row in enumerate(lines(file), 1) if row.startswith(prefix)))
    return {key: dict(amountByClassLevel={str(level): amount for level, amount in ratings}, bypassAnyOf=[],
                      source=anchor(file, 'Damage Reduction (Ex):'))
            for key, file, ratings in (
                ('barbarian', 'BARBARIAN.txt', [(7, 1), (10, 2), (13, 3), (16, 4), (19, 5)]),
                ('dwarven-defender', 'Prestige Class DWARVEN DEFENDER.txt', [(6, 3), (10, 6)]))}


def project_damage_reduction(core, class_levels, grants=()):
    """Preserve individual ratings: the highest rating can be bypassed while another applies."""
    result = []
    for key, rule in core['mechanics']['classDamageReductionById'].items():
        level = class_levels.get(key, 0)
        amount = max((amount for minimum, amount in rule['amountByClassLevel'].items()
                      if int(minimum) <= level), default=0)
        if amount:
            result.append(dict(sourceId=key, amount=amount, bypassAnyOf=[], source=rule['source']))
    for grant in grants:
        amount, clauses = grant['amount'], grant.get('bypassAnyOf', ())
        if type(amount) is not int or amount < 0 or any(
            not clause or isinstance(clause, str) or any(not isinstance(tag, str) or not tag for tag in clause)
            for clause in clauses
        ) or isinstance(clauses, str):
            raise ValueError('Invalid damage reduction grant')
        result.append(dict(grant, bypassAnyOf=[list(clause) for clause in clauses]))
    return result
