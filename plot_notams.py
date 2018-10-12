""" plot_notams.py
Description: Plot NOTAMS on a map.
Date: 2018-10-04

Usage: plot_notams.py [--date DATE] [--marble] [--infile FILE] [--outfile FILE] [-h]

Options:
  -h --help           Show this screen.
  -d --date DATE      Specify UTC date in ISO format YYYY-MM-DD.  Default is
                      today's UTC date.
  --marble            Use the bluemarble map background instead of the default
                      shadedrelief.
  --infile FILE       Read NOTAMs from YAML formatted file FILE.  If not
                      specified, the input file name will be derrived from
                      the --date option as <YYYY-MM-DD_notams.yaml>.
  --outfile FILE      Save the output plot as FILE.  If not specified, the
                      output file name will be derrived from the --date option
                      as <YYYY-MM-DD_notams.png>.

"""
# TODO: Add a date flag that selects the appropriate yaml file.  name yaml files
#       by date.  Remove the -n --notam flag?

# Standard Imports
import datetime
from docopt import docopt
import math
import matplotlib.patheffects as PathEffects
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
import numpy as np
import pytz
import re
import sys
import yaml


# Constants
INVALID_IDENT = "ERROR: {i_th} notam has invalid ident {ident}."
INVALID_LATITUDE = "ERROR: {i_th} notam has invalid latitude {latitude}."
INVALID_LONGITUDE = "ERROR: {i_th} notam has invalid longitude {longitude}."
INVALID_RADIUS = "ERROR: {i_th} notam has invalid radius {radius}."
IS_IDENT = re.compile("^.{1,20}$")
# IS_LAT Regular expression explaination:
# Direction {N, S} ------------------------------------------------------------------\
#                                                                                    |
# Seconds DD ---------------------------------------------------\                    |
#                                                               |                    |
# Minutes DD ------------------------------\                    |                    |
#                                          |                    |                    |
# Degrees DD ---------\                    |                    |                    |
#                     v                    v                    v                    v
IS_LAT = re.compile("^(?P<degrees>[0-9]{2})(?P<minutes>[0-9]{2})(?P<seconds>[0-9]{2})(?P<direction>[NS])$")
# IS_LON Regular expression explaination:
# Direction {E, W} --------------------------------------------------------------------\
#                                                                                      |
# Seconds DD -----------------------------------------------------\                    |
#                                                                 |                    |
# Minutes DD --------------------------------\                    |                    |
#                                            |                    |                    |
# Degrees [D]DD ------\                      |                    |                    |
#                     v                      v                    v                    v
IS_LON = re.compile("^(?P<degrees>[0-9]{2,3})(?P<minutes>[0-9]{2})(?P<seconds>[0-9]{2})(?P<direction>[EW])$")
IS_RADIUS = re.compile("^(?P<radius>\d+)(NM)?$")
MAX_LATITUDE = 90.0
MAX_LONGITUDE = 180.0
MINUTES_IN_ONE_DEGREE = 60
MISSING_REQUIRED_KEY = "ERROR: {i_th} notam missing required key {key}."
REQUIRED_KEYS = ['ident', 'lat', 'lon', 'rad']
SECONDS_IN_ONE_DEGREE = 3600


# Functions
def main(options):
    """
    Opens a yaml dump, validates the notams within the file, and generates a
    plot of the notams.

    """
    print("Opening %s ..." % options['--infile'])
    print("Collecting notams...")
    notams = import_notams(yaml_file=options['--infile'])
    print(notams)
    print("Computing Circles ...")
    notams['circles'] = compute_circles(notams)
    print("Generating Plot %s ..." % options['--outfile'])
    make_plot(notams=notams, outfile=options['--outfile'], use_marble=options['--marble'])
    print("Success")
    return


def init_notams(notams):
    """
    Ensure notams has all the keys required by other functions in this module.

    """
    for key in ['idents', 'radii', 'latitudes', 'longitudes']:
        if key not in notams:
            notams[key] = []
    return


def import_notams(yaml_file):
    """
    Read in the notams YAML dump.  Ensure that each NOTAM has the required keys.

    The YAML Dump should be a list of dictionaries - each dictionary represents
    one notam.  Each notam dictionary should have the following keys:
        ident - ID/name of the notam
        lat - latitude of the center of the notam formatted as DDMMSS[N|S]
              DD - two digit integer Degrees
              MM - two digit integer Minutes
              SS - two digit integer Seconds
              [N|S] - one character, 'N' for North and 'S' for South
        lon - longitude of the center of the notam formatted as [D]DDMMSS[E|W]
              [D]DD - two or three digit integer Degrees
              MM - two digit integer Minutes
              SS - two digit integer Seconds
              [E|W] - one character, 'E' for East and 'W' for West
        rad - integer radius of the notam in nautical miles formatted as [D][D][D][D]D[NM]
              [D][D][D][D]D - one to five digit integer (1-99999) Nautical Miles
              [NM] - Optional unit label

    """
    errors = []
    notams = {}
    init_notams(notams)

    # get raw_notams
    raw_notams = yaml.load(open(yaml_file, 'r'))

    # validate raw_notams and populate notams dictionary
    for ii, notam in enumerate(raw_notams):
        # check this notam for required keys
        for key in REQUIRED_KEYS:
            if key not in notam:
                errors.append(MISSING_REQUIRED_KEY.format(i_th=add_number_suffix(ii), key=key))
        # validate ident
        ident = validate_ident(notam['ident'])
        if ident is None:
            errors.append(INVALID_IDENT.format(i_th=add_number_suffix(ii), ident=notam['ident']))
        notams['idents'].append(notam['ident'])
        # validate latitude
        latitude = validate_lat(lat=notam['lat'].upper())
        if latitude is None:
            errors.append(INVALID_LATITUDE.format(i_th=add_number_suffix(ii), latitude=notam['lat']))
        notams['latitudes'].append(latitude)
        # validate longitude
        longitude = validate_lon(lon=notam['lon'].upper())
        if longitude is None:
            errors.append(INVALID_LONGITUDE.format(i_th=add_number_suffix(ii), longitude=notam['lon']))
        notams['longitudes'].append(longitude)
        # validate radius
        radius = validate_radius(r=notam['rad'].upper())
        if radius is None:
            errors.append(INVALID_RADIUS.format(i_th=add_number_suffix(ii), radius=notam['rad']))
        notams['radii'].append(radius)

    if errors:
        # print error messages and exit
        print('Errors detected:')
        for error in errors:
            print('   ', error)
        print('Exiting.')
        sys.exit(-1)
    return notams


def validate_ident(ident):
    """
    Returns valid ident, or None if ident is invalid.

    """
    m = re.match(IS_IDENT, ident)
    if m is None:
        return
    return ident


def validate_lat(lat):
    """
    Returns valid latitude, or None if the lat is invalid.

    """
    kwargs = {'m': re.match(IS_LAT, lat),
              'valid_directions': ['N', 'S'],
              'max_degrees': MAX_LATITUDE}
    return validate_lat_or_lon(**kwargs)


def validate_lon(lon):
    """
    Returns valid longitude, or None if the lon is invalid.

    """
    kwargs = {'m': re.match(IS_LON, lon),
              'valid_directions': ['E', 'W'],
              'max_degrees': MAX_LONGITUDE}
    return validate_lat_or_lon(**kwargs)


def validate_lat_or_lon(m, valid_directions, max_degrees):
    """
    Common checks for latitudes and longitudes.  Returns valid latitude or
    longitude, or None if the input is invalid.

    `m` is a re.match object or None.

    `valid_directons` is either the list ['N', 'S'] for latitudes, or ['E', 'W']
    for longitudes.

    `max_degrees` is either 90.0 for latitudes, or 180.0 for longitudes.

    """
    if m is None:
        return
    whole_degrees = m.group('degrees')
    # Skip validation of whole degrees for now.  If value == max_degrees, then
    # minutes and seconds must both be 0, which will be tested later.

    kwargs = {'number': m.group('minutes'),
              'min_val': 0,
              'max_val': 60}
    minutes = validate_range(**kwargs)
    if minutes is None:
        return

    kwargs = {'number': m.group('seconds'),
              'min_val': 0,
              'max_val': 60}
    seconds = validate_range(**kwargs)
    if seconds is None:
        return

    kwargs = {'direction': m.group('direction'),
              'valid_directions': valid_directions}
    sign = validate_direction(**kwargs)
    if sign is None:
        return

    abs_degrees = (
        int(whole_degrees) +
        float(minutes) / MINUTES_IN_ONE_DEGREE +
        float(seconds) / SECONDS_IN_ONE_DEGREE)
    kwargs = {
        'number': abs_degrees,
        'min_val': 0.0,
        'max_val': max_degrees}
    abs_degrees = validate_range(**kwargs)
    if abs_degrees is None:
        return
    degrees = sign * abs_degrees
    return degrees


def validate_direction(direction, valid_directions):
    """
    Returns integer -1 or +1 indicating the appropriate sign for degrees based
    on direction, or None if direction is invalid.

    """
    if direction not in valid_directions:
        return
    return [-1, 1][direction in ['N', 'E']]  # S and W are -1


def validate_range(number, min_val, max_val):
    """
    Returns validated number if it is a value such that
        min <= number <= max
    ... or None if number is invalid.

    NOTE: `number`, `min_val`, and `max_val` can be of type int, float, or
    string.  They will be cast as floats before they are compaired.

    """
    if float(number) < float(min_val) or float(number) > float(max_val):
        # number out of valid range
        return
    return number


def validate_radius(r):
    """
    Returns validated radius, or None if radius is invalid.

    """
    # consume argument
    m = re.match(IS_RADIUS, r)
    if m is None:
        # input does not match format
        return
    radius = int(m.group('radius'))
    return radius


def add_number_suffix(n):
    """
    Convert integer to place.  For example: 1 -> 1st, 2-> 2nd, 3 -> 3rd, ...

    Based on https://stackoverflow.com/questions/9647202/ordinal-numbers-replacement

    """
    # Explaination:
    # Final term maps numbers ending in 0 to 'th', 1 to 'st', 2 to 'nd', 3 to 'rd'. --\
    #                                                                                 |
    # Second term maps and number ending in 4-9 to 'th' ------------\                 |
    #                                                               |                 |
    # First term maps 10-19 to 'th' ---\                            |                 |
    #                                  v                            v                 v
    return "%d%s" % (n, "tsnrhtdd"[(math.floor(n / 10) % 10 != 1) * (n % 10 < 4) * (n % 10)::4])


def make_plot(notams, outfile, use_marble=False):
    """
    Plot NOTAMs.

    """
    fig = plt.figure()

    # set up orthographic map projection with
    # perspective of satellite looking down at 45N, 100W.
    # use low resolution coastlines.
    left = 0.0
    bottom = 0.05
    width = 1.0
    height = 0.9
    print('    Creating Basemap...')
    map = Basemap(projection='ortho',lat_0=45,lon_0=-100,resolution='l',
        ax=fig.add_axes([left, bottom, width, height]))

    print('    Adding features - lines...')
    # draw coastlines, country boundaries, state boundaries
    map.drawcoastlines(linewidth=0.25)
    map.drawcountries(linewidth=0.25)
    map.drawstates(linewidth=0.15)
    # draw lat/lon grid lines every 30 degrees.
    map.drawmeridians(np.arange(0,360,30), zorder=2)
    map.drawparallels(np.arange(-90,90,30), zorder=2)

    print('    Adding features - land/ocean...')
    if use_marble:
        map.drawlsmask(land_color='white', ocean_color='aqua', resolution='l')
        map.drawlsmask(resolution='l')
        map.bluemarble()
    else:  # default
        map.shadedrelief()

    print('    Adding Notams...')
    idents = notams['idents']
    latitudes = notams['latitudes']
    longitudes = notams['longitudes']
    radii = notams['radii']
    # Add Circles
    for ii in range(len(idents)):
       circle_lats, circle_lons = notams['circles'][ii]
       x, y = map(circle_lons, circle_lats)
       map.plot(x, y, marker=None, color='red', linewidth=1, zorder=6)
    # Add labels
    for ii in range(len(idents)):
        x, y = map(longitudes[ii], latitudes[ii])
        plt.text(
            x, y, idents[ii], fontsize=2, fontweight='bold', ha='center',
            va='center', color='white',
            path_effects=[PathEffects.withStroke(
                linewidth=3, foreground="black")],
            zorder=5)

    plt.title('NOTAM Footprints')
    print('    Saving...')
    fig.savefig(outfile, dpi=300)
    plt.close("all")


def compute_circles(notams):
    """
    Returns `circles`, a list of tuples - each tuple contains an array of
    latitudes and an array of longitudes defining one circle.

    `notams` is a dictionary containing keys 'idents', 'latitudes',
    'longitudes', and 'radii'.

    """
    circles = []
    idents = notams['idents']
    latitudes = notams['latitudes']
    longitudes = notams['longitudes']
    radii = notams['radii']
    for ii in range(len(idents)):
       circle_lats, circle_lons = compute_circle(latitudes[ii], longitudes[ii], radii[ii])
       circles.append((circle_lats, circle_lons))
    return circles


def compute_circle(lat, lon, radius_nautical_miles):
    """
    Returns a tuple containing an array of longitudes and latitudes defining
    locations at the given radius around the location,
    lon using the Haversine formula.

    Based on https://stochasticcoder.com/2016/04/06/python-custom-distance-radius-with-basemap/
    Adapted to use nautical miles instead of miles

    """
    lats = []
    lons = []
    for bearing in range(0, 360):
        lat2, lon2 = get_location(lat, lon, bearing, radius_nautical_miles)
        lats.append(lat2)
        lons.append(lon2)
    return lats, lons


def get_location(lat1, lon1, bearing, distance_nautical_miles):
    """
    Return the lat and lon of a location that has specified bearing and distance
    from lat1, lon1.

    Based on https://stochasticcoder.com/2016/04/06/python-custom-distance-radius-with-basemap/
    Adapted to use distances in nautical miles

    """
    lat1 = lat1 * math.pi / 180.0
    lon1 = lon1 * math.pi / 180.0
    # Earth's radius in nautical miles - ref http://science.answers.com/Q/What_is_the_radius_of_earth
    R = 3440.07
    distance_nautical_miles = distance_nautical_miles / R
    bearing = (bearing / 90.0) * math.pi / 2.0

    lat2 = math.asin(
        math.sin(lat1) * math.cos(distance_nautical_miles) +
        math.cos(lat1) * math.sin(distance_nautical_miles) * math.cos(bearing))

    lon2 = lon1 + math.atan2(
        math.sin(bearing) * math.sin(distance_nautical_miles) * math.cos(lat1),
        math.cos(distance_nautical_miles) - math.sin(lat1) * math.sin(lat2))

    lon2 = 180.0 * lon2 / math.pi
    lat2 = 180.0 * lat2 / math.pi
    return lat2, lon2


def utc_today():
    """
    Return ISO formatted date for this day in UTC timezone.

    """
    UTC = pytz.timezone('UTC')
    return datetime.datetime.now(UTC).date().isoformat()


def build_options():
    """
    Return dictionary options build from docopts and current date.

    """
    options = docopt(__doc__)
    if '--date' not in options or options['--date'] is None:
        options['--date'] = utc_today()
    # build infile name based on date
    if options['--infile'] is None:
        options['--infile'] = '_'.join([options['--date'], 'notams.yaml'])
    if options['--outfile'] is None:
        options['--outfile'] = '_'.join([options['--date'], 'notams.png'])
    return options


if __name__ == '__main__':
    main(options=build_options())
