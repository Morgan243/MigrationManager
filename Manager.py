import os
import socket
import libvirt
import sys
import threading
import time
import MigratorThread
import VirshHandler
from collections import namedtuple

OptionDesc = namedtuple('OptionDesc', 'config_tuple store_in parse')

class MigrationSettings:
    """
    Container for settings that multiple objects may need accessed to
    """
    def __init__(self, config_map = None):
        self.print_br = "\n"
        self.config_map = config_map

        self.p_host_pairs = list()
        self.unique_hosts = list()

        self.vm_groups = None
        self.destination = None

        self.bandwidth = None
        self.max_latency = None
        self.grouping = "serial"
        self.move_storage = False
        self.enable_benchmarking = False
        self.bench_name = None
        self.bench_iterations = 0
        self.bench_result_file = None

        if self.config_map != None:
            self.loadOptions(self.config_map)
        else:
            print "not config map provided!!!"

    def __str__(self):
        return ("hosts :: " + str(self.p_host_pairs) + 
                                    self.print_br +
                "vm groups :: " + str(self.vm_groups) + 
                                    self.print_br +
                "grouping :: " + self.grouping + 
                                    self.print_br +
                "storage migration :: " + str(self.move_storage) + 
                                    self.print_br +
                "badnwidth :: " + str(self.bandwidth))


    def loadOptions(self, config_map):
        """
        Parses through the config_map dictionary and parses them into the appriopriate variables and structures
        """
        print "Loading options"
        for option, value in config_map.items():

            if option == ("main", "hosts"):
                self.parseHosts(value)

            elif option == ("main", "destination"):
                self.destination = value.strip()

            elif option == ("main", "vms"):
                self.vm_groups = self.parseGroups(value)

            elif option == ("options", "bandwidth"):
                self.bandwidth = int(value)

            elif option == ("options", "grouping"):
                self.grouping = value.strip()

            elif option == ("options", "storage"):
                self.move_storage = self.checkTorF(value)

            elif option == ("options", "max_latency"):
                self.max_latency = int(value)

            elif option == ("benchmarking", "enabled"):
                self.enable_benchmarking = self.checkTorF(value)

            elif option == ("benchmarking", "benchmark"):
                self.bench_name = value.strip()

            elif option == ("benchmarking", "iterations"):
                self.bench_iterations = int(value)

            elif option == ("benchmarking", "output"):
                self.bench_result_file = value.strip()


    def parseGroups(self, vm_groups):
        """
        Interpret the VM groups string (provided as "vms" option in cofig)
        Groups are seperated by ':' and members of the group are seperated by ','
        RETURNS-> A list of group lists
        """
        # separate out the groups
        tmp_groups = vm_groups.split(':')

        groups = list()

        # separate out nodes in the group
        for group in tmp_groups:
            groups.append(group.strip().split(','))

        #remove extra whitespace from nodes
        for group in groups:
            for node in group:
                node.strip()
            group.sort()

        return groups


    def checkTorF(self, string):
        """
        Simply check if string is "true" or not
        RETURNS-> bool
        """
        if string.lower() == "true":
            return True
        else:
            return False

    def parseHosts(self, hosts):
        """
        Interpret hosts string (provided as "hosts" optin in config)
        Can specify pairs of PMs using ':' and members of pairs with ','
        """
        groups = hosts.split(':')
        self.p_host_pairs = list()

        for group in groups:
            group_hosts = group.strip().split(',')
            self.p_host_pairs.append( (group_hosts[0].strip(), group_hosts[1].strip()) )

            self.unique_hosts.append(group_hosts[0].strip())
            self.unique_hosts.append(group_hosts[1].strip())

class libvirt_MigrationManager:
    """
    Aggregates connections made by Virsh Handler and builds MigratorThreads using them. 
    Interfaces allow the launching of different migration strategies
    """
    def __init__(self, settings):
        self.settings = settings
        self.libvirt_handle = VirshHandler.libvirt_Handler( settings.unique_hosts )

        self.all_domains = self.libvirt_handle.getVMs()
        self.threads = list()

        self.buildMigrators()

        self.header_csv = ""
        self.result_latency_csv = ""

    # make a thread for each thread that needs migrating
    def buildMigrators(self):
        # go through hsot pairs
        for host_pair in self.settings.p_host_pairs:
            src_vms = self.libvirt_handle.getVMs(host_pair[0])
            dest_vms = self.libvirt_handle.getVMs(host_pair[1])

            # build migrators for both source and destination

            #print "DEST: " + str([ str(vm.name()) for vm in src_vms ])
            print "SRC: ",
            # go through all VMs on source PM
            for vm in src_vms:
                # no VMs explicitly specified, so move them all
                if self.vm_groups == None:
                    print vm.name() + ", ",
                    ips = (self.libvirt_handle.host_ips[host_pair[0]], self.libvirt_handle.host_ips[host_pair[1]])
                    mig_thread = MigratorThread.libvirt_Migrator(vm, self.libvirt_handle.host_connections[host_pair[0]],
                                                                    self.libvirt_handle.host_connections[host_pair[1]],
                                                                    self.settings.move_storage, int(self.settings.bandwidth),
                                                                    host_ips = ips)
                    self.threads.append( mig_thread )


            #print "DEST: " + str([ str(vm.name()) for vm in dest_vms ])
            print "DEST: ",
            for vm in dest_vms:
                if self.vm_groups == None:
                    print vm.name() + ", ",
                    ips = (self.libvirt_handle.host_ips[host_pair[0]], self.libvirt_handle.host_ips[host_pair[1]])
                    mig_thread = MigratorThread.libvirt_Migrator(vm, self.libvirt_handle.host_connections[host_pair[1]],
                                                                    self.libvirt_handle.host_connections[host_pair[0]],
                                                                    self.settings.move_storage, int(self.settings.bandwidth),
                                                                    host_ips = ips)
                    self.threads.append( mig_thread )

            print ""


    def doMigration(self):
        if self.settings.grouping == "serial":
            self.serialMigration()
        elif self.settings.grouping == "parallel":
            self.parallel_migration()

        if self.settings.bench_result_file != None:
            with open(self.settings.bench_result_file, 'a') as f:
                f.write(self.header_csv + "\n")
                f.write(self.result_latency_csv + "\n")


    def serialMigration(self):
        #migrate one at a time
        for i in self.threads:
            print i.domain.name() + ",",
            self.header_csv += i.domain.name() + ","
        print ""
        sys.stdout.flush()

        for i in self.threads:
            i.start()
            i.join()
            print '%0.3f, ' % (i.latency),
            self.result_latency_csv += '%0.3f, ' % (i.latency)
            sys.stdout.flush()
        print ""

    def parallel_migration(self):
        #start migrations
        for i in self.threads:
            i.start()
            print i.domain.name() + ",",
            self.header_csv += i.domain.name() + ","
        print ""
        sys.stdout.flush()

        for i in self.threads:
            i.join()
            print '%0.3f, ' % (i.latency),
            self.result_latency_csv += '%0.3f, ' % (i.latency)
            sys.stdout.flush()

        print ""



class MigrationManager:
    def __init__(self, domains = None, destination = None, storage_migration=False, max_latency = None):
        self.max_latency = max_latency
        self.domains = domains
        self.destination = destination
        self.storage_migration = storage_migration

        self.migrators_built = False
        self.threads = list()
        self.build_migrators()

        if self.storage_migration:
            print "Storage migration selected!"


    def build_migrators(self):
        #print "Migrating ALL VMS"
        for i in self.domains:
            self.threads.append(MigratorThread.Migrator(i, self.destination, self.storage_migration, self.max_latency))
        self.migrators_built = True

    def serial_migration(self):
        #migrate one at a time
        for i in self.threads:
            print i.domain + ",",
        print ""

        for i in self.threads:
            i.start()
            i.join()
            print '%0.3f, ' % (i.latency),
            sys.stdout.flush()
        print ""

    def parallel_migration(self):
        #start migrations
        for i in self.threads:
            i.start()
            print i.domain + ",",
            sys.stdout.flush()
        print ""

        for i in self.threads:
            i.join()
            print '%0.3f, ' % (i.latency),
            sys.stdout.flush()

        print ""



