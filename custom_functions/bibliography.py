#!/usr/bin/env python3

"""Bibliography results"""


from philologic.runtime.pages import page_interval
#from philologic.runtime.citations import citations, citation_links
from .citations import citations, citation_links
#from philologic.runtime.get_text import get_text_obj
from .get_text import get_text_obj
from philologic.runtime.DB import DB
from .customRuntime import bib_citation_format
from .cts_tools import decrement_level, get_parent_level, get_combined_level
import sys,re

def bibliography_results(request, config):
    """Fetch bibliography results"""
    db = DB(config.db_path + "/data/")

    #have_poetry = False 
    abbrev = ""
    decrement_count = 0
    decrement_max = 50

    if request.no_metadata:
        hits = db.get_all(db.locals["default_object_level"], request["sort_order"])
    else:

        if "head" in request.metadata:
            # This regex will strip line numbers from Bekker pages, and group 1 will exclude them.
            m = re.match(r'^([0-9]+[a-e]+)[\.0-9]*$', request.metadata["head"], re.I)
            if m:
                request.metadata["head"] = m.group(1)

	    # first do the search with quotes around the head
            request.metadata['head'] = '"%s"' % request.metadata['head']
        hits = db.query(sort_order=request["sort_order"], **request.metadata)

        ## If 'head' is in the metadata, then first query just the text to see whether it is poetry
        ## and also grab the abbreviation
        #if "head" in request.metadata:
        #    metadata_nohead = request.metadata.copy()
        #    del metadata_nohead['head']
        #    hits = db.query(sort_order=request["sort_order"], **metadata_nohead)
        #    for hit in hits:
        #        if "poetry" in hit["text_genre"]:
        #            have_poetry = True
        #        else:
        #            have_poetry = False
        #        if hit["abbrev"]: abbrev = hit["abbrev"]
   
        ## if we got no results from a poetic text, we may need to decrement down to a labeled line number
        #if len(hits) == 0 and have_poetry and ("cts_urn" in request.metadata or "abbrev" in request.metadata):
        if len(hits) == 0 and ("cts_urn" in request.metadata or "abbrev" in request.metadata):
            while len(hits) == 0:
                decrement_count += 1
                request.metadata["head"] = decrement_level(request.metadata["head"])
                hits = db.query(sort_order=request["sort_order"], **request.metadata)
                # don't do this forever
                if (decrement_count >= decrement_max):
                    break
            decrement_count = 0

        # If we get no results, check to see if we have a higher level saved in the head
        if "head" in request.metadata:
            if len(hits) == 0 and "." in request.metadata["head"] and ("cts_urn" in request.metadata or "abbrev" in request.metadata):
                metadata_copy = request.metadata.copy()
                while len(hits) == 0:
                    metadata_copy["head"] = get_parent_level(metadata_copy["head"])
                    if metadata_copy["head"]:
                        hits = db.query(sort_order=request["sort_order"], **metadata_copy)
                    else: break

            # If we still get no results, check to see if we are dealing with a head combining section and text
            if len(hits) == 0 and ("cts_urn" in request.metadata or "abbrev" in request.metadata):
                # first see if we get a hit by combining URN work number
                metadata_copy = request.metadata.copy()
                (urn_head, abbrev_head) = get_combined_level(request.metadata["cts_urn"], request.metadata["head"], abbrev)
                metadata_copy["head"] = urn_head
                hits = db.query(sort_order=request["sort_order"], **metadata_copy)
                # if still no hits, use the work number from the abbreviation
                if len(hits) == 0 and abbrev_head:
                    metadata_copy["head"] = abbrev_head
                    hits = db.query(sort_order=request["sort_order"], **metadata_copy)

        # finally, if we still have no results and we have a head, then search it unquoted
       	if "head" in request.metadata and len(hits) == 0:
            request.metadata['head'] = request.metadata['head'].strip('"')
            hits = db.query(sort_order=request["sort_order"], **request.metadata)

    if (
        request.simple_bibliography == "all"
    ):  # request from simple landing page report which gets all biblio in load order
        hits.finish()
        start = 1
        end = len(hits)
        page_num = end
    else:
        start, end, page_num = page_interval(request.results_per_page, hits, request.start, request.end)
    bibliography_object = {
        "description": {"start": start, "end": end, "n": page_num, "results_per_page": request.results_per_page},
        "query": dict([i for i in request]),
        "default_object": db.locals["default_object_level"],
    }
    results = []
    result_type = "doc"

    for hit in hits[start - 1 : end]:
        citation_hrefs = citation_links(db, config, hit)
        metadata_fields = {}
        for metadata in db.locals["metadata_fields"]:
            metadata_fields[metadata] = hit[metadata]

        # get custom bib citation format
        author = ""
        title = ""
        (author, title) = bib_citation_format(hit["filename"])

        citation = citations(hit, citation_hrefs, config, report="bibliography")

#        if author in ["NT", "Septuagint", "HH"]:
#            citation[0]["label"] = ' '.join([author, title]) + citation[0]["label"]
#        else:
#            citation[0]["label"] = ' '.join([author, title])
        #citation[0]["label"] = ' '.join([author, title])

        # sanitize section numbers and do not display div1s if they are non-numeric
        new_citation = []
        had_doc = False
        for cit in citation:
            #if "grc" in cit["label"]:
            #    try:
            #        cit["label"] = cit["label"].split("perseus-grc")[1]
            #    except:
            #        cit["label"] = cit["label"].split("grc")[1]

            #if "lat" in cit["label"]:
            #    try:
            #        cit["label"] = cit["label"].split("perseus-lat")[1]
            #    except:
            #        if author not in ["NT"]:
            #            cit["label"] = cit["label"].split("lat")[1]

            if cit["object_type"] == "doc":
                had_doc = True
                cit["href"] = citation_hrefs["doc"]

            if had_doc:
                if ((cit["label"].isnumeric() and cit["object_type"] == "div1") or cit["object_type"] != "div1") or not title:
                    new_citation.append(cit)
            else:
                new_citation.append(cit)

        result_type = hit.object_type
        #if request.simple_bibliography == "all":
        #    citation = citations(hit, citation_hrefs, config, report="simple_landing")
        #else:
        #    citation = citations(hit, citation_hrefs, config, report="bibliography", result_type=result_type)

        #print(citation, file=sys.stderr)
        #print(new_citation, file=sys.stderr)
        #print(citation_hrefs, file=sys.stderr)
        if config.dictionary_bibliography is False or result_type == "doc":
            results.append(
                {
                    "citation": new_citation,
                    "citation_links": citation_hrefs,
                    "philo_id": hit.philo_id,
                    "metadata_fields": metadata_fields,
                    "object_type": result_type,
                }
            )
        else:
            context = get_text_obj(hit, config, request, db.locals["token_regex"], images=False)
            results.append(
                {
                    "citation": new_citation,
                    "citation_links": citation_hrefs,
                    "philo_id": hit.philo_id,
                    "metadata_fields": metadata_fields,
                    "context": context,
                    "object_type": result_type,
                }
            )
    bibliography_object["results"] = results
    bibliography_object["results_length"] = len(hits)
    bibliography_object["query_done"] = hits.done
    bibliography_object["result_type"] = result_type
    return bibliography_object, hits
