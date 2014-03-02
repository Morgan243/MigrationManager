import os
import socket
import libvirt
import sys
import threading
import time
import MigratorThread

class libvirt_Handler:
    def __init__(self, hosts = None):
        self.hosts = hosts

        if self.hosts != None:
            self.host_connections = self.connectToHosts(self.hosts)
            self.host_domains = self.getAllHostsDomains()
        else:
            print "No hostnames passed to libvirt handler!!"

    # make connection to the hypervisors
    def connectToHosts(self, hosts):
        host_connections = dict()

        for host in hosts:
            print "connecting to " + str(host) + "...",
            host_connections[host] = libvirt.open("qemu+ssh://" + host + "/system")
            print "Success!"

    def getAllHostsDomains(self, host_connections = None):
        host_domains = dict()
        if host_connections == None:
            for host, conn in self.host_connections:
                host_domains[host] = list()
                for domain in conn.listDefinedDomains():
                    host_domains[host].append( conn.lookupByName(domain) )
            
        return host_domains

    def getVMs(self, hosts = None):
        vms = list()

        # if NONE, assume want all
        if hosts == None:
            for hostname, domains in self.host_domains:
                vms += domains
        elif hosts is list:
            for host in hosts:
                vms += self.host_domains[host]
        else:
            vms = self.host_connections[hosts]
        
        return vms


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


