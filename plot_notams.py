""" plot_notams.py
Description: Plot NOTAMS on a map.
Date: 2018-10-04

Usage: plot_notams.py [--notams FILE] [--outfile FILE] [--marble] [-h]

Options:
  -h --help           Show this screen.
  -n --notams FILE    Read NOTAMs from YAML formatted file FILE
                      [Default: notams.yaml].
  --marble            Use the bluemarble map background instead of the default
                      shadedrelief. [Default: False]
  --outfile FILE      Save plot as FILE.  [Default: notam_plot.png]

"""
# Standard Imports
from docopt import docopt
import math
import matplotlib.patheffects as PathEffects
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
import numpy as np
import re
import sys
import yaml


# Constants
INVALID_LATITUDE = "ERROR: {i_th} notam has invalid latitude {latitude}."
INVALID_LONGITUDE = "ERROR: {i_th} notam has invalid longitude {longitude}."
INVALID_RADIUS = "ERROR: {i_th} notam has invalid radius {radius}."

# IS_LATLONG Regular expression explaination:
# Direction {N, S, E, W} -----------------------------------------------------------------\
#                                                                                         |
# Seconds DD --------------------------------------------------------\                    |
#                                                                    |                    |
# Minutes DD -----------------------------------\                    |                    |
#                                               |                    |                    |
# Degrees [D]DD ---------\                      |                    |                    |
#                        v                      v                    v                    v
IS_LATLONG = re.compile("^(?P<degrees>[0-9]{2,3})(?P<minutes>[0-9]{2})(?P<seconds>[0-9]{2})(?P<direction>[NSEW])$")

IS_RADIUS = re.compile("^(?P<radius>\d+)(NM)?$")
MISSING_REQUIRED_KEY = "ERROR: {i_th} notam missing required key {key}."
REQUIRED_KEYS = ['id', 'lat', 'long', 'rad']


# Functions
def main(options):
    print("Opening %s ..." % options['--notams'])
    print("Collecting notams...")
    notams = import_notams(yaml_file=options['--notams'])
    print(notams)
    print("Generating Plot...")
    make_plot(notams=notams, outfile=options['--outfile'], use_marble=options['--marble'])
    print("Success")
    return


def init_notams(notams):
    """
    Ensure notams has all the keys required by other functions in this module.

    """
    for key in ['ids', 'radii', 'latitudes', 'longitudes']:
        if key not in notams:
            notams[key] = []
    return


def import_notams(yaml_file):
    """
    Read in the notams YAML dump.  Ensure that each NOTAM has an id, lat, long,
    and radius.

    The YAML Dump should be a list of dictionaries - each dictionary represents
    one notam.  Each notam dictionary should have the following keys:
        id - ID of the notam
        lat - latitude of the center of the notam formatted as DDMMSS[N|S]
              DD - two digit integer Degrees
              MM - two digit integer Minutes
              SS - two digit integer Seconds
              [N|S] - one character, 'N' for North and 'S' for South
        long - longitude of the center of the notam formatted as [D]DDMMSS[E|W]
              [D]DD - two or three digit integer Degrees
              MM - two digit integer Minutes
              SS - two digit integer Seconds
              [E|W] - one character, 'E' for East and 'W' for West
        rad - integer radius of the notam in nautical miles

    """
    errors = []
    notams = {}
    init_notams(notams)

    # get raw_notams
    raw_notams = yaml.load(open(yaml_file, 'r'))

    # validate raw_notams and populate notams dictionary
    for ii, notam in enumerate(raw_notams):
        for key in REQUIRED_KEYS:
            if key not in notam:
                errors.append(MISSING_REQUIRED_KEY.format(i_th=add_number_suffix(ii), key=key))
        notams['ids'].append(notam['id'])
        latitude = convert_str_to_decimal_degrees(s=notam['lat'].upper())
        if latitude is None:
            errors.append(INVALID_LATITUDE.format(i_th=add_number_suffix(ii), latitude=notam['lat']))
        notams['latitudes'].append(latitude)
        longitude = convert_str_to_decimal_degrees(s=notam['long'].upper())
        if longitude is None:
            errors.append(INVALID_LONGITUDE.format(i_th=add_number_suffix(ii), longitude=notam['long']))
        notams['longitudes'].append(longitude)

        radius = check_radius_format(r=notam['rad'].upper())
        if radius is None:
            errors.append(INVALID_RADIUS.format(i_th=add_number_suffix(ii), radius=notam['rad']))
        notams['radii'].append(radius)

    if errors:
        # print error messages and die
        print('Errors detected:')
        for error in errors:
            print('   ', error)
        print('Exiting.')
        sys.exit(-1)
    return notams


def convert_str_to_decimal_degrees(s):
    """
    Return decimal degrees from Latitude or Longitude who's format matches IS_LATLONG.

    """
    # consume argument
    m = re.match(IS_LATLONG, s)
    if m is None:
        # input does not match format
        return
    whole_degrees = m.group('degrees')
    minutes = m.group('minutes')
    seconds = m.group('seconds')
    direction = m.group('direction')

    # determine degrees
    if int(minutes) >= 60:
        # minutes out of valid range
        return
    if int(seconds) >= 60:
        # seconds out of valid range
        return
    # We don't have to check minutes of seconds < 0 due to the format of IS_LATLONG.
    sign = [-1, 1][direction in ['N', 'E']]  # S and W are -1
    degrees = sign * (int(whole_degrees) + float(minutes) / 60 + float(seconds) / 3600)

    # sanity check on valid range of lats/lons
    if direction in ['N', 'S'] and abs(degrees) > 90:
        # latitude degrees out of valid range
        return
    elif abs(degrees) > 180:  # E or W implied
        # longitude degrees out of valid range
        return
    return degrees


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


def check_radius_format(r):
    """
    Extract radius from string r who's format matches IS_RADIUS.

    """
    # consume argument
    m = re.match(IS_RADIUS, r)
    if m is None:
        # input does not match format
        return
    radius = int(m.group('radius'))
    return radius


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
    ids = notams['ids']
    latitudes = notams['latitudes']
    longitudes = notams['longitudes']
    radii = notams['radii']
    # Add Circles
    for ii in range(len(ids)):
       circle_lons, circle_lats = create_circle(latitudes[ii], longitudes[ii], radii[ii])
       x, y = map(circle_lons, circle_lats)
       map.plot(x, y, marker=None, color='red', linewidth=1, zorder=6)
    # Add labels
    for ii in range(len(ids)):
        x, y = map(longitudes[ii], latitudes[ii])
        plt.text(
            x, y, ids[ii], fontsize=2, fontweight='bold', ha='center',
            va='center', color='white',
            path_effects=[PathEffects.withStroke(
                linewidth=3, foreground="black")],
            zorder=5)

    plt.title('NOTAM Footprints')
    print('    Saving...')
    fig.savefig(outfile, dpi=300)
    plt.close("all")


def create_circle(lat, lon, radius_nautical_miles):
    """
    Create an array of locations at the given radius around the location lat,
    lon using the Haversine formula.

    Based on https://stochasticcoder.com/2016/04/06/python-custom-distance-radius-with-basemap/
    Adapted to use nautical miles instead of miles

    """
    latArray = []
    lonArray = []
    for bearing in range(0, 360):
        lat2, lon2 = get_location(lat, lon, bearing, radius_nautical_miles)
        latArray.append(lat2)
        lonArray.append(lon2)
    return lonArray, latArray


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


if __name__ == '__main__':
    options = docopt(__doc__)
    main(options)
