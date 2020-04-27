!/bin/bash
# Phalanx Install and setup script.

echo "Updating package manager"
run 'apt update'
echo "Updating package manager"
apt upgrade -y
apt install -y -q python3-pip
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
python3 /opt/phalanx/main.py -S
python3 /opt/phalanx/main.py -u
cp phalanx-startup.service /lib/systemd/system
systemctl daemon-reload
systemctl enable phalanx-startup.service
cd ../
rm -R Phalanx

echo "Install complete!"
echo "To update the block list run python3 main.py -u"
echo "To update the firewall rules run python3 main.py"
echo "These should be setup as cron jobs for automated updates"
