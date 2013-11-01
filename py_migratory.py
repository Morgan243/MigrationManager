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
	def __init__(self, method, domains, destination):
		self.method = method
		self.domains = domains
		self.destination = destination
		self.threads = list()

	def build_migrators(self):
		#print "Migrating ALL VMS"
		for i in domains:
			threads.append(Migrator(i, destination))

	def serial_migration(self):
		#migrate one at a time
		for i in threads:
			i.start()
			print i.domain + ",",
			sys.stdout.flush()
			i.join()
			print '%0.3f, ' % (i.latency),
			sys.stdout.flush()

	def parallel_migration(self:
		#start migrations
		for i in threads:
			i.start()
			print i.domain + ",",
			sys.stdout.flush()

		for i in threads:
			i.join()
			print '%0.3f, ' % (i.latency),
			sys.stdout.flush()

		print ""

class virsh_handler:
	def __init__(self):
		self.running_vms = get_running_vms()

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

		#split on whitespace and ignore the domain id number
		for i in virsh_lines:
			all_vms.append(i.split()[1:][0])

			if all_vms[-1][1] == 'running':
				running_vms.append(all_vms[-1][0])
			elif all_vms[-1][1] == 'shut off':
				offline_vms.append(all_vms[-1][0])




#list of vms that will migrate
to_migrate = 'centVM-0-0-00 centVM-0-0-01 centVM-0-0-02 centVM-0-0-03 centVM-0-0-04 centVM-0-1-00 centVM-0-1-01 centVM-0-1-02 centVM-0-1-03 centVM-0-1-04'

#to_migrate = 'centVM-0-1-03 centVM-0-1-04'
type = 'group'

hostname = socket.gethostname()
print  "Running on " + hostname
destination ='unknown'

#automatically migrate to the other host
if hostname == 'cpu-0-0.local':
	destination = 'cpu-0-1'
elif hostname == 'cpu-0-1.local':
	destination = 'cpu-0-0'

migrate_list = list()
migrate_list.sort()

handler = virsh_handler()

#keyword ALL: move all running VMs on the host to the destination
#if to_migrate == 'ALL':
#	for i in vms:
#		if i[1] == 'running':
#			migrate_list.append(i[0])
#else:
#	migrate_list = to_migrate.split()
