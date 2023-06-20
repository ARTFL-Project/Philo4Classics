#!/usr/bin/env python3

def bib_citation_format (filename):

    import os, sys, csv

    dirname = os.path.dirname(__file__)
    abbrevs_file = "Latin.abbrevs"
    abbrevs = ""
    if os.path.exists(os.path.join(dirname, abbrevs_file)):
        abbrevs = os.path.join(dirname, abbrevs_file)
    else:
        return (False,False)

    """Find appropriate abbrev for the citation"""
    abbrevs = list(csv.reader(open(abbrevs, 'rt'), delimiter='\t'))

    citation_short = ""
    try:
        for i in abbrevs:
            if filename.strip() in i:
                citation_short = i[0]
                break
        if not citation_short: return(False,False)
    except:
        return(False,False)

    author = citation_short.split()[0]
    title = ""

    try:
        title = citation_short.split()[1]
        title = ' '.join(citation_short.split()[1:])
    except:
        title = ""
    return (author, title)

def isEnglish(s):
    try:
        s.encode(encoding='utf-8').decode('ascii')
    except UnicodeDecodeError:
        return False
    else:
        return True

def isGreek(s):
    maxchar = max(s)
    if '\u0370' <= maxchar <= u'\u1fff':
        return True
    return False

def expand_codes ( code ):
    expanded = ""
    map0 = {
          "n-": "noun",
          "ne": "proper noun",
          "v-": "",
          "vc": "copula verb",
          "t-": "",
          "a-": "adjective",
          "ae": "proper name adjective",
          "d-": "adverb",
          "dd": "demonstrative adverb",
          "de": "proper name adverb",
          "di": "interrogative adverb",
          "dr": "relative adverb",
          "dx": "indefinite adverb",
          "c-": "conjunction",
          "e-": "particle",
          "r-": "preposition",
          "p-": "pronoun",
          "pa": "definite article",
          "pc": "reciprocal pronoun",
          "pd": "demonstrative pronoun",
          "pi": "interrogative pronoun",
          "pk": "reflexive pronoun",
          "pp": "personal pronoun",
          "pr": "relative pronoun",
          "ps": "possessive pronoun",
          "px": "indefinite pronoun",
          "m-": "numeral",
          "i-": "interjection",
          "e": "exclamation",
          "l": "article",
          "x": "particle",
          "g-": "particle",
          "gm": "modal particle"
    }
    map2 = {
          "1": "1",
          "2": "2",
          "3": "3"
    }
    map3 = {
          "s": "sg.",
          "d": "dual",
          "p": "pl."
    }
    map4 = {
          "p": "present",
          "i": "imperfect",
          "f": "future",
          "t": "future perfect",
          "a": "aorist",
          "r": "perfect",
          "l": "pluperfect"
    }
    map5 = {
           "i": "indicative",
           "m": "imperative",
           "n": "infinitive",
           "p": "participle",
           "s": "subjunctive",
           "o": "optative",
           "d": "gerund",
           "g": "gerundive",
           "u": "supine",
    }
    map6 = {
          "a": "active",
          "m": "middle",
          "p": "passive",
          "e": "middle-passive"
    }
    map7 = {
          "m": "masc.",
          "f": "fem.",
          "n": "neut.",
          "c": "common"
    }
    map8 = {
          "n": "nom.",
          "g": "gen.",
          "d": "dat.",
          "a": "acc.",
          "b": "abl.",
          "v": "voc.",
          "l": "loc.",
          "i": "instr."
    }
    map9 = {
          "c": "comparative",
          "s": "superlative"
    }

    if code[:2] in map0:
        expanded += " " + map0[code[:2]]
    if code[4:5] in map4:
        expanded += " " + map4[code[4:5]]
    if code[6:7] in map6:
        expanded += " " + map6[code[6:7]]
    if code[5:6] in map5:
        expanded += " " + map5[code[5:6]]
    if code[7:8] in map7:
        expanded += " " + map7[code[7:8]]
    if code[8:9] in map8:
        expanded += " " + map8[code[8:9]]
    if code[2:3] in map2:
        expanded += " " + map2[code[2:3]]
    if code[3:4] in map3:
        expanded += " " + map3[code[3:4]]
    if code[9:] in map9:
        expanded += " " + map9[code[9:]]

    return expanded

