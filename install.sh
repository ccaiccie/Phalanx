#!/bin/bash
# Phalanx Install and setup script.

if [ ! "$userid" = "0" ]; then
   echo "You have to run this script as root. eg."
   echo "  sudo install.sh"
   echo "Exiting."
   echo ${LINE}
   exit 9
else
   do_log "Check OK: User-ID is ${userid}."
fi

if [ "$ID" == "ubuntu" ] ; then
   dist='apt'
   distversion="ubuntu"
fi

if [ "$dist" == "apt" ]; then
   echo "Updating package manager"
   run 'apt update'
   echo "Updating package manager"
   run 'apt upgrade -y'
   run 'apt install -y -q python3 git'
   run '/usr/local/bin/python3 -m pip install pip3'
   run 'pip3 install requests'
   run 'pip3 install ipsetpy'
   run 'git clone https://github.com/sanyi/ipsetpy.git'
   run 'rm /usr/local/lib/python3.6/dist-packages/ipsetpy/wrapper.py'
   run 'cp ipsetpy/wrapper.py /usr/local/lib/python3.6/dist-packages/ipsetpy/wrapper.py'
   run 'rm -R ipsetpy'
   run 'mv iprange /usr/local/bin/iprange'
   run 'mkdir /opt/phalanx'
   run 'mv *.py /opt/phalanx'
   run 'mv *.py /opt/phalanx'
   run 'python3 /opt/phalanx/main.py -s'
   run 'python3 /opt/phalanx/main.py -u'
   run ' ln -s /opt/phalanx/main.py /usr/local/bin/main.py'
   run 'cp phalanx-startup.service /lib/systemd/system'
   run 'systemctl daemon-reload'
   run 'systemctl enable phalanx-startup.service'
fi

echo "Install complete!"
echo "To update the block list run python3 main.py -u"
echo "To update the firewall rules run python3 main.py"
echo "These should be setup as cron jobs for automated updates"
