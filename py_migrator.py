#!/usr/bin/python
import os
import socket
#import libvirt
import sys
import threading
import time
import Manager
import VirshHandler
import MigratorThread
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-m","--method",dest="migration_method",
            help="How to migrate: serial or parallel (default = serial)")

parser.add_option("-b","--bandwidth",dest="migration_bandwidth",
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

(options, args) = parser.parse_args()

def parse_groups():
    print "hey"
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

    if options.migration_bandwidth == None:
        handlers[-1].set_running_vms_speed(32)
    else:
        handlers[-1].set_running_vms_speed(options.migration_bandwidth)

    managers.append(Manager.MigrationManager(handlers[-1].running_vms, destination, options.migrate_storage))

for manager in managers:
    if options.migration_method == 'serial':
        manager.serial_migration()
    elif options.migration_method == 'parallel':
        manager.parallel_migration()
    elif options.migration_method == None:
        manager.serial_migration()
