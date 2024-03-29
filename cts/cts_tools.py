#!/usr/bin/env python3

import re
import sys
import json

def XML_validate(xmlcontent, fix=False):

    have_bs4 = False
    try:
        from bs4 import BeautifulSoup
        have_bs4 = True
    except ImportError:
        pass
    
    import xml.dom.minidom
    try:
        dom = xml.dom.minidom.parseString(xmlcontent) # or xml.dom.minidom.parseString(xml_string)
        return xmlcontent
    except Exception as e:
        if not fix:
            return XML_response(e)
        elif have_bs4:
            xmlcontent = str(BeautifulSoup(xmlcontent,'xml'))
            xmlcontent = re.sub(r'<\?xml version.*?>', '', xmlcontent, flags=re.S)
            return xmlcontent
        else:
            if "mismatched tag" in str(e):
                tag_minder =[] 
                for tag_obj in re.finditer(r'<.*?>', xmlcontent):
                    tag = tag_obj.group(0)
                    if not re.match(r'^.*?/>', tag, re.M):
                        m = re.match(r'<([^/]*?)[ >]', tag)
                        if m:
                            tag_minder.append(m.group(1))
                        m = re.match(r'</(.*?)[ >]', tag)
                        if m:
                            if tag_minder[-1] == m.group(1):
                                tag_minder.pop()
                                pass
                            else:
                                # We have a tag mismatch; determine whether we are missing an opening tag or a closing tag
                                if any(x for x in tag_minder if m.group(1) == x):
                                    # add the missing closing tag and pop its opening tag
                                    tag_to_add =  "</" + tag_minder.pop() + ">"
                                    xmlcontent1 = xmlcontent[:tag_obj.start() - len(tag_to_add)] + tag_to_add + xmlcontent[tag_obj.start() - len(tag_to_add):] 
                                    xmlcontent2 = xmlcontent[:tag_obj.start()] + tag_to_add + xmlcontent[tag_obj.start():] 
                                    try:
                                       dom = xml.dom.minidom.parseString(xmlcontent1) # or xml.dom.minidom.parseString(xml_string)
                                       xmlcontent = xmlcontent1
                                    except Exception as e: 
                                       xmlcontent = xmlcontent2
                                    # don't forget to pop the legitimate closing tag
                                    tag_minder.pop()
                                else:
                                    # remove the extraneous closing tag
                                    xmlcontent = xmlcontent[:tag_obj.start()] + xmlcontent[tag_obj.end():] 
              
                return xmlcontent

def parse_request(request):
    parsed_request = {}
    request = request.split("&")
    for arg in request:
        (k, v) = arg.split("=")
        parsed_request[k] = v
    return parsed_request

def validate_request(request):
    valid_requests = ["GetCapabilities", "GetValidReff", "GetPassage", "GetFirstUrn", "GetPrevNextUrn"]
    valid_params = ["request", "urn", "level", "context"]

    required_params = {"GetCapabilities": [], "GetValidReff": ["urn"], "GetPassage": ["urn"], "GetFirstUrn": ["urn"], "GetPrevNextUrn": ["urn"]}

    if not isinstance(request, dict):
        return 1
    else:
        needed_params = []
        for k in request.keys():
            if k not in valid_params or (request[k] not in valid_requests and k != "urn"):
                return 1

            # check for required params
            if request[k] in required_params:
                needed_params = required_params[request[k]]

            if k in needed_params: needed_params.remove(k)

            # Specific tests
            if k == "level":
                if not k.isnumeric(): return 4
            if k == "urn":
                (dummy1, dummy2) = get_cite_from_urn(request[k])
                if not dummy1: return 2
                #if dummy1 and dummy2:
                #    if not dummy2.isnumeric(): return 3

    if len(needed_params) > 0: return 1
    return 0

def parse_urn(urn):
    fields = urn.split(":")

    lang = get_lang(fields[2])

    try:
        group = ':'.join(fields[:4]).split('.')[0]
    except Exception as e:
        group = False
        error_log(e, "Malformed group in URN %s" % urn)

    try:
        group_id = ':'.join(fields[2:4]).split('.')[0]
    except Exception as e:
        group_id = False
        error_log(e, "Malformed group id in URN %s" % urn)

    try:
        work = urn
    except Exception as e:
        work = False
        error_log(e, "Malformed work in URN %s" % urn)

    try:
        work_id = ':'.join([fields[2], fields[3].split('.')[1]])
    except Exception as e:
        work_id = False
        error_log(e, "Malformed work id in URN %s" % urn)

    return (lang, group, group_id, work, work_id)

def perseus_to_cts_urn(urn):
    urn_match = re.match(r'^.*?:([a-z]+),([0-9]+),([0-9]+):([0-9:a-eα-ω]+)$', urn, re.I)
    if urn_match:
        lang = {'stoa':'latin', 'phi':'latin', 'tlg':'greek', 'pap':'greek'}
        collection = urn_match.group(1)

        # check if we have a known collection
        if collection not in lang.keys(): return urn

        # get rest of components of the urn
        group = urn_match.group(2)
        work = urn_match.group(3)
        passage = urn_match.group(4).replace(":",".")

        new_urn = "urn:cts:%sLit:%s%s.%s%s:%s" % (lang[collection], collection, group, collection, work, passage)
        return new_urn

    return urn

def get_cite_from_urn(urn):

    try:
        # first check for a URN with an edition
        urn_match = re.match(r'(urn:cts:\w+:\w+\.\w+\).[\w-]+:*([0-9\.a-eα-ω]+)*', urn, re.I)
        urn = urn_match.group(1)
        cite = urn_match.group(2)
    except Exception as e:
        try:
            # if the above fails, then we have a URN without edition
            urn_match = re.match(r'(urn:cts:\w+:\w+\.\w+):*([0-9\.a-eα-ω]+)*', urn, re.I)
            urn = urn_match.group(1)
            cite = urn_match.group(2)
        except Exception as e:
            # not a valid urn
            return (False, False)

    if urn and cite: return (urn, cite)
    elif urn and not cite: return (urn, False)

    return (False,False)

def clean_text(text):
    # get rid of word tags
    new_text = re.sub(r'<\/*w.*?>', '', text, flags=re.S)
    return new_text

def get_philo_id_from_urn(db, urn):
    if not urn: return ""
    metadata = {"cts_urn": urn}
    hits = db.query(sort_order="", **metadata)
    for hit in hits:
        return hit["philo_id"]
    return ""

def get_prev_next_urn(urn):
    if not urn:
        return ("","")
    fields = urn.split(":")
    textgroup = fields[-1].split(".")[0]
    text = fields[-1].split(".")[1]

    prefix = ''.join([s for s in text if s.isalpha()])
    text_num = text.split(prefix)[1]

    prev_text = prefix + '%03d' % (int(text_num) - 1)
    next_text = prefix + '%03d' % (int(text_num) + 1)

    if int(text_num) - 1 != 0:
        prev_urn = ':'.join(fields[:-1]) + ":" + textgroup + "." + prev_text
    else:
        prev_urn = ""
    next_urn = ':'.join(fields[:-1]) + ":" + textgroup + "." + next_text

    return(prev_urn, next_urn)

def decrement_level(head):
    has_quotes = False
    if '"' in head:
        has_quotes = True
        head = head.strip('"')

    try:
        new_head = head.split(".")
        line = int(new_head[-1])
        if line > 0:
            line = line - 1
        new_head[-1] = str(line)
    except Exception as e:
        new_head = head.split(".")
    if has_quotes:
        return '"%s"' % ".".join(new_head)
    else:
        return '%s' % ".".join(new_head)

def get_parent_level(head):
    head = head.strip('"')
    new_head = head.split(".")
    parent = new_head[:-1]
    if len(parent) > 0:
        return '"%s"' % '.'.join(parent)
    else:
        return False

def get_combined_level(urn, head, abbrev):
    head = head.strip('"')
    urn = urn.strip('"')
    # first combine urn work number and head
    text_num = re.match(r'^.*\.[a-z]+0*([0-9]+)$', urn, re.I)
    if text_num:
        urn_head = '"%s"' % (text_num.group(1) + "." + head)
    else:
        urn_head = False

    # next, if we have an abbrev, combine with abbrev
    text_num = re.match(r'^.* ([0-9]+)$', abbrev, re.I)
    if text_num:
        abbrev_head = '"%s"' % (text_num.group(1) + "." + head)
    else:
        abbrev_head = False

    return (urn_head, abbrev_head)

def get_lang(subcollection):

    subcollection_langs = {"greekLit": "grc", "latinLit": "lat", "hebLit": "heb"}
    try:
        return subcollection_langs[subcollection]
    except Exception as e:
        error_log(e, "Unknown subcollection %s" % subcollection)
        return False

def get_cts_divs(hit):
    divs = []
    for i in range(1,4):
        div = "cts_div" + str(i)
        divs.append(hit[div].lower())

    return divs

def error_log(e, msg):
    print('[CTS API Error] %s. Python Response: "%s"' % (msg, e), file=sys.stderr)
