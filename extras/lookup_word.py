#!/usr/bin/env python3

import os
import sqlite3
from wsgiref.handlers import CGIHandler

try:
    import simplejson as json
except ImportError:
    import json

from philologic.runtime.ObjectFormatter import adjust_bytes
from philologic.runtime.DB import DB

import sys
sys.path.append("..")
import custom_functions
from custom_functions import isGreek

try:
     from custom_functions import WebConfig
except ImportError:
     from philologic.runtime import WebConfig
try:
     from custom_functions import WSGIHandler
except ImportError:
     from philologic.runtime import WSGIHandler

def expand_codes ( code ):

    if code is None: return code

    expanded = ""
    map0 = {
          "n-": "noun",
          "ne": "proper noun",
          "v-": "",
          "vc": "",
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

def get_next_segment (cursor, tokenid):

    lemma = ""
    newid = str(int(tokenid) + 1)
    parses_query = "select lemma from parses where tokenid = ? order by prob desc;"

    parses_result = cursor.execute(parses_query, (newid, )).fetchone()
    lemma = parses_result[0]

    return lemma

def lookup_word_service(environ, start_response):
    status = '200 OK'
    headers = [('Content-type', 'application/json; charset=UTF-8'), ("Access-Control-Allow-Origin", "*")]
    start_response(status, headers)
    config = WebConfig(os.path.abspath(os.path.dirname(__file__)).replace('scripts', ''))
    db = DB(config.db_path + '/data/')
    request = WSGIHandler(environ, config)
    cursor = db.dbh.cursor()

    try: 
        word_id = request.id
    except NameError:
        word_id = 0

    if request.report == "concordance" or request.report == "word_property_filter":
        token = request.selected
    elif request.report == "kwic":
        token = request.selected
    elif request.report == "navigation":
        token = request.selected
        philo_id = request.philo_id.split(" ")
        text_obj = db[philo_id]
        start_byte, end_byte = int(text_obj.start_byte), int(text_obj.end_byte)
        filename = text_obj.filename
    else:
        pass
    token_n = 0
    yield lookup_word_by_id(db, cursor, token, token_n, word_id).encode("utf8")

def lookup_word_by_id(db, cursor, token, n, word_id):
    best_parse = ("","")
    all_parses = {}
    authority = ""
    blesslex = ""
    blesslemma = ""
    defn = ""
    best_defn = ""
    note = ""
    best_note = ""
    alt_lsj = ""
    best_prob = ""
    best_alt_lsj = ""
    lookup_word = token
    old_prob = 0
    morph_lang = ""

    alt_field = ""
    if isGreek(token):
        alt_field = "alt_lsj"
        morph_lang = "greek"
    else:
        alt_field = "alt_ls"
        morph_lang = "latin"

    try:
        tokenid = word_id
        lex_connect = sqlite3.connect(db.locals.db_path + "/data/lexicon.db")
        lex_cursor = lex_connect.cursor()
        auth_query = "select lex,code,lemma,prob,authority from parses where tokenid = ? and authority is not null;"
        parses_query = "select lex,code,lemma,prob,authority from parses where tokenid = ? order by prob desc;"
        shortdefs_query = "select lemma,def from shortdefs where lemma=?"
        Lexicon_query = "select Lexicon.lemma,Lexicon.code,Lexicon.%s,Lexicon.lexid,note from Lexicon where Lexicon.lexid=?;" % alt_field
        all_Lexicon_query = "select Lexicon.lemma,Lexicon.code,Lexicon.%s,Lexicon.lexid,note from lexicon where token in (select content from tokens where tokenid=?);" % alt_field

        # first check if we have an authorized result
        auth_result = lex_cursor.execute(auth_query, (tokenid, )).fetchone()
        if auth_result:
            lexid = auth_result[0]
            authority = auth_result[4]

            # for the authorized parse, get the Lexicon entry
            Lexicon_result = lex_cursor.execute(Lexicon_query, (lexid, )).fetchone()
            # handle segments in special manner
            if auth_result[0] is None:
                 #lookup_word = get_next_segment(lex_cursor, tokenid)
                 best_parse = (auth_result[2], auth_result[1])
            else:
                 best_parse = (Lexicon_result[0], Lexicon_result[1])
                 best_defn = Lexicon_result[3]
                 best_alt_lsj = Lexicon_result[2]
                 best_note = Lexicon_result[4]

            if best_parse[0] == "segment": lookup_word = get_next_segment(lex_cursor, tokenid)
            else: lookup_word = best_parse[0]

        else:
            # if we don't have an authorized result, get the highest probability result
            prob_result = lex_cursor.execute(parses_query, (tokenid, )).fetchone()
            lexid = prob_result[0]

            Lexicon_result = lex_cursor.execute(Lexicon_query, (lexid, )).fetchone()
            if prob_result[0] is None:
                best_parse = (prob_result[2], prob_result[1])
            elif Lexicon_result:
                lookup_word = best_parse[0]
                best_parse = (Lexicon_result[0], Lexicon_result[1])
#                best_defn = Lexicon_result[3]
                best_alt_lsj = Lexicon_result[2]
                best_note = Lexicon_result[4]
            else:
                best_defn = "Unknown"
            lookup_word = best_parse[0]

        # now get the shortdef
        shortdefs_result = lex_cursor.execute(shortdefs_query, (best_parse[0], )).fetchone()
        if shortdefs_result:
            best_defn = shortdefs_result[1]
        else:
            best_defn = ""

        # now get all of the other possible parse results
        Lexicon_result = lex_cursor.execute(all_Lexicon_query, (tokenid, )).fetchall()
        for Lexicon_row in Lexicon_result:
            L_lemma = Lexicon_row[0]
            L_pos = Lexicon_row[1]
            parse = (L_lemma, L_pos)

            alt_lsj = Lexicon_row[2]
            note = Lexicon_row[4]

            # now get the shortdef
            shortdefs_result = lex_cursor.execute(shortdefs_query, (parse[0], )).fetchone()
            if shortdefs_result:
                best_defn = shortdefs_result[1]
            else:
                best_defn = ""

            # if the current result is not a best_parse, then include it
            if parse != best_parse:
                if L_lemma not in all_parses:
                    expanded_pos = expand_codes(L_pos)
                    all_parses[L_lemma] = [(expanded_pos, defn, alt_lsj, note)]
                else:
                    expanded_pos = expand_codes(L_pos)
                    all_parses[L_lemma].append((expanded_pos, "", alt_lsj, note))

    except Exception as e:
        print(str(e) + " on line " + str(e.__traceback__.tb_lineno), file=sys.stderr)

    # check if 'user' cookie is set to determine whether to construct the morph_url
    cookies = os.environ['HTTP_COOKIE']
    cookies = cookies.split(';')
    #print(cookies, file=sys.stderr)
    morph_url = ""
    if any("user" in var for var in cookies):
        morph_url = "https://anastrophe.uchicago.edu/cgi-bin/perseus/morph.pl?id=%s&&lang=%s" % (tokenid, morph_lang)

    result_object = {
        'properties': [{"property": "Definition",
                        "value": best_defn},
                       {"property": "Parse",
                        #"value": expand_codes(row['pos']) + " %s %s" % (u"\u2713" if authority else "", u"\u2713" if blesslex else "")},
                        #"value": ("%s") % (expand_codes(row['pos']))},
                        "value": ("%s") % (expand_codes(best_parse[1]))},
                       {"property": "Alt_lsj",
                       "value": best_alt_lsj},
                       {"property": "note",
                       "value": best_note},
        ],
        'problem_report': 'https://docs.google.com/forms/d/1lyhb35OB9JLuMwy8-PK6gOFn6EnO9c9W52WoICLkuac/viewform?formkey=clpPVXBDZkJ6bDlTLVZOZThybFBNbGc6MA',
        'token': token,
        'tokenid': tokenid,
        'morph_url': morph_url,
        #'lemma': row['lemma'],
        'lemma': best_parse[0],
        'blesslemma': u"\u2713" if blesslemma else "",
        'authority': u"\u2713" if authority else "",
        #'philo_id': row['philo_id'],
        'philo_id': "FIX THIS",
        'alt_lemma': [],
        "dictionary_name": 'Logeion',
        "dictionary_lookup": "https://logeion.uchicago.edu/" + token,
        "alt_parses": [{
            "lemma": l,
            "parse": all_parses[l],
            "dictionary_lookup": "https://logeion.uchicago.edu/" + ''.join([i for i in l if not str(i).isdigit()])
        } for l, p in all_parses.items()]  #,
    }
    return json.dumps(result_object)

if __name__ == "__main__":
    if len(sys.argv) > 6:
        db = DB(sys.argv[1])
        print(db.dbh, file=sys.stderr)
        cursor = db.dbh.cursor()
        lookup_word(cursor, sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6])
    else:
        CGIHandler().run(lookup_word_service)
