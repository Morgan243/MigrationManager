#!/usr/bin/python2
import os
import socket
import libvirt
import sys
import threading
import time
import MigratorThread
from optparse import OptionParser
import socket

class libvirt_Handler:
    def __init__(self, hosts = None):
        self.hosts = hosts

        self.host_connections = self._connectToHosts(self.hosts)
        self.host_domains = self._getAllHostsDomains()
        self.host_defined_domains = self._getAllDefinedDomains()

    # make connection to the hypervisors
    def _connectToHosts(self, hosts):
        host_connections = dict()

        if hosts != None:
            for host in hosts:
                print "connecting to " + str(host) + "...",
                host_connections[host] = libvirt.open("qemu+ssh://" + host + "/system")
                print "Success!"
        else:
            print "No hostnames passed to libvirt handler, connecting to local machine VMM..."
            hostname = socket.gethostname()
            print "connecting to " + str(hostname) + "...",
            host_connections[hostname] = libvirt.open(None)
            print "Success!"


        return host_connections

    # gets running vms
    def _getAllHostsDomains(self, host_connections = None):
        host_domains = dict()
        if host_connections == None:
            for host, conn in self.host_connections.items():
                host_domains[host] = list()
                for ID in conn.listDomainsID():
                    host_domains[host].append( conn.lookupByID(ID) )

        return host_domains

    def _getAllDefinedDomains(self, host_connections = None):
        host_defined_domains = dict()
        if host_connections == None:
            for host, conn in self.host_connections.items():
                host_defined_domains[host] = list()
                for name in conn.listDefinedDomains():
                    host_defined_domains[host].append( conn.lookupByName(name) )

        return host_defined_domains

    def getVMs(self, hosts = None):
        vms = list()

        # if NONE, assume want all
        if hosts == None:
            for hostname, domains in self.host_domains.items():
                vms += domains
        elif hosts is list:
            for host in hosts:
                vms += self.host_domains[host]
        else:
            vms = self.host_domains[hosts]

        return sorted(vms, key = lambda x: x.name())

    def stopDomains(self, hosts = None, vms = None):
        # if nothing provided, stop all vms on all nodes
        if hosts == None and vms == None:
            print "Stopping all domains on all hosts..."
            for host, domain_conns in self.host_domains.items():
                for dom_conn in domain_conns:
                    print "Stopping " + str(dom_conn.name()) + " on " + str(host) + "...",
                    if not debug:
                        dom_conn.shutdown()
                    print "Success! (sleeping to avoid lock problem)"
                    time.sleep(7)

    def startDomains(self, hosts = None, vms = None):
        # if nothing provided, start all vms on all nodes
        if hosts == None and vms == None:
            print "Starting all domains on all hosts..."
            for host, domain_conns in self.host_defined_domains.items():
                for dom_conn in domain_conns:
                    print "Starting " + str(dom_conn.name()) + " on " + str(host) + "...",
                    if not debug:
                        dom_conn.create()
                    print "Success! (sleeping to avoid lock problem)"
                    time.sleep(7)



# Interfaces with Virsh to parse available VMs and apply settings to domains
class virsh_handler:
    def __init__(self, destination, domains=None, latency = None):
        self.latency = latency

        if domains == None:
            self.all_vms, self.running_vms, self.offline_vms = self.get_vms()
        else:
            print "Custom VM list supplied: " + str(domains)
            self.running_vms = domains
        self.destination = destination


    def get_vms(self):
        all_vms = list()
        running_vms = list()
        offline_vms = list()

        #get a list of running vms
        virsh_out = os.popen('virsh list --all').read()

        #separate into lines and remove unecessary data
        virsh_lines = virsh_out.split('\n')

        virsh_lines.remove(' Id    Name                           State')
        virsh_lines.remove('----------------------------------------------------')
        virsh_lines.remove('')
        virsh_lines.remove('')

        temp_list = list()

        #split on whitespace and ignore the domain id number
        for i in virsh_lines:
            temp_list.append(i.split()[1:])
            all_vms.append(temp_list[-1][0])

            if temp_list[-1][1] == 'running':
                running_vms.append(temp_list[-1][0])
            elif temp_list[-1][1] == 'shut':
                offline_vms.append(temp_list[-1][0])

        all_vms.sort()
        running_vms.sort()
        offline_vms.sort()

        return (all_vms, running_vms, offline_vms)

    def set_all_vms_speed(self, Mbps):
        for i in self.all_vms:
            self.set_migrate_speed(Mbps, i)

    def set_running_vms_speed(self, Mbps):
        for i in self.running_vms:
            self.set_migrate_speed(Mbps, i)

    def set_migrate_speed(self,Mbps,domain):
        virsh_out = os.popen("virsh migrate-setspeed "+domain+" "+str(Mbps)).read()

    def set_running_vms_downtime(self,milliseconds):
        print "Setting downtime to "+ milliseconds + "ms"
        for i in self.running_vms:
            self.set_max_downtime(milliseconds, i)


    def set_max_downtime(self,milliseconds, domain):
        virsh_out = os.popen("virsh migrate-setmaxdowntime " + domain + " " + str(milliseconds)).read()




debug = False

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-d","--debug",dest="debug", default=False, action="store_true",
                help="Turn on debug mode")

    parser.add_option("-s","--start-all",dest="start_all", default=False, action="store_true",
                help="Start all domains running on hosts specified with '-p'. If hosts not specified, then " +
                      "this command will stop all VMs on the machine which it is run")

    parser.add_option("-x","--stop-all",dest="stop_all", default=False, action="store_true",
                help="Stop all domains running on hosts specified with '-p'. If hosts not specified, then " +
                      "this command will stop all VMs on the machine which it is run")

    parser.add_option("-p","--physical-hosts", dest="pm_hosts", default = None,
                help="CSV of hosts that are running a hypervisor that are running any of the VMs included in other options. " +
                "If this option isn't used, then only the host this is run on will be included in checks. The PM used in destination " +
                "will automatically be included, but can also be included here if you wish")

    (options, args) = parser.parse_args()

    debug = options.debug

    virt_handler = libvirt_Handler(options.pm_hosts.split(','))

    if options.stop_all:
        virt_handler.stopDomains()
    elif options.start_all:
        virt_handler.startDomains()
