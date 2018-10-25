"""
Flask NOTAM App
===============
This Flask creates a web interface for displaying GPS NOTAMs.

Requirements
1) The default display shall display the following:
    * The (SELECTED DAY), which defaults to UTC today
    * A (DATE) input field and a (CHANGE DAY) button
    * A list of valid NOTAMS from the yaml file corresponding to the
     (SELECTED DAY)
    * A button for each displayed NOTAM to (DELETE) it
    * A button to (ADD NOTAM) to the list of valid NOTAMS
    * A plot of the NOTAM, if the image exists
    * A button to (PLOT) to generate the plot for the SELECTED DAY

2) The (CHANGE DAY) button shall:
   * validate the (DATE) input field, and
   * cause the page to reload with the valid specified (DATE) as the
     SELECTED DAY.

3) A (DELETE NOTAM) button shall:
   * remove the related NOTAM from the displayed list of NOTAMS,
   * update the SELECTED DAY's yaml file, and
   * add emphasis to the the (PLOT) button.

4) The (ADD NOTAM) button shall:
   * validate the input fields,
   * add a NOTAM to the displayed list of NOTAMS,
   * update the SELECTED DAY's yaml file, and
   * cause add emphasis to the (PLOT) button.

5) The (PLOT) button shall:
   * Cause a new plot to be generated for the SELECTED DAY, and
   * remove emphasis from the (PLOT) button.

"""
# Stantard Imports
import datetime
from flask import Flask, render_template, request
import os

# Custom Imports
import lib_notam_yaml as lny
import plot_notams


# Constants
DATA_DIR = "static/data/"


# Setup
app = Flask(__name__)


# Views 
@app.route("/", methods=["GET"])
def home(day=None):
    if day is None:
        day = plot_notams.utc_today()
    input_file = os.path.join(DATA_DIR, '_'.join([day, 'notams.yaml']))
    notam_list = lny.import_notams(yaml_file=input_file)
    # TODO: how to get plot emphasis?
    return render_template("index.html",
                           day=day,
                           notam_list=notam_list,
                           utc_timestamp=datetime.datetime.utcnow().isoformat())


@app.route("/", methods=["POST"])
def home_post():
    if request.form['btn'] == 'today':
        return home()
    elif request.form['btn'] == 'date':
        day = request.form['day']
        print("Selecting new day,", day)
        return home(day)
    elif request.form['btn'] == 'plot':
        day = request.form['day']
        print("Plotting", day)
        # TODO: how to run the plot in the background or speed up plotting?
        options = plot_notams.build_options(day=day)
        plot_notams.main(options=options)
        return home(day)
    elif request.form['btn'] == 'del':
        print("Deleting NOTAM")
        day = request.form['day']
        yaml_file = os.path.join(DATA_DIR, '_'.join([day, 'notams.yaml']))
        kwargs = {'yaml_file': yaml_file,
                  'ident': request.form['ident'],
                  'lat': request.form['lat'],
                  'lon': request.form['lon'],
                  'rad': request.form['rad']}
        lny.delete_notam(**kwargs)
        # TODO: how to get plot emphasis in this case?
        return home(day)
    elif request.form['btn'] == 'upd':
        print("Updating NOTAM")
        day = request.form['day']
        yaml_file = os.path.join(DATA_DIR, '_'.join([day, 'notams.yaml']))
        kwargs = {'yaml_file': yaml_file,
                  'orig_ident': request.form['orig_ident'],
                  'orig_lat': request.form['orig_lat'],
                  'orig_lon': request.form['orig_lon'],
                  'orig_rad': request.form['orig_rad'],
                  'ident': request.form['ident'],
                  'lat': request.form['lat'],
                  'lon': request.form['lon'],
                  'rad': request.form['rad']}
        lny.modify_notam(**kwargs)
        # TODO: how to get plot emphasis in this case?
        return home(day)
    elif request.form['btn'] == 'add':
        print("Adding NOTAM")
        day = request.form['day']
        print("Captured Day")
        yaml_file = os.path.join(DATA_DIR, '_'.join([day, 'notams.yaml']))
        kwargs = {'yaml_file': yaml_file,
                  'ident': request.form['ident'],
                  'lat': request.form['lat'],
                  'lon': request.form['lon'],
                  'rad': request.form['rad']}
        lny.add_notam(**kwargs)
        # TODO: how to get plot emphasis in this case?
        return home(day)
    else:
        print('found weird post')
        return home()


if __name__ == '__main__':
    app.run(host="0.0.0.0")
