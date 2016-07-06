#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Output classes for ETL.
#
# Author: Just van den Broecke
#
from stetl.outputs.httpoutput import HttpOutput
from stetl.util import Util
from stetl.packet import FORMAT

log = Util.get_log('sosoutput')

class SOSTOutput(HttpOutput):
    """
    Output via SOS-T protocol over plain HTTP.

    consumes=FORMAT.record
    """

    def __init__(self, configdict, section):
        HttpOutput.__init__(self, configdict, section, consumes=FORMAT.record_array)
        self.content_type = self.cfg.get('content_type', 'application/json;charset=UTF-8')
        self.sos_request = self.cfg.get('sos_request', 'insert-observation')

        # Template file, to be used as POST body with substituted values
        self.template_file_ext = self.cfg.get('template_file_ext', 'json')
        self.template_file_root = self.cfg.get('template_file_root', 'sostemplates')
        self.template_file_path = '%s/%s.%s' % (self.template_file_root, self.sos_request, self.template_file_ext)

    def init(self):
        # read the template once
        log.info('Init: read template')
        self.file = open(self.template_file_path, 'r')
        log.info("file opened : %s" % self.template_file_path)

        # Read the template string
        self.template_str = self.file.read()

        # Cleanup
        self.file.close()
        self.file = None

        # For insert-sensor we need the Procedure SML (XML) and escape/insert this into
        # the JSON insert-sensor string.
        if self.sos_request == 'insert-sensor':

            f = open('%s/procedure-desc.xml' % self.template_file_root, 'r')
            proc_desc = f.read()
            proc_desc = proc_desc.replace('"', '\\"')
            proc_desc = proc_desc.replace('\n', '')
            self.template_str = self.template_str.replace('{procedure-desc.xml}', proc_desc)
            f.close()

    def create_payload(self, packet):
        record = packet.data

        if self.sos_request == 'insert-sensor':

            # String substitution based on Python String.format()
            # <local_id>STA-NL00807</local_id>
            # <natl_station_code>807</natl_station_code>
            # <eu_station_code>NL00807</eu_station_code>
            # <name>Hellendoorn-Luttenbergerweg</name>
            # <municipality>Hellendoorn</municipality>
            # <altitude>7</altitude>
            # <altitude_unit>m</altitude_unit>
            # <area_classification>http://dd.eionet.europa.eu/vocabulary/aq/areaclassification/rural</area_classification>
            # <activity_begin>1976-04-02T00:00:00+01:00</activity_begin>
            # <activity_end></activity_end>
            # <version></version>
            # <belongs_to></belongs_to>
            # <lon></lon>
            # <lat></lat>
            format_args = dict()
            format_args['station_id'] = record['natl_station_code']
            format_args['station_name'] = record['name']
            # if record['municipality'] is not None and len(record['municipality']) > 0:
            #     format_args['name'] += ' - ' + record['municipality']
            format_args['station_altitude'] = record['altitude']
            format_args['station_lon'] = record['lon']
            format_args['station_lat'] = record['lat']

            payload = self.template_str.format(**format_args)
            # print payload
        else:
            if self.sos_request == 'insert-observation':
                format_args = dict()
                # need station_id, unique_id (sample_id?),
                # component, municipality(may be null), station_lat, station_lon,
                # sample_time, sample_value
                format_args['component'] = record['name']
                format_args['station_id'] = record['device_id']

                # See issue: somehow the unique_id ends up in the capabilities doc!
                format_args['unique_id'] = record['gid']

                # Time format: "yyyy-MM-dd'T'HH:mm:ssZ"  e.g. 2013-09-29T18:46:19+0100
                format_args['sample_time'] = record['time']

                # municipality = record['municipality']
                # if municipality is None or len(municipality) == 0:
                #     municipality = 'Unknown municipality for station id %s' % record['station_id']

                format_args['municipality'] = 'Nijmegen'
                format_args['station_lon'] = record['lon']
                format_args['station_lat'] = record['lat']
                format_args['sample_value'] = record['value']

                payload = self.template_str.format(**format_args)
                # print payload

        return payload
