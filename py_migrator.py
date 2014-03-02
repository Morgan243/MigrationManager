#!/usr/bin/python2
import os
import socket
import libvirt
import sys
import threading
import time
import Manager
import VirshHandler
import MigratorThread
import ConfigParser
from optparse import OptionParser


def parse_groups(groups_str):
    # separate out the groups
    tmp_groups = groups_str

    groups = list()

    # separate out nodes in the group
    for group in tmp_groups:
        groups.append(group.split(','))

    #remove extra whitespace from nodes
    for group in groups:
        for node in group:
            node.strip()
        group.sort()

    return groups


def loadConfig(config_path):
    config_map = dict()
    config = ConfigParser.ConfigParser()
    config.read(config_path)

    for section in config.sections():
        for option in config.options(section):
            try:
                config_map[(section, option)] = config.get(section, option)
                print option + " :: " + config_map[(section, option)]
            except:
                print "Exception loading " + option + " in section " + section
    return config_map 

def loadOptions(options, config_map):
    if config_map == None:
        print "Config map is NONE in loadOptions!"
        config_map = dict()

    if options.destination != None:
        config_map[ ("main", "destination") ] = options.destination

    if options.domain_groups != None:
        config_map[ ("main", "vms") ] = options.domain_groups

    if options.migration_method != None:
        config_map[ ("options", "grouping") ] = options.migration_method

    print str(config_map)


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-m","--method",dest="migration_method",
                help="How to migrate: serial or parallel (default = serial)")

    parser.add_option("-b","--bandwidth",dest="migration_bandwidth",default=32,
                help="Bandwidth to allocate to each migration (Mbps) (default = 32)")

    parser.add_option("-l","--max-latency",dest="max_latency",
                help="Force migration to suspend and finish offline after the specified time (seconds)")

    parser.add_option("-t","--max-downtime",dest="max_downtime",
                help="Set the maximum tolerable downtime for hosts (milliseconds)")

    parser.add_option("-s","--storage",dest="migrate_storage", default=False, action="store_true",
                help="Perform storage migration. Be sure storage is allocated on destination")

    parser.add_option("-g","--group",dest="domain_groups",
                help="Specify groups of VMs, nodes in group are comma separated, groups are : separated")

    parser.add_option("-d","--destination",dest="destination",
                help="What host to migrate the machines to")

    parser.add_option("-p","--physical-hosts", dest="pm_hosts", default = None,
                help="CSV of hosts that are running a hypervisor that are running any of the VMs included in other options. " +
                "If this option isn't used, then only the host this is run on will be included in checks. The PM used in destination " + 
                "will automatically be included, but can also be included here if you wish")

    parser.add_option("-c","--config-path",dest="config_path",
                help="Path to an ini-like config file, options set here will be overwritten with synonomous CLI options")

    (options, args) = parser.parse_args()

    config_map = None
    if options.config_path != None:
        config_map = loadConfig(options.config_path)
    else:
        config_map = dict()

    loadOptions(options, config_map)

    settings = Manager.MigrationSettings(config_map)

    print str(settings)
    #manager = Manager.libvirt_MigrationManager(settings)
    #manager.doMigration()
