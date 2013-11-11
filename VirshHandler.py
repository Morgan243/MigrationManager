import os
import socket
#import libvirt
import sys
import threading
import time
import MigratorThread

# Interfaces with Virsh to parse available VMs and apply settings to domains
class virsh_handler:
    def __init__(self, destination, domains=None, latency = None):
        self.latency = latency

        if domains == None:
            self.all_vms, self.running_vms, self.offline_vms = self.get_vms()
        else:
            print "Custom VM list supplied: " + domains
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


