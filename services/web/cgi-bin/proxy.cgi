#!/usr/bin/env python


"""This is a blind proxy that we use to get around browser
restrictions that prevent the Javascript from loading pages not on the
same server as the Javascript.  This has several problems: it's less
efficient, it might break some sites, and it's a security risk because
people can use this proxy to browse the web and possibly do bad stuff
with it.  It only loads pages via http and https, but it can load any
content type. It supports GET and POST requests."""

import urllib2
import cgi
import sys, os

# Designed to prevent Open Proxy type stuff.
allowedHosts = ['sosmet.nerc-bas.ac.uk',
                'geoservices.knmi.nl',
                'api.smartemission.nl',
                'smartemission.nl',
                'sensors.geonovum.nl',
                'www.nationaalgeoregister.nl',
                'gis.kademo.nl',
                'innovatie.kadaster.nl',
                'localhost',
                'wms.nitg.tno.nl',
                'www.groene-omgeving.nl',
                '82.98.255.91',
                'www.kademo.nl',
                'kademo.nl',
                'kademo.nl:80',
                'afnemers.ruimtelijkeplannen.nl',
                'acceptatie.geodata.nationaalgeoregister.nl',
                'geodata.nationaalgeoregister.nl']

allowedReferers = [
    'smartemission.nl',
    'geonovum.nl',
    'kademo.nl',
    'heron-mc.org'
]

method = os.environ["REQUEST_METHOD"]

if method == "POST":
    qs = os.environ["QUERY_STRING"]
    d = cgi.parse_qs(qs)
    if d.has_key("url"):
        url = d["url"][0]
    else:
        url = "http://www.openlayers.org"
else:
    fs = cgi.FieldStorage()
    url = fs.getvalue('url', "http://www.openlayers.org")

try:
    referer_arr = os.environ.get("HTTP_REFERER", "http://not.present.com/bla").split('/')[2].split(':')[0].split('.')[-2:]
    referer = referer_arr[0] + '.' + referer_arr[1]

    host = url.split("/")[2].split(':')[0]
    if referer not in allowedReferers:
        print "Status: 502 Bad Gateway"
        print "Content-Type: text/plain"
        print
        print "This proxy does not allow you to access that location (%s)." % (host,)
        print
        print os.environ

    elif url.startswith("http://") or url.startswith("https://"):
        headers = {}

        if os.environ.get("HTTP_ACCEPT"):
            headers['Accept'] = os.environ["HTTP_ACCEPT"]
        if os.environ.get("HTTP_FIWARE_SERVICE"):
            headers['FIWARE-Service'] = os.environ["HTTP_FIWARE_SERVICE"]
            if os.environ.get("HTTP_FIWARE_SERVICEPATH"):
                headers['FIWARE-Servicepath'] = os.environ["HTTP_FIWARE_SERVICEPATH"]
            if os.environ.get("HTTP_X_AUTH_TOKEN"):
                headers['X-FI-WARE-OAuth-Header-Name'] = 'X-Auth-Token'
                headers['X-FI-WARE-OAuth-Token'] = 'true'
                headers['X-Auth-Token'] = os.environ.get("HTTP_X_AUTH_TOKEN")

        if method == "POST":
            length = int(os.environ["CONTENT_LENGTH"])
            headers['Content-Type'] = os.environ["CONTENT_TYPE"]

            body = sys.stdin.read(length)
            r = urllib2.Request(url, body, headers)
            y = urllib2.urlopen(r)
        else:
            r = urllib2.Request(url, headers=headers)
            y = urllib2.urlopen(r)

        # print content type header
        i = y.info()
        if i.has_key("Content-Type"):
            print "Content-Type: %s" % (i["Content-Type"])
        else:
            print "Content-Type: text/plain"

        if i.has_key("Content-Disposition"):
            print "Content-Disposition: %s" % (i["Content-Disposition"])

        print
        # print str(os.environ)
        print y.read()

        y.close()
    else:
        print "Content-Type: text/plain"
        print
        print "Illegal request."

except Exception, E:
    print "Status: 500 Unexpected Error"
    print "Content-Type: text/plain"
    print
    print "An unexpected error occurred. Error text was:", E
