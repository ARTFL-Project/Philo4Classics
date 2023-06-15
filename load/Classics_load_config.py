###############################
## General Loading Variables ##
###############################

# Define location of local Philo4Classics directory
philo4classics = "/home/waltms/Philo4Classics"

# Default path to Greek Lexicon if different from philo4classics
lexicon_db = "/var/www/cgi-bin/perseus/LatinLexicon.sqlite"

# Default abbrevs file
abbrevs_file = "Latin.abbrevs"

# Define a Greek load to which Perseus URNs should point
#Greek_load = "http://some.server.com/philologic4/TextLoad/"
Greek_load = ""

# Define a Latin load to which Perseus URNs should point
#Latin_load = "http://some.server.com/philologic4/TextLoad/"
Latin_load = ""

# Define default object level
default_object_level = "doc"

# Define navigable objects: doc, div1, div2, div3, para.
#navigable_objects = ("doc", "div1", "div2", "div3", "para")

## Define text objects to generate plain text files for various machine learning tasks
## For instance, this could be ['doc', 'div1']
plain_text_obj = []

## Define whether to store all words with their philo IDs. Useful for data-mining tasks
## where keeping the index information (and byte offset) is important.
store_words_and_ids = True

#####################
## Parsing Options ##
#####################

# These are doc level XPATHS used to parse a standard TEI header.
# These XPATHS need to be inside a <teiHeader> and strictly apply to the entire document..
# Only useful if you parse a TEI header.
doc_xpaths = {
    "author": [
#        ".//sourceDesc/bibl/author[@type='marc100']",
#        ".//sourceDesc/bibl/author[@type='artfl']",
#        ".//sourceDesc/bibl/author",
        ".//titlestmt/author",
        ".//titleStmt/author",
        ".//sourceDesc/biblStruct/monogr/author/name",
        ".//sourceDesc/biblFull/titleStmt/author",
        ".//sourceDesc/biblFull/titleStmt/respStmt/name",
        ".//sourceDesc/biblFull/titleStmt/author",
        ".//sourceDesc/bibl/titleStmt/author",
    ],
    "urn": [
        ".//idno"
    ],
    "title": [
#        ".//sourceDesc/bibl/title[@type='marc245']",
#        ".//sourceDesc/bibl/title[@type='artfl']",
#        ".//sourceDesc/bibl/title",
        ".//titlestmt/title",
        ".//titleStmt/title",
        ".//sourceDesc/bibl/titleStmt/title",
        ".//sourceDesc/biblStruct/monogr/title",
        ".//sourceDesc/biblFull/titleStmt/title",
    ],
    "author_dates": [".//sourceDesc/bibl/author/date", ".//titlestmt/author/date"],
    "create_date": [
        ".//profileDesc/creation/date",
        ".//fileDesc/sourceDesc/bibl/imprint/date",
        ".//sourceDesc/biblFull/publicationStmt/date",
        ".//profileDesc/dummy/creation/date",
        ".//fileDesc/sourceDesc/bibl/creation/date",
    ],
    "publisher": [
        ".//sourceDesc/bibl/imprint[@type='artfl']",
        ".//sourceDesc/bibl/imprint[@type='marc534']",
        ".//sourceDesc/bibl/imprint/publisher",
        ".//sourceDesc/biblStruct/monogr/imprint/publisher/name",
        ".//sourceDesc/biblFull/publicationStmt/publisher",
        ".//sourceDesc/bibl/publicationStmt/publisher",
        ".//sourceDesc/bibl/publisher",
        ".//publicationStmt/publisher",
        ".//publicationStmp",
    ],
    "pub_place": [
        ".//sourceDesc/bibl/imprint/pubPlace",
        ".//sourceDesc/biblFull/publicationStmt/pubPlace",
        ".//sourceDesc/biblStruct/monog/imprint/pubPlace",
        ".//sourceDesc/bibl/pubPlace",
        ".//sourceDesc/bibl/publicationStmt/pubPlace",
    ],
    "pub_date": [
        ".//sourceDesc/bibl/imprint/date",
        ".//sourceDesc/biblStruct/monog/imprint/date",
        ".//sourceDesc/biblFull/publicationStmt/date",
        ".//sourceDesc/bibFull/imprint/date",
        ".//sourceDesc/bibl/date",
        ".//text/front/docImprint/acheveImprime",
    ],
    "extent": [".//sourceDesc/bibl/extent", ".//sourceDesc/biblStruct/monog//extent", ".//sourceDesc/biblFull/extent"],
    "editor": [
        ".//sourceDesc/bibl/editor",
        ".//sourceDesc/biblFull/titleStmt/editor",
        ".//sourceDesc/bibl/title/Stmt/editor",
    ],
    "identifiers": [".//publicationStmt/idno"],
    "text_genre": [".//profileDesc/textClass/keywords[@scheme='genre']/term", ".//SourceDesc/genre"],
    "keywords": [".//profileDesc/textClass/keywords/list/item"],
    "language": [
        ".//profileDesc/language/language"
        ".//profileDesc/langUsage/language"
    ],
    "notes": [".//fileDesc/notesStmt/note", ".//publicationStmt/notesStmt/note"],
    "auth_gender": [".//publicationStmt/notesStmt/note"],
    "collection": [".//seriesStmt/title"],
    "period": [
        ".//profileDesc/textClass/keywords[@scheme='period']/list/item",
        ".//SourceDesc/period",
        ".//sourceDesc/period",
    ],
    "text_form": [".//profileDesc/textClass/keywords[@scheme='form']/term"],
    "structure": [".//SourceDesc/structure", ".//sourceDesc/structure"],
    "idno": [".//fileDesc/publicationStmt/idno/"],
}

# Maps any given tag to one of PhiloLogic's types. Available types are div, para, page, and ref.
# Below is the default mapping.
tag_to_obj_map = {
    "div": "div",
    "div1": "div",
    "div2": "div",
    "div3": "div",
    "hyperdiv": "div",
    "front": "div",
    "milestone":"para",
    "note": "para",
    "p": "para",
    "sp": "para",
    "lg": "para",
    "epigraph": "para",
    "argument": "para",
    "postscript": "para",
    "opener": "para",
    "closer": "para",
    "stage": "para",
    "castlist": "para",
    "list": "para",
    "q": "para",
    "add": "para",
    "pb": "page",
    "ref": "ref",
    "graphic": "graphic",
}

# Defines which metadata to parse out for each object. All metadata defined here are attributes of a tag,
# with the exception of head which is its own tag. Below are defaults.
metadata_to_parse = {
    "doc": ["cts_urn", "cts_edition", "abbrev"],
    "div": ["head", "type", "n", "id", "vol", "subtype"],
    "para": ["who", "resp", "id", "n"],
    "page": ["n", "id", "facs"],
    "ref": ["target", "n", "type"],
    "graphic": ["facs"],
    "line": ["n", "id"],
}

# Define a file (with full path) containing words to index. Must be one word per line.
# Useful for filtering out dirty OCR.
words_to_index = ""

# This regex defines how to tokenize words and punctuation
token_regex = r"\w+|[&\w;]+"
#token_regex = "[\&A-Za-z0-9\177-\377][\&A-Za-z0-9\177-\377\_\';\u02bc\u00b7]*"


# Define the order in which files are sorted. This will affect the order in which
# results are displayed. Supply a list of metadata strings, e.g.:
# ["date", "author", "title"]
sort_order = ["author", "urn", "title", "filename"]

# A list of tags to ignore: contents will not be indexed
# This should be a list of tag names, such as ["desc", "gap"]
suppress_tags = []

# --------------------- Set Apostrophe Break ------------------------
# Set to True to break words on apostrophe.  Probably False for
# English, True for French.  Your milage may vary.
break_apost = True

# ------------- Define Characters to Exclude from Index words -------
# Leading to a second list, characters which can be in words
# but you don't want to index.
chars_not_to_index = r"\[\{\]\}"

# ---------------------- Treat Lines as Sentences --------------------
# In linegroups, break sentence objects on </l> and turns off
# automatic sentence recognition.  Normally off.
break_sent_in_line_group = False

# ------------------ Skip in word tags -------------------------------
# Tags normally break words.  There may be exceptions.  To run the
# exception, turn on the exception and list them as patterns.
# Tags will not be indexed and will not break words. An empty list turns of the feature
tag_exceptions = [
    r"<hi[^>]*>",
    r"<emph[^>]*>",
    r"<\/hi>",
    r"<\/emph>",
    r"<orig[^>]*>",
    r"<\/orig>",
    r"<sic[^>]*>",
    r"<\/sic>",
    r"<abbr[^>]*>",
    r"<\/abbr>",
    r"<i>",
    r"</i>",
    r"<sup>",
    r"</sup>",
]

# ------------- UTF8 Strings to consider as word breakers -----------
# In SGML, these are ents.  But in Unicode, these are characters
# like any others.  Consult the table at:
# www.utf8-chartable.de/unicode-utf8-table.pl?start=8016&utf8=dec&htmlent=1
# to see about others. An empty list disables the feature.
# Note that these strings must be marked as binary as they are UTF8 strings
unicode_word_breakers = [
    b"\xe2\x80\x93",  # U+2013 &ndash; EN DASH
    b"\xe2\x80\x94",  # U+2014 &mdash; EM DASH
    b"\xc2\xab",  # &laquo;
    b"\xc2\xbb",  # &raquo;
    b"\xef\xbc\x89",  # fullwidth right parenthesis
    b"\xef\xbc\x88",  # fullwidth left parenthesis
    b"\xe2\x80\x90",  # U+2010 hyphen for greek stuff
    b"\xce\x87",  # U+00B7 ano teleia
    b"\xe2\x80\xa0",  # U+2020 dagger
    b"\xe2\x80\x98",  # U+2018 &lsquo; LEFT SINGLE QUOTATION
    b"\xe2\x80\x99",  # U+2019 &rsquo; RIGHT SINGLE QUOTATION
    b"\xe2\x80\x9c",  # U+201C &ldquo; LEFT DOUBLE QUOTATION
    b"\xe2\x80\x9d",  # U+201D &rdquo; RIGHT DOUBLE QUOTATION
    b"\xe2\x80\xb9",  # U+2039 &lsaquo; SINGLE LEFT-POINTING ANGLE QUOTATION
    b"\xe2\x80\xba",  # U+203A &rsaquo; SINGLE RIGHT-POINTING ANGLE QUOTATION
    b"\xe2\x80\xa6",  # U+2026 &hellip; HORIZONTAL ELLIPSIS
]

#  ----------------- Set Long Word Limit  -------------------
#  Words greater than 235 characters (bytes) cause an indexing
#  error.  This sets a limit.  Words are then truncated to fit.
long_word_limit = 200

# ------------------ Hyphenated Word Joiner ----------------------------
# Softhypen word joiner.  At this time, I'm trying to join
# words broken by &shy;\n and possibly some additional
# selected tags.  Could be extended.
join_hyphen_in_words = True

# ------------------ Abbreviation Expander for Indexing. ---------------
# This is to handle abbreviation tags.  I have seen two types:
#       <abbr expan="en">&emacr;</abbr>
#       <abbr expan="Valerius Maximus">Val. Max.</abbr>
# For now, lets's try the first.
abbrev_expand = True

# ---------------------- Flatten Ligatures for Indexing --------------
# Convert SGML ligatures to base characters for indexing.
# &oelig; = oe.  Leave this on.  At one point we should think
# Unicode, but who knows if this is important.
flatten_ligatures = True

# Define a list of strings which mark the end of a sentence.
# Note that this list will be added to the current one which is [".", "?", "!"]
sentence_breakers = [";",u"\u00b7"]

# Define which punctuation should be flagged as such. This should NOT include
# any punctuation which mark sentence breaks. Use regex to match characters.
punctuation = ""

# Define a language for the POS tagger. For language available, see Spacy documentation.
# You will need to install the relevant language and use the proper language code in the value
# below. If empty string, no tagger is run.
# Note that the tagger has an non-trival impact on parse time.
pos_tagger = ""


###########################################
####### ADVANCED CUSTOMIZATIONS ###########
###########################################

# Some custom interals for just this config file

if not lexicon_db:
    lexicon_db = philo4classics + "/extras/lexicon.db"

# This is where you define your own parser which needs to have the same signature
# as the one located in python/philologic/Parser.py
import sys, os

if not os.path.exists(philo4classics):
    print("Your specified philo4classics path (%s) does not exist." % philo4classics)
    sys.exit()
sys.path.append(philo4classics + "/load")

abbrevs_urns = {}
with open (philo4classics + "/custom_functions/" + abbrevs_file) as f:
    abbrevs_content = f.readlines()
    for line in abbrevs_content:
        fields = line.split("\t")
        #filename = fields[2]
        urn = fields[-1].strip()
        abbrev = fields[0]
        for filename in range(2,4):
            if fields[filename]:
                abbrevs_urns[fields[filename]] = [abbrev, urn]

try:
    import ClassicsPostFilters
    import ClassicsLoadFilters
    import ClassicsParser
except ModuleNotFoundError as err:
    print("One or more philo4classics modules seem to be missing: %s." % err)
    print("Please verify that all three are present in %s/ ." % philo4classics)
    sys.exit()

parser_factory = ClassicsParser.XMLParser
parser_factory.abbrevs_urns = abbrevs_urns
post_filters = ClassicsPostFilters.PerseusPostFilters
load_filters = ClassicsLoadFilters.set_load_filters(lexicon_db=lexicon_db)
