import sys
import os
import shutil
import difflib
import unicodedata
import sqlite3
import gzip
from philologic.loadtime.OHCOVector import Record

def greek_normalized_word_frequencies(loader_obj):
    print('Generating normalized word frequencies...')
    frequencies = loader_obj.destination + '/frequencies'
    output = open(frequencies + "/normalized_word_frequencies", "w")
    for line in open(frequencies + '/word_frequencies'):
        word, count = line.split("\t")
        #norm_word = word.decode('utf-8')
        norm_word = word
        norm_word = [i for i in unicodedata.normalize("NFKD",norm_word) if not unicodedata.combining(i)]
        #norm_word = ''.join(norm_word).encode('utf-8')
        norm_word = ''.join(norm_word)
        print(norm_word + "\t" + word, file=output)
    output.close()

def concat_milestones(loader,text):
    tmp_file = open(text["sortedtoms"] + ".tmp","w")
    
    current_n = {}
    abbrev = ""
    for line in open(text["sortedtoms"]):
        type, name, id, attrib = line.split('\t')
        id = id.split()
        record = Record(type,name,id)
        record.attrib = eval(attrib)

        #if type == "doc":
        if "abbrev" in record.attrib:
            abbrev = record.attrib["abbrev"] + " "
        #        #print("FOUND ABBREV %s" % abbrev, file=sys.stderr)

        if type == "div1":
            if "n" in record.attrib:
                current_n["div1"] = record.attrib["n"]
                #record.attrib["head"] = abbrev + record.attrib["n"]
                # special handling for dictionaries like Lewis & Short, where homonyms
                # have separate entries with an 'n' attrib
                if "id" in record.attrib:
                    if record.attrib["n"] not in record.attrib["id"]:
                        record.attrib["head"] = record.attrib["n"]
                else:
                    record.attrib["head"] = record.attrib["n"]
                print(record.attrib["head"], file=sys.stderr)
            if "div2" in current_n: del current_n["div2"]
            if "div3" in current_n: del current_n["div3"]
        elif type == "div2":
            if "n" in record.attrib:
                if "div1" in current_n.keys() and current_n["div1"] not in abbrev:
                    current_n["div2"] = current_n["div1"] + "." + record.attrib["n"]
                    #record.attrib["head"] = abbrev + current_n["div2"]
                    record.attrib["head"] = current_n["div2"]
                else:
                    record.attrib["head"] = record.attrib["n"]
            if "div3" in current_n: del current_n["div3"]
        elif type == "div3":
            if "n" in record.attrib:
                if "div2" in current_n.keys():
                    current_n["div3"] = current_n["div2"] + "." + record.attrib["n"]
                    #record.attrib["head"] = abbrev + current_n["div3"]
                    record.attrib["head"] = current_n["div3"]
                else:
                    record.attrib["head"] = record.attrib["n"]
        print(record, file=tmp_file)
    tmp_file.close()
    os.remove(text["sortedtoms"])
    os.rename(text["sortedtoms"] + ".tmp", text["sortedtoms"])

def fix_card_milestones(loader, text):
    last_card = None
    temp_file = open(text['sortedtoms'] + '.tmp',"w")
    for line in open(text['sortedtoms']):    
        type, word, id, attrib = line.split('\t')
        id = id.split()
        record = Record(type, word, id)
        record.attrib = eval(attrib) 
        if "type" in record.attrib and record.attrib["type"] == "card":
            if last_card:
                last_card.attrib["head"] = last_card.attrib["head"] + " - " + record.attrib["head"]
#                print >> sys.stderr, last_card
                print(last_card, file=temp_file)
            last_card = record
        else:
            print(record, file=temp_file)
    if last_card:
        last_card.attrib["head"] = last_card.attrib["head"] + " - (end)"
        print(last_card, file=temp_file)

    temp_file.close()
    tomscommand = "sort %s > %s" % (text["sortedtoms"]+".tmp",text["sortedtoms"])
    os.system(tomscommand)
    os.remove(text["sortedtoms"]+".tmp")

def index_word_attributes(*fields):
    def inner_index_word_attributes(loader,text):
        tmp_file = open(text["raw"] + ".tmp","w")
        for line in open(text["raw"]):
            rec_type, word, id, attrib = line.split('\t')
            id = id.split()
            if rec_type == "word":
#                word = word.decode("utf-8").lower().encode("utf-8")
                record = Record(rec_type, word, id)
                record.attrib = eval(attrib)
                for field in fields:                
                    if field in record.attrib:
                        val = field + ":" + record.attrib[field]                            
                        aux_record = Record(rec_type,val,id)
                        aux_record.attrib = eval(attrib)
                        aux_record.attrib["real_token"] = word
                        if " " in val:
                            pass
#                            print >> sys.stderr, "ERROR: space in token: ", val
                        else:    
                            print(aux_record, file=tmp_file)

                print(record, file=tmp_file)
            else:
                record = Record(rec_type, word, id)
                record.attrib = eval(attrib)
                print(record, file=tmp_file)
        os.remove(text["raw"])
        os.rename(text["raw"] + ".tmp",text["raw"])        
    return inner_index_word_attributes

def index_word_attributes_post(*fields):
    def inner_index_word_attributes_post(loader):
        print >> sys.stderr, "cleaning up words for db"
        words = loader.destination + "/WORK/all_words_ordered"
        out_fn = loader.destination + "/WORK/all_words_ordered.tmp"
        outfile = open(out_fn,"w")
        for line in open(words,"r"):
            rec_type, word, id, attrib = line.split('\t')
            remove = False
            for field in fields:
                if word.startswith(field + ":"):
                    remove = True
            if remove:
#                print >> sys.stderr, "removing :" + line[:-1]
                pass
            else:
                print(line[:-1], file=outfile)
        outfile.close()
        os.remove(words)
        os.rename(out_fn,words)
    return inner_index_word_attributes_post

def perseus_id_morph_tokens(lex):
    def inner_perseus_id_morph_tokens(loader,text):

        dbn = lex
        raw_file = text["raw"]
        tmp_filename = text["raw"] + ".tmp"
        tmp_file = open(tmp_filename,"w")

        base_filename = os.path.basename(raw_file).replace(".raw","")
        
        #Parser tokens
        raw_lines = open(raw_file).readlines()
        
        dbh = sqlite3.connect(dbn)
        dbc = dbh.cursor()

        #Loop through splits and match token id in DB        
        line_num = 0
        total_lines = len(raw_lines)
        for token_line in raw_lines:

            line_num += 1
            sys.stdout.write("\rProgress: %d/%d (%.2f%%)\t" % (line_num, total_lines, (line_num / float(total_lines)) * 100) )
            sys.stdout.flush()
            
            kind, name, id, attrib = token_line.split("\t")
            if kind == "word":
                id = id.split()
                r = Record(kind,name,id)
                r.attrib = eval(attrib)
                r.attrib["filename"] = text["name"]
                if "id" in r.attrib:
                    tokenid = r.attrib["id"]
                else:
                    # assume it's English and insert with dummy attributes
                    r.attrib["lemma"] = ""
                    r.attrib["pos"] = "----------"
                    r.attrib["tokenid"] = 10000000 + line_num
                    print(r, file=tmp_file)
                    continue
                dbc.execute("SELECT tokens.content,tokens.tokenid,parses.lex,parses.prob,Lexicon.lemma,Lexicon.code from tokens,parses,Lexicon where tokens.tokenid=? and tokens.tokenid=parses.tokenid and parses.lex=Lexicon.lexid order by parses.prob desc;",(tokenid,))
                row = dbc.fetchone()
                if (row == None):                    
                    dbc.execute("SELECT authority,code,lemma from parses where tokenid=? order by prob desc;",(tokenid,))
                    row = dbc.fetchone()
                    if row != None:
                        r.attrib["lemma"] = row[2]
                        r.attrib["pos"] = row[1]
                        r.attrib["tokenid"] = tokenid
                        if row[2] == "<unknown>": r.attrib["pos"] = "----------"
#                       best_parse = dbc.fetchone()
                        print(r, file=tmp_file)
                    else:
                        print("%s: Not Found in tokens or parses: %s" % (base_filename.split("/")[-1], ' '.join(token_line.split("\t"))), file=sys.stderr)

                        sys.stdout.flush()
                else:
#                matched += 1
                    r.attrib["lemma"] = row[4]
                    r.attrib["pos"] = row[5]
                    r.attrib["tokenid"] = tokenid
                    print(r, file=tmp_file)
            else:
                kind, name, id, attrib = token_line.split("\t")
                id = id.split()
                r = Record(kind,name,id)
                r.attrib = eval(attrib)
                print(r, file=tmp_file)

        os.remove(text['raw'])
        os.rename(tmp_filename, text['raw'])
    return inner_perseus_id_morph_tokens
    
def perseus_align_morph_tokens(lex):
    def inner_perseus_align_morph_tokens(loader,text):
        dbn = lex
        raw_file = text["raw"]
        tmp_filename = text["raw"] + ".tmp"
        tmp_file = open(tmp_filename,"w")
        #dbn = sys.argv[1]
        #raw_file = sys.argv[2]

        base_filename = os.path.basename(raw_file).replace(".raw","")
        
        #Parser tokens
        raw_lines = open(raw_file).readlines()
        
        parser_tokens = []
        orig_parser_tokens = []
        parser_splits = []
        for line in raw_lines:
            kind, content, id, attrib = line.split("\t")
            if kind == "word":
                word = content.decode("utf-8")
#                if word and word[0] == u"\u02bd": # trim superfluous leading apostrophe/breathing
#                    word = word[1:]
#                if word and word[0] == u"\u02bc":
#                    word = word[1:]
#                if word and word[-1] == u"\u03c3": # substitute terminal sigma for regular sigma at the end.
#                    word = word[:-1] + u"\u03c2"
#                if word and word[-1] == u"\u02bc":
#                    word = word[:-1]
                if word and word[-1] == u" ":
                    word = word[:-1]
                word = word + "\n"
                norm_word = "".join(c.encode("utf-8") for c in unicodedata.normalize("NFKD",word) if not unicodedata.combining(c))
                if norm_word[-2:] == " \n":
        #           print repr(norm_word)
                    norm_word = norm_word[:-2] + "\n"  
                parser_tokens.append(norm_word)
                orig_parser_tokens.append(content)
            else:
                parser_tokens.append("<"+content+">")
                orig_parser_tokens.append("<"+content+">")
            parser_splits.append((kind,content,id,attrib))
        #        print repr(norm_word)
        
        #DB tokens
        
        dbh = sqlite3.connect(dbn)
        dbc = dbh.cursor()
        dbc.execute("SELECT content,tokenid FROM tokens WHERE file=? AND type='word' ORDER BY seq;",(base_filename,))
        
        db_tokens = []
        orig_db_tokens = []
        db_tokenids = []
        token_count = 0
        while True:
            row = dbc.fetchone()
            if row == None:
                if token_count == 0:
                    print("No tokens found for %s." % base_filename, file=sys.stderr)
                    return
                break
            else:
                token_count += 1
#                word = row[0].lower().replace(u"\u02bc",u"\u1fbd").strip() + "\n"
                word = row[0].strip() + "\n"
                norm_word = "".join(c.encode("utf-8") for c in unicodedata.normalize("NFKD",word) if not unicodedata.combining(c))
                if norm_word[-2:] == " \n":
        #           print repr(norm_word)
                    norm_word = norm_word[:-2] + "\n"        
                db_tokens.append(norm_word)
                db_tokenids.append(row[1])
                orig_db_tokens.append(row[0])
        
#        junker = lambda x: x == "(tag)\n"
        junker = lambda x: False

        differ = difflib.SequenceMatcher(junker,parser_tokens, [x.decode('utf-8').lower().encode('utf-8') for x in db_tokens])
        
        matched = 0.0
        total = 0.0
        
        opcodes = differ.get_opcodes()
                        
        for code, i1, i2, j1, j2 in opcodes:
            total = i2 + 1.0
            if code == "equal":
        #        print >> sys.stderr, code, i1, i2, j1, j2
        #        print >> sys.stderr, code, i1, i2, j1, j2
                for i,j in zip(range(i1,i2),range(j1,j2)):     
                    kind, name, id, attrib = parser_splits[i]
                    id = id.split()
                    r = Record(kind,name,id)
                    r.attrib = eval(attrib)
                    r.attrib["filename"] = text["name"]
                    tokenid = db_tokenids[j]
                    dbc.execute("SELECT tokens.content,tokens.tokenid,parses.lex,parses.prob,Lexicon.lemma,Lexicon.code from tokens,parses,Lexicon where tokens.tokenid=? and tokens.tokenid=parses.tokenid and parses.lex=Lexicon.lexid order by parses.prob desc;",(tokenid,))
                    row = dbc.fetchone()
                    if (row == None):                    
                        dbc.execute("SELECT authority,code,lemma from parses where tokenid=? order by prob desc;",(tokenid,))
                        best_parse = dbc.fetchone()
                        print("Lexicon lookup error on: %s, %s, %s" % (name,tokenid, best_parse), file=sys.stderr)
                        print(r, file=tmp_file)
                        continue
        #            print row[0].encode('utf-8'),row[1],row[2],row[3],row[4].encode("utf-8"),row[5].encode("utf-8")
                    else:
                        matched += 1
                        r.attrib["lemma"] = row[4]
                        r.attrib["pos"] = row[5]
                        r.attrib["tokenid"] = tokenid
                        print(r, file=tmp_file)
            else:
                if code == "replace":
#                    print >> sys.stderr, code, i1, i2, j1, j2
                    print("%s: '%s', db: '%s' [%s]" % (text["name"], " ".join(t for t in orig_parser_tokens[i1:i2]), "".join(t for t in orig_db_tokens[j1:j2]).encode("utf-8"), ",".join(str(i) for i in db_tokenids[j1:j2])), file=sys.stderr)
                    pass
                for i in range(i1,i2): #i1:i2 will contain no elements if this is an insert.
                    kind, name, id, attrib = parser_splits[i]
                    id = id.split()
                    r = Record(kind,name,id)
                    r.attrib = eval(attrib)
                    print(r, file=tmp_file)
                        
        print("%s: matched %d / %d tokens for %f aligned" % (base_filename, matched, token_count, matched / token_count), file=sys.stderr)
        os.remove(text['raw'])
        os.rename(tmp_filename, text['raw'])
    return inner_perseus_align_morph_tokens
    
if __name__ == "__main__":
    aligner = perseus_align_morph_tokens(sys.argv[2])
    loader = {}
    parsed_text = sys.argv[1]
    text = {"raw":parsed_text,"name":parsed_text}
    shutil.copy2(text["raw"],text["raw"] + ".backup")
    aligner(loader,text)
    os.remove(text["raw"])
    os.rename(text["raw"] + ".backup",text["raw"])
    
