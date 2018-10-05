NOTAMs MACOSX Environment setup
===============================
# Install Homebrew
#  - see https://brew.sh

# Get Conda
brew install $(cat requirements.brew)

# Create a virtual environment
conda create -n notams python=3.7

# Install dependencies
source activate notams
conda install -c conda-forge --file requirements.conda
pip install -r requirements.pip

# Profit
