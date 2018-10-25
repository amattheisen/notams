#!/usr/bin/bash
# Vagrant dev install script for Centos7
TOOLUSER=notams
TOOLNAME=notams

echo Creating ${TOOLUSER} user.
# =============================
useradd -m -p${TOOLUSER} ${TOOLUSER}

echo Enabling ${TOOLUSER} sudo.
# =============================
echo "%${TOOLUSER} ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/${TOOLUSER}

echo Enabling passwordless login.
# ===============================
su - ${TOOLUSER} -c "mkdir -m 700 /home/${TOOLUSER}/.ssh"
mv /tmp/host_id_rsa.pub /home/${TOOLUSER}/.ssh/authorized_keys
chmod 700 /home/${TOOLUSER}/.ssh/authorized_keys
chown ${TOOLUSER}:${TOOLUSER} /home/${TOOLUSER}/.ssh/authorized_keys

echo Moving files into place.
# ===========================
mv /tmp/.gitconfig /home/${TOOLUSER}/
chown ${TOOLUSER}:${TOOLUSER} /home/${TOOLUSER}/.gitconfig
mv /tmp/.vimrc /home/${TOOLUSER}/
mv /tmp/.vim /home/${TOOLUSER}/
chown -R ${TOOLUSER}:${TOOLUSER} /home/${TOOLUSER}/.vim
chown ${TOOLUSER}:${TOOLUSER} /home/${TOOLUSER}/.vimrc
mv /vagrant/${TOOLUSER}_id_rsa* /home/${TOOLUSER}/
chown ${TOOLUSER}:${TOOLUSER} /home/${TOOLUSER}/${TOOLUSER}_id_rsa*

echo Moving git repository into place.
# ======================================
mv /tmp/${TOOLNAME} /opt/${TOOLNAME}
chown -R ${TOOLUSER}:${TOOLUSER} /opt/${TOOLNAME}

sudo bash /tmp/install.sh
