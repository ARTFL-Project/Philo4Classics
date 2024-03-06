#!/usr/bin/env python3

import sys
import re
import os
import os.path
import sqlite3
import time
import string

tomsdb = "./toms.db"


# Important Settings #

lemmas_file = "lemmas_ranked.txt"
lemma_collocates_file = "lemma_collocates.txt"
lemmas_by_author_file = "lemmas_by_author_ranked.txt"
lemmas_by_text_file = "lemmas_by_text.txt"
forbidden_lemmas = ['ΑΒΓ', 'segment', '<unknown>', 'unknown']
#infodb = "/var/sqlite/logeion-dbs/GreekInfo.sqlite"
infodb = "/home/waltms/GreekInfo.sqlite"

#############################################################
### There should be no need to modify anything below here ### 
#############################################################

### Functions and Classes ###

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def user_inputchoices(question, default_choice, all_choices):
    eprint("\nChoices: %s" % ', '.join(all_choices))
    user_choice = ""
    while user_choice not in all_choices:
        user_choice = input(question % default_choice) or default_choice
        if not user_choice:
            return default_choice
        elif user_choice not in all_choices: eprint("Sorry, unknown. Select from listed choices.")
    return user_choice

def user_setpath(question, default_choice="", path_suffix=""):
    user_choice = ""
    if path_suffix: user_choice = os.path.join(user_choice, path_suffix)
    while not os.path.exists(user_choice) or not user_choice:
        if default_choice: user_choice = input(question % default_choice) or default_choice
        else: user_choice = input(question)

        #if not os.path.exists(os.path.join(user_choice, path_suffix)) and user_choice:
        if not os.path.exists(user_choice) and user_choice:
            user_choice = input('Sorry, the path "%s" does not exist. Please enter an existing path: ' % user_choice)
    return user_choice
    #if os.path.join(user_choice, path_suffix) == user_choice:
    #    return user_choice
    #else:
    #    return os.path.join(user_choice, path_suffix)

def lump_texts(author):

    NT = ['Mark', 'Matthew', 'Luke', 'John', 'Acts', 'Romans', 'I Corinthians', 'II Corinthians', 'Galatians', 'Ephesians', 'Philippians', 'Colossians', 'I Thessalonians', 'II Thessalonians', 'I Timothy', 'II Timothy', 'Titus', 'Philemon', 'Hebrews', 'James', 'I Peter', 'II Peter', 'I John', 'II John', 'III John', 'Jude', 'Revelation']

    if author in NT: author = "NT"
    if "HH" in author: author = "HH"

    return author

class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

    def __iter__(self):
          for each in [('author', ''),('philo_type', '')]:
              yield each

def parse_urn(urn):
    fields = urn.split(":")

    collection = fields[2]

    try:
        group = ':'.join(fields[:4]).split('.')[0]
    except Exception as e:
        group = False

    try:
        group_id = ':'.join(fields[2:4]).split('.')[0]
    except Exception as e:
        group_id = False

    try:
        work = urn
    except Exception as e:
        work = False

    try:
        work_id = ':'.join([fields[2], fields[3].split('.')[1]])
    except Exception as e:
        work_id = False

    return (collection, group, group_id, work, work_id)

# Stat Functions #

def get_lemma_ranks(cursor, cutoff=50):
    # count lemma instances
    eprint("Counting lemma instances...", end="", flush=True)
    rows = cursor.execute('select lemma, count(lemma) from words where pos !="----------" and philo_name like "%lemma%" group by lemma').fetchall()
    eprint("done")

    # reverse sort lemmas by instance count
    eprint("Rank lemmas...", end="", flush=True)
    lemmas_sorted = sorted(rows, key=lambda x: x[1], reverse=True)
    eprint("done")

    # rank the lemmas
    prev_count = 0
    nominal_rank = 1
    rank = 1
    lemmas_ranked = []
    total_count_base = sum(set(j for i, j in lemmas_sorted)) / 10000.0 # (?) Taken from create_frequencies.py in old_scripts/
    for lemma in lemmas_sorted:
        if lemma[0] in forbidden_lemmas: continue
        if lemma[1] < cutoff: continue
        if lemma[1] != prev_count:
            rank = nominal_rank

        lemmas_ranked.append((lemma[0], rank, lemma[1], float(lemma[1]) / total_count_base))

        nominal_rank += 1
        prev_count = lemma[1]

    return lemmas_ranked


def get_collocations(cursor, tomsdb, lemmas_ranked, cutoff=6000, filter_frequency=100):

    # get collocations
    try:
        sys.path.append(os.path.abspath(os.path.dirname(tomsdb)).replace('data', ''))
        from custom_functions import collocation_results
        eprint('[Using Philo4Classics collocation_results()]')
    except Exception as e:
        eprint('[Using default Philologic4 collocation_results()]')
        from philologic.runtime import collocation_results

    from philologic.runtime import WebConfig

    config = WebConfig(os.path.abspath(os.path.dirname(tomsdb)).replace('data', ''))
    collocations = []
    eprint("Getting lemma collocates... ", end="", flush=True)
    for (lemma, rank, count, rate) in lemmas_ranked:
        if rank > cutoff: break 

        request = AttrDict()
        #request.metadata = {'author': 'Aeschylus'}
        request.metadata = {}
        request['report'] = 'collocation'
        request['q'] = 'lemma:' + lemma
        #request['author'] = 'Aeschylus'
        request['author'] = ''
        request['start'] = 0
        request['end'] = 0
        request['colloc_filter_choice'] = 'frequency'
        request['arg'] = 0
        request['sort_order'] = ['rowid']
        request['collocate_distance'] = '' 
        request['filter_frequency'] = filter_frequency
        request['max_time'] = ''
        request['lemmas'] = "no"

        collocation_object = collocation_results(request, config)
        sys.stderr.write("\x1b7\x1b[%dD%s\x1b8" % (1, rank))
        sys.stderr.flush()
        for (k,v) in sorted(collocation_object['collocates'].items(), key=lambda x: x[1]['count'], reverse=True)[0:10]:
            if k in forbidden_lemmas: continue
            if k == lemma: continue
            collocations.append((lemma, k, v['count']))

    sys.stderr.write("\x1b7\x1b[%dD%s\x1b8" % (4, '...finished'))
    eprint("")
    return collocations

def get_lemmas_by_text(cursor, cutoff=5):

    # grab doc level philo_id for all lemmas, grouped by lemma and philo_id
    eprint("Counting lemma instances by doc...", end="", flush=True)
    rows = cursor.execute("select lemma, substr(philo_id, 1, instr(philo_id, ' ')) from words where lemma !='' group by lemma, philo_id;").fetchall()
    lemmas_by_doc = {}
    for row in rows:
        doc = row[1].strip(' ')
        lemma = row[0]
        if lemma in forbidden_lemmas: continue
    
        # count lemma instances per doc
        if doc not in lemmas_by_doc:
            lemmas_by_doc[doc] = {}
        else:
            if lemma not in lemmas_by_doc[doc]:
                lemmas_by_doc[doc][lemma] = 1
            else:
                lemmas_by_doc[doc][lemma] += 1
    lemmas_by_doc_sorted = {}
    for doc in lemmas_by_doc.keys():
        lemmas_by_doc_sorted[doc] = dict(sorted(lemmas_by_doc[doc].items(), key=lambda item: item[1], reverse=True))
        lemmas_by_doc_sorted[doc] = {k:v for k,v in lemmas_by_doc_sorted[doc].items() if v > cutoff}
        #print(lemmas_by_doc_sorted[doc])
    eprint("done")

    # grab total words per doc 
    print("Counting words per doc...", end="", flush=True)
    rows = cursor.execute("select lemma, substr(philo_id, 1, instr(philo_id, ' ')) from words where philo_type='word' and tokenid not null group by philo_id;").fetchall()
    words_per_doc = {}
    for row in rows:
        doc = row[1].strip(' ')
        lemma = row[0]
        if lemma in forbidden_lemmas: continue
        # count word instances per doc 
        if doc not in words_per_doc:
            words_per_doc[doc] = 1
        else:
            words_per_doc[doc] += 1
    eprint("done")

    eprint("Grab title and cts_urn by text...", end="", flush=True)
    rows = cursor.execute('select philo_id, title, cts_urn from toms where philo_id like "% 0 0 0 0 0 0" and title is not null;').fetchall()
    
    lemmas_by_text = []
    for row in rows:
        doc = row[0].split()[0]
        text = row[1]
        cts_urn = row[2]
        for lemma in lemmas_by_doc_sorted[doc]:
            lemmas_by_text.append((lemma, lemmas_by_doc_sorted[doc][lemma], lemmas_by_doc_sorted[doc][lemma]/words_per_doc[doc], doc, text, cts_urn)) 

    eprint("done")
    return lemmas_by_text

def get_lemmas_by_author(cursor, cutoff=5):

    # grab doc level philo_id for all lemmas, grouped by lemma and philo_id
    eprint("Counting lemma instances by doc...", end="", flush=True)
    rows = cursor.execute("select lemma, substr(philo_id, 1, instr(philo_id, ' ')) from words where lemma !='' group by lemma, philo_id;").fetchall()
    lemma_count_by_doc = {}
    for row in rows:
        doc = row[1].strip(' ')
        lemma = row[0]
        if lemma in forbidden_lemmas: continue
    
        # count lemma instances per doc
        if lemma not in lemma_count_by_doc:
            lemma_count_by_doc[lemma] = {doc: 1}
        else:
            if doc not in lemma_count_by_doc[lemma]:
                lemma_count_by_doc[lemma][doc] = 1
            else:
                lemma_count_by_doc[lemma][doc] += 1
    eprint("done")

    #print(lemma_count_by_doc)

    # grab total words per doc 
    print("Counting words per doc...", end="", flush=True)
    rows = cursor.execute("select lemma, substr(philo_id, 1, instr(philo_id, ' ')) from words where philo_type='word' and tokenid not null group by philo_id;").fetchall()
    words_per_doc = {}
    for row in rows:
        doc = row[1].strip(' ')
        lemma = row[0]
        if lemma in forbidden_lemmas: continue
        # count word instances per doc 
        if doc not in words_per_doc:
            words_per_doc[doc] = 1
        else:
            words_per_doc[doc] += 1
    eprint("done")

    #print(words_per_doc)

    # grab doc levels by author
    eprint("Grab docs and words by author...", end="", flush=True)
    rows = cursor.execute('select author, philo_id, title, cts_urn from toms where philo_id like "% 0 0 0 0 0 0" and author is not null or title is not null;').fetchall()
    author_urns = {}
    docs_by_author = {}
    words_per_author = {}
    for row in rows:
        doc = row[1].split()[0]
        author = row[0] if row[0] else row[2]
        author = lump_texts(author)
        (collection, group, group_id, work, work_id) = parse_urn(row[3])
        urn = group

        if urn not in author_urns:
            author_urns[author] = urn

        # list docs per author and count total words per author
        if author not in docs_by_author:
            docs_by_author[author] = [doc]
            words_per_author[author] = words_per_doc[doc]
        else:
            docs_by_author[author].append(doc)
            words_per_author[author] += words_per_doc[doc]

    eprint("done")

    #print(docs_by_author)
    #print(words_by_author)

    # cross-tabulate the above three results to get lemma counts by author
    eprint("Build lemma counts and ratios by author...", end="", flush=True)
    lemmas_by_author = {}
    lemmas_by_author_relative = {}
    for lemma in lemma_count_by_doc:
        for doc, count in lemma_count_by_doc[lemma].items():
            author = [key for key, v in docs_by_author.items() if doc in v][0]
            if lemma not in lemmas_by_author:
                lemmas_by_author[lemma] = {author: count}
                lemmas_by_author_relative[lemma] = {author: count/words_per_author[author]}
            else:
                if author not in lemmas_by_author[lemma]:
                    lemmas_by_author[lemma][author] = count
                    lemmas_by_author_relative[lemma][author] = count/words_per_author[author]
                else:
                    lemmas_by_author[lemma][author] += count
                    lemmas_by_author_relative[lemma][author] = lemmas_by_author[lemma][author]/words_per_author[author]
    eprint("done")
    #print(lemmas_by_author)
    #print(lemmas_by_author_relative)

    # sort lemmas by author
    lemmas = lemmas_by_author.keys()
    #print(lemmas)
    lemmas_by_author_sorted = {i: lemmas_by_author[i] for i in lemmas}
    lemmas_by_author_relative_sorted = {i: lemmas_by_author_relative[i] for i in lemmas}
    #print(lemmas_by_author_relative_sorted)

    # rank the lemmas by author
    lemmas_by_author = []
    for lemma in lemmas_by_author_sorted:
        lemma_counts = lemmas_by_author_sorted[lemma]
        lemma_ratios = lemmas_by_author_relative_sorted[lemma]
        lemma_ratios_sorted = dict(sorted(lemma_ratios.items(), key=lambda item: item[1], reverse=True))
        rank = 1
        for author in lemma_ratios_sorted:
            lemmas_by_author.append((lemma, rank, lemma_ratios_sorted[author], lemma_counts[author], author, author_urns[author]))
            if rank >= cutoff: break
            rank += 1

    return lemmas_by_author

### End of Functions and Classes ###

# Process Paths and Options #

tomsdb = "./toms.db"

while not os.path.exists(tomsdb): 
    try:
        tomsdb = sys.argv[1]
    except:
        tomsdb = user_setpath("Please enter a path to toms.db: ", path_suffix="toms.db")

possible_stats=["all", "collocations", "lemmas", "lemmas_by_text", "lemmas_by_author"]
stats = ""
try:
    for i in range(1, 4):
        if sys.argv[i].lower() in possible_stats:
            stats = sys.argv[i]
            break
    if not stats:
        eprint("Unknown stat!")
        stats = user_inputchoices("Which stats would you like to get [%s]? ", "all", possible_stats)
except:
    stats = user_inputchoices("Which stats would you like to get [%s]? ", "all", possible_stats)

possible_out=["db", "sqlite", "file", "text"]
out = ""
try:
    for i in range(1, 4):
        if sys.argv[i].lower() in possible_out:
            out = sys.argv[i]
            break
except:
    out = user_inputchoices("Output [%s]? ", "sqlite", possible_out)

eprint("-->Path: %s" % tomsdb)
eprint("-->Stats: %s" % stats)

if out in ["db", "sqlite"]:
    infodb = user_setpath("Please enter a path to the Info sqlite [%s]: ", default_choice=infodb)
    eprint("-->Output: %s (%s)" % (out, infodb))
else:
    eprint("-->Output: %s" % out)

conn = sqlite3.connect(tomsdb)
cursor = conn.cursor()

if stats == "lemmas" or stats == "all":
    # Ranked Lemmas
    lemmas_ranked = get_lemma_ranks(cursor, 50)

    if out in ["file"]:
        eprint("[Writing]     lemma ranks to [%s]..." % lemmas_file, end="", flush=True)
        f = open(lemmas_file, "w")
        for (lemma, rank, count, rate) in lemmas_ranked:
            #print("%s\t%s\t%d\t%.3f" % (lemma, rank, count, rate), file=f)
            print("%s\t%s\t%d\t%.3f\t%s" % (lemma, rank, count, rate, lemma.rstrip(string.digits)), file=f)
            sys.stderr.write("\x1b7\x1b[%dD%s\x1b8" % (1, rank))
            sys.stderr.flush()
        sys.stderr.write("\x1b7\x1b[%dD%s\x1b8" % (3, '...finished'))
        f.close()

    elif out in ["db", "sqlite"]:
        eprint("[Deleting]     frequencies in [%s]..." % infodb, end="", flush=True)
        infoconn = sqlite3.connect(infodb)
        infocursor = infoconn.cursor()
        infocursor.execute('delete from frequencies')
        eprint("finished")
        eprint("[Writing]     lemma ranks to [%s]..." % infodb, end="", flush=True)
        for (lemma, rank, count, rate) in lemmas_ranked:
            infocursor.execute('insert into frequencies values (?,?,?,?,?)', (lemma, rank, count, str(round(rate, 3)), lemma.rstrip(string.digits)))
            sys.stderr.write("\x1b7\x1b[%dD%s\x1b8" % (1, rank))
        sys.stderr.write("\x1b7\x1b[%dD%s\x1b8" % (3, '...finished'))
        eprint("finished")
        eprint("[Rebuilding]  f_l index...", end="", flush=True)
        infocursor.execute('drop index if exists f_l')
        infocursor.execute('CREATE INDEX f_l on frequencies(lookupform)')
        eprint("finished")
        infoconn.commit()
        infoconn.close()
        
    elif out in ["text"]:
        for (lemma, rank, count, rate) in lemmas_ranked:
            print("%s\t%s\t%d\t%.3f\t%s" % (lemma, rank, count, rate, lemma.rstrip(string.digits)))
    eprint("")

if stats == "lemmas_by_text" or stats == "all":
    # lemmas by text
    lemmas_by_text = get_lemmas_by_text(cursor, 0)

    if out in ["file"]:
        eprint("[Writing]     lemma counts by text to [%s]..." % lemmas_by_text_file, end="", flush=True)
        f = open(lemmas_by_text_file, "w")
        for (lemma, count, rate, doc, text, urn) in lemmas_by_text:
            print("%s\t%d\t%.7f\t%s\t%s\t%s" % (lemma, count, rate, doc, text, urn), file=f)
            sys.stderr.write("\x1b7\x1b[%dD%s\x1b8" % (1, doc))
            sys.stderr.flush()
        sys.stderr.write("\x1b7\x1b[%dD%s\x1b8" % (3, '...finished'))
        f.close()

    elif out in ["db", "sqlite"]:
        infoconn = sqlite3.connect(infodb)
        infocursor = infoconn.cursor()

        # check if cts_urn field exists
        try:
            infocursor = infoconn.execute('select * from textFreqs')
        except sqlite3.OperationalError as e:
            message = e.args[0]
            if message.startswith("no such table"):
                infocursor.execute('CREATE TABLE textFreqs(lemma text, count integer, ratio float, philo_id text, title text, cts_urn text)')
                infoconn.commit()
            else:
                raise

        names = [description[0] for description in infocursor.description]
        if "cts_urn" in names:
            eprint("[Deleting]     textFreqs in [%s]..." % infodb, end="", flush=True)
            infocursor.execute('delete from textFreqs')
            print("finished")
        else:
            eprint("[Dropping]     textFreqs in [%s]..." % infodb, end="", flush=True)
            infocursor.execute('drop table textFreqs')
            eprint("finished")
            eprint("[Creating]     textFreqs in [%s]..." % infodb, end="", flush=True)
            infocursor.execute('CREATE TABLE textFreqs(lemma text, count integer, ratio float, philo_id text, title text, cts_urn text)')
            eprint("finished")

        eprint("[Writing]     lemma counts by text to [%s]..." % infodb, end="", flush=True)
        for (lemma, count, rate, doc, text, urn) in lemmas_by_text:
            infocursor.execute('insert into textFreqs values (?,?,?,?,?,?)', (lemma, count, str(round(rate, 7)), doc, text, urn))
            sys.stderr.write("\x1b7\x1b[%dD%s\x1b8" % (1, doc))
        sys.stderr.write("\x1b7\x1b[%dD%s\x1b8" % (3, '...finished'))
        eprint("finished")
        eprint("[Rebuilding]  dF_l index...", end="", flush=True)
        infocursor.execute('drop index if exists dF_l')
        infocursor.execute('CREATE INDEX dF_l on textFreqs(philo_id)')
        eprint("finished")
        infoconn.commit()
        infoconn.close()

    elif out in ["text"]:
        for (lemma, count, percentage, doc, text, urn) in lemmas_by_text:
            print("%s\t%d\t%f\t%s\t%s\t%s" % (lemma, count, percentage, doc, text, urn))
    eprint("")

if stats == "lemmas_by_author" or stats == "all":
    # Lemmas by Author
    lemmas_by_author = get_lemmas_by_author(cursor, 5)

    if out in ["file"]:
        eprint("[Writing]     lemma ranks by author to [%s]..." % lemmas_by_author_file, end="", flush=True)
        f = open(lemmas_by_author_file, "w")
        for (lemma, rank, percentage, count, author, urn) in lemmas_by_author:
            print("%s\t%d\t%s\t%f\t%s\t%d" % (lemma, rank, author, percentage, urn, count), file=f)
        f.close()
        eprint("finished")

    elif out in ["db", "sqlite"]:
        infoconn = sqlite3.connect(infodb)
        infocursor = infoconn.cursor()

        # check if cts_urn field exists
        infocursor = infoconn.execute('select * from authorFreqs')
        names = [description[0] for description in infocursor.description]
        if "cts_urn" in names:
            eprint("[Deleting]     authorFreqs in [%s]..." % infodb, end="", flush=True)
            infocursor.execute('delete from authorFreqs')
            print("finished")
        else:
            eprint("[Dropping]     authorFreqs in [%s]..." % infodb, end="", flush=True)
            infocursor.execute('drop table authorFreqs')
            eprint("finished")
            eprint("[Creating]     authorFreqs in [%s]..." % infodb, end="", flush=True)
            infocursor.execute('CREATE TABLE authorFreqs(lemma text, rank integer, author text, freq float, cts_urn text)')
            eprint("finished")

        eprint("[Writing]     lemma ranks by author to [%s]..." % infodb, end="", flush=True)
        for (lemma, rank, percentage, count, author, urn) in lemmas_by_author:
            infocursor.execute('insert into authorFreqs values (?,?,?,?,?)', (lemma, rank, author, f'{percentage:.10f}', urn))
        eprint("finished")
        eprint("[Rebuilding   aF_l index...", end="", flush=True)
        infocursor.execute('drop index if exists aF_l')
        infocursor.execute('CREATE INDEX aF_l on authorFreqs(lemma)')
        eprint("finished")
        infoconn.commit()
        infoconn.close()

    elif out in ["text"]:
        for (lemma, rank, percentage, count, author, urn) in lemmas_by_author:
            print("%s\t%d\t%s\t%f\t%s\t%d" % (lemma, rank, author, percentage, urn, count))
    eprint("")

if stats == "collocations" or stats == "all":
    # Collocations
    lemmas_ranked = get_lemma_ranks(cursor, 50)
    collocations = get_collocations(cursor, tomsdb, lemmas_ranked, 6000, 100)
    
    if out in ["file"]:
        eprint("[Writing]     lemma collocates to [%s]... " % lemma_collocates_file, end="", flush=True)
        f = open(lemma_collocates_file, "w")
        for (lemma, collocate, count) in collocations:
            print("%s\t%s\t%d\t%s" % (lemma, collocate, count, lemma.rstrip(string.digits)), file=f)
        f.close()
        eprint("finished")

    elif out in ["db", "sqlite"]:
        eprint("[Deleting]     collocations in [%s]..." % infodb, end="", flush=True)
        infoconn = sqlite3.connect(infodb)
        infocursor = infoconn.cursor()
        infocursor.execute('delete from collocations')
        print("finished")
        eprint("[Writing]     collocations to [%s]..." % infodb, end="", flush=True)
        for (lemma, collocate, count) in collocations:
            infocursor.execute('insert into collocations values (?,?,?,?)', (lemma, collocate, count, lemma.rstrip(string.digits)))
        eprint("finished")
        eprint("[Rebuilding]  c_l index...", end="", flush=True)
        infocursor.execute('drop index if exists c_l')
        infocursor.execute('CREATE INDEX c_l on collocations(lookupform)')
        eprint("finished")
        infoconn.commit()
        infoconn.close()

    elif out in ["text"]:
        for (lemma, collocate, count) in collocations:
            print("%s\t%s\t%d\t%s" % (lemma, collocate, count, lemma.rstrip(string.digits)))
    eprint("")

