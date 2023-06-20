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
    if word_id:
        yield lookup_word_by_id(db, cursor, token, token_n, word_id).encode("utf8")
    else:
        yield lookup_word(db, cursor, token, token_n, start_byte, end_byte, filename).encode("utf8")

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

    alt_field = ""
    if isGreek(token):
        alt_field = "alt_lsj"
    else:
        alt_field = "alt_ls"

    try:
        tokenid = word_id
        lex_connect = sqlite3.connect(db.locals.db_path + "/data/lexicon.db")
        lex_cursor = lex_connect.cursor()
        auth_query = "select lex,code,lemma,prob,authority from parses where tokenid = ? and authority is not null;"
        parses_query = "select lex,code,lemma,prob,authority from parses where tokenid = ? order by prob desc;"
        Lexicon_query = "select Lexicon.lemma,Lexicon.code,Lexicon.%s,shortdefs.def,Lexicon.lexid,note from Lexicon,shortdefs where Lexicon.lexid=? and shortdefs.lemma=Lexicon.lemma;" % alt_field
        all_Lexicon_query = "select Lexicon.lemma,Lexicon.code,Lexicon.%s,shortdefs.def,Lexicon.lexid,note from lexicon,shortdefs where token in (select content from tokens where tokenid=?) and shortdefs.lemma=Lexicon.lemma;" % alt_field

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
                 best_note = Lexicon_result[5]

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
                best_defn = Lexicon_result[3]
                best_alt_lsj = Lexicon_result[2]
                best_note = Lexicon_result[5]
            else:
                best_defn = "Unknown"
            lookup_word = best_parse[0]

        # now get all of the other possible parse results
        Lexicon_result = lex_cursor.execute(all_Lexicon_query, (tokenid, )).fetchall()
        for Lexicon_row in Lexicon_result:
            L_lemma = Lexicon_row[0]
            L_pos = Lexicon_row[1]
            parse = (L_lemma, L_pos)

            alt_lsj = Lexicon_row[2]
            defn = Lexicon_row[3]
            note = Lexicon_row[5]

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
        #'lemma': row['lemma'],
        'lemma': best_parse[0],
        'blesslemma': u"\u2713" if blesslemma else "",
        'authority': u"\u2713" if authority else "",
        #'philo_id': row['philo_id'],
        'philo_id': "FIX THIS",
        'alt_lemma': [],
        "dictionary_name": 'Logeion',
        "dictionary_lookup": "http://logeion.uchicago.edu/" + lookup_word,
        "alt_parses": [{
            "lemma": l,
            "parse": all_parses[l],
            "dictionary_lookup": "http://logeion.uchicago.edu/" + ''.join([i for i in l if not str(i).isdigit()])
        } for l, p in all_parses.items()]  #,
    }
    return json.dumps(result_object)

def lookup_word(db, cursor, token, n, start, end, filename):
    #print("Hello!", file=f)
    #f = open("/tmp/test.log", "a")
    i = 0
    query = "select * from words where (start_byte >= ?) and (end_byte <= ?) and (filename = ?);"
    print("%s %s %s" % ("QUERY", query, (start,end,filename)), file=f)
    cursor.execute(query, (start, end, filename))
    #token_lower = token.decode("utf-8").lower().encode("utf-8")
    token_lower = token.lower()
    for row in cursor.fetchall():
        #print (row, file=f)
        #print("%s %s" % (row['philo_name'], type(row['philo_name'])), file=f)
        #print(token, file=f)
        #if row['philo_name'] == token_lower:
        # don't check against lowercase, ridiculous!
        if row['philo_name'] == token:
            #print(row['philo_name'], file=f)
            #print(row["tokenid"], file=f)

            best_parse = (row["lemma"], row["pos"])
            #print("Best Parse: %s", best_parse, file=f)
            all_parses = {}
            authority = ""
            blesslex = ""
            blesslemma = ""
            best_prob = ""
            defn = ""
            best_defn = ""
            alt_lsj = ""
            best_alt_lsj = ""
            try:
                tokenid = row["tokenid"]
                #print(db.locals.db_path, file=f)
                lex_connect = sqlite3.connect(db.locals.db_path + "/data/lexicon.db")
                lex_cursor = lex_connect.cursor()
                prob_cursor = lex_connect.cursor()
                auth_query = "select authority from parses where authority is not null and tokenid = ?;"
                auth_result = lex_cursor.execute(auth_query, (tokenid, )).fetchone()
                if auth_result:
                    authority = auth_result[0]
                #print("Authority: %s" % authority, file=f)

                lex_query = "select Lexicon.lemma,Lexicon.code,Lexicon.alt_lsj,shortdefs.def,Lexicon.lexid from lexicon,shortdefs where token in (select content from tokens where tokenid=?) and shortdefs.lemma=Lexicon.lemma;"
                #lex_query = "select Lexicon.lemma,Lexicon.code,Lexicon.alt_lsj,shortdefs.def from lexicon,shortdefs where token in (select content from tokens where tokenid=?) and shortdefs.lemma=Lexicon.lemma;"
                #                lex_query = "select Lexicon.lemma,Lexicon.code,authority,shortdefs.def from parses,Lexicon,shortdefs where parses.tokenid = ? and parses.lex=Lexicon.lexid and shortdefs.lemma=Lexicon.lemma;"
                #print ("LEX QUERY %s %s %s" % (lex_query, tokenid, token), file=f)
                lex_cursor.execute(lex_query, (tokenid, ))

                raw_parses = []
                for parse_row in lex_cursor.fetchall():

                    #print("Parse row: %s %s %s %s" % (parse_row[0], parse_row[1], parse_row[2], parse_row[3]), file=f)

                    prob = ""
                    prob_query = "select lex,prob from parses where tokenid=? order by prob desc;" 
                    prob_cursor.execute(prob_query, (tokenid, ))
                    for prob_row in prob_cursor.fetchall():
                        if prob_row[0] == parse_row[4]:
                            prob = prob_row[1]
                            #print("%s|%s" % (prob_row[0], prob), file=f)
                            continue

                    p_lemma, p_pos = parse_row[0], parse_row[1]
                    parse = (p_lemma, p_pos)
#                    if not defn and parse_row[2]:
                    if parse_row[3]:
                        defn = parse_row[3]
                        #print("%s %s" % ("DEFINITION:", parse_row[3]), file=f);
                    else:
                        defn = ""
                    if parse_row[2]:
                        alt_lsj = parse_row[2]
                        #print("ALT LSJ: %s" % alt_lsj, file=f)
                    else:
                        #print("NO ALT LSJ", file=f)
                        alt_lsj = ""

                    #print("Compare parses. Best: %s, Current: %s" % (best_parse, parse), file=f)
                    if parse != best_parse:
                        raw_parses.append(parse)
                        #print("ALT LSJ? (%s)" % alt_lsj, file=f)
                        if p_lemma not in all_parses:
                            expanded_pos = expand_codes(p_pos)
                            #expanded_pos = "%s %s" % (expand_codes(p_pos), prob if prob else "0")
                            if p_lemma == best_parse[0]: defn = ""
                            all_parses[p_lemma] = [(expanded_pos, defn, alt_lsj)]
                        else:
                            expanded_pos = expand_codes(p_pos)
                            #expanded_pos = "%s %s" % (expand_codes(p_pos), prob if prob else "0")
                            if p_lemma == best_parse[0]: defn = ""
                            all_parses[p_lemma].append((expanded_pos, "", alt_lsj))
                    else:
                        best_defn = defn
                        best_alt_lsj = alt_lsj
                        best_prob = prob
                        pass

            except:
                pass
            if i == int(n):
                lookup_word = row['lemma']
                if lookup_word == "<unknown>":
                    lookup_word = token
                result_object = {
                    'properties': [{"property": "Definition",
                                    "value": best_defn},
                                   {"property": "Parse",
                                    "value": ("%s") % (expand_codes(row['pos']))},
                                    #"value": ("%s %s") % (expand_codes(row['pos']), u"\u2713" if authority else "")},
                                    #"value": ("%s %s %s") % (expand_codes(row['pos']), u"\u2713" if authority else "", best_prob if best_prob else "")},
                                   {"property": "Alt_lsj",
                                    "value": best_alt_lsj}
                    ],
                    'problem_report': 'https://docs.google.com/forms/d/1lyhb35OB9JLuMwy8-PK6gOFn6EnO9c9W52WoICLkuac/viewform?formkey=clpPVXBDZkJ6bDlTLVZOZThybFBNbGc6MA',
                    'token': token,
                    'tokenid': tokenid,
                    'lemma': row['lemma'],
                    'blesslemma': u"\u2713" if blesslemma else "",
                    'authority': u"\u2713" if authority else "",
                    'philo_id': row['philo_id'],
                    "dictionary_name": 'Logeion',
                    "dictionary_lookup": "http://logeion.uchicago.edu/" + lookup_word,
                    "alt_parses": [{
                        "lemma": l,
                        "parse": all_parses[l],
                        "dictionary_lookup": "http://logeion.uchicago.edu/" + ''.join([i for i in l if not str(i).isdigit()])
                    } for l, p in all_parses.items()]  #,
                }
                return json.dumps(result_object)
            else:
                i += 1
    return json.dumps({})

if __name__ == "__main__":
    if len(sys.argv) > 6:
        db = DB(sys.argv[1])
        print(db.dbh, file=sys.stderr)
        cursor = db.dbh.cursor()
        lookup_word(cursor, sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6])
    else:
        CGIHandler().run(lookup_word_service)
