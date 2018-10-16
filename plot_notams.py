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
# Standard Imports
import datetime
from docopt import docopt
import math
import matplotlib.patheffects as PathEffects
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
import numpy as np
import os
import pytz
import sys


# Custom Imports
from lib_notam_yaml import import_notams, validate_ident, validate_lat, validate_lon, validate_radius



# Constants
NOTAM_PLOT_KEYS = ['idents', 'latitudes', 'longitudes', 'radii']
PLOT_DIR = "static/images/"


# Functions
def main(options):
    """
    Opens a yaml dump, validates the notams within the file, and generates a
    plot of the notams.

    """
    print("Opening %s ..." % options['--infile'])
    print("Collecting notams...")
    notam_list = import_notams(yaml_file=options['--infile'])
    notams = create_plot_dictionary(notam_list=notam_list)
    print(notams)
    print("Computing Circles ...")
    notams['circles'] = compute_circles(notams)
    print("Generating Plot %s ..." % options['--outfile'])
    make_plot(notams=notams,
              outfile=options['--outfile'],
              use_marble=options['--marble'])
    print("Success")
    return


def create_plot_dictionary(notam_list):
    """
    Create a dictionary of lists for plotting using a previously validated
    `notam_list`.

    """
    notams = {}
    for key in NOTAM_PLOT_KEYS:
        notams[key] = []
    for notam in notam_list:
        notams['idents'].append(validate_ident(notam['ident']))
        notams['latitudes'].append(validate_lat(lat=notam['lat'].upper()))
        notams['longitudes'].append(validate_lon(lon=notam['lon'].upper()))
        notams['radii'].append(validate_radius(r=notam['rad'].upper()))
    return notams


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
    ax = fig.add_axes([left, bottom, width, height])
    print('    Creating Basemap...')
    map = Basemap(projection='ortho', lat_0=45, lon_0=-100, resolution='l', ax=ax)
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
    fig.savefig(os.path.join(PLOT_DIR, outfile), dpi=300)
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


def build_options(day=False):
    """
    Return dictionary options build from docopts and current date.

    """
    options = docopt(__doc__)
    if '--date' not in options or options['--date'] is None:
        if day:
            options['--date'] = day
        else:
            options['--date'] = utc_today()
    # build infile name based on date
    if options['--infile'] is None:
        options['--infile'] = '_'.join([options['--date'], 'notams.yaml'])
    if options['--outfile'] is None:
        options['--outfile'] = '_'.join([options['--date'], 'notams.png'])
    return options


if __name__ == '__main__':
    main(options=build_options())
