#!/usr/bin/env python3

import re
import sys
import json

#from .citations import citations, citation_links
#from .get_text import get_concordance_text
from philologic.runtime.DB import DB
#from philologic.runtime import generate_text_object
sys.path.append("..")
from philologic.runtime.get_text import get_text
from philologic.runtime.HitList import CombinedHitlist
from .cts_tools import parse_request, validate_request, parse_urn, get_cite_from_urn, clean_text, XML_validate, decrement_level, get_parent_level, get_combined_level

# custom response
xmlresponse='<>%s</response>'

# API XML
error_response='<cts:%s xmlns:m="http://mulberrytech.com/xslt/util" xmlns:cts="http://chs.harvard.edu/xmlns/cts3" xmlns:tei="http://www.tei-c.org/ns/1.0"><cts:request><cts:requestName>%s</cts:requestName></cts:request><CTSError><message>%s</message><code>%s</code></CTSError></cts:%s>'
xmlinventory='<TextInventory xmlns="http://chs.harvard.edu/xmlns/cts3/ti" xmlns:dc="http://purl.org/dc/elements/1.1/" tiversion="3.0.rc1">%s</TextInventory>'
xmltextgroup='<textgroup projid="%s" urn="%s"><groupname xml:lang="eng">%s</groupname>#XML#</textgroup> '
xmlwork='<work projid="%s" urn="%s" xml:lang="%s"><title xml:lang="eng">%s</title><edition><label>%s</label><online docname="%s">#XML#</online></edition></work>'
xmlrequest='<request><requestName>%s</requestName><requestUrn>%s</requestUrn></request>'
xmlgetpassage='<cts:GetPassage xmlns:m="http://mulberrytech.com/xslt/util" xmlns:cts="http://chs.harvard.edu/xmlns/cts3" xmlns:tei="http://www.tei-c.org/ns/1.0"><cts:request><cts:requestName>GetPassage</cts:requestName><cts:requestUrn>%s</cts:requestUrn><cts:psg>%s</cts:psg><cts:workUrn>%s</cts:workUrn><cts:groupname>%s</cts:groupname><cts:title>%s</cts:title><cts:versionInfo>5.0.rc2</cts:versionInfo></cts:request><cts:reply>%s</cts:reply></cts:GetPassage>'

# API Functions
def XML_response(message):
    return xmlresponse % message

def Error_response(err_no, request, message):
    return error_response % (request, request, message, err_no, request) 

def XML_builder(template, content):
    try:
        return template % (tuple(content))
    except:
        return False

def XMLcitationMapping(content):

    # the actual number of citation labels is uncertain, so remove blanks
    content = [i for i in content if i != ""]

    try:
        xmlmapping='<citationMapping>%s</citationMapping>'
        xmlcitation='<citation label="%s" xpath="">#XML#</citation>'
        xmlcontent = "#XML#"
        for citation in content:
           xmlcontent = xmlcontent.replace("#XML#", xmlcitation % citation) 

        #clean up last citation
        xmlcontent = re.sub( r'>#XML#.*?<\/citation>', '/>', xmlcontent, flags=re.S)

        return xmlcontent
    except Exception as err:
        print(err, file=sys.stderr)
        return False

def request_GetCapabilities(cts_config, config, request):
    #needed_fields = ["author", "title", "publisher", "filename"]
    db = DB(config.db_path + "/data/")
    content = ["", "", ""]
    #hits = db.query(sort_order=request["sort_order"], **metadata_nohead)
    hits = db.get_all(db.locals["default_object_level"], "")
    gc = ""
    for hit in hits:
        urn = hit["cts_urn"]
        if not urn: continue
        (lang, group, group_id, work, work_id) = parse_urn(urn)
        if not lang or not group or not group_id or not work or not work_id: continue

        groupcontent = [group_id, group, hit["author"]]
        tg = XML_builder(xmltextgroup, groupcontent)

        workcontent = [work_id, work, lang, hit["title"], hit["title"], hit["filename"]]
        w = XML_builder(xmlwork, workcontent)

        citationcontent = []
        for i in range(1,4):
            div = "cts_div" + str(i)
            citationcontent.append(hit[div])
        c = XMLcitationMapping(citationcontent)

        if tg and w and c:
            w = w.replace('#XML#', c)
            tg = tg.replace("#XML#", w)

        gc += tg

    return (0, xmlinventory % gc)

def request_GetValidReff(cts_config, config, request):
    db = DB(config.db_path + "/data/")
    (urn, cite) = get_cite_from_urn(request["urn"])

    metadata = {"cts_urn": urn}
    text = db.query(sort_order="", **metadata)
    
    #get philo_id for text urn
    philo_id = ""
    for t in text: philo_id = t["philo_id"]
    if not philo_id: return (3, "Unknown urn")

    # get all heads for the text
    cursor = db.dbh.cursor()
    text_id = philo_id.split()[0]
    query = 'select * from toms where philo_id LIKE "{0} %" and head !="";'.format(text_id)
    cursor.execute(query)

    requestcontent = ["GetValidReff", request["urn"]]
    gvr = "<GetValidReff>%s<reply><reff>" % (XML_builder(xmlrequest, requestcontent))

    for row in cursor.fetchall():

        # check if a passage was included in the request, in which case, limit the responses to only that section
        if cite:
            if re.match(r'^' + cite + r'\..*$', row["head"]):
                gvr += "<urn>%s:%s</urn>" % (urn, row["head"])
        else:
            #print(row["head"], file=sys.stderr)
            gvr += "<urn>%s:%s</urn>" % (urn, row["head"])

    gvr += "</reff></reply></GetValidReff>"

    return (0, gvr)

def request_GetPassage(cts_config, config, request):

    # check if urn is a passage urn
    (urn, cite) = get_cite_from_urn(request["urn"])
    if cite:
        db = DB(config.db_path + "/data/")
        metadata = {"cts_urn": urn, "head": cite}
        hits = db.query(sort_order="", **metadata)

        #################################################################################
        ### If we get no hits then jump through some hoops to find the correct 'head' ###
        #################################################################################

        # If we have Bekker pages with line numbers, then strip the line numbers
        m = re.match(r'^([0-9]+[a-e]+)[\.0-9]*$', metadata["head"], re.I)
        if m:
            metadata["head"] = m.group(1)

        # first do the search with quotes around the head
        metadata['head'] = '"%s"' % metadata['head']
        hits = db.query(sort_order="", **metadata)

        # Next, check to see if we have final greek-letter-section following a period (Hdt.), exclude final period
        m = re.match(r'^("[1-9\.]+)\.([α-ω]+")$', metadata["head"], re.I)
        if len(hits) == 0 and m:
            metadata["head"] = m.group(1) + m.group(2)

            # Try again
            hits = db.query(sort_order="", **metadata)

        # Query just the text to see whether it is poetry and also grab the abbreviation
        metadata_nohead = metadata.copy()
        del metadata_nohead['head']
        hits = db.query(sort_order="", **metadata_nohead)
        for hit in hits:
            if "poetry" in hit["text_genre"]: have_poetry = True
            else: have_poetry = False
            if hit["abbrev"]: abbrev = hit["abbrev"]

        # try again
        hits = db.query(sort_order="", **metadata)

        # if we got no results from a poetic text, we may need to decrement down to a labeled line number
        #if len(hits) == 0 and have_poetry:
        if len(hits) == 0:
            decrement_count = 0
            decrement_max = 50
            while len(hits) == 0:
                decrement_count += 1
                metadata["head"] = decrement_level(metadata["head"])
                hits = db.query(sort_order="", **metadata)
                # don't do this forever
                if (decrement_count >= decrement_max):
                    break
            cite = metadata["head"]

        # If we get no results, check to see if we have a higher level saved in the head
        if len(hits) == 0 and "." in metadata["head"]:
            metadata_copy = metadata.copy()
            while len(hits) == 0:
                metadata_copy["head"] = get_parent_level(metadata_copy["head"])
                if metadata_copy["head"]:
                    hits = db.query(sort_order="", **metadata_copy)
                else: break

        # If we still get no results, check to see if we are dealing with a head combining section and text
        if len(hits) == 0:
            # first see if we get a hit by combining URN work number
            metadata_copy = metadata.copy()
            (urn_head, abbrev_head) = get_combined_level(metadata["cts_urn"], metadata["head"], abbrev)
            metadata_copy["head"] = urn_head
            hits = db.query(sort_order="", **metadata_copy)
            # if still no hits, use the work number from the abbreviation
            if len(hits) == 0 and abbrev_head:
                metadata_copy["head"] = abbrev_head
                hits = db.query(sort_order="", **metadata_copy)

        # if we still have no hits then search without quotes
        if len(hits) == 0:
            metadata['head'] = metadata['head'].strip('"')
            hits = db.query(sort_order="", **metadata)

        #################################################################################

        for hit in hits:
            # first get the cts_divs from the doc level 
            philo_id = hit["philo_id"]
            philo_doc = ' '.join([philo_id.split(' ')[0]] + ['0' for i in philo_id.split(' ')[1:]])
            cursor = db.dbh.cursor()
            query = 'select * from toms where philo_id == "%s";' % philo_doc
            cursor.execute(query)
            (cts_div1, cts_div2, cts_div3) = cursor.fetchone()[14:17]

            # find out at what div level we are fetching xml text
            # so that we know what levels above it to wrap around
            # the fetched xml
            div_level = len([i for i in philo_id.split(' ') if i != '0']) - 1

            div_wrapper = "#XML"
            tei_wrapper = "<tei:TEI><tei:text><tei:body>#XML</tei:body></tei:text></tei:TEI>"

            # create the div wrapper
            #print(div_level, file=sys.stderr)
            for i in list(reversed(range(div_level)))[:-1]:
                div_type = vars()["cts_div" + str(i)]
                div_wrapper = '<tei:div type="%s">' % (div_type) + div_wrapper + '</tei:div>'

            if hit["head"].startswith(cite) and hit["cts_urn"] == urn:
                philo_id = hit["philo_id"]
                text = get_text(hit, hit["start_byte"], hit["end_byte"] - hit["start_byte"], config.db_path).decode()

                # clean up and put in div and tei wrappers
                text = clean_text(text)
                text = div_wrapper.replace("#XML", text)
                text = tei_wrapper.replace("#XML", text)

                requestcontent = [request["urn"], cite, urn, hit["author"], hit["title"], text]
                gp = XML_builder(xmlgetpassage, requestcontent)
                gp = XML_validate(gp, fix=True)
                return (0, gp)
        return (3, "Invalid passage references or urn")
    else:
        return (3, "No Passage Specified")

    ##get philo_id for text urn
    #for t in text: philo_id = t["philo_id"]


def cts_results(request, cts_config, config):
    request = parse_request(request)
    err_code = validate_request(request)

    if not err_code:
        (err_code, response) = globals()["request_" + request["request"]](cts_config, config, request)
        if not err_code:
            return '<?xml version="1.0"?>' + response
        else:
            return Error_response(err_code, request["request"], response)
    else:
        return Error_response(err_code, "request", "Invalid Request")
