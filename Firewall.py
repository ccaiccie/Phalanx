import ipsetpy
import logging
import re
import subprocess


class FirewallIpsets:
    def __init__(self, block_list, set_name, log_level):
        logging.basicConfig(format='%(asctime)s,%(levelname)s,%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p',
                            level=log_level)
        self.block_list = block_list
        self.set_name = set_name

    def create_ip_set(self):
        '''
        Create ipset based using variables provided to the Class at runtime. Sets length to match the length of the
        provided list to conserve memory.
        '''
        logging.debug("Setting IPSet Max Length")
        try:
            logging.debug("Creating IPSet")
            ipsetpy.ipset_create_set(self.set_name, "hash:ip", maxelem=len(self.block_list) + \
                                                                           (len(self.block_list)*float(0.1)))
            logging.info("IPSet %s Created", str(self.set_name))
        except:
            logging.error("IPSet Already Exists")

    def delete_old_set(self):
        '''
        List all current ipsets in memory and remove old ipsets that are no longer in use.
        '''
        name_regex = re.compile("^Name: ")
        count = 0
        logging.debug("Searching current IPSet Names")
        for ip_set in ipsetpy.ipset_list().splitlines():
            if re.search(name_regex, str(ip_set)):
                if ip_set.split(" ")[1] != self.set_name:
                    count = count + 1
                    logging.debug("Deleting old IPSet: %s", ip_set.split(" ")[1])
                    ipsetpy.ipset_destroy_set(ip_set.split(" ")[1])
        if count == 1:
            logging.info("Removed %s unused IPSet", str(count))
        else:
            logging.info("Removed %s unused IPSets", str(count))

    def convert_block_list_to_ipset(self):
        '''
        Loops through provided list and adds each IP address to the previously created ipset.
        '''
        for ip in self.block_list:
            logging.debug("Adding %s to %s", str(ip), str(self.set_name))
            ipsetpy.ipset_add_entry(self.set_name, ip, exist=True)
        logging.info("Added %s IP addresses to IPSet Name: %s", str(len(self.block_list)),str(self.set_name))

    @staticmethod
    def reset_chain(chain):
        '''
        Flushes all rules in chain.
        '''
        logging.info("Flushing all iptables rules in %s.", chain)
        subprocess.run(["iptables", "-F", chain])

    def drop_ipset_traffic(self, interface, chain, source_or_destination):
        '''
        Adds rule to chain dropping traffic based on interface, chain, and source or destination.
        '''
        logging.info("Adding rule to %s chain to drop inbound traffic on %s that a %s address in ipset: %s."\
                     , chain, interface, source_or_destination, self.set_name)
        if source_or_destination == "source":
            direction = "src"
        if source_or_destination == "destination":
            direction = "dst"
        subprocess.run(["iptables", "-A", chain.upper(), "-m", "set", "--match-set", self.set_name, direction, "-m",\
                        "physdev", "--physdev-in", interface, "-j" "LOGGING"])
