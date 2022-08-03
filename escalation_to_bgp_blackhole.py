#!/usr/bin/python3
 
import requests
import os
import re
import sys
import time
import urllib.request, urllib.parse, urllib.error
import random
import logging
import subprocess

# If blackholed host exceed these values we will run gobgp announce to blackhole it
incoming_mbits_threshold = 100
outgoing_mbits_threshold = 100

incoming_packets_threshold = 2000
outgoing_packets_threshold = 2000

# Please use here only 16 bit communities
bgp_community = '65001:777'

bgp_next_hop = '11.22.33.44'
 
# Please set correct password here
auth_data = ('admin', 'your_password_replace_it')

# Script logic starts
logging.basicConfig(filename='/tmp/escalation_to_bgp_blackhole.py.log', format='%(asctime)s %(message)s', level=logging.DEBUG)

blackholed_hosts = requests.get('http://127.0.0.1:10007/blackhole',  auth=auth_data)

if blackholed_hosts.status_code != 200:
    logging.warn("Can't get list of blackholed hosts with error code: " + str(r.status_code))
    sys.exit(1)

if not blackholed_hosts.json()['success']:
    logging.warn("API method blackhole returned error " + r.json()['error_text'])
    sys.exit(1)

blackholed_ip_addresses = []

for blackholed_entity in blackholed_hosts.json()['values']:
    blackholed_ip = blackholed_entity['ip'].replace('/32', '', -1)
    blackholed_ip_addresses.append(blackholed_ip)

if len(blackholed_ip_addresses) == 0:
    # logging.info("We have zero blackholed IP addresses")
    sys.exit(0)

logging.warn("We have %d blackholed IP addresses" % len(blackholed_ip_addresses))

# Here we keep list of networks which should be blocked
already_blocked_networks = []

for ip_address in blackholed_ip_addresses:
    r = requests.get('http://127.0.0.1:10007/single_host_counters/' + ip_address, auth=auth_data)

    if r.status_code != 200: 
        logging.warn("Can't get counters for host " + ip_address + " status code: " + str(r.status_code))
        sys.exit(1)

    if not r.json()['success']:
       logging.warn("API method returned error " + r.json()['error_text'])
       sys.exit(1)

    metrics = r.json()['object']

    threshold_crossed = False

    incoming_bandwidth = metrics['in_bytes']/1000/1000*8
    outgoing_bandwidth = metrics['out_bytes']/1000/1000*8

    if incoming_bandwidth >= incoming_mbits_threshold:
        logging.info("Host crossed incoming mbit threshold: %d mbits with traffic: %d Mbits" % (incoming_mbits_threshold, incoming_bandwidth))
        threshold_crossed = True

    if outgoing_bandwidth >= outgoing_mbits_threshold:
        logging.info("Host crossed outgoing mbit threshold: %d mbits with traffic: %d Mbits" % (outgoing_mbits_threshold, outgoing_bandwidth))
        threshold_crossed = True

    if metrics['in_packets'] >= incoming_packets_threshold:
        logging.info("Host crossed incoming packet per second threshold %d with traffic %d" %(incoming_packets_threshold, metrics['in_packets']))
        threshold_crossed = True

    if metrics['out_packets'] >= outgoing_packets_threshold: 
        logging.info("Host crossed outgoing packet per second threshold %d with traffic %d" %(outgoing_packets_threshold, metrics['out_packets']))
        threshold_crossed = True

    if threshold_crossed:
        logging.info("We will apply escalation rule")
        ip_address_with_last_zero_octet = re.sub('\.\d+$', '.0', ip_address)

        subnet = ip_address_with_last_zero_octet + "/24"

        already_blocked_networks.append(subnet)
 
        # Load active announces
        active_announces = subprocess.check_output("gobgp global rib -a ipv4", shell=True)

        active_announcess_array = active_announces.split("\n")
 
        already_blocked = False

        for active_announces_line in active_announcess_array:
            if subnet in active_announces_line:
                already_blocked = True
 
        if not already_blocked:
            command = "gobgp global rib add -a ipv4 " + subnet + " community " + bgp_community + " nexthop " + bgp_next_hop 
            logging.info("Will execute following command: " + command)
    
            res = subprocess.call(command, shell=True)

            if res != 0:
                logging.warn("Failed to announce affected subnet")
        else:
            logging.info("This subnet was already announced")

# Here we will remove /24 announces if host was unblocked on FastNetMon's side
logging.info("Should be locked networks:" + str(already_blocked_networks))

all_active_announces = subprocess.check_output("gobgp global rib -a ipv4", shell=True)

all_announced_networks = []

for active_announces_line in active_announcess_array:
    if 'AS_PATH' in active_announces_line:
        continue
       
    if '/24' not in active_announces_line:
        continue 

    splitted_line = re.split(r'\s+', active_announces_line)

    all_announced_networks.append(splitted_line[1])

for announced_network in all_announced_networks:
    if announced_network in already_blocked_networks:
        logging.info("Network " + str(announced_network) + " should be active")
        continue

    logging.info("We should remove this subnet " + announced_network)
    command_to_remove = "gobgp global rib del -a ipv4 " + announced_network
    logging.info("Execute command: " + command_to_remove)

    res = subprocess.call(command_to_remove, shell=True)

    if res != 0:
        logging.info("Can't remove subnet")
