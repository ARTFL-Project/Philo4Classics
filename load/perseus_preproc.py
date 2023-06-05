#!/usr/bin/env python

import philologic.shlaxtree as st
import codecs
import sys
import os
import re
import string
import sqlite3

import os,sys,re
from lxml import etree
#import xml.etree.ElementTree as etree
#from StringIO import StringIO
from io import StringIO

def parse_file(fn):
    fh = open(fn)
    doc = fh.read()
#        tree = etree.fromstring(doc)
    #print tree
    it = etree.iterparse(StringIO(doc))
    for _, el in it:
        if '}' in el.tag:
            el.tag = el.tag.split('}', 1)[1]  # strip all namespace
    root = it.root
    return(root)

def preproc(filenames,db):
    dbh = sqlite3.connect(db)
    all_data = []
    for i,fn in enumerate(filenames):
        base_fn = os.path.basename(fn)
        try:
            tree = parse_file(fn)
        except:
            print("\nPARSE ERROR ON: %s \n %s" % (fn,sys.exc_info()[:2]))
            continue
        data = {"filename":os.path.basename(fn)}
        abbrev = ""

        dbc = dbh.cursor()
        dbc.execute("SELECT abbrev FROM abbreviations WHERE filename = ?;",(base_fn,))
        row = dbc.fetchone()
        if row:
            abbrev = row[0]
        else:
            #print >> sys.stderr, "NO ABBREVIATION FOR ", fn
            print("NO ABBREVIATION FOR %s" % fn, file=sys.stderr)
                    
#        if tree.find(".//author") == None:
#            data["author"] = ""
#        else:
#            data["author"] = tree.find(".//author").text
#            author_n = tree.find(".//author").get("n") or ""
#            abbrev += author_n + " "
#        data["title"] = tree.find(".//title").text
#        title_n = tree.find(".//title").get("n") or ""
#        if title_n:
#            abbrev += title_n
#        else:
#            abbrev = ""
        print("%s ABBREV: %s" %(fn, abbrev))
        data["abbrev"] = abbrev
#        print "\n\t", fn,data["author"],data["title"],"\n"
        refs = tree.find(".//refsDecl")
        if refs is None:
            refs = tree.find(".//refsdecl")
        units = []
    #   print etree.tostring(refs)
        for state in refs:
    #       print etree.tostring(state)
            if state.tag == "step":
                unit = state.attrib["refunit"]
                
            else: unit = state.attrib["unit"]
            if unit == "line" or unit == "card":
                units.append("card")
                units.append("line")
                break
            else:
                units.append(unit)
            
    #   print units
        unit_stack = units[:]
        unit_types = {}
        unit_paths = {}
        text = tree.find(".//text")
        for el in text.iter():
            if el.tag == "l" or el.tag == "lb":
                if "line" in unit_stack:
                    unit = "line"
                    unit_stack.remove(unit)
                    unit_types[unit] = el.tag
                    unit_paths[unit] = "./text//%s" % el.tag               
            else:
                unit_attr = "type"
                if el.tag == "milestone":
                    unit_attr = "unit"
                if unit_attr in el.attrib:
                    if el.attrib[unit_attr] in unit_stack:
                        unit = el.attrib[unit_attr]
                        unit_stack.remove(unit)
                        unit_types[unit] = el.tag
                        unit_paths[unit] = "./text//%s[@%s='%s']" % (el.tag,unit_attr,unit)
                        if len(unit_stack) == 0:
                            break
                        #   print i,fn,tre
        
        data["options"] = {"xpaths":[("doc",".")] }

        divtypes = ["div1","div2","div3"]
        divt = 0
        for u in units:            
            if u in unit_stack:
                print("%s MISSING: %s" % (fn, u))
                continue
#            print unit_paths[u] 
            if u == "line":            
                data["options"]["xpaths"].append( ("page",unit_paths[u]) )
                break
            data["options"]["xpaths"].append( (divtypes[divt],unit_paths[u]) )
            divt += 1
            if divt == 3: break
        print ("%s %s" % (fn, unit_paths))
        all_data.append(data)
    #print "sorting"
    all_data.sort(reverse=False,key=lambda d: (d['filename']) )
    return all_data
    
if __name__ == "__main__":
    all_data = preproc(sys.argv[1:])    
    for d in all_data:                                                                                                                                                                                                               
        #print d['date'],d['author'],d['title'],d['text_genre'],d['auth_gender'],d['period'],d['publisher'],d['pub_place'],d['pub_date'],d['editor'],d['author_dates'],d['identifiers'],d['collection'],d['extent'],d['notes'],d['keywords'],d['filename']  
        print(d['filename'],d['author'],d['title'])
