#!/bin/bash
RTOOLUSER=notams  # the remote username
RTOOLPW=notams
TOOL="notams"  # the tool directory
SCRIPTDIR=$(cd $(dirname $0) && pwd -P)

echo "Running The ${TOOL} production install script from ${SCRIPTDIR}"
# ====================================================================

echo ""
read -p "Enter remote hostname or IP address for new ${TOOL} install: " REMOTEHOSTNAME
# ====================================================================================
ping -c1 $REMOTEHOSTNAME
if [ ! $? -eq 0 ]
then
    echo "${REMOTEHOSTNAME} not reachable.  Install Failed.  Exiting."
    exit 3
fi
REMOTE=${RTOOLUSER}@${REMOTEHOSTNAME}

echo ""
echo "Enabling passwordless login for ${REMOTE}.  Please enter ${RTOOLUSER}'s password."
# ======================================================================================
rsync -av enable_passwordless_login.sh ~/.ssh/id_rsa.pub $REMOTE:
if [ ! $? -eq 0 ]
then
    echo "${REMOTEHOSTNAME} login failed.  Install Failed.  Exiting."
    exit 4
fi
echo ""
echo "Please enter ${RTOOLUSER}'s password one more time."
# ========================================================
ssh -tt $REMOTE bash enable_passwordless_login.sh
if [ ! $? -eq 0 ]
then
    echo "${REMOTEHOSTNAME} login failed.  Install Failed.  Exiting."
    exit 5
fi
echo "Passwordless login to $REMOTE is now enabled.  Enjoy!"
# ==========================================================

echo "Copying gitconfig and vim configs to ${REMOTE}"
# ===================================================
rsync -av ~/.gitconfig ~/.vimrc ~/.vim $REMOTE:

echo ""
echo "Please provide remote sudo password for /opt directory creation."
# =====================================================================
ssh -tt $REMOTE "sudo -S < <(echo ${RTOOLPW}) mkdir -p /opt/${TOOL}"
if [ $? -ne 0 ]; then
    echo "${REMOTEHOST} /opt/${TOOL} creation failed.  Install Failed.  Exiting."
    exit 6
fi
ssh -tt $REMOTE "sudo -S < <(echo ${RTOOLPW}) chown -R ${RTOOLUSER}:${RTOOLUSER} /opt/${TOOL}"

echo "Copying ${TOOL} repo files to ${REMOTE}"
# =========================================
EXCLUDES=" --exclude '*__pycache__*' --exclude '*.pyc' --exclude '*.swp' "
echo rsync -av $EXCLUDES ${SCRIPTDIR}/* ${REMOTE}:/opt/${TOOL}
rsync -av $EXCLUDES ${SCRIPTDIR} ${REMOTE}:/opt/${TOOL}

echo "Please provide remote sudo password to run install script."
# ===============================================================
ssh -tt $REMOTE "sudo  -S < <(echo ${RTOOLPW}) bash /opt/${TOOL}/vagrant/install.sh"
