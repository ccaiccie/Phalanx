!/bin/bash
# Phalanx Install and setup script.

echo "Updating package manager"
run 'apt update'
echo "Updating package manager"
apt upgrade -y
apt install -y -q python3-pip ipset
pip3 install requests
pip3 install ipsetpy
git clone https://github.com/sanyi/ipsetpy.git
mv /usr/local/lib/python3.8/dist-packages/ipsetpy/wrapper.py /usr/local/lib/python3.8/dist-packages/ipsetpy/wrapper.py.old
cp ipsetpy/ipsetpy/wrapper.py /usr/local/lib/python3.8/dist-packages/ipsetpy/wrapper.py
rm -R ipsetpy
mv iprange /usr/local/bin/iprange
chmod +x /usr/local/bin/iprange
mkdir /opt/phalanx
mv *.py /opt/phalanx
mv *.json /opt/phalanx
cd ../
rm -R Phalanx
clear
echo "Adding crontab entry to run script on boot"
crontab -l | { cat; echo "@reboot python3 /opt/phalanx/main.py&"; } | crontab -
echo "Adding crontab entry to update block lists daily at 1:00am"
crontab -l | { cat; echo "0 1 * * * python3 /opt/phalanx/main.py -u&"; } | crontab -
echo "Adding crontab entry to update firewall with new blocklist daily at 1:30am"
crontab -l | { cat; echo "30 1 * * * python3 /opt/phalanx/main.py&"; } | crontab -
echo
echo
echo
python3 /opt/phalanx/main.py -S
echo
python3 /opt/phalanx/main.py -u
echo
python3 /opt/phalanx/main.py
echo
echo "Install complete!"
echo "To update the block list run python3 /opt/phalanx/main.py -u"
echo
echo "To update the firewall rules run python3 /opt/phalanx/main.py"
echo
echo "To change cron automated tasks run: sudo crontab -e"
