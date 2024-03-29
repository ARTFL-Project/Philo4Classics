#!/usr/bin/env python3
"""Citations"""


from philologic.runtime.link import make_absolute_object_link, make_absolute_query_link
from .customRuntime import get_cts_divs
import sys


def citation_links(db, config, i):
    """ Returns links to a PhiloLogic object and all its ancestors."""
    if config.skip_table_of_contents is False:
        doc_href = make_absolute_object_link(config, i.philo_id[:1]) + "/table-of-contents"
    else:
        doc_href = make_absolute_object_link(config, i.philo_id[:1], i.bytes)
    div1_href = make_absolute_object_link(config, i.philo_id[:2], i.bytes)
    div2_href = make_absolute_object_link(config, i.philo_id[:3], i.bytes)
    div3_href = make_absolute_object_link(config, i.philo_id[:4], i.bytes)
    page_href = make_absolute_object_link(config, i.page.philo_id, i.bytes)
    try:
        line_href = make_absolute_object_link(config, i.line.philo_id, i.bytes)
    except AttributeError:
        line_href = ""

    links = {
        "doc": doc_href,
        "div1": div1_href,
        "div2": div2_href,
        "div3": div3_href,
        "para": "",
        "page": page_href,
        "line": line_href,
    }

    for metadata_type in db.locals["metadata_types"].values():
        if metadata_type == "para":
            links["para"] = make_absolute_object_link(config, i.philo_id[:5], i.bytes)
            break
    return links


def citations(hit, citation_hrefs, config, report="concordance", citation_type=None, result_type="doc"):
    """ Returns a representation of a PhiloLogic object and all its ancestors
        suitable for a precise citation. """
    if citation_type is None:
        citation_type = config[report + "_citation"]
    citation = []
    for citation_object in citation_type:
        cite = {}
        cite["label"] = get_label(config, hit, citation_object)
        if cite["label"]:
            cite["prefix"] = citation_object["prefix"]
            cite["suffix"] = citation_object["suffix"]
            cite["separator"] = citation_object["separator"]
            cite["href"] = cite_linker(hit, citation_object, citation_hrefs, config, report)
            cite["style"] = citation_object["style"]
            cite["object_type"] = citation_object["object_level"]
            citation.append(cite)
    return citation

def get_label(config, hit, citation_object):
    """Get metadata labels"""
    label = ""
    if citation_object["object_level"] == "doc":
        label = hit[citation_object["field"]].strip() or hit["abbrev"]
    
    # for divs, make sure that the current level's type is one listed in the refdecl, which are saved in cts_divs in the doc level
    valid_type = False
    obj_type = getattr(hit, citation_object["object_level"]).type.lower()
    obj_subtype = getattr(hit, citation_object["object_level"]).subtype.lower()
    #print(citation_object["object_level"], file=sys.stderr)
    #print(obj_type, file=sys.stderr)
    #print(get_cts_divs(hit), file=sys.stderr)
    #print("Div1 type: " + hit.div1.philo_type, file=sys.stderr)
    #print("Div1 head: " + hit.div1.head, file=sys.stderr)

    # accommodate Bekker and Stephanus sections
    if obj_type in ['bekker', 'stephanus']: obj_type = 'section'
    if obj_subtype in ['bekker', 'stephanus']: obj_type = 'section'

    # first check if we're dealing with a special case for cards
    if obj_type in get_cts_divs(hit) or obj_subtype in get_cts_divs(hit) or hit.div3.philo_type != "div3" or (hit.div3.head == "" and hit.div2.type == "card") or config.dictionary:
        valid_type = True

    if citation_object["object_level"].startswith("div") and valid_type:
        if citation_object["field"] == "head":
            if citation_object["object_level"] == "div1":
                label = get_div1_name(hit)
                if label == "Text" and hit.div1.philo_id[-1] == 0:  # This is a fake div1 of id 0
                    label = ""
            else:
                div1_name = get_div1_name(hit)
                div2_name = get_div2_name(hit)
                div3_name = ""
                if hit.div3.philo_type != hit.div2.philo_type:
                    div3_name = hit.div3.n.strip() or hit.div3.head.split('.')[-1]

                # if the head of the section combines the book number and section,
                # and the book number was already grabbed in the div1, then
                # have div2_name only show the section number in the citation,
                # but make sure that we are not dealing with a range
                if div1_name + "." in div2_name and "-" not in div2_name:
                    div2_name = div2_name.split('.')[-1]

#                div3_name = ""
#                if any(map(str.isdigit, hit.div3.head.strip())):
#                    div3_name = hit.div3.head.strip()
#                else:
#                    div3_name = hit.div3.n.strip()
                if div3_name == div2_name and hit.div3.philo_id[-1] == 0:
                    div3_name = ""
                if div2_name == div1_name and hit.div2.philo_id[-1] == 0:
                    div2_name = ""
                if citation_object["object_level"] == "div2":
                    label = div2_name
                else:
                    label = div3_name
        else:
            label = hit[citation_object["object_level"]][citation_object["field"]].strip()
        if label == "[NA]":
            #if citation_object["object_level"] == "div1":
            #    label = "Section"
            #else:
            #    label = "Subsection"
            label = ""
#    elif citation_object["object_level"] == "para":
#        label = hit[citation_object["field"]].strip().title()
#    elif citation_object["object_level"] == "page":
#        page_num = hit.page[citation_object["field"]]
#        if page_num:
#            try:
#                label = str(page_num)
#            except UnicodeEncodeError:
#                label = page_num.encode("utf-8", "ignore")  # page number is a unicode char
#            label = "page {}".format(label)
    elif citation_object["object_level"] == "line":
        try:
            line = hit.line[citation_object["field"]].strip()
            if line:
                label = "line %s" % str(line)
        except TypeError:
            pass
    return label


def get_div1_name(hit):
    """Get div1 names"""
    label = hit.div1.head
    if not label:
        if hit.div1.philo_name == "__philo_virtual":
            #label = "Section"
            return ""
        else:
            if hit.div1["type"] and hit.div1["n"]:
                label = hit.div1["type"] + " " + hit.div1["n"]
            else:
                label = hit.div1["head"] or hit.div1["type"] or hit.div1["philo_name"] or hit.div1["philo_type"]
    if label:
        try:
            #label = label[0].upper() + label[1:]
            label = label[0] + label[1:]
            label = label.strip()
        except IndexError:
            pass
    return label

def get_div2_name(hit):
    """Get div2 names"""
    label = hit.div2.head or hit.div2.n.strip()
    if not label:
        if hit.div2.philo_name == "__philo_virtual":
            #label = "Sub Section"
            return ""
        else:
            if hit.div2["type"] and hit.div2["n"]:
                label = hit.div2["type"] + " " + hit.div2["n"]
            elif hit.div2["n"]:
                label = hit.div2["n"]
            else:
                label = hit.div2["head"] or hit.div2["type"] or hit.div2["philo_name"] or hit.div2["philo_type"]
    if label:
        try:
            #label = label[0].upper() + label[1:]
            label = label[0] + label[1:]
            label = label.strip()
        except IndexError:
            pass
    return label

def cite_linker(hit, citation_object, citation_hrefs, config, report):
    """Get links"""
    href = None
    if citation_object["link"]:
        if citation_object["object_level"] == "doc":
            if citation_object["field"] == "title" or citation_object["field"] == "filename":
                href = citation_hrefs["doc"]
            elif report == "bibliography" and citation_object["field"] == "head":
                href = make_absolute_object_link(config, hit.philo_id)
            else:
                params = [
                    ("report", "bibliography"),
                    (citation_object["field"], '"%s"' % hit[citation_object["field"]]),
                ]
                href = make_absolute_query_link(config, params)
        else:
            href = citation_hrefs[citation_object["object_level"]]
    return href
