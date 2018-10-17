"""
NOTAM YAML Library
==================
This library contains the logic to extract GPS NOTAMs from a yaml dump file,
validating a notam, and write notams to a yaml dump file.

"""
# Standard Imports
import math
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
NOTAM_KEYS = ['ident', 'lat', 'lon', 'rad']
SECONDS_IN_ONE_DEGREE = 3600


# Functions
def add_notam(yaml_file, ident, lat, lon, rad):
    """
    Add a notam to a YAML dump file.

    """
    new_notam = {'ident': ident, 'lat': lat, 'lon': lon, 'rad': rad}
    notam_list = import_notams(yaml_file=yaml_file)
    notam_list.append(new_notam)
    success = export_notams(yaml_file=yaml_file, notam_list=notam_list)
    return success    


def delete_notam(yaml_file, ident, lat, lon, rad):
    """
    Delete a notam from a YAML dump file.

    """
    success = False
    notam_list = import_notams(yaml_file=yaml_file)
    for ii, notam in enumerate(notam_list):
        if (notam['ident'] == ident and
                notam['lat'] == lat and
                notam['lon'] == lon and
                notam['rad'] == rad):
            success = True
            break
    if success:
        notam_list.pop(ii)
        success = success and export_notams(yaml_file=yaml_file, notam_list=notam_list)
    return success


def modify_notam(yaml_file, orig_ident, orig_lat, orig_lon, orig_rad, ident, lat, lon, rad):
    """
    Modify a notam in a YAML dump file.

    """
    success = False
    notam_list = import_notams(yaml_file=yaml_file)
    for ii, notam in enumerate(notam_list):
        if (notam['ident'] == orig_ident and
                notam['lat'] == orig_lat and
                notam['lon'] == orig_lon and
                notam['rad'] == orig_rad):
            success = True
            notam['ident'] = ident
            notam['lat'] = lat
            notam['lon'] = lon
            notam['rad'] = rad
            break
    if success:
        success = success and export_notams(yaml_file=yaml_file, notam_list=notam_list)
    return success


def export_notams(yaml_file, notam_list):
    """
    Export the `notam_list` to FILE `yaml_file` as a YAML dump.

    """
    success = False
    notams_yaml = yaml.dump(notam_list)
    # TODO: Add try/except here?
    # try:
    fdout = open(yaml_file, 'w')
    print(notams_yaml, file=fdout)
    success = True
    # except PermissionError:
    # pass???  or raise error???
    return success


def import_notams(yaml_file):
    """
    Read in the NOTAMs from YAML dump FILE `yaml_file`.  Ensure that each NOTAM
    has the required keys.  Return the list of NOTAMS.

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
    notam_list = []

    # get raw_notams
    try:
        raw_notams = yaml.load(open(yaml_file, 'r'))
    except FileNotFoundError:
        return notam_list  # no notams
    if not raw_notams:
        return notam_list  # no notams in file
    # validate raw_notams and populate notams dictionary
    for ii, notam in enumerate(raw_notams):
        # check this notam for required keys
        valid_notam = True
        for key in NOTAM_KEYS:
            if key not in notam:
                errors.append(MISSING_REQUIRED_KEY.format(i_th=add_number_suffix(ii), key=key))
                valid_notam = False 
        # validate ident
        ident = validate_ident(notam['ident'])
        if ident is None:
            errors.append(INVALID_IDENT.format(i_th=add_number_suffix(ii), ident=notam['ident']))
            valid_notam = False 
        # validate latitude
        latitude = validate_lat(lat=notam['lat'].upper())
        if latitude is None:
            errors.append(INVALID_LATITUDE.format(i_th=add_number_suffix(ii), latitude=notam['lat']))
            valid_notam = False 
        # validate longitude
        longitude = validate_lon(lon=notam['lon'].upper())
        if longitude is None:
            errors.append(INVALID_LONGITUDE.format(i_th=add_number_suffix(ii), longitude=notam['lon']))
            valid_notam = False 
        # validate radius
        radius = validate_radius(r=notam['rad'].upper())
        if radius is None:
            errors.append(INVALID_RADIUS.format(i_th=add_number_suffix(ii), radius=notam['rad']))
            valid_notam = False 
        if valid_notam:
            notam_list.append(notam)

    if errors:
        # error(s) encountered loading|validating yaml file.
        print('Errors detected:')
        for error in errors:
            print('   ', error)
    return notam_list


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
