#!/usr/bin/python
import os
import socket
import libvirt
import sys
import threading
import time
class Migrator(threading.Thread):
	def __init__(self, domain, destination):
		threading.Thread.__init__(self)
		self.domain = domain
		self.destination = destination
		self.latency = 0

	def run(self):
		self.migrate_vm(self.domain, self.destination)

	def migrate_vm(self, domain, destination):
		t1 = time.time()
		mig_out=os.popen("virsh migrate --live " + domain + " qemu+ssh://" +destination+"/system").read();
		t2 = time.time()
		self.latency = t2 - t1;
		return mig_out

class MigrationManager:
	def __init__(self, domains, destination):
		self.migrators_built = False
		self.domains = domains
		self.destination = destination
		self.threads = list()
		self.build_migrators()

	def build_migrators(self):
		#print "Migrating ALL VMS"
		for i in self.domains:
			self.threads.append(Migrator(i, destination))
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

		for i in self.threads:
			i.join()
			print '%0.3f, ' % (i.latency),
			sys.stdout.flush()

		print ""

class virsh_handler:
	def __init__(self, destination):
		self.all_vms, self.running_vms, self.offline_vms = self.get_vms()
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
if hostname == 'cpu-0-0.local':
	destination = 'cpu-0-1'
elif hostname == 'cpu-0-1.local':
	destination = 'cpu-0-0'

migrate_list = list()
migrate_list.sort()

handler = virsh_handler(destination)
#print "ALL: " + str(handler.all_vms)
#print "RUNNING: " + str(handler.running_vms)
#print "OFFLINE: " + str(handler.offline_vms)

handler.set_running_vms_speed(64)

migrationManager = MigrationManager(handler.running_vms, destination)
migrationManager.serial_migration()

