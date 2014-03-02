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



def parse_groups():
    if options.domain_groups is None:
        return None
    else:
        # seaprate out the groups
        tmp_groups = options.domain_groups.split(';')

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


def oldLaunch(options):
    print "Falling back to old options..."
    groups = parse_groups()

    print "Groups: " + str(groups)

    if options.destination != None:
        destination = options.destination
    else:
        print "Destination must be set!"
        sys.exit(0)

    handlers = list()
    managers = list()

    # setup a handler and manager for each group
    for group in groups:
        handlers.append( VirshHandler.virsh_handler(destination, group, options.max_latency) )

        handlers[-1].set_running_vms_speed(options.migration_bandwidth)

        managers.append(Manager.MigrationManager(handlers[-1].running_vms, destination, options.migrate_storage, options.max_latency))

    for manager in managers:
        if options.migration_method == 'serial':
            manager.serial_migration()
        elif options.migration_method == 'parallel':
            manager.parallel_migration()
        elif options.migration_method == None:
            manager.serial_migration()

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
                help="Specify groups of VMs, nodes in group are comma separated, groups are ; separated")

    parser.add_option("-d","--destination",dest="destination",
                help="What host to migrate the machines to")

    parser.add_option("-c","--config-path",dest="config_path",
                help="Path to an ini-like config file")

    (options, args) = parser.parse_args()

    config_map = None
    if options.config_path != None:
        config_map = loadConfig(options.config_path)
    else:
        oldLaunch(options)

    settings = Manager.MigrationSettings(config_map)

    print str(settings)

