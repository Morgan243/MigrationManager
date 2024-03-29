import os
import socket
import libvirt
import sys
import threading
import time

class libvirt_Migrator(threading.Thread):
    def __init__(self, domain_conn, source, destination, migrate_storage=False, bandwidth = 32, max_latency = None, src_ip = None, dest_ip = None):
        threading.Thread.__init__(self)

        # mark this true if an exception was thrown during migration
        self.except_thrown = False

        self.domain = domain_conn
        self.dom_name = self.domain.name()
        self.source = source
        self.destination = destination
        self.migrate_storage = migrate_storage
        self.bandwidth = bandwidth
        self.max_latency = max_latency
        #self.host_ips = host_ips
	self.src_ip = src_ip
	self.dest_ip = dest_ip

        self.flags = self.build_migrate_flags()

        self.latency = 0

    def run(self):
        t1 = time.time()
        #print "GOING TO IP: " + str(self.host_ips[1])
        #self.domain = self.domain.migrate(self.destination, self.flags, None, None, self.bandwidth)
        #self.domain = self.domain.migrateToURI(self.destination.getURI() , self.flags, None, self.bandwidth)
        #print "URI: " + str(self.destination.getURI())
        #print "DEST IP: " + str(self.dest_ip)

        try:
            self.return_code = self.domain.migrateToURI2(self.destination.getURI(), "tcp://" + self.dest_ip, None,  self.flags, None, self.bandwidth)
        
            if self.return_code != 0:
                print "MIGRATION RETURNED NON-ZERO: " + self.return_code
                raise 
        except:
		
            print "Exception thrown (" + self.dom_name + ")"
            print "ERROR: " + str(sys.exc_info()[0])
            self.except_thrown = True

        t2 = time.time()
        self.latency = t2 - t1

    def build_migrate_flags(self):
        flags = libvirt.VIR_MIGRATE_LIVE

        if self.migrate_storage:
            flags = flags | libvirt.VIR_MIGRATE_NON_SHARED_DISK | libvirt.VIR_MIGRATE_PEER2PEER

	return flags

    def getLatency(self):
	try:
		lat = '0.3f' % (self.latency)
	except:
		#print "PROBLEM: " + str(self.latency)
		lat = str(self.latency)


        if self.except_thrown:
            lat += '!'

        return lat



class Migrator(threading.Thread):
    def __init__(self, domain, destination, migrate_storage=False, max_latency = None):
        threading.Thread.__init__(self)
        self.max_latency = max_latency
        self.domain = domain
        self.destination = destination
        self.migrate_storage = migrate_storage
        self.latency = 0

    def run(self):
#        if self.migrate_storage:
#            self.migrate_vm_storage(self.domain, self.destination)
#        else:
#            self.migrate_vm(self.domain, self.destination)

        self.time_run_cmd(self.build_migrate_cmd(self.domain, self.destination))


    def time_run_cmd(self, cmd):
	t1 = time.time()
	out = os.popen(cmd).read()
	t2 = time.time()
	self.latency = t2 - t1
	return out

    def build_migrate_cmd(self, domain , destination ):
        options =''
        if self.max_latency != None:
            options += '--timeout ' + str(self.max_latency) + ' '

        if self.migrate_storage:
            options += '--copy-storage-all '

        options += '--live '
        cmd = "virsh migrate " + options + domain + " qemu+ssh://" + destination +"/system"
	return cmd

    def migrate_vm(self, domain, destination):
        t1 = time.time()
        mig_out=os.popen("virsh migrate --live " + domain + " qemu+ssh://" +destination+"/system").read();
        t2 = time.time()
        self.latency = t2 - t1;
        return mig_out

    def migrate_vm_storage(self, domain, destination):
        t1 = time.time()
        mig_out=os.popen("virsh migrate --copy-storage-all --live " + domain + " qemu+ssh://" +destination+"/system").read();
        t2 = time.time()
        self.latency = t2 - t1;
        return mig_out

