"""Read source descriptions without inheriting or rewriting their clauses."""
import re
import unicodedata

def normalized(text):
    text = unicodedata.normalize('NFKC', text).casefold().translate(str.maketrans('’‘“”–—', "''\"\"--"))
    return ' '.join(text.split())


def spell_sources(lines):
    text = '\n'.join(lines('SPELLBOOK.txt'))
    pattern = re.compile(r'^([^\n]+)\n\s*Short Description:[ \t]*(.*?)\nLong Description:[ \t]*\n?(.*?)(?=\nClass:)', re.M | re.S)
    return {normalized(name.strip()): (short.strip(), long.strip()) for name, short, long in pattern.findall(text)}
