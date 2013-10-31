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

#dont actually do anything!
debug = 0
#to_migrate = 'ALL'
to_migrate = 'centVM-0-0-00'
type = 'group'

hostname = socket.gethostname()
print  "Running on " + hostname
destination ='unknown'

if hostname == 'cpu-0-0.local':
	destination = 'cpu-0-1'
elif hostname == 'cpu-0-1.local':
	destination = 'cpu-0-0'

print "Will migrate to " + destination

virsh_out = os.popen('virsh list').read()

virsh_lines = virsh_out.split('\n')

virsh_lines.remove(' Id    Name                           State')
virsh_lines.remove('----------------------------------------------------')
virsh_lines.remove('')
virsh_lines.remove('')

#print virsh_lines

vms=list()

for i in virsh_lines:
	#print i
	#split on whitespace and ignore the domain id
	vms.append(i.split()[1:])

migrate_list = list()
migrate_string = ''

if to_migrate != 'ALL':
	migrate_list = to_migrate.split()
	print migrate_list
else:
	for i in vms:
		if i[1] == 'running':
			#print i[0] + " is running!"
			migrate_string = migrate_string + i[0] + " "
			migrate_list.append(i[0])
			#if debug == 1:
			#	print "DEBUG: time virsh migrate --live " + i[0] + " qemu+ssh://" + destination + "/system"
			#else:
				#mig_time = os.popen("time virsh migrate --live " + i[0] + " qemu+ssh://" + destination + "/system")
				
#print migrate_string
#print migrate_list

threads = list()
migrate_list.sort()

#print "Migrating ALL VMS"
for i in migrate_list:
	#print "\tMigrating " + i
	threads.append(Migrator(i, destination))

for i in threads:
	i.start()
	print i.domain + ",",
	sys.stdout.flush()

print ""

for i in threads:
	i.join()
	print '%0.3f, ' % (i.latency),
	sys.stdout.flush()

print ""
