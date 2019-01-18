"""
NOTAM Retriever
===============
This module contains the logic to retrieve GPS NOTAMs from a website, save them,
and generate their plots.

Usage:
    retrieve_notams.py -h
    retrieve_notams.py [--url URL | --use-file FILE] [--plotdir DIR] [--datadir DIR] [--debug]

Options:
  -h --help           Show this screen.
  --debug             Print verbose debugging output.
  --url URL           Read NOTAMs from a URL.  If not specified, the default URL
                      is the pilotweb site.
  --use-file FILE     Read NOTAMS from FILE instead of from a url.  The default
                      behavior is to read from a url.
  --plotdir DIR       Override the default output dir for plots.
  --datadir DIR       Override the default output dir for yaml files.

"""
# Standard Imports
from docopt import docopt
import datetime
from itertools import groupby
from operator import itemgetter
import os
import re
import requests


# Custom Imports
import lib_notam_yaml as lyn
import plot_notams


# Constants
DATADIR = [os.path.dirname(__file__), 'static_notams', 'data']
DATAURL = 'https://pilotweb.nas.faa.gov/PilotWeb/noticesAction.do?queryType=ALLGPS&formatType=DOMESTIC'
IDENT_SUBSTRING_RE = re.compile('!GPS <b>(?P<ident>[0-9/].*)</b>')
LATLON_SUBSTRING_RE = re.compile('(?P<latlon>[0-9]{6}[NS][0-9]{6,7}[EW])')
PLOTDIR = ['static_notams', 'images']
RADIUS_SUBSTRING_RE = re.compile('(?P<radius>[0-9]{1,4}) ?NM')
TIMESPAN_DATE_FORMAT = "%y%m%d%H%M"
TIMESPAN_SUBSTRING_RE = re.compile('(?P<timespan>(?P<start>[0-9]{10})-(?P<stop>[0-9]{10}))')


# Functions
def main(options):
    """
    Extract NOTAMs from a website, populate daily yaml files, and generate
    plots.

    """
    url = options['--url']
    # plotdir = options['--plotdir']
    datadir = options['--datadir']
    use_file = options['--use-file']

    # get data from file
    # ==================
    # data: key = unique radius/latlon/timespan
    #       value = list of notams idents with radius, latlon, and timespan
    #                matching key.
    data = {}
    if use_file:
        with open(use_file, 'r') as fd:
            lines = fd.readlines()
    else:  # download url
        r = requests.get(url)
        lines = r.text.split('\n')
    for line in lines:
        if line.find('!GPS') < 0:
            continue
        if options['--debug']:
            print('parsing line:', line)
        key, value = process_html_line(line)
        if not key and not value:
            # skip lines that do not contain a notam
            # e.g. "<span> !GPS <b>11/153</b> (KNMH A0027/18)  GPS NAV PRN 18 OUT OF SERVICE 1811191400-1902162359</span>"
            continue

        if options['--debug']:
            print('found key:', key, 'with value', value)
        if key not in data:
            data[key] = []
        data[key].append(value)

    for key in data:
        print('Read\n', data[key], *key)

    notam_dict = process_html_data(data)
    print("Exporting to yaml...")
    for day, notam_list in notam_dict.items():
        print(day, '\n', notam_list, '\n\n')
        for notam in notam_list:
            yaml_file = os.path.join(*datadir, '_'.join([day, 'notams.yaml']))
            lyn.add_notam(yaml_file=yaml_file, **notam)
    print("Updating plots...")
    for day in notam_dict:
        plot_notams.main(options=plot_notams.build_options(day=day))
    return


def process_html_data(data):
    """
    Return a dictionary built from the HTML data, where
        keys are ISO-formatted date strings,  values are lists of notams,
    For example:
        {'2018-10-10': [{'ident': '10/30-35',
                         'lat': '393835N',
                         'lon': '1174702W',
                         'rad': '400NM'}],
         '2018-10-11': [{'ident': '10/30-35',
                         'lat': '393835N',
                         'lon': '1174702W',
                         'rad': '400NM'}]}

    """
    # Determine abbreviated idents, lats, lons, and dates.
    # ====================================================
    notam_dict = {}
    for key, idents in data.items():
        radius, latlon, timespan = key
        ident = abbreviate_idents(idents)
        lat, lon = split_latlon(latlon)
        notam = {
            'ident': ident,
            'lat': lat,
            'lon': lon,
            'rad': radius,
        }
        days = days_from_timespan(timespan)
        for day in days:
            if day not in notam_dict:
                notam_dict[day] = []
            notam_dict[day].append(notam)
    return notam_dict


def process_html_line(line):
    """
    Extract meaningful NOTAM information from a line like RAW_NOTAM.

    RAW_NOTAM = "															<span> !GPS <b>10/155</b> (KZOA A0758/18)  ZOA NAV GPS (NTC GPS 18-38H) (INCLUDING WAAS, GBAS, AND ADS-B) MAY NOT BE AVBL WI A 270NM RADIUS CENTERED AT 352119N1163405W (HEC339034) FL400-UNL, 221NM RADIUS AT FL250, 148NM RADIUS AT 10000FT, 111NM RADIUS AT 4000FT AGL, 87NM RADIUS AT 50FT AGL. 1810271830-1810272030</span>"

    Returns the list [key, value],
        where key is the tuple (max_radius, first_latlon, first_timespan)
        and value is the first ident found.
    """
    idents_found = [m.group('ident') for m in IDENT_SUBSTRING_RE.finditer(line)]
    try:
        first_ident = idents_found[0]
    except IndexError:
        return None, None

    radii_found = [int(m.group('radius')) for m in RADIUS_SUBSTRING_RE.finditer(line)]
    try:
        max_radius = ''.join([str(max(radii_found)), 'NM'])
    except ValueError:
        return None, None

    latlons_found = [m.group('latlon') for m in LATLON_SUBSTRING_RE.finditer(line)]
    try:
        first_latlon = latlons_found[0]
    except IndexError:
        return None, None

    timespans_found = [m.group('timespan') for m in TIMESPAN_SUBSTRING_RE.finditer(line)]
    try:
        first_timespan = timespans_found[0]
    except IndexError:
        return None, None

    key = (max_radius, first_latlon, first_timespan)
    value = first_ident
    return key, value


def split_latlon(latlon):
    """
    Split a latlon into latitude and longitude.  For Example:

        '325413N1135609W' -> ['325413N', '1135609W']
        '325413N805609W' -> ['325413N', '805609W']

    """
    return latlon[0:7], latlon[7:]


def days_from_timespan(timespan):
    """
    Return the list of ISO-formatted dates timespan includes at least one minute
    of.  For Example:
        '1810291000-1810291300' -> ['2018-10-29']
        '1810261630-1810282359' -> ['2018-10-26', '2018-10-27', '2018-10-28']
    """
    m = TIMESPAN_SUBSTRING_RE.match(timespan)
    if not m:
        raise ValueError('ERROR: Timespan received with bad format: %s' % timespan)
    start_dt = datetime.datetime.strptime(m.group('start'), TIMESPAN_DATE_FORMAT)
    stop_dt = datetime.datetime.strptime(m.group('stop'), TIMESPAN_DATE_FORMAT)
    days = []
    this_day = start_dt.replace(hour=0, minute=0)
    while this_day < stop_dt:
        days.append(this_day.date().isoformat())
        this_day += datetime.timedelta(days=1)
    return days


def abbreviate_idents(idents):
    """
    Reduce a list of idents.  For Example:
        ['10/133', '10/134', '10/135', '10/136', '10/137'] -> '10/133-137'
        ['10/133', '10/135', '10/136', '10/137', '10/138'] -> '10/133,135-138'

    NOTE: prefix ('10/' in the examples above) must be the same for entire
          idents or ValueError is raised.

    Inspired by: https://stackoverflow.com/questions/2154249/identify-groups-of-continuous-numbers-in-a-list#2154437

    """
    if not idents:
        # nothing to do for empty lists
        return

    def f(x):
        # subtract 2nd element from first element.
        return x[0] - x[1]

    split_idents = [[int(item) for item in ident.split('/')] for ident in idents]
    prefixes, suffixes = zip(*split_idents)

    # Ensure all prefixes are identical.
    for prefix in prefixes:
        if prefix != prefixes[0]:
            raise ValueError('ERROR: Found multiple unique prefixes in idents.  All prefixes must be identical.')

    # Abbreviate suffixes
    suffixes_str = ''
    for _, g in groupby(enumerate(suffixes), f):
        group = (map(itemgetter(1), g))
        group = list(map(int, group))
        if group[0] == group[-1]:
            # single number
            group_str = str(group[0])
        else:
            # number range
            group_str = '-'.join([str(group[0]), str(group[-1])])
        if not suffixes_str:
            # first suffix range
            suffixes_str = group_str
        else:
            suffixes_str = ','.join([suffixes_str, group_str])

    result = '/'.join([str(prefixes[0]), suffixes_str])
    return result


def build_options():
    options = docopt(__doc__)
    if not options['--url']:
        options['--url'] = DATAURL
    if not options['--plotdir']:
        options['--plotdir'] = PLOTDIR
    if not options['--datadir']:
        options['--datadir'] = DATADIR
    return options


if __name__ == '__main__':
    main(options=build_options())
