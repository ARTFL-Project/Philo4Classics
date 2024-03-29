#!/usr/bin/env python3
"""Navigate inside objects"""

import re, sys

from .citations import citation_links, citations
from .get_text import get_text_obj
from philologic.runtime.DB import DB
from .cts_tools import get_prev_next_urn, get_philo_id_from_urn


def generate_text_object(request, config, note=False):
    """Return text object given an philo_id"""
    # verify this isn't a page ID or if this is a note
    if len(request.philo_id.split()) == 9 and note is not True:
        width = 9
    else:
        width = 7
    db = DB(config.db_path + "/data/", width=width)
    if note:
        target = request.target.replace("#", "")
        doc_id = request.philo_id.split()[0] + " %"
        cursor = db.dbh.cursor()
        cursor.execute("select philo_id from toms where id=? and philo_id like ? limit 1", (target, doc_id))
        philo_id = cursor.fetchall()[0]["philo_id"].split()[:7]
        obj = db[philo_id]
    else:
        try:
            obj = db[request.philo_id]
        except ValueError:
            obj = db[" ".join(request.path_components)]
        philo_id = obj.philo_id
    if width != 9:
        while obj["philo_name"] == "__philo_virtual" and obj["philo_type"] != "div1":
            philo_id.pop()
            obj = db[philo_id]
    philo_id = list(obj.philo_id)
    while int(philo_id[-1]) == 0:
        philo_id.pop()
    text_object = {"query": dict([i for i in request]), "philo_id": " ".join([str(i) for i in philo_id])}
    text_object["prev"] = neighboring_object_id(db, obj.prev, width)
    text_object["next"] = neighboring_object_id(db, obj.next, width)

    if text_object["prev"] == "":
        prev_text = get_prev_next_urn(obj["cts_urn"])[0]
        prev_text = get_philo_id_from_urn(db, prev_text)
        text_object["prev"] = neighboring_object_id(db, prev_text, width)

    if text_object["next"] == "":
        next_text = get_prev_next_urn(obj["cts_urn"])[1]
        next_text = get_philo_id_from_urn(db, next_text)
        text_object["next"] = neighboring_object_id(db, next_text, width)

    metadata_fields = {}
    for metadata in db.locals["metadata_fields"]:
        metadata_fields[metadata] = obj[metadata]
    text_object["metadata_fields"] = metadata_fields
    #print(metadata_fields, file=sys.stderr)
    if width != 9:
        citation_hrefs = citation_links(db, config, obj)
        citation = citations(obj, citation_hrefs, config, report="navigation")
    else:
        db = DB(config.db_path + "/data/", width=7)
        doc_obj = db[obj.philo_id[0]]
        citation_hrefs = citation_links(db, config, doc_obj)
        citation = citations(doc_obj, citation_hrefs, config, report="navigation")
    #print(citation, file=sys.stderr)
    text_object["citation"] = citation
    text, imgs = get_text_obj(obj, config, request, db.locals["token_regex"], note=note)
    if config.navigation_formatting_regex:
        for pattern, replacement in config.navigation_formatting_regex:
            text = re.sub(r"%s" % pattern, "%s" % replacement, text)
    text_object["text"] = text
    text_object["imgs"] = imgs
    try:
        text_object["translation"] = "%squery?report=bibliography&method=proxy&cts_urn=%s&head=%s" % (config.translation_dbname, metadata_fields["cts_urn"], metadata_fields["head"])
        if 'greek' in metadata_fields["cts_urn"]: text_object["translation_lang"] = "Greek"
        if 'latin' in metadata_fields["cts_urn"]: text_object["translation_lang"] = "Latin"
    except:
        text_object["translation"] = ""
    return text_object

def neighboring_object_id(db, philo_id, width):
    """Get neighboring object ID"""
    if not philo_id:
        return ""
    philo_id = philo_id.split()[:width]
    while philo_id[-1] == "0":
        philo_id.pop()
    philo_id = str(" ".join(philo_id))
    obj = db[philo_id]
    if obj["philo_name"] == "__philo_virtual" and obj["philo_type"] != "div1":
        # Remove the last number (1) in the philo_id and point to one object
        # level lower
        philo_id = " ".join(philo_id.split()[:-1])
    #print(philo_id, file=sys.stderr)
    return philo_id
