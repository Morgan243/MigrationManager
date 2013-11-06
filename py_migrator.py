#!/usr/bin/python
import os
import socket
import libvirt
import sys
import threading
import time
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-m","--method",dest="migration_method", 
			help="How to migrate: serial or parallel (default = serial)")

parser.add_option("-b","--bandwidth",dest="migration_bandwidth", 
			help="Bandwidth to allocate to each migration (Mbps) (default = 32)")

parser.add_option("-s","--storage",dest="migrate_storage", default=False, action="store_true",
			help="Perform storage migration. Be sure storage is allocated on destination")

parser.add_option("-d","--destination",dest="destination",
			help="What host to migrate the machines to")

(options, args) = parser.parse_args()


class Migrator(threading.Thread):
	def __init__(self, domain, destination, migrate_storage=False):
		threading.Thread.__init__(self)
		self.domain = domain
		self.destination = destination
		self.migrate_storage = migrate_storage
		self.latency = 0

	def run(self):
		if self.migrate_storage:
			self.migrate_vm_storage(self.domain, self.destination)
		else:
			self.migrate_vm(self.domain, self.destination)

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

class MigrationManager:
	def __init__(self, domains, destination, storage_migration=False):
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
			self.threads.append(Migrator(i, self.destination, self.storage_migration))
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

class virsh_handler:
	def __init__(self, destination, domains=None):
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


#list of vms that will migrate
to_migrate = 'centVM-0-0-00 centVM-0-0-01 centVM-0-0-02 centVM-0-0-03 centVM-0-0-04 centVM-0-1-00 centVM-0-1-01 centVM-0-1-02 centVM-0-1-03 centVM-0-1-04'

#to_migrate = 'centVM-0-1-03 centVM-0-1-04'
type = 'group'

hostname = socket.gethostname()
#print  "Running on " + hostname
destination ='unknown'

#automatically migrate to the other host
if options.destination != None:
	destination = options.destination
elif hostname == 'cpu-0-0.local':
	destination = 'cpu-0-1'
elif hostname == 'cpu-0-1.local':
	destination = 'cpu-0-0'

migrate_list = list()
migrate_list.sort()

handler = virsh_handler(destination)
#print "ALL: " + str(handler.all_vms)
#print "RUNNING: " + str(handler.running_vms)
#print "OFFLINE: " + str(handler.offline_vms)

if options.migration_bandwidth == None:
	handler.set_running_vms_speed(32)
else:
	handler.set_running_vms_speed(options.migration_bandwidth)

migrationManager = MigrationManager(handler.running_vms, destination, options.migrate_storage)

if options.migration_method == 'serial':
	migrationManager.serial_migration()
elif options.migration_method == 'parallel':
	migrationManager.parallel_migration()
elif options.migration_method == None:
	migrationManager.serial_migration()

