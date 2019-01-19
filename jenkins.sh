# To call this script from jenkins, include the following lines in the build
# command for the jenkins job:
#
#     basedir=/var/lib/jenkins/test
#     notams_branch=master
#     
#     mkdir -p ${basedir} || true;
#     
#     # clone repos
#     git clone git@github.com:amattheisen/notams.git ${basedir}/notams || true;
#     
#     # checkout desired branches
#     cd ${basedir}/notams; git checkout ${notams_branch}; git pull;
#     
#     # run script
#     ./jenkins.sh
#
basedir=/var/lib/jenkins/test
notams_branch=master
repo=notams
tool_short_name=notams
qa_server=moonrock
doc_path="/var/www/http/docs"


mkdir -p ${basedir} || true;

# clone repos
git clone git@github.com:amattheisen/${repo}.git ${basedir}/${repo} || true;

# checkout desired branches
cd ${basedir}/${repo}; git checkout ${notams_branch}; git pull;

# run tests
conda create -n $tool_short_name python=3.6 || true;
cd ${basedir}/${repo}; source activate ${tool_short_name};
conda install -y --name ${tool_short_name} -c conda-forge --file requirements.conda
pip install -r requirements.pip;
pip install -r test_requirements.pip;
python setup.py test;

# run build docs
python setup.py build_sphinx;

# push docs to production webserver
rsync -av docs/html/* ${doc_path}/${tool_short_name};
source deactivate;

# update tool on moonrock [if repo changed]
if [ -f last_jenkins_build.txt ] ; then
    LAST_GIT_COMMIT=$(cat last_jenkins_build.txt)
else
    LAST_GIT_COMMIT=UNKNOWN
fi
if [ $GIT_COMMIT != $LAST_GIT_COMMIT ] ; then
    echo Last built commit was $LAST_GIT_COMMIT, building new commit $GIT_COMMIT.
    echo ${qa_server} | bash ./prod_install.sh
    echo $GIT_COMMIT > last_jenkins_build.txt
fi
