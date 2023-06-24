#!/usr/bin/python3

import sys
import re
import os
from subprocess import call
from shutil import copyfile
import glob
import philologic
from philologic.runtime.DB import DB
import filecmp

from Classics_load_config import lexicon_db
from Classics_load_config import abbrevs_file
from Classics_load_config import Greek_load
from Classics_load_config import Latin_load
from Classics_load_config import translation_load

# Important Settings #

philologic_path="/var/www/html/philologic4/" # the script will prompt you to verify this path

# Usually Blank Settings #

lexicon_path="" # If you want to use a lexicon path different from lexicon_db in Classics_load_config.py, then use this, otherwise leave blank. If both this and lexicon_db are blank, then the script will assume that "lexicon.db" can be found in extras/ and will copy it over to the load

# Rarely Touched Settings #

files2own = [] # only add files that give you permission problems. If you don't know, don't touch this 
files2group = ["app/index.html", "app/shared/searchForm/metadataFields.html", "app/shared/searchForm/searchTerms.html", "app/shared/searchForm/searchForm.html"] # known files that need to be grouped for the fix script 

#############################################################
### There should be no need to modify anything below here ### 
#############################################################

cwd = os.getcwd().split("/")[-1]
if (cwd != "load"):
    print("Please cd to 'load' directory!")
    sys.exit()

### Functions ###

def user_inputchoices(question, default_choice, all_choices):
    print("\nChoices: %s" % ', '.join(all_choices))
    user_choice = ""
    while user_choice not in all_choices:
        user_choice = input(question % default_choice) or default_choice
        if user_choice not in all_choices: print("Sorry, unknown. Select from listed choices.")
    return user_choice

def user_setpath(question, default_choice="", path_prefix=""):
    user_choice = ""
    while not os.path.exists(os.path.join(path_prefix, user_choice)) or not user_choice:
        if default_choice: user_choice = input(question % default_choice) or default_choice
        else: user_choice = input(question)

        if not os.path.exists(os.path.join(path_prefix, user_choice)) and user_choice == default_choice:
            user_choice = input("The path specified in fix_load.py (%s) does not exist, please specify an existing path and then fix it in the script: " % default_choice)
        elif not os.path.exists(os.path.join(path_prefix, user_choice)) and user_choice != default_choice:
            user_choice = input('Sorry, the path "%s" does not exist. Please enter an existing path: ' % os.path.join(path_prefix, user_choice))
    return user_choice

class visual_progress():
    def __init__(self, marker):
        self.marker = marker
        self.warning_marker = '*!*'
        self.fixes = 0
        self.errors = 0
        self.warnings = 0
    def progress(self, num=1):
        self.fixes += num
        print(self.marker, end="", flush=True)
    def warning(self, num=1):
        self.warnings += num
        print(self.warning_marker, end="", flush=True)
    def problem(self, num=1):
        self.errors += num
    def total(self):
        return(self.fixes)
    def total_err(self):
        return(self.errors)
    def total_warn(self):
        return(self.warnings)

show = visual_progress('...')

def own_file(file_path):
    call('cp ' + file_path + ' ~/my_temp_file', shell=True)
    call('rm -f ' + file_path, shell=True)
    call('mv ~/my_temp_file ' + file_path, shell=True)
    return

def open_for_mod(file_path, rw):
    try:
        f = open(file_path, rw)
    except FileNotFoundError:
        print(file_path + " does not exist.")
        sys.exit()
    except PermissionError:
        print ("...owning!", end="")
        own_file(file_path)
        f = open(file_path, rw)
    global current_file
    current_file = file_path
    return f

def close_for_mod(file_path, new_text):
    try:
        f = open(file_path, 'w')
    except FileNotFoundError:
        print(file_path + " does not exist.")
        sys.exit()
    except PermissionError:
        print ("...owning!", end="")
        own_file(file_path)
        f = open(file_path, 'w')
    f.write(new_text)
    f.close()

def regexmatch(pattern, text, userflags, critical=True):
    f = ""
    f = re.search(pattern, text, flags=userflags)
    try:
        testf = f.group()
    except AttributeError:
        if critical:
            print("\n\t\t***Critical Regex Error!***")
            print("\t\tPattern not found: %s" % pattern)
            print("\t\tin: %s" % current_file)
            show.problem()
            return None
        else:
            show.warning()
            return None
    return f

def smartcopy(orig, dest, force=False):
    orig_file = orig.split('/')[-1]
    need_copy = False
    if force: need_copy = True
    else:
        if not os.path.exists(dest):
            need_copy = True
        else:
            if not filecmp.cmp(orig, dest, shallow=False):
                print ("\nNewer version of %s available." % orig_file)
                overwrite_choice = user_inputchoices("Overwrite? [%s]", "yes", ["yes", "no"])
                if "y" in overwrite_choice: need_copy = True
                print("")
            else:
                print("...%s is latest." % orig_file)
    if need_copy:
        print("...%s" % orig_file)
        copyfile(orig, dest)
        
### End of Functions ###

# verify philologic path
if not philologic_path:
    print ('"philologic_path" is blank!')
philologic_path = user_setpath("Please hit enter or specify a different path for PhiloLogic [%s]: ", philologic_path)

(myload, type_of_fix) = ("", "")

try:
    myload = sys.argv[1]
    type_of_fix = sys.argv[2]
except:
    if len(sys.argv) == 2:
        type_of_fix = user_inputchoices("Specify type of load? [%s]: ", "text", ["text", "dictionary", "no", "cts"])
    elif len(sys.argv) == 1:
        myload = user_setpath("Please enter the name of an existing load: ", path_prefix=philologic_path)
myload_path = os.path.join(philologic_path, myload)

# check that load actually exists
if not os.path.exists(myload_path):
    print('\nLoad "%s" does not exist!' % myload)
    print("Existing loads: %s" % ', '.join(os.listdir(philologic_path)))
    myload = user_setpath("Please enter the name of an existing load: ", path_prefix=philologic_path)
    myload_path = os.path.join(philologic_path, myload)

####################################################################
# only install cts api This is located early in the script because
#little else needs to be done in order to install just the cts api
####################################################################
if (type_of_fix == "cts"):
    init_path = "%s/custom_functions/__init__.py" % (myload_path)

    print  ("Installing CTS API", end = "")
    smartcopy("../cts/cts_tools.py", myload_path + "/custom_functions/cts_tools.py")
    show.progress()
    smartcopy("../cts/cts_api.py", myload_path + "/custom_functions/cts_api.py")
    show.progress()
    smartcopy("../cts/cts.cfg", myload_path + "/data/cts.cfg")
    show.progress()
    smartcopy("../cts/cts.py", myload_path + "/cts.py")
    call("chmod go+x " + myload_path + "/cts.py", shell=True)
    show.progress()
    print(" (done)")

    # read in and fix nit 
    init = open_for_mod(init_path, 'r').read()
    print ("__init__.py", end="")

    #insert cts_api init
    f = re.search(r'cts_api', init, flags=re.S)
    try:
        f = f.group()
    except:
        init += "from .cts_api import cts_results\n"
        show.progress()
    #insert cts_tools init
    f = re.search(r'cts_tools', init, flags=re.S)
    try:
        f = f.group()
    except:
        init += "from .cts_tools import *\n"
        show.progress()

    close_for_mod(init_path, init)
    print(" (done)")

    print('\nFixing load "%s" FINISHED with %d fixes applied and %s regexmatch error(s).\n' %(myload, show.total(), show.total_err()))
    sys.exit()
####################################################################

# grab a list of all abbrevs files
abbrevs_files = glob.glob("../custom_functions/*abbrevs")

#print ("Abbreviation File Choices: ", end = "")
abbrevs_choices = [re.sub(r"^.*\/", "", i) for i in abbrevs_files]
if "Lat" in myload: abbrevs_file = "Latin.abbrevs"
if len(abbrevs_choices) > 1:
    abbrevs_file = user_inputchoices("Which abbrevs file do you want to use? [%s] ",  abbrevs_file, abbrevs_choices)

#specify an alternate lexicon.db path
if not lexicon_path and lexicon_db:
    lexicon_path = user_setpath("\nPlease hit enter or specify a different lexicon path [%s] ", lexicon_db)

# type of fix
if type_of_fix != "" and type_of_fix not in ['dictionary', 'text', 'no', 'cts']:
    print("Unknown type of fix.")
    sys.exit()

# if dictionary but missing reference load
if type_of_fix == "dictionary" and not Greek_load and not Latin_load:
    user_choice = user_inputchoices("You are loading a dictionary, but have not specified a reference load (Greek and/or Latin) in the config file. Continue? [%s] ", 'no', ['yes', 'no'])
    if user_choice.lower().startswith('n'):
        sys.exit()

# Add missing final slashes
if Greek_load and not Greek_load.endswith('/'): Greek_load += "/"
if Latin_load and not Latin_load.endswith('/'): Latin_load += "/"
if translation_load and not translation_load.endswith('/'): translation_load += "/"

#################################################
###          Paths of Files to Edit           ###
#################################################

web_config_path = "%s/data/web_config.cfg" % (myload_path)
db_locals_path = "%s/data/db.locals.py" % (myload_path)
philoLogic_js_path = "%s/app/assets/js/philoLogic.js" % (myload_path)
philoLogic_css_path = "%s/app/assets/css/philoLogic.css" % (myload_path)
index_html_path = "%s/app/index.html" % (myload_path)
searchForm_html_path = "%s/app/shared/searchForm/searchForm.html" % (myload_path)
searchArguments_html_path = "%s/app/shared/searchArguments/searchArguments.html" % (myload_path)
kwic_html_path = "%s/app/components/concordanceKwic/kwic.html" % (myload_path)
concordance_html_path = "%s/app/components/concordanceKwic/concordance.html" % (myload_path)
navigationBar_html_path = "%s/app/components/textNavigation/navigationBar.html" % (myload_path)
textObject_html_path = "%s/app/components/textNavigation/textObject.html" % (myload_path)
init_path = "%s/custom_functions/__init__.py" % (myload_path)
customRuntime_path = "%s/custom_functions/customRuntime.py" % (myload_path)
get_sorted_kwic_path = "%s/scripts/get_sorted_kwic.py" % (myload_path)
get_word_frequency_path = "%s/scripts/get_word_frequency.py" % (myload_path)
get_landing_page_content_path = "%s/scripts/get_landing_page_content.py" % (myload_path)
autocomplete_metadata_path = "%s/scripts/autocomplete_metadata.py" % (myload_path)
word_property_filter_path = "%s/reports/word_property_filter.py" % (myload_path)

# Core Runtime Files Copied and Lightly Adjusted

get_text_path = "%s/custom_functions/get_text.py" % (myload_path)
ObjectFormatter_path = "%s/custom_functions/ObjectFormatter.py" % (myload_path)

#################################################
###    Files to Preemptively Own and Group    ###
#################################################

for f in files2own:
    print("Owning: %s!" % (f))
    own_file(myload_path + "/" + f)

for f in files2group:
    print("Grouping: %s!" % (f))
    call("chmod g+w " + myload_path + "/" + f, shell=True)

#################################################
###     make tokenid in words table INT       ###
#################################################

#print("Is tokenid integer? ", end="")
#db = DB(myload_path + '/data/')
#cursor = db.dbh.cursor()
#query = "select * from sqlite_master where type='table';"
#cursor.execute(query)
#tokenid_int_exists = False
#for row in cursor.fetchall():
#    if "tokenid INT" in row["name"]:
#        tokenid_int_exists = True
#        print("yes!")
#        break
#
#if not tokenid_int_exists:
#    print("no!")
#    print("Redoing words_tokenid as INT in toms.db...", end="", flush=True)
#    #query = "alter table words add column tokenid2 INT;"
#    #cursor.execute(query)
#    query = "update words set 'tokenid' = cast(tokenid as INT);"
#    cursor.execute(query)
#    print("done!")

#################################################
###     index tokenid in words table          ###
#################################################

print("tokenid index exists? ", end="")
db = DB(myload_path + '/data/')
cursor = db.dbh.cursor()
query = "select * from sqlite_master where type='index';"
cursor.execute(query)
tokenid_index_exists = False
for row in cursor.fetchall():
    if "tokenid" in row["name"]:
        tokenid_index_exists = True
        print("yes!")
        break

if not tokenid_index_exists:
    print("no!")
    print("Building words_tokenid_index in toms.db...", end="", flush=True)
    query = "create index words_tokenid_index on words (tokenid);"
    cursor.execute(query)
    print("done!")

#################################################
###      Copy over Custom Functions           ###
#################################################

#need_copy = False
#for fname in os.listdir("../custom_functions"):
#    if fname.endswith('py') or fname.endswith('abbrevs'):
#        if not os.path.exists(myload_path + "/custom_functions/" + fname):
#            need_copy = True
#
#if need_copy:
#    print("Copying Custom Functions")
print("Copying Custom Functions")
smartcopy("../cts/cts_tools.py", myload_path + "/custom_functions/cts_tools.py")
for fname in os.listdir("../custom_functions"):
#  if not os.path.exists(myload_path + "/custom_functions/" + fname) and (fname.endswith('py') or fname.endswith('abbrevs')):
#        print("..." + fname)
#        copyfile("../custom_functions/" + fname, myload_path + "/custom_functions/" + fname)
    if fname.endswith('py') or fname.endswith('abbrevs'):
        smartcopy("../custom_functions/" + fname, myload_path + "/custom_functions/" + fname)


#################################################
###      Copy over Runtime P4 Files           ###
###        for Custum Adjustments             ###
#################################################
# Why not just ship these with the package?     #
# Because we only need to make minor adjustments#
# and while future versions of P4 may make      # 
# significant updates to these files, we should #
# still be able to make surgical edits with     #
# crafty enough regex                           #
#################################################

runtime2copy = ['get_text.py', 'ObjectFormatter.py']

p4path = '/'.join(philologic.__file__.split('/')[0:-1]) + "/runtime/"
print("...*PhiloLogic path: %s" % p4path)

for fname in runtime2copy:
    if not os.path.exists(myload_path + "/custom_functions/" + fname):
            print("+..." + fname)
            copyfile(p4path + fname, myload_path + "/custom_functions/" + fname)

#################################################
###          Copy over Custom Fonts           ###
#################################################

need_copy = False
for fname in os.listdir("../fonts"):
    if fname.endswith('ttf') or fname.endswith('woff'):
        if not os.path.exists(myload_path + "/app/assets/fonts/" + fname):
            need_copy = True

if need_copy:
    print("Copying Custom Fonts")

for fname in os.listdir("../fonts"):
    if not os.path.exists(myload_path + "/app/assets/fonts/" + fname):
        print("..." + fname)
        copyfile("../fonts/" + fname, myload_path + "/app/assets/fonts/" + fname)

#################################################
###          Copy over Custom Images          ###
#################################################

need_copy = False
for fname in os.listdir("../images"):
    if fname.endswith('png') or fname.endswith('jpg'):
        if not os.path.exists(myload_path + "/app/assets/img/" + fname):
            need_copy = True

if need_copy:
    print("Copying Custom images")

for fname in os.listdir("../images"):
    if not os.path.exists(myload_path + "/app/assets/img/" + fname):
        print("..." + fname)
        copyfile("../images/" + fname, myload_path + "/app/assets/img/" + fname)

#################################################
###          Copy over Custom extras/         ###
#################################################
# lexicon dance
if not lexicon_path:
    if not os.path.exists(myload_path + "/data/lexicon.db"):
        if os.path.exists("../extras/lexicon.db"):
            print("Copying Lexicon")
            print("...lexicon.db")
            copyfile("../extras/lexicon.db", myload_path + "/data/lexicon.db")
        else:
            print("Exception! lexicon.db not found in extras/\n..lookup_word.py will not work. Please copy the lexicon to %s/data/lexicon.db" % (myload_path))
else:
    if not os.path.exists(myload_path + "/data/lexicon.db"):
        if os.path.exists(lexicon_path):
            print("Soft-linking " + lexicon_path)
            os.symlink(lexicon_path, myload_path + "/data/lexicon.db")
        else:
            print("Exception! Lexicon full path invalid.\n..lookup_word.py will not work. Please symlink the lexicon to %s/data/lexicon.db" % (myload_path))

print("Copying extras/")
smartcopy("../extras/lookup_word.py", myload_path + "/scripts/lookup_word.py", force=True)
smartcopy("../extras/wordObjectDetail.html", myload_path + "/app/shared/wordObjectDetail/wordObjectDetail.html", force=True)
smartcopy("../extras/get_more_context.py", myload_path + "/scripts/get_more_context.py", force=True)
smartcopy("../extras/searchLemma.html", myload_path + "/app/shared/searchForm/searchLemma.html")

#################################################
#################################################
#################################################
init = open_for_mod(init_path, 'r').read()

print ("Building __init__", end="")

# insert toc init
f = re.search(r'generate_toc_object', init, flags=re.S)
try:
    f = f.group()
except:
    init += "from .table_of_contents import generate_toc_object\n"
    show.progress()

# insert navigation init
f = re.search(r'navigation', init, flags=re.S)
try:
    f = f.group()
except:
    init += "from .navigation import generate_text_object\n"
    show.progress()

#insert kwic init
f = re.search(r'kwic_results', init, flags=re.S)
try:
    f = f.group()
except:
    init += "from .kwic import kwic_results\n"
    show.progress()
    init += "from .kwic import kwic_hit_object\n"
    show.progress()

#insert concordance init
f = re.search(r'concordance_results', init, flags=re.S)
try:
    f = f.group()
except:
    init += "from .concordance import concordance_results\n"
    show.progress()

#insert bibliography init
f = re.search(r'bibliography_results', init, flags=re.S)
try:
    f = f.group()
except:
    init += "from .bibliography import bibliography_results\n"
    show.progress()

#insert collocation init
f = re.search(r'collocation_results', init, flags=re.S)
try:
    f = f.group()
except:
    init += "from .collocation import collocation_results\n"
    show.progress()

#insert get_concordance_text init
f = re.search(r'get_concordance_text', init, flags=re.S)
try:
    f = f.group()
except:
    init += "from .get_text import get_concordance_text\n"
    show.progress()

#insert group_by_range init
f = re.search(r'group_by_range', init, flags=re.S)
try:
    f = f.group()
except:
    init += "from .landing_page import group_by_range\n"
    show.progress()

#insert generate_word_frequency init
f = re.search(r'generate_word_frequency', init, flags=re.S)
try:
    f = f.group()
except:
    init += "from .generate_word_frequency import generate_word_frequency\n"
    show.progress()

#insert filter_word_by_property init
f = re.search(r'filter_word_by_property', init, flags=re.S)
try:
    f = f.group()
except:
    init += "from .filter_word_by_property import filter_words_by_property\n"
    show.progress()

#insert cts_tools init
f = re.search(r'cts_tools', init, flags=re.S)
try:
    f = f.group()
except:
    init += "from .cts_tools import *\n"
    show.progress()

#insert isEnglish  init
f = re.search(r'isEnglish', init, flags=re.S)
try:
    f = f.group()
except:
    init += "from .customRuntime import isEnglish\n"
    show.progress()

#insert isGreek  init
f = re.search(r'isGreek', init, flags=re.S)
try:
    f = f.group()
except:
    init += "from .customRuntime import isGreek\n"
    show.progress()

#insert ObjectFormatter init
f = re.search(r'format_concordance', init, flags=re.S)
try:
    f = f.group()
except:
    init += "from .ObjectFormatter import adjust_bytes, format_concordance, format_text_object\n"
    init += "from .ObjectFormatter import format_strip\n"
    show.progress()

close_for_mod(init_path, init)
print(" (done)")

#################################################
###          Modify Abbrevs File Choice       ###
#################################################

# read in and fix customRuntime.py
customRuntime = open_for_mod(customRuntime_path, 'r').read()
print ("customRuntime", end="")

customRuntime = re.sub(r'( *)abbrevs_file = "(.*?)"', r'\1abbrevs_file = "%s"' % abbrevs_file, customRuntime, flags=re.S)
show.progress()

close_for_mod(customRuntime_path, customRuntime)
print(" (done)")

#################################################
###               First File                  ###
###               web_config.cfg              ###
#################################################

# read in and fix web_config.cfg 
web_config = open_for_mod(web_config_path, 'r').read()

print ("web_config.cfg", end="")

# General fixes for all types of loads
# get dictionary_lookup working
web_config = web_config.replace("dictionary_lookup = \'\'", "dictionary_lookup = \'https://logeion.uchicago.edu/'")
show.progress()

# Get rid of all uses of small-caps
web_config = web_config.replace("small-caps", "")
show.progress()

# Toggle on button showing of header in TOC
web_config = web_config.replace("header_in_toc = False", "header_in_toc = True")
show.progress()

# Add lemma, token and pos word facets
web_config = web_config.replace("words_facets = []", 'words_facets = [{"lemma":"lemma"}, {"token":"token"}, {"pos":"pos"}]')
show.progress()

# kill time_series
web_config = re.sub(r"( *)(#*)('time_series')", r"#\1\3", web_config, flags=re.S)
show.progress()

# limit metadata fields
f = regexmatch(r'metadata = \[.*?\]', web_config, re.S)
if (f):
    f = f.group()
    new_f = ""
    if '#' not in f:
        # comment out
        new_f = re.sub(r'^', r"#", f, flags=re.M)
        show.progress()
        if type_of_fix != "dictionary":
            new_f += "\nmetadata = [ \
\n        'author', \
\n        'title', \
\n        'text_genre', \
\n        'language', \
\n        'who', \
\n        'cts_urn' \
\n]"
        else:
           new_f = "\nmetadata = []" 
        #swap in new conf
        web_config = re.sub(re.escape(f), new_f, web_config, flags=re.S)

f = regexmatch(r'metadata_input_style = \{.*?\}', web_config, re.S)
if (f):
    f = f.group()
    new_f = ""
    if '#' not in f:
        # comment out
        new_f = re.sub(r"'philo_div3_id': 'text'", r"'philo_div3_id': 'text',\n\t# fix_load was here\n\t'language': 'text'", f, flags=re.S)
        show.progress()
        #swap in new conf
        web_config = re.sub(re.escape(f), new_f, web_config, flags=re.S)

# limit facets
f = regexmatch(r'facets = \[.*?\]', web_config, re.S)
if (f) and type_of_fix != "dictionary":
    f = f.group()
    new_f = ""
    if '#' not in f:
        # comment out
        new_f = re.sub(r'^', r"#", f, flags=re.M)
        show.progress()
        new_f += "\nfacets = [ \
\n        'author', \
\n        'title', \
\n        'text_genre', \
\n        'who' \
\n]"
        #swap in new conf
        web_config = re.sub(re.escape(f), new_f, web_config, flags=re.S)

# fix search example to conform with metadata limits
if type_of_fix != "dictionary":
    f = regexmatch(r'[^ ]search_examples = \{.*?\'(urn:.*?)\'.*?\}', web_config, re.S)
    if(f):
        xmlbase = f.group(1)
        f = f.group()
        new_f = ""
        if '#' not in f:
            # comment out
            new_f = re.sub(r'^', r"#", f, flags=re.M)
            show.progress()
            new_f += "\nsearch_examples = { \
\n        'author': 'Xenophon', \
\n        'title': 'Anabasis', \
\n        'text_genre': 'prose', \
\n        'language': 'Greek', \
\n        'who': '\"Ὀδυσσεύς\"', \
\n        'cts_urn': '\"" + xmlbase + "\"'\
\n}"
            #swap in new conf
            web_config = re.sub(re.escape(f), new_f, web_config, flags=re.S)

# specify metadata aliases
if type_of_fix != "dictionary":
    web_config = web_config.replace("metadata_aliases = {}","metadata_aliases = {'who': 'Speaker', 'text_genre': 'Genre', 'author': 'Author', 'title': 'Title', 'head': 'cts_passage'}")
else:
    web_config = web_config.replace("metadata_aliases = {}","metadata_aliases = {'who': 'Speaker', 'text_genre': 'Genre', 'author': 'Author', 'title': 'Title', 'head': 'Head'}")
show.progress()

# fixes for dictionaries
if (type_of_fix == "dictionary"):

    # add reference dbnames
    f = regexmatch(r'(dbname.*?)\s?#', web_config, re.S)
    if (f):
        f = f.group(1)
        new_f = ""
        if '_dbname' not in f:
            # add reference dbs
            new_f = f + 'Greek_dbname = "%s"\nLatin_dbname = "%s"\n' % (Greek_load, Latin_load)
            show.progress()
            #swap in new conf
            web_config = re.sub(re.escape(f), new_f, web_config, flags=re.S)

    #fix settings
    web_config = web_config.replace("dictionary = False", "dictionary = True")
    show.progress()

    web_config = web_config.replace("dictionary_bibliography = False", "dictionary_bibliography = True")
    show.progress()

    web_config = web_config.replace("landing_page_browsing = \'default\'", "landing_page_browsing = \'dictionary\'")
    show.progress()

    # limit dico_letter_range 
    f = regexmatch(r'dico_letter_range = \[.*?\]', web_config, re.S)
    if (f):
        f = f.group()
        new_f = ""
        if '#' not in f:
            # comment out
            new_f = re.sub(r'^', r"#", f, flags=re.M)
            show.progress()
            new_f += "\ndico_letter_range = []"
            web_config = re.sub(re.escape(f), new_f, web_config, flags=re.S)
    #web_config = re.sub(r'dico_letter_range *= *\[.+?\]', 'dico_letter_range = []', web_config, flags=re.S) 
    show.progress()

    # limit facets
    f = regexmatch(r'facets = \[.*?\]', web_config, re.S)
    if (f):
        f = f.group()
        new_f = ""
        if '#' not in f:
            # comment out
            new_f = re.sub(r'^', r"#", f, flags=re.M)
            show.progress()
            new_f += "\nfacets = ['head']"
            web_config = re.sub(re.escape(f), new_f, web_config, flags=re.S)
    #web_config = re.sub(r'[^_#]facets = \[.*?\'head\',.*?\]', "\nfacets = [\'head\']", web_config, flags=re.S)
    show.progress()

# fixes for everything else
if (type_of_fix == "text"):
    try:
        # Change author and title ranges to A-Z
        conf = re.search(r'Author.*?\'queries\': \[.*?(\'A-D\',.*?\'S-Z\').*?\]', web_config, flags=re.S)
        new_conf = re.sub(conf.group(1), '\'A-Z\'', conf.group(), flags=re.S)
        # swap in the new string
        web_config = re.sub(re.escape(conf.group()), new_conf, web_config, flags=re.S)
        show.progress()

        conf = re.search(r'Title.*?\'queries\': \[.*?(\'A-D\',.*?\'S-Z\').*?\]', web_config, flags=re.S)
        new_conf = re.sub(conf.group(1), '\'A-Z\'', conf.group(), flags=re.S)
        # swap in the new string
        web_config = re.sub(re.escape(conf.group()), new_conf, web_config, flags=re.S)
        show.progress()
    except:
        show.progress()

    # Add a translation dbname
    f = regexmatch(r'(dbname.*?)\s?#', web_config, re.S)
    if (f):
        f = f.group(1)
        new_f = ""
        if '_dbname' not in f:
            # add db
            new_f = f + 'translation_dbname = "%s"' % (translation_load)
            show.progress()
            #swap in new conf
            web_config = re.sub(re.escape(f), new_f, web_config, flags=re.S)

    # don't display title in kwic bib 
    f = re.search(r'kwic_bibliography_fields = \[.*?\]', web_config, flags=re.S)
    f = f.group()
    # comment out
    new_f = ""
    if '#' not in f:
        new_f = re.sub(r'\'title\'', r"#'title'", f, flags=re.S)
        show.progress()
        #swap in new conf 
        web_config = re.sub(re.escape(f), new_f, web_config, flags=re.S)

    #reduce number of consecutive spaces in conc display
    web_config = re.sub(r'\&nbsp;\&nbsp;', '&nbsp;', web_config, flags=re.S) 
    web_config = re.sub(r'\&nbsp;\&nbsp;', '&nbsp;', web_config, flags=re.S) 
    web_config = re.sub(r'\&nbsp;', '', web_config, flags=re.S) 
    show.progress()

    #replace > with . for separators
    web_config = re.sub(r'\&gt;', '.', web_config, flags=re.S) 

    #replace , with '' for separators
    web_config = re.sub(r'\',\'', '\'\'', web_config, flags=re.S) 

    # remove "page" in conc bib
    web_config = re.sub(r'\[ page', '[', web_config, flags=re.S) 
    show.progress()

    # don't display title in concordance citation (but leave it in for bibliography)
    f = regexmatch(r'(concordance_citation = \[.*?\},)(.*?{.*?\'field\': \'title\'.*?\},)', web_config, re.S)
    # comment out
    if (f):
        if '#' not in f.group(2):
            new_f = f.group(1) + re.sub(r'\n', r'\n#', f.group(2), flags=re.S)
            web_config = re.sub(re.escape(f.group()), new_f, web_config, flags=re.S)
            show.progress()

    # don't display year in concordance citation (but leave it in for bibliography)
    #f = re.search(r'(concordance_citation = \[.*?\},.*?)(\s*?{\s*?\'field\': \'year\'.*?\},)', web_config, flags=re.S)
    f = regexmatch(r'(concordance_citation = \[.*?\},.*?)([\s#]*?{[\s#]*?\'field\': \'year\'.*?\},)', web_config, re.S)
    # comment out
    if (f):
        if '#' not in f.group(2):
            new_f = f.group(1) + re.sub(r'\n', r'\n#', f.group(2), flags=re.S)
            web_config = re.sub(re.escape(f.group()), new_f, web_config, flags=re.S)
            show.progress()

    # add newline sepeparator after title
    f = regexmatch(r'(navigation_citation = \[.*?\},)(.*?{.*?\'field\': \'title\'.*?\},)', web_config, re.S)
    if (f):
        if '#' not in f.group(2):
            new_f = f.group(1) + re.sub(r"'separator': ''", r"'separator': '<br>'", f.group(2), flags=re.S)
            web_config = re.sub(re.escape(f.group()), new_f, web_config, flags=re.S)
            show.progress()

    # add prefix for collection
    f = regexmatch(r'(navigation_citation = \[.*?\},.*?)({\s*?\'field\': \'collection\'.*?\}\s*?\})', web_config, re.S)
    if (f):
        if '#' not in f.group(2):
            group2 = re.sub(r"'prefix': ''", r"'prefix': '['", f.group(2), flags=re.S)
            group2 = re.sub(r"'suffix': ''", r"'suffix': ']'", group2, flags=re.S)
            #print(group2)
            new_f = f.group(1) + group2
            web_config = re.sub(re.escape(f.group()), new_f, web_config, flags=re.S)
            show.progress()

    # don't display year in navigation citation
    # comment out
    f = regexmatch(r'(navigation_citation = \[.*?\},.*?)(\n[\s#]*{[\s#]*?\'field\': \'year\'.*?\},)', web_config, re.S)
    if (f):
        if '#' not in f.group(2):
            #print(re.sub(r'\n', r'\n#', f.group(2), flags=re.S))
            new_f = f.group(1) + re.sub(r'\n', r'\n#', f.group(2), flags=re.S)
            web_config = re.sub(re.escape(f.group()), new_f, web_config, flags=re.S)
            show.progress()

    # don't display pub_place in navigation citation
    # comment out
    f = regexmatch(r'(navigation_citation = \[.*?\},.*?)(\n[\s#]*{[\s#]*?\'field\': \'pub_place\'.*?\},)', web_config, re.S)
    if (f):
        if '#' not in f.group(2):
            #print(re.sub(r'\n', r'\n#', f.group(2), flags=re.S))
            new_f = f.group(1) + re.sub(r'\n', r'\n#', f.group(2), flags=re.S)
            web_config = re.sub(re.escape(f.group()), new_f, web_config, flags=re.S)
            show.progress()

close_for_mod(web_config_path, web_config)
print(" (done)")

#################################################
###                New File                   ###
###                philoLogic.js              ###
#################################################

# read in and fix philoLogic.js
philoLogic_js = open_for_mod(philoLogic_js_path, 'r').read()

print("philoLogic.js", end="")

# General fixes for all types of loads

# fix for dictionary lookup using 'd'
# grab the function
#f = re.search(r'function dictionaryLookup.*?}\)\(\);', philoLogic_js, flags=re.S)
f = regexmatch(r'function dictionaryLookup.*?}\)\(\);', philoLogic_js, re.S)
if (f):
    f = f.group()
    # find the lines to comment out
    new_f = ""
    if '/*' not in f:
        new_f = re.sub(r'( *var century.*?})', r'/*\n\1\n*/', f, flags=re.S)
        # change another line
        new_f = re.sub(r'var link.*?selection', 'var link = philoConfig.dictionary_lookup + selection', new_f)
        show.progress()

        # add δ stuff
        new_f = re.sub(r'if \(event.key === \"d\"\)', 'if (event.key === \"d\" || event.key === \"δ\")', new_f)
        show.progress()

        # swap in the new function
        philoLogic_js = re.sub(re.escape(f), new_f, philoLogic_js, flags=re.S)

# remove quotes around collocation hits
f = regexmatch(r'vm.resolveCollocateLink.*?}', philoLogic_js, re.S)
if (f):
    f = f.group()
    new_f = ""
    if 'fix_load' not in f:
        new_f = re.sub(r'( *)(var q \= localParams\.q \+ )(\' \"\' \+ word \+ \'\"\';)', r"\1//fix_load was here\n\1//\2\3\n\1if (localParams.lemmas == 'yes' || localParams.q.includes('lemma:')){ word = 'lemma:' + word; }\n\1\2 ' ' + word + '';", f, flags=re.S)
        show.progress()
        philoLogic_js = re.sub(re.escape(f), new_f, philoLogic_js, flags=re.S)

# fix directives for new way of clicking on words to look them up
#f = re.search(r'\.directive\(\'loading.*?animateOnLoad\)', philoLogic_js, flags=re.S)
f = regexmatch(r'\.directive\(\'loading.*?animateOnLoad\)', philoLogic_js, re.S)
if (f):
    f = f.group()
    new_f = ""
    if '//' not in f:
        new_f = re.sub(r"( *)(\.directive\('selectWord', selectWord\))", r"//\1\2\n\1.directive('xmlW', selectWord)", f, flags=re.S)
        show.progress()
        directive_content = ".directive('compile', ['$compile', function ($compile) { \
\n                return function(scope, element, attrs) { \
\n                scope.$watch( \
\n                function(scope) { \
\n                // watch the 'compile' expression for changes \
\n                return scope.$eval(attrs.compile); \
\n                }, \
\n                function(value) { \
\n                // when the 'compile' expression changes \
\n                // assign it into the current DOM \
\n                element.html(value); \
\n \
\n                // compile the new DOM and link it to the current \
\n                // scope. \
\n                // NOTE: we only compile .childNodes so that \
\n                // we don't get into infinite loop compiling ourselves \
\n                $compile(element.contents())(scope); \
\n                } \
\n                ); \
\n                }; \
\n                }])"
        new_f = re.sub(r"( *)(\.directive\('animateOnLoad', animateOnLoad\))", r"\1\2\n\1" + directive_content, new_f, flags=re.S)
        show.progress()
        philoLogic_js = re.sub(re.escape(f), new_f, philoLogic_js, flags=re.S)

f = re.search(r'[\*\/]* *function selectWord.*?}\;.*?}', philoLogic_js, flags=re.S)
f = f.group()
new_f = ""
if '/*' not in f:
    function_content = "function selectWord($location, request, $rootScope, $window) {\
\n    return {\
\n        restrict: 'C',\
\n        link: function (scope, element, attrs) {\
\n            element.bind('click', function () {\
\n                scope.$apply(function () {\
\n                    var query = $location.search();\
\n                    var text = element.text();\
\n                    if ($rootScope.report === 'concordance' || $rootScope.report === 'word_property_filter') {\
\n                    var parent = angular.element('#results_container');\
\n                    var position = parseInt(attrs.position) - 1;\
\n                    var resultPromise = request.script(query, {\
\n                        script: 'lookup_word.py',\
\n                        selected: text,\
\n                        philo_id: parent.attr('philo-id'),\
\n                        id: element.attr('id'),\
\n                        position: position\
\n                    });\
\n                    } else if ($rootScope.report === 'kwic') {\
\n                    var parent = angular.element('#results_container');\
\n                    var position = parseInt(attrs.position) - 1;\
\n                    var resultPromise = request.script(query, {\
\n                        script: 'lookup_word.py',\
\n                        selected: text,\
\n                        philo_id: parent.attr('philo-id'),\
\n                        id: element.attr('id'),\
\n                        position: position\
\n                    });\
\n                    } else if ($rootScope.report === \"textNavigation\") {\
\n                    var parent = angular.element('#text-obj-content');\
\n                    var resultPromise = request.script(query, {\
\n                        script: 'lookup_word.py',\
\n                        selected: text,\
\n                        philo_id: parent.attr('philo-id'),\
\n                        id: element.attr('id'),\
\n                        report: \"navigation\"\
\n                    });\
\n                    }\
\n                    resultPromise.then(function (response) {\
\n                        if (!$.isEmptyObject(response.data)) {\
\n                            $rootScope.wordProperties = response.data;\
\n                            angular.element('#wordProperty').modal('show');\
\n                        }\
\n                    });\
\n                });\
\n            });\
\n        }\
\n    };\
\n}"
    new_f = re.sub(r"^(.*)$", r"/*\1*/\n" + function_content, f, flags=re.S)
    show.progress()
    philoLogic_js = re.sub(re.escape(f), new_f, philoLogic_js, flags=re.S)


#f = re.search(r'[\/]* *function concordance.*?}[^\;] *?}', philoLogic_js, flags=re.S)
f = regexmatch(r'[\/]* *function concordance.*?}[^\;] *?}', philoLogic_js, re.S)
if (f):
    f = f.group()
    new_f = ""
    if '//' not in f:
        new_f = re.sub(r"( *)(function concordance.*?\) \{)", r"//\1\2\n\1function concordance($rootScope, $http, $compile, request) {", f, flags=re.S)
        show.progress()
        new_f = re.sub(r"( *)(moreContextElement.html\(response.data\).promise\(\).done\(function\(\) \{)", r"//\1\2\n\1moreContextElement.html($compile(response.data)(scope)).promise().done(function() {", new_f, flags=re.S)
        show.progress()
        philoLogic_js = re.sub(re.escape(f), new_f, philoLogic_js, flags=re.S)

#f = re.search(r' *function textObject.*?}\)\;.*?}\)\;.*?}', philoLogic_js, flags=re.S)
f = regexmatch(r' *function textObject.*?}\)\;.*?}\)\;.*?}', philoLogic_js, re.S)
if (f):
    f = f.group()
    new_f = ""
    if 'fix_load' not in f:
        function_content = "\
\n                    // #fix_load was here#\
\n                    if ((!scope.textObject.metadata_fields.head || !/[0-9a-z]+\./i.test(scope.textObject.metadata_fields.head)) && scope.textObject.metadata_fields.n) {\
\n                        scope.textObject.metadata_fields.whereami = scope.textObject.metadata_fields.n;\
\n                    } else if (!scope.textObject.metadata_fields.head && scope.textObject.metadata_fields.abbrev) {\
\n                       scope.textObject.metadata_fields.whereami = scope.textObject.metadata_fields.abbrev;\
\n                    } else {\
\n                        scope.textObject.metadata_fields.whereami = scope.textObject.metadata_fields.head;\
\n                    }\
\n                    // #fix_load was here#\
\n"
        new_f = re.sub(r"textNavigationValues.navBar = true;", r"textNavigationValues.navBar = true;\n" + function_content, f, flags=re.S)
        show.progress()
        philoLogic_js = re.sub(re.escape(f), new_f, philoLogic_js, flags=re.S)

f = regexmatch(r"(\s+)(.directive\('collocationOptions'.*?\)).*?\)", philoLogic_js, re.S)
if (f):
    if "fix_load" not in f.group(0):
        new_f = "%s%s//fix_load was here%s%s" % (f.group(2), f.group(1), f.group(1), ".directive('searchLemma', searchLemma)")  
        f = f.group(2)
        show.progress()
        philoLogic_js = re.sub(re.escape(f), new_f, philoLogic_js, flags=re.S)

f = regexmatch(r"(\s+)(function searchMethods\(\) \{.*?}\s+\}).*?}", philoLogic_js, re.S)
if (f):
    if "fix_load" not in f.group():
        content = "\
\n\n    // fix_load was here\
\n    function searchLemma() {\
\n        return {\
\n            templateUrl: 'app/shared/searchForm/searchLemma.html',\
\n            replace: true\
\n        }\
\n    }"
        new_f = "%s%s" % (f.group(2), content)
        f = f.group(2)
        show.progress()
        philoLogic_js = re.sub(re.escape(f), new_f, philoLogic_js, flags=re.S)

f = regexmatch(r"(\s+)(function searchArguments\(.*?\) \{.*?}\s+\}.*?\}.*?\}.*?\}.*?\}.*?\}.*?\}.*?\}.*?\})", philoLogic_js, re.S)
if (f):
    if "fix_load" not in f.group():
        f = f.group(2)
        # insert "lemma:" string when metadata "lemmas" is "yes"
        content='if (queryParams.lemmas == "yes" && !queryParams.q.includes("lemma") && queryParams.q) { queryParams.q = "lemma:" + queryParams.q; }'

        new_f = re.sub(r"( +)(if \(queryParams.q.split\(' '\).length > 1\) \{)", r"\1//fix_load was here\n\1" + content + r"\n\1\2", f, flags=re.S)
        show.progress()

        # manage CTS URN queries
        content = '\
\n                if (queryParams.q.includes("urn:")) {\
\n                        var regex = /^(.+?:.+?:.+?:.+?):(.*$)/;\
\n                        var urn = regex.exec(queryParams.q);\
\n                        console.log(urn);\
\n                        if (urn != null) {\
\n                                if (urn[2] != "") {\
\n                                        queryParams.cts_urn=\'"\' + urn[1] + \'"\';\
\n                                        queryParams.head=\'"\' + urn[2] + \'"\';\
\n                                        delete queryParams.q;\
\n                                } else {\
\n                                        queryParams.cts_urn=\'"\' + urn[1] + \'"\';\
\n                                        delete queryParams.q;\
\n                                        delete queryParams.head;\
\n                                }\
\n                        } else {\
\n                                queryParams.cts_urn=\'"\' + queryParams.q + \'"\';\
\n                                delete queryParams.q;\
\n                                delete queryParams.head;\
\n                        }\
\n                      $location.url(URL.objectToUrlString(queryParams));\
\n                      $rootScope.formData = queryParams;\
\n                }else if (queryParams.q.includes("cite:")) {\
\n                        var regex = /^cite:(.+?):(.*?)$/;\
\n                        var citation = regex.exec(queryParams.q);\
\n                        if (citation != null) {\
\n                                if (citation[2] != "") {\
\n                                        queryParams.abbrev=\'"\' + citation[1] + \'"\';\
\n                                        queryParams.head=\'"\' + citation[2] + \'"\';\
\n                                        delete queryParams.q;\
\n                                } else {\
\n                                        queryParams.abbrev=\'"\' + citation[1] + \'"\';\
\n                                        delete queryParams.q;\
\n                                        delete queryParams.head;\
\n                                }\
\n                        } else {\
\n                                queryParams.abbrev=\'"\' + queryParams.q.replace("cite:","") + \'"\';\
\n                                delete queryParams.q;\
\n                                delete queryParams.head;\
\n                        }\
\n                      $location.url(URL.objectToUrlString(queryParams));\
\n                      $rootScope.formData = queryParams;\
\n                }\
'

        new_f = re.sub(r"( +)(if \(queryParams.q.split\(' '\).length > 1\) \{(.*?\}){9})", r"\1\2\n\1//fix_load was here\1" + content + r"\n", new_f, flags=re.S)
        show.progress()

        philoLogic_js = re.sub(re.escape(f), new_f, philoLogic_js, flags=re.S)

# add a buildWordCriteria function for displaying word criteria
f = regexmatch(r'(\S*var buildCriteria.*?return.*?\})(.*?\})', philoLogic_js, re.S)
if (f):
    new_f = ""
    if 'fix_load' not in f.group(2):
        f = f.group(1)
        function_content = '\
\n        // fix_load was here\
\n        var buildWordCriteria = function(queryParams) {\
\n            var queryArgs = angular.copy(queryParams);\
\n            var wordCriteria = []\
\n            var word_property = "";\
\n            var word_property_value = "";\
\n            for (var k in queryArgs) {\
\n                if (k === "word_property") { word_property = queryArgs[k]; }\
\n                if (k === "word_property_value") { word_property_value = queryArgs[k]; }\
\n            }\
\n            if (queryArgs["report"] === "word_property_filter" && word_property) {\
\n                wordCriteria.push({ key: word_property, alias: word_property, value: word_property_value });\
\n            }\
\n            return wordCriteria\
\n        }\
\n        // fix_load was here\
'
        new_f = f + function_content
        show.progress()
        philoLogic_js = re.sub(re.escape(f), new_f, philoLogic_js, flags=re.S)

f = regexmatch(r'(\s*)(queryArgs.biblio.*?;)(.*?;)', philoLogic_js, re.S)
if (f):
    new_f = ""
    if 'fix_load' not in f.group(3):
        content = f.group(1) + "//fix_load was here" + f.group(1) + "queryArgs.wordCriteria = buildWordCriteria(queryParams);"
        new_f = f.group(1) + f.group(2) + content
        f = f.group(1) + f.group(2)
        show.progress()
        philoLogic_js = re.sub(re.escape(f), new_f, philoLogic_js, flags=re.S)

# Allow word criteria to be clicked away
f = regexmatch(r'(\s*var removeMetadata.*?\})\s*return', philoLogic_js, re.S)
if (f):
    new_f = ""
    if 'fix_load' not in f.group(1):
        f = f.group()
        function_content = '\
\n            // fix_load was here\
\n	    if (metadata === "token" || metadata === "lemma" || metadata === "pos") {\
\n		    delete queryParams["word_property"];\
\n		    delete queryParams["word_property_value"];\
\n		    queryParams.report = "concordance";\
\n	    }\
\n            // fix_load was here\
'
        new_f = re.sub(r"(\s*)(delete queryParams\[metadata\];)", function_content + r"\1\2", f, flags=re.S)
        show.progress()
        new_f = re.sub(r'( *)(if \(queryParams.*?"bibliography")(.*?\{)', r'// \1\2\3\n\1\2' + ' || queryParams.report === "word_property_filter"' + r'\3', new_f, flags=re.S)
        show.progress()
        philoLogic_js = re.sub(re.escape(f), new_f, philoLogic_js, flags=re.S)

f = regexmatch(r"(^\s+.*)(biblioFields.push\('head'\);)", philoLogic_js, re.M)
if (f):
    if "/" not in f.group(1):
        f = f.group()
        new_f = re.sub(r"(^\s+.*)(biblioFields.push\('head'\);)", r'\1//\2 // fix_load was here', f, flags=re.M)
        show.progress()
        philoLogic_js = re.sub(re.escape(f), new_f, philoLogic_js, flags=re.S)


close_for_mod(philoLogic_js_path, philoLogic_js)
print(" (done)")

#################################################
###                New File                   ###
###                philoLogic.css             ###
#################################################

# read in and fix philoLogic.css
philoLogic_css = open_for_mod(philoLogic_css_path, 'r').read()
print("philoLogic.css", end="")

#grab #footer to add things right below it at the beginning of the file
if 'Libertine' not in philoLogic_css:
    f = re.search(r'#footer \{.*?\}', philoLogic_css, flags=re.S)
    f = f.group()
    new_f = f
    content = "\n\n@font-face {\
    \n    font-family: \'LinLibertinePhilo41';\
    \n    src:url(\'../fonts/LinLibertinePhilo41.woff\') format(\'woff\'),\
    \n        url(\'../fonts/LinLibertinePhilo41.woff2\') format(\'woff2\'),\
    \n        url(\'../fonts/LinLibertinePhilo41.svg#LinLibertinePhilo41\') format(\'svg\'),\
    \n        url(\'../fonts/LinLibertinePhilo41.eot\'),\
    \n        url(\'../fonts/LinLibertinePhilo41.eot?#iefix\') format(\'embedded-opentype\'),\
    \n        url(\'../fonts/LinLibertinePhilo41.ttf\') format(\'truetype\');\
    \n\
    \n    font-weight: normal;\
    \n    font-style: normal;\
    \n    font-display: swap;\
    \n}"
    new_f += content
    show.progress()
    philoLogic_css = re.sub(re.escape(f), new_f, philoLogic_css, flags=re.S)

# add a noshow class to suppress header content
f = regexmatch(r'(span\.note.*?}).*?}', philoLogic_css, re.S)
if (f):
    if 'noshow' not in f.group():
        f = f.group(1)
        new_f = f + '\n\n.noshow {\n    font-size: 0em;\n}'
        show.progress()
        philoLogic_css = re.sub(re.escape(f), new_f, philoLogic_css, flags=re.S)

#grab b.headword css
f = re.search(r'b\.headword \{.*?\}', philoLogic_css, flags=re.S)
f = f.group()
# comment out
if '/*' not in f:
    new_f = re.sub(r' *(font.*;)', r'/*\n\1\n*/', f, flags=re.S)
    show.progress()
    # add new headword css
    content = "\n\nb.headword::after {\
\n    content: \"\\\A\" attr(orth_orig);\
\n    white-space: pre;\
\n}"
    new_f += content
    show.progress()
    #swap in new css
    philoLogic_css = re.sub(re.escape(f), new_f, philoLogic_css, flags=re.S)

# grab .code-block
f = re.search(r'\.code-block \{.*?\}', philoLogic_css, flags=re.S)
f = f.group()
if 'Libertine' not in f:
    new_f = re.sub(r'( *)font-family.*?;', r"\1font-family: 'LinLibertinePhilo41', sans-serif;", f, flags=re.S)
    show.progress()
    philoLogic_css = re.sub(re.escape(f), new_f, philoLogic_css, flags=re.S)

# grab xml-milestone::before, this is for prose line numbers
f = re.search(r'xml-milestone.*?::before \{.*?\}', philoLogic_css, flags=re.S)
f = f.group()
if 'bold' not in f:
    new_f = re.sub(r'( *)xml-milestone::before', r'\1xml-milestone:not([unit="Reitzpage"])::before', f, flags=re.S)
    show.progress()
    new_f = re.sub(r'( *)content.*?;', r'\1content: attr(n);\n\1white-space: pre;', new_f, flags=re.S)
    show.progress()
    new_f = re.sub(r'( *)color.*?;', r'\1color: #000000;\n\1font-weight: bold;', new_f, flags=re.S)
    show.progress()
    new_f = re.sub(r'( *)font-size.*?;', r'\1font-size: 0.8em;', new_f, flags=re.S)
    show.progress()
    new_f = re.sub(r'( *)font-family.*?;', r"\1font-family: 'LinLibertinePhilo41', sans-serif;", new_f, flags=re.S)
    show.progress()
    # add in css for paragraph breaks when unit="para"
    content = "\n\n.xml-milestone[unit=\"para\"]::before {\
\n    content: \"\\\A\\\A\";\
\n    display: inline;\
\n}"
    new_f += content
    show.progress()
    content = "\n\n.xml-milestone[unit=\"para\"] {\
\n    display: none;\
\n}"
    new_f += content
    show.progress()
    content = "\n\n.xml-milestone[unit=\"page\"] {\
\n    display: none;\
\n}"
    new_f += content
    show.progress()
    # add section numbers in prose for texts using divs instead of milestones
    content = "\n\n.xml-div2[type=\"section\"]::before, .xml-div3[type=\"section\"]::before {\
\n    content: attr(n);\
\n    color: #000000;\
\n    font-weight: bold;\
\n    font-family: \'LinLibertinePhilo41\', sans-serif;\
\n    font-size: 0.8em;\
\n}"
    new_f += content
    show.progress()
    # add chapter numbers in prose for texts using divs instead of milestones
    content = "\n\n.xml-milestone[unit=\"chapter\"]::before, .xml-div2[type=\"chapter\"]::before {\
\n    content: attr(n);\
\n    color: #000000;\
\n    font-weight: bold;\
\n    font-family: \'LinLibertinePhilo41\', sans-serif;\
\n    font-size: 1.2em;\
\n}"
    new_f += content
    show.progress()
    #swap in new css
    philoLogic_css = re.sub(re.escape(f), new_f, philoLogic_css, flags=re.S)

# grab xml-add, this is to fix pluses and minuses using <> and []
f = re.search(r'xml-add \{.*?\}', philoLogic_css, flags=re.S)
f = f.group()
if '/*' not in f:
    new_f = re.sub(r'( *)(color.*?;)', r'/*\1\2*/', f, flags=re.S)
    show.progress()
    content = '\n.xml-add::before {\
\n    content: "<";\
\n}\
\n.xml-add::after {\
\n    content: ">";\
\n}\
\ndel {\
\n    text-decoration: none;\
\n}\
\ndel::before {\
\n    content: "[";\
\n}\
\ndel::after {\
\n    content: "]";\
\n}'
    new_f += content
    show.progress()
    #swap in new css
    philoLogic_css = re.sub(re.escape(f), new_f, philoLogic_css, flags=re.S)

# grab kwic_line and fix font
f = re.search(r'\.kwic_line \{.*?\}', philoLogic_css, flags=re.S)
f = f.group()
if 'Libertine' not in f:
    content = "font-family: \'LinLibertinePhilo41\', sans-serif;"
    new_f = re.sub(r'( *)(line-height.*?;)', r'\1\2\n\1' + content, f, flags=re.S)
    show.progress()
    #swap in new css
    philoLogic_css = re.sub(re.escape(f), new_f, philoLogic_css, flags=re.S)

# grab colloc-row and fix font
f = re.search(r'\.colloc-row \{.*?\}', philoLogic_css, flags=re.S)
f = f.group()
if 'Libertine' not in f:
    content = "font-family: \'LinLibertinePhilo41\', sans-serif;"
    new_f = re.sub(r'( *)(display.*?;)', r'\1\2\n\1' + content, f, flags=re.S)
    show.progress()
    #swap in new css
    philoLogic_css = re.sub(re.escape(f), new_f, philoLogic_css, flags=re.S)

# grab collocation_counts and fix font
f = re.search(r'\.collocation_counts \{.*?\}', philoLogic_css, flags=re.S)
f = f.group()
if 'Libertine' not in f:
    content = "font-family: \'LinLibertinePhilo41\', sans-serif;"
    new_f = re.sub(r'( *)(padding.*?;)', r'\1\2\n\1' + content, f, flags=re.S)
    show.progress()
    #swap in new css
    philoLogic_css = re.sub(re.escape(f), new_f, philoLogic_css, flags=re.S)

# grab xml-w. By default it does not exist, only xml-w::before, but the 
# following search should grab either
f = re.search(r'\.xml-w.*?\{.*?\}', philoLogic_css, flags=re.S)
f = f.group()
if 'Libertine' not in f:
    content = "\n.xml-w {\
\n    font-family: \'LinLibertinePhilo41\', sans-serif;\
\n}\n\n"
    new_f = content + f
    show.progress()
    #swap in new css
    philoLogic_css = re.sub(re.escape(f), new_f, philoLogic_css, flags=re.S)

# grab xml-l, this is for poetry line number size
#f = re.search(r'xml-l \{.*?\}', philoLogic_css, flags=re.S)
f = regexmatch(r'xml-l \{.*?\}', philoLogic_css, re.S)
if (f):
    f = f.group()
    if 'Libertine' not in f:
        content = "\n    font-family: \'LinLibertinePhilo41\', sans-serif;\
\n    display: block;"
        new_f = re.sub(r'( *)display.*?;', content, f, flags=re.S)
        show.progress()
        #swap in new css
        philoLogic_css = re.sub(re.escape(f), new_f, philoLogic_css, flags=re.S)

# grab xml-l::before, this is for poetry line number size
#f = re.search(r'xml-l::before \{.*?\}', philoLogic_css, flags=re.S)
f = regexmatch(r'xml-l::before \{.*?\}', philoLogic_css, re.S)
if (f):
    f = f.group()
    if '0.9em' not in f:
        new_f = re.sub(r'( *)font-size.*?;', r'\1font-size: 0.9em;', f, flags=re.S)
        show.progress()
        #swap in new css
        philoLogic_css = re.sub(re.escape(f), new_f, philoLogic_css, flags=re.S)

# grab xml-l[n]::before, this is for poetry line number size
#f = re.search(r'xml-l\[n\]::before \{.*?\}', philoLogic_css, flags=re.S)
f = regexmatch(r'xml-l\[n\]::before \{.*?\}', philoLogic_css, re.S)
if (f):
    f = f.group()
    if 'bold' not in f:
        new_f = re.sub(r'( *)color.*?;', r'\1color: #909090;\n\1font-weight: bold;\n\1text-indent: -0.5em;', f, flags=re.S)
        show.progress()
        #swap in new css
        philoLogic_css = re.sub(re.escape(f), new_f, philoLogic_css, flags=re.S)

#grab xml-sp::before
#f = re.search(r'\.xml-sp::before \{.*?\}', philoLogic_css, flags=re.S)
f = regexmatch(r'\.xml-sp::before \{.*?\}', philoLogic_css, re.S)
if (f):
    f = f.group()
    if 'who' not in f:
        # change content and add more formatting
        new_f = re.sub(r'( *)content.*;', r'\1content: attr(who);\n\1display: block;\n\1font-weight: 700;\n\1padding-top: 10px;\n\1font-size: 1.1em;', f, flags=re.S)
        show.progress()
        content = "\n.xml-sp[rend=\"none\"]::before {\
\n    content: \'\';\
\n}"
        new_f += content
        show.progress()

        content = "\n.xml-q::before {\
\n    content: attr(who);\
\n    display: inline-block;\
\n    font-weight: 700;\
\n}"
        new_f += content
        show.progress()

        content = "\n.xml-q[rend=\"none\"]::before {\
\n    content: \'\';\
\n}"
        new_f += content
        show.progress()

        content = "\ndiv[subtype=\"chapter\"]::before {\
\n    content: attr(n);\
\n    color: #000000;\
\n    font-weight: bold;\
\n    font-family: 'LinLibertinePhilo41', sans-serif;\
\n    font-size: 1.2em;\
\n}"
        new_f += content
        show.progress()

        content = "\ndiv[subtype=\"section\"]::before {\
\n    content: attr(n);\
\n    color: #000000;\
\n    font-weight: bold;\
\n    font-family: 'LinLibertinePhilo41', sans-serif;\
\n    font-size: 0.8em;\
\n}"
        new_f += content
        show.progress()

        content = "\ndiv[subtype=\"card\"]::before {\
\n    content: attr(n) "   ";\
\n    white-space: pre;\
\n    color: #000000;\
\n    font-weight: bold;\
\n    font-family: 'LinLibertinePhilo41', sans-serif;\
\n    font-size: 0.8em;\
\n}"
        new_f += content
        show.progress()

        if type_of_fix == "dictionary":
            content = "\ndiv[class='philologic-fragment'] {\
\n    font-family: 'LinLibertinePhilo41', sans-serif;\
\n    font-size: 1.1em;\
\n}\
\n\
\nspan[class='philologic-fragment'] {\
\n    font-family: 'LinLibertinePhilo41', sans-serif;\
\n    font-size: 1.1em;\
\n}\
\n\
\nb[lang='greek'] {\
\n    font-family: 'LinLibertinePhilo41', sans-serif;\
\n    font-weight: bold;\
\n    font-size: 1.1em;\
\n}"
            new_f += content
            show.progress()

        #swap in new css
        philoLogic_css = re.sub(re.escape(f), new_f, philoLogic_css, flags=re.S)

#grab text-content-area
f = regexmatch(r'\.text-content-area \{.*?\}', philoLogic_css, re.S)
if (f):
    f = f.group()
    if 'Libertine' not in f:
        # change to Libertine font
        new_f = re.sub(r'( *)(font-family.*)}', r"\1/*\2\1font-family: 'LinLibertinePhilo41', sans-serif;\n}", f, flags=re.S)
        show.progress()
        #swap in new css
        philoLogic_css = re.sub(re.escape(f), new_f, philoLogic_css, flags=re.S)

#grab xml-speaker
f = regexmatch(r'\.xml-speaker \{.*?display.*?\}', philoLogic_css, re.S)
if (f):
    f = f.group()
    if 'bold' not in f:
        # make bold and increase size slightly
        new_f = re.sub(r'( *)(display.*;)', r'\1\2\n\1font-weight: bold;\n\1font-size: 1.1em;', f, flags=re.S)
        show.progress()
        #swap in new css
        philoLogic_css = re.sub(re.escape(f), new_f, philoLogic_css, flags=re.S)

#grab xml-speaker::before
#f = re.search(r'\.xml-speaker\++.*?::before \{.*?\}', philoLogic_css, flags=re.S)
f = regexmatch(r'\.xml-speaker\++.*?::before \{.*?\}', philoLogic_css, re.S)
if (f):
    f = f.group()
    if 'who' not in f:
        # change content and add more formatting
        new_f = re.sub(r'( *)content.*;', r'\1content: attr(who);\n\1display: block;\n\1font-weight: 700;\n\1padding-top: 10px;', f, flags=re.S)
        show.progress()
        #swap in new css
        philoLogic_css = re.sub(re.escape(f), new_f, philoLogic_css, flags=re.S)

#grab xml-cit css
#f = re.search(r'\.xml-cit\ \{.*?\}', philoLogic_css, flags=re.S)
f = regexmatch(r'\.xml-cit\ \{.*?\}', philoLogic_css, re.S)
if (f):
    f = f.group()
    if '/*' not in f:
        # comment out
        new_f = re.sub(r' *(padding.*;)', r'/*\n\1\n*/', f, flags=re.S)
        show.progress()
        #swap in new css
        philoLogic_css = re.sub(re.escape(f), new_f, philoLogic_css, flags=re.S)

#grab xml-gap::after css
#f = re.search(r'\.xml-gap::after \{.*?\}', philoLogic_css, flags=re.S)
f = regexmatch(r'\.xml-gap::after \{.*?\}', philoLogic_css, re.S)
if (f):
    f = f.group()
    if '/*' not in f:
        # comment out and add new content
        new_f = re.sub(r'( *)(content.*;)', r'/*\1\2*/\n\1content: "...";', f, flags=re.S)
        show.progress()
        #swap in new css
        philoLogic_css = re.sub(re.escape(f), new_f, philoLogic_css, flags=re.S)

#grab xml-pb::before css
#f = re.search(r'\.xml-pb::before \{.*?\}', philoLogic_css, flags=re.S)
f = regexmatch(r'\.xml-pb::before \{.*?\}', philoLogic_css, re.S)
if (f):
    f = f.group()
    if '/*' not in f:
        # comment out
        new_f = re.sub(r'(.*})', r'/*\n\1\n*/', f, flags=re.S)
        show.progress()
        #swap in new css
        philoLogic_css = re.sub(re.escape(f), new_f, philoLogic_css, flags=re.S)

#grab xml-pb-image css
#f = re.search(r'\.xml-pb-image \{.*?\}', philoLogic_css, flags=re.S)
f = regexmatch(r'\.xml-pb-image \{.*?\}', philoLogic_css, re.S)
if (f):
    f = f.group()
    if '/*' not in f:
        new_f = re.sub(r'display.*?;', r'display: none;', f, flags=re.S)
        show.progress()
        #swap in new css
        philoLogic_css = re.sub(re.escape(f), new_f, philoLogic_css, flags=re.S)

    #grab xml-cit::before css
    if '/*' not in f:
        f = re.search(r'\.xml-cit::before \{.*?\}', philoLogic_css, flags=re.S)
        f = f.group()
        # comment out
        new_f = re.sub(r' *(content.*;)', r'/*\n\1\n*/', f, flags=re.S)
        show.progress()
        #swap in new css
        philoLogic_css = re.sub(re.escape(f), new_f, philoLogic_css, flags=re.S)

#grab xml-cit::after css
#f = re.search(r'\.xml-cit::after \{.*?\}', philoLogic_css, flags=re.S)
f = regexmatch(r'\.xml-cit::after \{.*?\}', philoLogic_css, re.S)
if (f):
    f = f.group()
    if '/*' not in f:
        # comment out
        new_f = re.sub(r' *(content.*;)', r'/*\n\1\n*/', f, flags=re.S)
        show.progress()
        #add some css
        content = "\n\n.xml-sense {\n    padding-left: 2.3em;\n    display: block;\n}"
        content += "\n\n.xml-sense::before {\n    content: attr(n) \" \";\n}"
        content += "\n\nspan[level^=\'2\'] { \
\n    padding-left: 4em;\
\n    display: block;\
\n    text-indent: -1.5em;\
\n}"
        content += "\n\nspan[level^=\'3\'] {\
\n    padding-left: 6em;\
\n    display: block;\
\n    text-indent: -1.5em;\
\n}"
        new_f += content
        show.progress()
        #swap in new css
        philoLogic_css = re.sub(re.escape(f), new_f, philoLogic_css, flags=re.S)

close_for_mod(philoLogic_css_path, philoLogic_css)
print(" (done)") 

#################################################
###                New File                   ###
###                index.html                 ###
#################################################

# read in and fix index.html
index_html = open_for_mod(index_html_path, 'r').read()
print("index.html", end="")

# grab the header 
#f = re.search(r'(<div id=\"header\">.*<\/div>).*<\!--Main content-->', index_html, flags=re.S)
f = regexmatch(r'(<div id=\"header\">.*<\/div>).*<\!--Main content-->', index_html, re.S)
if (f):
    f = f.group(1)
    # find the lines to change
    new_f = ""
    if '<!--fix_load was here-->' not in f:
        new_f = re.sub(r'<a href=\"http:\/\/www.atilf.fr\/\">ATILF-CNRS<\/a>', '<!--fix_load was here-->\n\t\t    <a href="https://classics.uchicago.edu">Classics department</a>', f)
        show.progress()
        new_f = re.sub(r'<a href=\"https:\/\/artfl-project.uchicago.edu\/content\/contact-us\".*?<\/a>', '<a href="https://forms.gle/zM46MJjMEN279Q2v5" title="Tell us what you really think!">Report a Problem</a>', new_f)
        show.progress()
        new_f = re.sub(r'<a href=\"https:\/\/artfl-project.uchicago.edu\".*?<\/a>', '<!--fix_load was here-->\n\t\t    <a href="https://perseus.uchicago.edu">Perseus UChicago Home</a>', new_f)
        show.progress()
        #swap in new html 
        index_html = re.sub(re.escape(f), new_f, index_html, flags=re.S)

# grab the footer 
#f = re.search(r'(<div class=\"container-fluid\" id=\"footer\">.*<\/div>).*<\!--Modal dialog-->', index_html, flags=re.S)
f = regexmatch(r'(<div class=\"container-fluid\" id=\"footer\">.*<\/div>).*<\!--Modal dialog-->', index_html, re.S)
if (f):
    f = f.group(1)
    # find the lines to change
    new_f = ""
    if '<!--fix_load was here-->' not in f:
        new_f = re.sub(r'(<\/a>PhiloLogic4)', r'\1\n\t\t<!--fix_load was here-->\n\t\t<br><font face="LinuxLibertinePhilo41">Linux Libertine Font</font>\n\t\t<a href="https://sourceforge.net/projects/linuxlibertine/" title="Linux Libertine Greek font contributed by Rolf Noyer">\n\t\t\t<img src="app/assets/img/linuxlibertine.png" height="48" width="48">\n\t\t</a>', f)
        show.progress()
        #swap in new html 
        index_html = re.sub(re.escape(f), new_f, index_html, flags=re.S)

close_for_mod(index_html_path, index_html)
print(" (done)") 

#################################################
###                New File                   ###
###                searchForm.html            ###
#################################################

# read in and fix searchForm.html
searchForm_html = open_for_mod(searchForm_html_path, 'r').read()
print("searchForm.html", end="")

# turn off spellcheck
#conf = re.search(r'(<form id=\"search\")(.*?>)', searchForm_html, flags=re.S)
f = regexmatch(r'(<form id=\"search\")(.*?>)', searchForm_html, re.S)
if (f):
    searchForm_html = re.sub(re.escape(f.group()), f.group(1) + " spellcheck=\"false\"" + f.group(2), searchForm_html)
    show.progress()

# add lemmas search matching option
f = regexmatch(r'(</div>\n[\t ]+</div>\n[\t ]+</div>\n[\t ]+</div>\n[\t ]+</div>\n)(.*?)([\t ]+)(<search-methods.+?></search-methods>)', searchForm_html, re.S)
if (f):
    if "fix_load" not in f.group(0):
        #new_f = '<search-lemma ng-if="formData.report == \'collocation\'"></search-lemma>\n' + f.group(3) + "<!--fix_load was here-->\n" + f.group(3) + f.group(4)
        new_f = '<search-lemma></search-lemma>\n' + f.group(3) + "<!--fix_load was here-->\n" + f.group(3) + f.group(4)
        f = f.group(4)
        show.progress()
        searchForm_html = re.sub(re.escape(f), new_f, searchForm_html, flags=re.S)

close_for_mod(searchForm_html_path, searchForm_html)
print(" (done)") 

#################################################
###                New File                   ###
###           searchArguments.html            ###
#################################################

# read in and fix searchArguments.html
searchArguments_html = open_for_mod(searchArguments_html_path, 'r').read()
print("searchArguments.html", end="")

# add word criteria display
f = regexmatch(r'(<div style.*?>.*?Bibliography.*?</div>)(.*?</div>)', searchArguments_html, re.S)
if (f):
    if "fix_load" not in f.group(2):
        f = f.group(1)
        new_f = f + '\
\n    <div style="margin-top: 5px;">\
\n        <!--fix_load was here-->\
\n        Word criteria:\
\n        <span class="biblio-criteria" ng-repeat="metadata in queryArgs.wordCriteria" style="margin: 1px">{{ ::metadata.alias }} : <b>{{ ::metadata.value }}</b>\
\n                        <span class="glyphicon glyphicon-remove-circle" ng-click="removeMetadata(metadata.key, formData, restart)"></span>\
\n        </span>\
\n        <b ng-if="queryArgs.wordCriteria.length === 0">None</b>\
\n    </div>\
'
        show.progress()
        searchArguments_html = re.sub(re.escape(f), new_f, searchArguments_html, flags=re.S)

close_for_mod(searchArguments_html_path, searchArguments_html)
print(" (done)") 

#################################################
###                New File                   ###
###                kwic.html                  ###
#################################################

# read in and fix kwic.html
kwic_html = open_for_mod(kwic_html_path, 'r').read()
print("kwic.html", end="")

# use div3 for hit links 
kwic_html = re.sub('citation_links.div1','citation_links.div3', kwic_html)
show.progress()

# compile the result.context
kwic_html = re.sub('<span ng-bind-html="result.context \| unsafe"></span>', '<span compile="result.context"></span>', kwic_html)
show.progress()

close_for_mod(kwic_html_path, kwic_html)
print(" (done)") 

#################################################
###                New File                   ###
###                concordance.html           ###
#################################################

# read in and fix conordance.html
concordance_html = open_for_mod(concordance_html_path, 'r').read()
print("concordance.html", end="")

# add compile to allow angular to work correctly
concordance_html = re.sub('<div class="default-length" ng-bind-html="result.context \| unsafe"></div>', '<div class="default-length" compile="result.context"></div>', concordance_html)
show.progress()

close_for_mod(concordance_html_path, concordance_html)
print(" (done)") 

#################################################
###              New File                     ###
###              navigationBar.html           ###
#################################################

# read in and fix navigationBar.html
navigationBar_html = open_for_mod(navigationBar_html_path, 'r').read()
print("navigationBar.html", end="")

# Have the nav bar actually show where you are
# 'whereami' is defined in the textObject function in philoLogic.js
navigationBar_html = re.sub('Table of contents', '{{ textObject.metadata_fields.whereami }}', navigationBar_html)
show.progress()

# Add a button to go to translation load; translation is defined in navigation.py
button = '<a ng-if="philoConfig.translation_dbname != ''" class="btn btn-primary" id="translate" ng-href="{{textObject.translation}}"><span>Translation</span></a>'
navigationBar_html = re.sub('</button>\s*</div>', '</button>\n%s\n</div>' % button, navigationBar_html, flags=re.S)
show.progress()

close_for_mod(navigationBar_html_path, navigationBar_html)
print(" (done)") 

#################################################
###              New File                     ###
###              textObject.html              ###
#################################################

# read in and fix textObject.html
textObject_html = open_for_mod(textObject_html_path, 'r').read()
print("textObject.html", end="")

# Change text
textObject_html = re.sub(r"(\s+)(To look up a word in a dictionary, select the word with your mouse and press 'd' on your keyboard.)", r'\1<!--\2-->\1Click on a word for parses and a link to Logeion.', textObject_html, re.S)
show.progress()

close_for_mod(textObject_html_path, textObject_html)
print(" (done)") 

#################################################
###          scripts/get_sorted_kwic.py       ###
#################################################

# read in and fix get_sorted_kwic 
get_sorted_kwic = open_for_mod(get_sorted_kwic_path, 'r').read()

print ("get_sorted_kwic.py", end="")

# fix the offset bug for sorting
get_sorted_kwic = get_sorted_kwic.replace("[start:end]", "[start-1:end]")
show.progress()

# make sure we load our custom kwic_hit_object()
get_sorted_kwic = get_sorted_kwic.replace("from philologic.runtime import (kwic_hit_object, page_interval)", "from philologic.runtime import page_interval")
show.progress()

f = regexmatch(r'import custom_functions.*?try', get_sorted_kwic, re.S)
if (f):
    f = f.group()
    if "fix_load" not in f:
        new_f = re.sub(r"import custom_functions", r"import custom_functions\n#fix_load was here\nfrom custom_functions import kwic_hit_object\n", f, flags=re.M)
        show.progress()
        get_sorted_kwic = re.sub(re.escape(f), new_f, get_sorted_kwic, flags=re.S)

close_for_mod(get_sorted_kwic_path, get_sorted_kwic)
print(" (done)")

#################################################
###          scripts/get_word_frequency       ###
#################################################

# read in and fix get_word_frequency 
get_word_frequency = open_for_mod(get_word_frequency_path, 'r').read()

print ("get_word_frequency.py", end="")

# make sure we load our generate_word_frequency()
f = regexmatch(r'import custom_functions.*?try', get_word_frequency, re.S)
if (f):
    f = f.group()
    if "fix_load" not in f:
        new_f = re.sub(r"import custom_functions", r"import custom_functions\n#fix_load was here\nfrom custom_functions import generate_word_frequency\n", f, flags=re.M)
        show.progress()
        get_word_frequency = re.sub(re.escape(f), new_f, get_word_frequency, flags=re.S)

close_for_mod(get_word_frequency_path, get_word_frequency)
print(" (done)")

#################################################
###         scripts/autocomplete_metadata       ###
#################################################

# read in and fix get_word_frequency 
autocomplete_metadata = open_for_mod(autocomplete_metadata_path, 'r').read()

print ("autocomplete_metadata.py", end="")

# fix unicode problem
f = regexmatch(r'def exact_word_pattern_search.*?subprocess', autocomplete_metadata, re.S)
if (f):
    f = f.group()
    if "fix_load" not in f:
        new_f = re.sub(r'(\s*)(command.*?path\])', r'\1#\2\1#fix_load was here\1command = ["egrep", "-a", b"%s[[:blank:]]?" % term.encode("utf-8"), path]', f, flags=re.M)
        show.progress()
        autocomplete_metadata = re.sub(re.escape(f), new_f, autocomplete_metadata, flags=re.S)

# stop lowercasing!
autocomplete_metadata = re.sub(r'(\s+)(norm_tok = token.lower\(\))', r'\1#\2\1norm_tok = token', autocomplete_metadata)
show.progress()
autocomplete_metadata = re.sub(r'(\s+)(substr_token = token.lower\(\))', r'\1#\2\1substr_token = token', autocomplete_metadata)
show.progress()

close_for_mod(autocomplete_metadata_path, autocomplete_metadata)
print(" (done)")

#################################################
###    scripts/get_landing_page_content       ###
#################################################

# read in and fix get_landing_page_content
get_landing_page_content = open_for_mod(get_landing_page_content_path, 'r').read()

print ("get_landing_page_content.py", end="")

# do not group by 'title' when displaying the titles of all texts because texts
# with the same exact title will not all be accessible 
f = regexmatch(r'from philologic.runtime import group_by_metadata.*?import custom_functions', get_landing_page_content, re.S, critical=False)
if (f):
    f = f.group()
    if "fix_load" not in f:
        new_f = re.sub(r"import custom_functions", r"import custom_functions\nfrom custom_functions import group_by_range\n", f, flags=re.M)
        get_landing_page_content = re.sub(re.escape(f), new_f, get_landing_page_content, flags=re.S)
        show.progress()

        get_landing_page_content = get_landing_page_content.replace('from philologic.runtime import group_by_metadata, group_by_range', '#from philologic.runtime import group_by_metadata, group_by_range\n#fix_load was here\nfrom philologic.runtime import group_by_metadata')
        show.progress()

close_for_mod(get_landing_page_content_path, get_landing_page_content)
print(" (done)")

#################################################
###     reports/word_property_filter.py       ###
#################################################

# read in and fix word_property_filter.py
word_property_filter = open_for_mod(word_property_filter_path, 'r').read()

print ("word_property_filter.py", end="")

# make sure we call filter_words_by_property() correctly
f = regexmatch(r' *filter_results.*config\)', word_property_filter, re.S)
if (f):
    f = f.group()
    if "fix_load" not in f:
        content = "filter_results = filter_words_by_property(request, config)"
        new_f = re.sub(r"^( *)(.*)", r"#\1\2", f, flags=re.M)
        new_f = re.sub(r"^#( *)(.*)", r"#\1\2\n\1#fix_load was here\n\1" + content, new_f, flags=re.S)
        show.progress()
        word_property_filter = re.sub(re.escape(f), new_f, word_property_filter, flags=re.S)

close_for_mod(word_property_filter_path, word_property_filter)
print(" (done)")

#################################################
###    custom_functions/ObjectFormatter.py    ###
#################################################

# read in and fix ObjectFormatter 
ObjectFormatter_py = open_for_mod(ObjectFormatter_path, 'r').read()

print ("ObjectFormatter.py", end="")

# import cts functions
f = regexmatch(r'import.*?BEGIN', ObjectFormatter_py, re.S)
if (f):
    f = f.group()
    if "fix_load" not in f:
        new_f = re.sub(r"from philologic.utils import convert_entities", r"from philologic.utils import convert_entities\n#fix_load was here\nfrom .cts_tools import perseus_to_cts_urn, get_cite_from_urn", f, flags=re.M)
        show.progress()
        ObjectFormatter_py = re.sub(re.escape(f), new_f, ObjectFormatter_py, flags=re.S)

# turn perseus urns into real links in format_concordance
f = regexmatch(r'format_concordance.*?elif el.tag == "title":', ObjectFormatter_py, re.S)
if (f):
    f = f.group()
    if "fix_load" not in f:
        # add header suppression handling 
        new_f = re.sub(r'(\s*)(allowed_tags.*?\))', r'\1\2\1non_header_tags = set(["div1", "div2", "div3", "milestone", "text", "head", "body", "castList"])\1inHeader = True' , f, flags=re.S)
        show.progress()
        new_f = re.sub(r'(\s*)(for el in xml.iter\(\):)', r'\1\2\1    if el.tag in allowed_tags or el.tag in non_header_tags:\1        inHeader = False' , new_f, flags=re.S)
        show.progress()
        new_f = re.sub(r'(\s*)(if el.tag not in allowed_tags:)', r'\1\2\1    if inHeader and el.tag != "div":\1        el.attrib["class"] = "noshow"' , new_f, flags=re.S)
        show.progress()
        # add bibl urn handling
        new_f = re.sub(r'"br"\]', r'"br", "bibl"]', new_f, flags=re.S)
        show.progress()
        content = 'if el.tag == "bibl":\
\n            el.tag = "a"\
\n            if "n" in el.attrib:\
\n                urn = perseus_to_cts_urn(el.attrib["n"])\
\n                (urn, cite) = get_cite_from_urn(urn)\
\n                if urn and cite:\
\n                    if "greek" in urn: text_load = config.Greek_dbname\
\n                    if "latin" in urn: text_load = config.Latin_dbname\
\n                    el.attrib["href"] = text_load + \'query?report=bibliography&method=proxy&cts_urn=%s&head=%%22%s%%22\' % (urn, cite)\
\n                    el.attrib["target"] = "_blank"'      
        new_f = re.sub(r'(\s*)(elif el.tag == "title":)', r'\1#fix_load was here\1' + content + r'\1\2', new_f, flags=re.S)
        show.progress()
        ObjectFormatter_py = re.sub(re.escape(f), new_f, ObjectFormatter_py, flags=re.S)

# turn perseus urns into real links in format_text_object
f = regexmatch(r'format_text_object.*?elif el.tag == "head":', ObjectFormatter_py, re.S)
if (f):
    f = f.group()
    if "fix_load" not in f:
        ## add header suppression handling 
        #new_f = re.sub(r'(\s*)(allowed_tags.*?\))', r'\1\2\1non_header_tags = set(["div1", "div2", "div3", "milestone", "text", "head", "body", "castList"])\1inHeader = True' , f, flags=re.S)
        #show.progress()
        #new_f = re.sub(r'(\s*)(for el in xml.iter\(\):)', r'\1\2\1    if el.tag in allowed_tags or el.tag in non_header_tags:\1        inHeader = False' , new_f, flags=re.S)
        #show.progress()
        #new_f = re.sub(r'(\s*)(if el.tag not in allowed_tags:)', r'\1\2\1    if inHeader and el.tag != "div":\1        el.attrib["class"] = "noshow"' , new_f, flags=re.S)
        #show.progress()
        # add bibl urn handling
        #new_f = re.sub(r'"br"\]', r'"br", "bibl"]', new_f, flags=re.S)
        #show.progress()
        content = 'if el.tag == "bibl":\
\n                el.tag = "a"\
\n                if "n" in el.attrib:\
\n                    urn = perseus_to_cts_urn(el.attrib["n"])\
\n                    (urn, cite) = get_cite_from_urn(urn)\
\n                    if urn and cite:\
\n                        if "greek" in urn: text_load = config.Greek_dbname\
\n                        if "latin" in urn: text_load = config.Latin_dbname\
\n                        el.attrib["href"] = text_load + \'query?report=bibliography&method=proxy&cts_urn=%s&head=%%22%s%%22\' % (urn, cite)\
\n                        el.attrib["target"] = "_blank"'      
        new_f = re.sub(r'(\s*)(elif el.tag == "head":)', r'\1#fix_load was here\1' + content + r'\1\2', f, flags=re.S)
        show.progress()
        ObjectFormatter_py = re.sub(re.escape(f), new_f, ObjectFormatter_py, flags=re.S)
# stop deleting ids in concordance
f = regexmatch(r' *if \(.*?\["id"\]', ObjectFormatter_py, re.S)
if (f):
    f = f.group()
    if 'fix_load' not in f:
        new_f = re.sub(r"^( *)(.*)", r"#\1\2", f, flags=re.M)
        new_f = re.sub(r"^( *)(.*)", r"\1\2#fix_load", new_f, flags=re.M)
        show.progress()
        ObjectFormatter_py = re.sub(re.escape(f), new_f, ObjectFormatter_py, flags=re.S)

# add a pipe to indicate end of line
f = regexmatch(r'(text\[last_offset:\])(.*?)(xml = FragmentParserParse)', ObjectFormatter_py, re.S)
if (f):
    if 'fix_load' not in f.group(2):
        content = "text = re.sub(rb'</l>', b'</l>||', text) #fix_load. Add pipes to indicate end of line"
        new_f = f.group(1) + f.group(2) + content + f.group(2) + f.group(3)
        show.progress()
        f = f.group()
        ObjectFormatter_py = re.sub(re.escape(f), new_f, ObjectFormatter_py, flags=re.S)

# strip/replace tags in a way that retains spans with word ids
f = regexmatch(r' *output = clean_tags.*?$', ObjectFormatter_py, re.M)
if (f):
    f = f.group()
    if 'fix_load' not in f:
        new_f = re.sub(r"^( *)(.*)", r"#\1\2 #fix_load", f, flags=re.M) 
        content = '\
\n    allowed_tags = set(["head", "item", "quote", "p", "div", "foreign", "milestone", "note", "span", "philoHighlight", "w"])\
\n    found_highlight = False\
\n    for el in xml.iter():\
\n        orig_tag = el.tag\
\n        if el.tag.startswith("DIV"):\
\n            el.tag = el.tag.lower()\
\n        if el.tag in allowed_tags:\
\n            if el.tag == "philoHighlight":\
\n                word_match = re.match(word_regex, el.tail)\
\n                if word_match:\
\n                    el.text = el.tail[: word_match.end()]\
\n                    el.tail = el.tail[word_match.end() :]\
\n                    found_highlight = True\
\n                el.tag = "span"\
\n                el.attrib["class"] = "highlight"\
\n            if el.tag == "w":\
\n                el.tag = "span"\
\n                el.attrib["class"] = "xml-w"\
\n            if el.tag == "quote": el.tag = "l"\
\n            if el.tag == "p": el.tag = "l"\
\n            if el.tag == "div": el.tag = "l"\
\n            if el.tag == "item": el.tag = "l"\
\n            if el.tag == "milestone": el.tag = "l"\
\n            if el.tag == "head": el.tag = "l"\
\n        else:\
\n            etree.strip_tags(xml, el.tag)\
\n    if not found_highlight:\
\n        import sys\
\n        print("Problem XML Tag: " + orig_tag, file=sys.stderr)\
\n        print(text.decode("utf8", "ignore"), file=sys.stderr)\
\n    output = etree.tostring(xml).decode("utf8", "ignore")\
\n    output = re.sub(r\'\\\A<div class="philologic-fragment">\', "", output)\
\n    output = re.sub(r"</div>\\\Z", "", output)\
\n    output = convert_entities(output)'

        new_f += content
        show.progress()
        ObjectFormatter_py = re.sub(re.escape(f), new_f, ObjectFormatter_py, flags=re.S)

close_for_mod(ObjectFormatter_path, ObjectFormatter_py)
print(" (done)")

#################################################
###                   END                     ###
#################################################

print('\nFixing load "%s" FINISHED with %d fixes applied and %s regexmatch error(s) and %s regexmatch warning(s).\n' %(myload, show.total(), show.total_err(), show.total_warn()))
