import requests
import re
import ipaddress
import subprocess
import logging


class ContactSite:
    def __init__(self, site_url, log_level):
        logging.basicConfig(format='%(asctime)s,%(levelname)s,%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p',
                            level=log_level)
        self.response = requests.get(site_url)
        self.regex_ip = re.compile("\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")

    def alien_vault(self):
        '''
        AlienVault posts their IP Reputation list with the IP starting the line followed a space and hash comment. The
        comment lists the reputation type, country or origin, and GPS coordinates for the IP. This function strips
        everything out of the line and does a regex match on the IP address. It then validates that the IP is globally
        routable before appending the IP to the raw list.
        '''
        raw_list = []
        logging.debug("Downloading list from AlientVault")
        if self.response.status_code == 200:
            logging.debug("Successfully connected to AlienVault")
            for line in str.split(self.response.text, "\n"):
                if re.search(self.regex_ip, str(line).split(' ')[0]):
                    if ipaddress.ip_address(str(line).split(' ')[0]).is_global:
                        raw_list.append(str(line).split(' ')[0])
                    else:
                        pass
            return raw_list
        if self.response.status_code != 200:
            logging.error("AlientVault URL returned: %s status code", self.response.status_code)

    def cisco_talos(self):
        '''
        CISCO Talos posts IP addresses as single lines containing one IP address per line. This function takes each line
        and does a regex search to validate that the line contains a properly formatted IP address. If the IP address is
        a globally routable IP address it appends the IP to the end of the Raw list which is returned by the function.
        '''
        raw_list = []
        logging.debug("Downloading list from CISCO Talos")
        if self.response.status_code == 200:
            for line in str.split(self.response.text, "\n"):
                if re.search(self.regex_ip, str(line)):
                    if ipaddress.ip_address(line).is_global:
                        raw_list.append(str(line))
                    else:
                        pass
            return raw_list
        if self.response.status_code != 200:
            logging.error("CISCO Talos URL returned: %s status code", self.response.status_code)

    def isc_dshield(self):
        '''
        ISC DSheild posts IP addresses in a manner similar to a WHOIS record therefore blocks are lists in netblocks.
        This takes those netblocks, transforms them into CIDR notation, enumerates all IP addresses within the netblock,
        and ff the IP address is a globally routable IP address it appends the IP to the end of the Raw list which is
        returned by the function.
        '''
        raw_list = []
        logging.debug("Downloading list from ISC")
        if self.response.status_code == 200:
            for line in str.split(self.response.text, "\n"):
                if re.search(self.regex_ip, str(str.split(line, '\t'))):
                    for ip in ipaddress.IPv4Network(str.split(line, '\t')[0] + '/' + str.split(line, '\t')[2]):
                        if ipaddress.ip_address(ip).is_global:
                            raw_list.append(str(ip))
                        else:
                            pass
            return raw_list
        if self.response.status_code != 200:
            logging.error("ISC URL returned: %s status code", self.response.status_code)


class CondenseList:
    def __init__(self, file, log_level):
        logging.basicConfig(format='%(asctime)s,%(levelname)s,%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p',
                            level=log_level)
        self.file = file

    def compress(self):
        logging.debug("Sending block list file to iprange to compress and extract CIDRs")
        ip_range_output = subprocess.run(["/usr/local/bin/iprange", "--optimize", self.file], stdout=subprocess.PIPE)
        return str(ip_range_output.stdout, "utf-8").splitlines()
