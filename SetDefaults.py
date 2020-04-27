import subprocess
import os, sys
import logging


class NetworkSetup:
    def __init__(self, log_level):
        '''
        Checks that the script is being run with Root Privileges.
        Runs native linux ip command and pulls all interface information to include interface name, type,
        and mac address. Creates a list of all interfaces that are not loopback or bridges and generates a dictionary
        that is used later to provide information to the user running the script.
        '''
        logging.basicConfig(format='%(asctime)s,%(levelname)s,%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p',
                            level=log_level)
        if not os.geteuid()==0:
            sys.exit("This must be run as root.")
        raw_odd_links = []
        raw_even_links =[]
        self.links_joined = []
        self.links = {}
        logging.debug("Getting list of interfaces from the system.")
        get_links = subprocess.run(["ip", "link"], capture_output=True)
        raw_links = str(get_links.stdout.decode("utf-8")).split("\n")
        for i in range(0, len(raw_links)):
             if i % 2:
                 raw_even_links.append(raw_links[i])
             else:
                 raw_odd_links.append(raw_links[i])
        for i in range(0, len(raw_even_links)):
            odd_link = raw_even_links[i]
            self.links_joined.append(raw_odd_links[i] + " " + odd_link.lstrip())
        for link in self.links_joined:
            if link.split(" ")[1].strip(":") not in ["lo", "br0"]:
                self.links[str(int(link.split(" ")[0].strip(":"))-1)] = {"name":link.split(" ")[1].strip(":"), \
                        "type": link.split(" ")[15], "mac":link.split(" ")[16]}

    def check_int_names(self, interface):
        links = []
        for link in self.links_joined:
            if link.split(" ")[1].strip(":") not in ["lo"]:
                links.append(link.split(" ")[1].strip(":"))
        if interface in links:
            return interface

    @staticmethod
    def rename_int_name(interface, name):
        logging.warning("Shutting down interface %s.", interface)
        subprocess.run(["ip", "link", "set", interface, "down"])
        logging.warning("Renaming interface %s to %s.", interface, name)
        subprocess.run(["ip", "link", "set", interface, "name", name])
        logging.warning("Interface %s coming online.", name)
        subprocess.run(["ip", "link", "set", name, "up"])

    @staticmethod
    def bridge_setup_interfaces(interface0, interface1):
        '''
        Change interface names, bridge interfaces to Promiscuous mode and build bridge.
        '''
        logging.debug("Setting bridge interfaces to promiscuous mode.")
        for i in [interface0, interface1]:
            logging.warning("Shutting down interface %s.", i)
            subprocess.run(["ip", "link", "set", "dev", i, "down"])
            logging.debug("Checking if %s is in promiscuous mode.", i)
            link_promiscuous_check = subprocess.run(["ip", "a", "show", i], capture_output=True)
            if "PROMISC" in str(link_promiscuous_check.stdout.decode("utf-8")).split(","):
                logging.debug("%s: Already in promiscuous mode.", i)
            else:
                subprocess.run(["ip", "link", "set", i, "promisc", "on"])
            logging.debug("Creating bridge")
            subprocess.run(["ip", "link", "add", "name", "br0", "type", "bridge"])
            subprocess.run(["ip", "link", "set", "dev", "br0", "up"])
            subprocess.run(["ip", "link", "set", "dev", i, "master", "br0"])
            logging.warning("Interface %s coming online.", i)
            subprocess.run(["ip", "link", "set", "dev", i, "up"])

    def bridge_setup(self):
        '''
        Takes input from the user and generates default configuration for the bridge interface and saves the bridge
        information to the config file.
        '''
        logging.info("Loading Configuration File")
        logging.info("Configuration File Loaded")
        logging.debug("Setting up Bridge Network.")
        print("Please follow prompts to setup bridge interface.")
        print("Link Number:" + "\t" + "Link Name:" + "\n")
        link_number = 0
        for link in self.links:
            link_number += 1
            for i in link:
                print(str(i) + "\t\t" + self.links[i]["name"])
        while True:
            wan0 = input("Enter number for WAN0 / ISP interface: ")
            wan1 = input("Enter number for WAN1 / Your Router interface: ")
            management = input("Enter number for Management interface: ")
            if wan0 == wan1 or wan0 == management:
                print("You have entered the same interface twice; please try again.\n")
                continue
            elif wan1 == wan0 or wan1 == management:
                print("You have entered the same interface twice; please try again.\n")
                continue
            try:
                if int(wan0) > link_number or int(wan1) > link_number or int(management) > link_number:
                    print("You have entered a number not in the list; please try again.\n")
                    continue
            except ValueError:
                print("One of your entries is not a number; please try again.\n")
                continue
            else:
                break
        return self.links[wan0]["name"], self.links[wan1]["name"], self.links[management]["name"]


class FirewallSetup:
    '''
    Ensure logging is properly setup and default rules are configured for managment interface.
    '''
    def __init__(self, log_level):
        logging.basicConfig(format='%(asctime)s,%(levelname)s,%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p',
                            level=log_level)
        self.list_iptables_rules = subprocess.run(["iptables", "-S"], capture_output=True)

    def setup_logging_chain(self):
        logging.info("Checking for iptables Logging Chain.")
        if "-N LOGGING" not in self.list_iptables_rules.stdout.decode("utf-8"):
            logging.info("Adding iptables Logging Chain.")
            subprocess.run(["iptables", "-N", "LOGGING"])
        else:
            logging.info("Logging Chain already in iptables.")
        if "-m limit" not in self.list_iptables_rules.stdout.decode("utf-8"):
            logging.info("Adding iptables Logging rate limit.")
            subprocess.run(["iptables", "-A", "LOGGING", "-m", "limit", "--limit", "2/min", "-j", "LOG",\
                            "--log-prefix", "Firewall-Dropped: "])
        else:
            logging.info("Logging rate limit already in iptables.")
        if "-A LOGGING -j DROP" not in self.list_iptables_rules.stdout.decode("utf-8"):
            logging.info("Adding iptables Logging default drop rule.")
            subprocess.run(["iptables", "-A", "LOGGING", "-j", "DROP"])
        else:
            logging.info("Logging default drop rule already in iptables.")

    @staticmethod
    def reset_chain(chain):
        '''
        Flushes all rules in chain.
        '''
        logging.info("Flushing all iptables rules in %s.", chain)
        subprocess.run(["iptables", "-F", chain])

    def set_management_icmp(self, config_setting):
        logging.info("Allow icmp set to %s in config.", config_setting)
        if config_setting == "True":
            if "-p icmp -j ACCEPT" not in self.list_iptables_rules.stdout.decode("utf-8"):
                logging.info("Adding rule allowing icmp in iptables.")
                subprocess.run(["iptables", "-A", "INPUT", "-i", "MAN", "-p", "icmp", "-j", "ACCEPT"])
            else:
                logging.info("Rule allowing icmp in already in iptables.")

    def set_management_ports(self, protocol, port, source_or_destination):
        logging.info("Checking for iptables allows traffic to %s.", port)
        if source_or_destination == "source":
            direction = "--sport"
        if source_or_destination == "destination":
            direction = "--dport"
        if "-p " + protocol + " --dport " + port not in self.list_iptables_rules.stdout.decode("utf-8"):
            logging.info("Adding iptables rule allowing %s/%s.", protocol, port)
            subprocess.run(["iptables", "-A", "INPUT", "-i", "MAN", "-p", protocol, direction, port, "-j", "ACCEPT"])
        else:
            logging.info("Rule allowing traffic via %s/%s already in iptables.", protocol, port)

    def set_management_default_drop(self):
        logging.info("Checking if MAN default drop rule is in iptables.")
        if "-j LOGGING" not in self.list_iptables_rules.stdout.decode("utf-8"):
            logging.info("Adding MAN default drop rule to iptables.")
            subprocess.run(["iptables", "-A", "INPUT", "-i", "MAN", "-j", "LOGGING"])
        else:
            logging.info("Default drop rule for MAN interface already in iptables.")