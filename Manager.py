import os
import socket
import libvirt
import sys
import threading
import time
import MigratorThread

class MigrationSettings:
    def __init__(self, config_map = None):
        self.print_br = "\n"
        self.config_map = config_map

        self.p_host_pairs = None
        self.bandwidth = None
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


    def loadOptions(self, config_map):
        print "Loading options"
        for option, value in config_map.items():
            if option == ("main", "hosts"):
                self.parseHosts(value)

            elif option == ("options", "bandwidth"):
                self.bandwidth = int(value)

            elif option == ("options", "grouping"):
                self.grouping = value

            elif option == ("options", "storage"):
                self.move_storage = self.checkTorF(value)

            elif option == ("benchmarking", "enabled"):
                self.enable_benchmarking = self.checkTorF(value)

            elif option == ("benchmarking", "benchmark"):
                self.bench_name = value

            elif option == ("benchmarking", "iterations"):
                self.bench_iterations = int(value)

            elif option == ("benchmarking", "output"):
                self.bench_result_file = value

    def __str__(self):
        return ("hosts :: " + str(self.p_host_pairs) + self.print_br + 
              "grouping :: " + self.grouping + self.print_br + 
              "storage migration :: " + str(self.move_storage))

    def checkTorF(self, string):
        if string.lower() == "true":
            return True
        else:
            return False

    def parseHosts(self, hosts):
        groups = hosts.split(':')
        self.p_host_pairs = list()

        for group in groups:
            group_hosts = group.strip().split(',')
            self.p_host_pairs.append( (group_hosts[0].strip(), group_hosts[1].strip()) )

class MigrationManager:
    def __init__(self, domains, destination, storage_migration=False, max_latency = None):
        self.max_latency = max_latency
        self.migrators_built = False
        self.domains = domains
        self.destination = destination
        self.storage_migration = storage_migration
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


