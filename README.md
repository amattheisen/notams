Overview
========
This repository can be used to create a map to visualize the GPS NOTAM
information available [here](http://notams.aim.faa.gov/notamSearch/nsapp.html).

MACOSX Environment setup
========================
Install Homebrew
----------------
see https://brew.sh

Install Conda
-------------
    brew install $(cat requirements.brew)

Create a virtual environment
----------------------------
    conda create -n notams python=3.7

Install dependencies
--------------------
    source activate notams
    conda install -c conda-forge --file requirements.conda
    pip install -r requirements.pip

Profit
------
    source activate notams
    python app.py
