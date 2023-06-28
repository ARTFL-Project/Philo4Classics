#!/usr/bin/env python3
"""Concordance report"""

import re
import sys

from philologic.runtime.pages import page_interval
from .citations import citations, citation_links
#from philologic.runtime.get_text import get_concordance_text
from .get_text import get_concordance_text
from philologic.runtime.DB import DB
from philologic.runtime.HitList import CombinedHitlist
from .customRuntime import bib_citation_format
from .cts_tools import decrement_level, get_parent_level, get_combined_level

def concordance_results(request, config):
    """Fetch concordances results."""
    db = DB(config.db_path + "/data/")

    #have_poetry = False
    abbrev = ""
    decrement_count = 0
    decrement_max = 50

    if request.collocation_type:
        first_hits = db.query(request["q"], request["method"], request["arg"], **request.metadata)
        second_hits = db.query(request["left"], request["method"], request["arg"], **request.metadata)
        hits = CombinedHitlist(first_hits, second_hits)
    else:
        # This regex will strip line numbers from  Bekker pages; group 1 will exclude them.
        if "head" in request.metadata:
            m = re.match(r'^([0-9]+[a-e]+)[\.0-9]*$', request.metadata["head"], re.I)
            if m:
                request.metadata["head"] = m.group(1)

            # first do the search with quotes around the head
            request.metadata['head'] = '"%s"' % request.metadata['head']
        hits = db.query(request["q"], request["method"], request["arg"], sort_order=request["sort_order"], **request.metadata)

        # If no results, and 'head' is in the metadata, then first query just the text to see whether it is poetry
        if len(hits) == 0 and "head" in request.metadata and "cts_urn" in request.metadata:
            metadata_nohead = request.metadata.copy()
            del metadata_nohead['head']
            hits = db.query(sort_order=request["sort_order"], **metadata_nohead)
            for hit in hits:
                if "poetry" in hit["text_genre"]:
                    have_poetry = True
                else:
                    have_poetry = False
                abbrev = hit["abbrev"]

            # if we got no results from a poetic text, we may need to decrement down to a labeled line number
            if len(hits) == 0 and have_poetry:
                while len(hits) == 0:
                    decrement_count += 1
                    request.metadata["head"] = decrement_level(request.metadata["head"])
                    hits = db.query(request["q"], request["method"], request["arg"], sort_order=request["sort_order"], **request.metadata)
                    # don't do this forever
                    if (decrement_count >= decrement_max):
                        break
                decrement_count = 0

            # If we get no results, check to see if we have a higher level saved in the head
            if len(hits) == 0 and "." in request.metadata["head"]:
                while len(hits) == 0:
                    request.metadata["head"] = get_parent_level(request.metadata["head"])
                    if request.metadata["head"]:
                        hits = db.query(request["q"], request["method"], request["arg"], sort_order=request["sort_order"], **request.metadata)
                    else: break

            # If we still get no results, check to see if we are dealing with a head combining section and text
            if len(hits):
                # first see if we get a hit by combining URN work number
                metadata_copy = request.metadata.copy()
                (urn_head, abbrev_head) = get_combined_level(request.metadata["cts_urn"], request.metadata["head"], abbrev)
                metadata_copy["head"] = urn_head
                hits = db.query(request["q"], request["method"], request["arg"], sort_order=request["sort_order"], **metadata_copy)
                # if still no hits, use the work number from the abbreviation
                if len(hits) == 0:
                    metadata_copy["head"] = abbrev_head
                    hits = db.query(request["q"], request["method"], request["arg"], sort_order=request["sort_order"], **metadata_copy)
            
            # if we still have no hits and we have a 'head', then search without quotes
            if "head" in request.metadata and len(hits) == 0:
                request.metadata['head'] = request.metadata['head'].strip('"')
                hits = db.query(request["q"], request["method"], request["arg"], sort_order=request["sort_order"], **request.metadata)

    start, end, page_num = page_interval(request["results_per_page"], hits, request.start, request.end)

    concordance_object = {
        "description": {"start": start, "end": end, "results_per_page": request.results_per_page},
        "query": dict([i for i in request]),
        "default_object": db.locals["default_object_level"],
    }

    formatting_regexes = []
    if config.concordance_formatting_regex:
        for pattern, replacement in config.concordance_formatting_regex:
            compiled_regex = re.compile(r"%s" % pattern)
            formatting_regexes.append((compiled_regex, replacement))
    results = []
    for hit in hits[start - 1 : end]:
        citation_hrefs = citation_links(db, config, hit)
        metadata_fields = {}
        for metadata in db.locals["metadata_fields"]:
            metadata_fields[metadata] = hit[metadata]

        # get custom bib citation format
        author = ""
        title = ""
        (author, title) = bib_citation_format(hit["filename"])
        if title:
            if not re.match(r'^.*\.', title):
                title += " . "

        citation = citations(hit, citation_hrefs, config, report="concordance")

#        if author in ["NT", "Septuagint", "HH"]:
#            citation[0]["label"] = ' '.join([author, title]) + citation[0]["label"]
#        else:
#            citation[0]["label"] = ' '.join([author, title])
        if author or title:
            citation[0]["label"] = ' '.join([author, title])

        # sanitize section numbers and do not display div1s if they are non-numeric
        new_citation = []
        had_doc = False
        for cit in citation:
            if "grc" in cit["label"]:
                try:
                    cit["label"] = cit["label"].split("perseus-grc")[1]
                except:
                    cit["label"] = cit["label"].split("grc")[1]

            if "lat" in cit["label"]:
                try:
                    cit["label"] = cit["label"].split("perseus-lat")[1]
                except:
                    if author not in ["NT"]:
                        cit["label"] = cit["label"].split("lat")[1]

            if cit["object_type"] == "doc": had_doc = True

            if had_doc:
                if ((cit["label"].isnumeric() and cit["object_type"] == "div1") or cit["object_type"] != "div1") or not title:
                    new_citation.append(cit)
            else:
                new_citation.append(cit)

        context = get_concordance_text(db, hit, config.db_path, config.concordance_length)
        if formatting_regexes:
            for formatting_regex, replacement in formatting_regexes:
                context = formatting_regex.sub(r"%s" % replacement, context)
        result_obj = {
            "philo_id": hit.philo_id,
            "citation": new_citation,
            "citation_links": citation_hrefs,
            "context": context,
            "metadata_fields": metadata_fields,
            "bytes": hit.bytes,
        }
        results.append(result_obj)
    concordance_object["results"] = results
    concordance_object["results_length"] = len(hits)
    concordance_object["query_done"] = hits.done
    return concordance_object
