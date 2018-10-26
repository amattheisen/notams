### RUN AS ROOT
RUSER="notams"
TOOL="notams"
PORT=8091

echo Create ${RUSER} user as administrator.
# =====================================
useradd -m ${RUSER}
echo "${RUSER}:${RUSER}" | chpasswd
usermod -aG wheel ${RUSER}

echo Prepare /opt.
# ==============
chown -R ${RUSER}:${RUSER} /opt

echo Install EPEL YUM repo and YUM Packages.
# ========================
yum --enablerepo=updates clean metadata
yum install -y -q wget
wget http://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
rpm -ivh epel-release-latest-7.noarch.rpm
rm epel-release-latest-7.noarch.rpm
yum install -y -q $(cat /opt/${TOOL}/requirements.yum)

echo Set up ssh.
# ==============
su - ${RUSER} -c "mkdir /home/${RUSER}/.ssh"
chmod 700 /home/${RUSER}
chmod 700 /home/${RUSER}/.ssh
chmod 600 /home/${RUSER}/.ssh/id_rsa
chown -R ${RUSER}:${RUSER} /home/${RUSER}/.ssh
if [ -f /home/${RUSER}/.ssh/id_rsa ] && [ -f /home/${RUSER}/.ssh/id_rsa.pub ] ; then
    echo Using existing RSA keys.
    # ===========================
elif [ -f /home/${RUSER}/${RUSER}_id_rsa ] && [ -f /home/${RUSER}/${RUSER}_id_rsa.pub ] ; then
    echo "Adding canned RSA keys (for github.com)."
    # =============================================
    mv /home/${RUSER}/${RUSER}_id_rsa /home/${RUSER}/.ssh/id_rsa
    mv /home/${RUSER}/${RUSER}_id_rsa.pub /home/${RUSER}/.ssh/id_rsa.pub
    chmod 600 /home/${RUSER}/.ssh/id_rsa*
    chown ${RUSER}:${RUSER} /home/${RUSER}/.ssh/id_rsa*
else
    echo Creating New RSA keys.
    # =========================
    su - ${RUSER} -c 'ssh-keygen -f ~/.ssh/id_rsa -q -N ""'
fi

echo Allowing httpd thru Firewalld.
# =================================
firewall-cmd --zone=public --add-service=http --permanent

echo Installing and configuring screen.
# =====================================
# NOTE: (screen installed by default).
cp /opt/${TOOL}/vagrant/screenrc /home/${RUSER}/.screenrc
chown ${RUSER}:${RUSER} /home/${RUSER}/.screenrc

echo Installing and configuring oh my zsh.
# ========================================
chsh ${RUSER} -s /bin/zsh
su ${RUSER} -c "wget -nv https://raw.githubusercontent.com/robbyrussell/oh-my-zsh/master/tools/install.sh -O /home/${RUSER}/ohmyzsh.sh"
su - ${RUSER} -c "bash /home/${RUSER}/ohmyzsh.sh"
cp /opt/${TOOL}/vagrant/zshrc /home/${RUSER}/.zshrc
chown ${RUSER}:${RUSER} /home/${RUSER}/.zshrc

# conda
PATH=$PATH:/opt/conda/bin
CONDA_INSTALL=$(which conda);
if [ $CONDA_INSTALL = "/opt/conda/bin/conda" ] ; then
    echo Using existing conda installation.
    # =====================================
else
    echo Install conda.
    # =================
    rm -rf /opt/conda
    wget -nv https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh
    umask 000
    bash miniconda.sh -b -p /opt/conda
    umask 022
    sudo ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh
fi
echo Create conda environment for this tool.
# ==========================================
su - ${RUSER} -c "/opt/conda/bin/conda create -y -q --prefix /opt/conda/envs/${TOOL} python=3.7"
restorecon -Rv /opt/conda

echo "Installing conda & pip packages."
# =====================================
su - ${RUSER} -c "/opt/conda/bin/conda install --name ${TOOL} -c conda-forge --file /opt/${TOOL}/requirements.conda && /opt/conda/envs/${TOOL}/bin/pip install -q -r /opt/${TOOL}/requirements.pip"



echo Preparing SELINUX permissions for gunicorn
## ============================================
mkdir /opt/${TOOL}/static_notams/data || True
## Feed the SE Linux Beast.
setsebool -P httpd_can_network_connect on
semanage port -a -t http_port_t -p tcp ${PORT}   # allow httpd to serve tool port
semanage fcontext -a -t httpd_var_run_t "/opt/${TOOL}/.*\.py"
semanage fcontext -a -t httpd_sys_rw_content_t "/opt/${TOOL}/static_notams/data"
semanage fcontext -a -t httpd_sys_rw_content_t "/opt/${TOOL}/static_notams/images"
restorecon -Rv /opt/${TOOL}
## <SE LINUX NOTES>
##    semanage fcontext -l | grep /opt/${TOOL}  # list the selinux fcontexts
##    setenforce enforcing
##    setenforce permissive
## </NOTES>



echo Setting up Supervisord.
# ==========================
ln -sf -T /opt/${TOOL}/vagrant/supervisor.conf /etc/supervisord.d/${TOOL}.ini
systemctl enable supervisord
systemctl restart supervisord
supervisorctl reread
supervisorctl update
jobs=$(grep program /opt/${TOOL}/vagrant/supervisor.conf| grep -v ^# | sed 's/\[program://' | sed 's/\]//')
for job in $jobs; do
    supervisorctl restart $job
done

echo Installing nginx to server static files.
# ===========================================
rm /etc/nginx/nginx.conf
cp /opt/${TOOL}/vagrant/nginx.conf /etc/nginx/nginx.conf
ln -sf -T /opt/${TOOL}/vagrant/${TOOL}.conf /etc/nginx/conf.d/${TOOL}.conf
systemctl enable nginx
systemctl restart nginx

echo Setting up crontab to retrieve notams.
# =========================================
su - ${RUSER} -c "crontab -e < /opt/${TOOL}/vagrant/crontab.${RUSER}"
