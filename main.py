import json
import logging
import os
import argparse
import requests
from datetime import datetime
from ListActions import ContactSite, CondenseList
from Firewall import FirewallIpsets
from SetDefaults import NetworkSetup, FirewallSetup

config_file = "/opt/phalanx/config.json"
now = datetime.now()
run_time = str(now.strftime("%m/%d/%Y-%H:%M"))

parser = argparse.ArgumentParser(prog="Phalanx", description="Firewall automation program that builds a transparent \
                                firewall using publicly available threat feeds.")

parser.add_argument("-S", "--setup", dest="setup", \
                    help="Setup configuration file", action="store_true", default=False)
parser.add_argument("-u", "--update", dest="update", \
                    help="Update Block-list file.", action="store_true", default=False)
parser.add_argument("-v", "--verbosity", dest="verbosity", \
                    help="Increase output verbosity", action="store_true", default=False)
parser.add_argument("-vv", "--debug", dest="debug", \
                    help="Set verbosity to debug", action="store_true", default=False)

args = parser.parse_args()

if args.verbosity is True:
    log_level = logging.INFO
elif args.debug is True:
    log_level = logging.DEBUG
else:
    log_level = logging.WARN

logging.basicConfig(format='%(asctime)s,%(levelname)s,%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=log_level)

logging.debug("Reading Configuration File: %s", config_file)
if not os.path.exists(config_file):
    logging.critical("Missing Configuration File: %s", config_file)
    logging.critical("Ensure %s is located in %s", config_file, path)
with open(config_file, 'r') as file:
    config = json.load(file)
    file.close()

if args.setup is True or config["Setup_Ran"] == "False":
    logging.info("Configuration File Loaded")
    logging.info("Checking config file for interface name.")
    if config["WAN0"] == "" or config["WAN1"] == "":
        logging.info("Running first time setup to select bridge interfaces.")
        bridge_interfaces = NetworkSetup(log_level).bridge_setup()
        config.update({"WAN0": bridge_interfaces[0]})
        config.update({"WAN1": bridge_interfaces[1]})
        config.update({"MAN": bridge_interfaces[2]})
    else:
        logging.warning("Bridge already configured in Config File.")
        modify_config_ack = input("Do you want to modify the current bridge interfaces?\nRename interfaces? Y/N: ")
        if modify_config_ack not in ["y", "n", "yes", "no"]:
            modify_config_ack = input("Please enter Y/N")
        if modify_config_ack.casefold() == "N".casefold():
            logging.warning("Leaving current settings in configuration file.")
        elif modify_config_ack.casefold() == "Y".casefold():
            bridge_interfaces = NetworkSetup(log_level).bridge_setup()
            config.update({"WAN0": bridge_interfaces[0]})
            config.update({"WAN1": bridge_interfaces[1]})
            config.update({"MAN": bridge_interfaces[2]})
    config.update({"Setup_Ran": "True"})
    with open(config_file, "w") as file:
        json.dump(config, file, sort_keys=True, indent=4)
        file.close()

elif args.update is True:
    ip_block_list = config["path"] + "/" + config["ip_block"]
    dshield_success = True
    talos_success = True
    otx_success = False
    dshield = []
    talos = []
    otx = []
    try:
        dshield = ContactSite(config['dshield'], log_level).isc_dshield()
        dshield_success = True
    except requests.exceptions.ConnectionError:
        dshield_success = False
        logging.warning("Failed to connect to dshield.")
    try:
        talos = ContactSite(config['cisco_talos'], log_level).cisco_talos()
        talos_success = True
    except requests.exceptions.ConnectionError:
        talos_success = False
        logging.warning("Failed to connect to CISCO Talos.")
    try:
        otx = ContactSite(config['otx'], log_level).alien_vault()
        otx_success = True
    except requests.exceptions.ConnectionError:
        otx_success = False
        logging.warning("Failed to connect to AlienVault OTX.")
    union = []
    for site in ((dshield_success, dshield), (talos_success, talos), (otx_success, otx)):
        if site[0] is True:
            union.append(site[1])
    block_list = set().union(*union)
    logging.debug("Sorting block list by ip address and saving to file: %s", ip_block_list)
    with open(ip_block_list, "w") as file:
        for ip in sorted(block_list, key=lambda ip: (int(ip.split(".")[0]), int(ip.split(".")[1]),\
                                                     int(ip.split(".")[2]), int(ip.split(".")[3]))):
            file.write(str(ip) + "\n")
        file.close()
    logging.info("Block List saved to file:%s", ip_block_list)
    compressed_list = CondenseList(ip_block_list, log_level).compress()
    with open(ip_block_list, "w") as file:
        logging.info("Compressed block list saved as JSON to file:%s", ip_block_list)
        json.dump(compressed_list, file, sort_keys=True, indent=4)
        file.close()

else:
    for interface in ["WAN0", "WAN1", "MAN"]:
        if NetworkSetup(log_level).check_int_names(interface) is None:
            NetworkSetup(log_level).rename_int_name(config[interface], interface)
    if NetworkSetup(log_level).check_int_names("br0") is None:
        NetworkSetup(log_level).bridge_setup_interfaces("WAN0", "WAN1")

    FirewallSetup(log_level).setup_logging_chain()
    FirewallSetup(log_level).reset_chain("INPUT")
    FirewallSetup(log_level).set_management_icmp(config["ALLOW_ICMP"])
    for port in config["MAN_Dst_Ports"]:
        FirewallSetup(log_level).set_management_ports(port[0], port[1], "destination")
    for port in config["MAN_Src_Ports"]:
        FirewallSetup(log_level).set_management_ports(port[0], port[1], "source")
    FirewallSetup(log_level).set_management_default_drop()
    ip_block_list = config["path"] + "/" + config["ip_block"]
    with open(ip_block_list, "r") as file:
        ips_and_cidrs = json.load(file)
        file.close()
    FirewallIpsets(ips_and_cidrs, run_time, log_level).create_ip_set()
    FirewallIpsets(ips_and_cidrs, run_time, log_level).convert_block_list_to_ipset()
    FirewallIpsets(ips_and_cidrs, run_time, log_level).delete_old_set()
    FirewallIpsets(ips_and_cidrs, run_time, log_level).reset_chain("FORWARD")
    FirewallIpsets(ips_and_cidrs, run_time, log_level).drop_ipset_traffic("WAN0", "FORWARD", "source")
    FirewallIpsets(ips_and_cidrs, run_time, log_level).drop_ipset_traffic("WAN1", "FORWARD", "destination")