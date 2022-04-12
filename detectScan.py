#!/usr/bin/env python
import socket,sys
import time
from struct import *
from collections import OrderedDict
import os
import signal
import optparse 
#define ETH_P_ALL    0x0003


class bgcolors:
	HEADER = '\033[95m'
	OKBLUE = '\033[94m'
	OKGREEN = '\033[92m'
	WARNING = '\033[93m'
	FAIL = '\033[91m'
	ENDC = '\033[0m'
	BOLD = '\033[1m'
	UNDERLINE = '\033[4m'



global threewayhandshake,waiting,fullscandb,halfscandb,xmasscandb,nullscandb,finscandb,scannedports,blacklist

blacklist = []
fullscandb = {}
halfscandb = {}
xmasscandb = {}
nullscandb = {}
finscandb = {}
waiting = []
threewayhandshake = []
scannedports = {}

LANip = '172.19.245.201'


def convert(dec):
	final = []
	flags = OrderedDict([("128","CWR"),("64","ECE"),("32","URG"),("16","ACK"),("8","PSH"),("4","RST"),("2","SYN"),("1","FIN")])
	for i in flags.keys():
		if(dec>=int(i)):
			dec = dec-int(i)
			final.append(flags[i])
	return final

def eth_addr (a) :
    b = "%.2x:%.2x:%.2x:%.2x:%.2x:%.2x" % (ord(a[0]) , ord(a[1]) , ord(a[2]), ord(a[3]), ord(a[4]) , ord(a[5]))
    return b
 
def time_diff(outside,vaxt=5):
    netice = (time.time()-int(outside))/60
    if(netice>=vaxt):
        return True
def show_ports(signum,frm):
	for ips in scannedports:
		for single in scannedports[ips]:
			while(scannedports[ips].count(single)!=1):
				scannedports[ips].remove(single)
	print("\n\n")
   
	for ip in blacklist:
		if(scannedports.has_key(str(ip)) and ip!=LANip):
			print("Attacker from ip "+ip+" scanned ["+ ",".join(scannedports[ip])+"] ports.")


def threewaycheck(sip,dip,sport,dport,seqnum,acknum,flags):
	data = sip+":"+str(sport)+"->"+dip+":"+str(dport)+"_"+str(seqnum)+"_"+str(acknum)+"_"+"/".join(flags)
	if("SYN" in flags and len(flags)==1):
		if(seqnum>0 and acknum==0):
			waiting.append(str(seqnum)+"_"+str(acknum)+"_"+sip+":"+str(sport)+"->"+dip+":"+str(dport))
	elif("SYN" in flags and "ACK" in flags and len(flags)==2):
		for i in waiting:
			pieces = i.split("_")
			ack_old = pieces[1]
			seq_old = pieces[0]
			if(acknum==int(seq_old)+1):
				del waiting[waiting.index(i)]
				waiting.append(str(seqnum)+"_"+str(acknum)+"_"+sip+":"+str(sport)+"->"+dip+":"+str(dport))
				break

	elif("ACK" in flags and len(flags)==1):
		for i in waiting:
			pieces = i.split("_")
			ack_old = pieces[1]
			seq_old = pieces[0]
			if(seqnum==int(ack_old) and acknum==int(seq_old)+1):
				index_i = waiting.index(i)				
				del waiting[index_i]
				threewayhandshake.append(sip+":"+str(sport)+"->"+dip+":"+str(dport))			
				break

def scancheck(sip,dip,sport,dport,seqnum,acknum,flags):
	global data,dataforthreewaycheck,dbdata,reverse	
	data = sip+":"+str(sport)+"->"+dip+":"+str(dport)+"_"+str(seqnum)+"_"+str(acknum)+"_"+"/".join(flags)
	dataforthreewaycheck = sip+":"+str(sport)+"->"+dip+":"+str(dport)
	revthreeway = dip+":"+str(dport)+"->"+sip+":"+str(sport)
	dbdata = sip+"->"+dip
	reverse = dip+"->"+sip
	if(halfconnectscan(sip,dip,sport,dport,seqnum,acknum,flags)):
		returned = halfconnectscan(sip,dip,sport,dport,seqnum,acknum,flags)
		if(isinstance(returned,(str))):
			print(returned)
			return False, 0
		else:
			#print (bgcolors.BOLD+bgcolors.OKBLUE+revthreeway+bgcolors.ENDC+bgcolors.WARNING+bgcolors.BOLD+" Port Scanning Detected: [Style not Defined]:Attempt to connect closed port!"+bgcolors.ENDC)
			return True, sip
	elif(fullconnectscan(sip,dip,sport,dport,seqnum,acknum,flags)):
		returned = fullconnectscan(sip,dip,sport,dport,seqnum,acknum,flags)
		if(isinstance(returned,(str))):
			print (returned)
			return False, 0
		else:
			#print (bgcolors.BOLD+bgcolors.OKBLUE+revthreeway+bgcolors.ENDC+bgcolors.WARNING+bgcolors.BOLD+" Port Scanning Detected: [Style not Defined]:Attempt to connect closed port!"+bgcolors.ENDC)
			return True, sip
	elif(xmasscan(sip,dip,sport,dport,seqnum,acknum,flags)):
		#print (bgcolors.BOLD+bgcolors.OKBLUE+dataforthreewaycheck+bgcolors.ENDC +bgcolors.BOLD+bgcolors.FAIL+ " => [Runtime Detection:] XMAS scan detected!"+bgcolors.ENDC)
		return True, sip
	elif(finscan(sip,dip,sport,dport,seqnum,acknum,flags)):
		#print (bgcolors.BOLD+bgcolors.OKBLUE+ dataforthreewaycheck+bgcolors.ENDC+ bgcolors.BOLD+bgcolors.FAIL+" => [Runtime Detection:] FIN scan detected!"+bgcolors.ENDC)
		return True, sip
	elif(nullscan(sip,dip,sport,dport,seqnum,acknum,flags)):
		#print (bgcolors.BOLD+bgcolors.OKBLUE+dataforthreewaycheck +bgcolors.ENDC+bgcolors.BOLD+bgcolors.FAIL+ " => [Runtime Detection:] NULL scan detected!"+bgcolors.ENDC)
		return True, sip
	return False, 0

def fullconnectscan(sip,dip,sport,dport,seqnum,acknum,flags):
	if(scannedports.has_key(dip)):
		scannedports[dip].append(str(sport))
	else:
		scannedports[dip] = []
		scannedports[dip].append(str(sport))
	
	if(dataforthreewaycheck in threewayhandshake):
		if("ACK" in flags and "RST" in flags and len(flags)==2):
			if(fullscandb.has_key(dbdata)):
				counter = int(fullscandb[dbdata])
				if(counter>=3):
					
					if(str(dip) not in blacklist):
						blacklist.append(str(dip))
					return bgcolors.BOLD+bgcolors.OKBLUE+ dip+":"+str(dport)+"->"+sip+":"+str(sport)+bgcolors.ENDC+ bgcolors.BOLD+bgcolors.FAIL+" => [Runtime Detection:] Full connect scan detected!"+bgcolors.ENDC				
				else:
					counter = counter + 1
					fullscandb[dbdata] = str(counter)
			else:
				counter = 0
				fullscandb[dbdata] = str(counter)
				
	else:
		if("SYN" in flags and len(flags)==1):
			if(seqnum>0 and acknum==0):
				fullscandb[dbdata+"_SYN"] = str(seqnum)+"_"+str(acknum)+"_"+str(sport)+"_"+str(dport)
				
		elif("RST" in flags and "ACK" in flags and len(flags)==2):
			if(fullscandb.has_key(dip+"->"+sip+"_SYN")):
				manage = fullscandb[dip+"->"+sip+"_SYN"]
				pieces = manage.split("_")
				old_acknum = int(pieces[1])
				old_seqnum = int(pieces[0])
				if(seqnum==0 and acknum==old_seqnum+1):
					if(fullscandb.has_key(dbdata)):
						counter = int(fullscandb[dbdata])
						if(counter>=3):
							
							if(str(dip) not in blacklist):
								blacklist.append(str(dip))
							return True
						else:
							counter = counter + 1
							fullscandb[dbdata] = str(counter)
					else:
						counter = 0
						fullscandb[dbdata] = str(counter)
	return False			

def halfconnectscan(sip,dip,sport,dport,seqnum,acknum,flags):
	if(scannedports.has_key(dip)):
		scannedports[dip].append(str(sport))
	else:
		scannedports[dip] = []
		scannedports[dip].append(str(sport))
	
	if("SYN" in flags and seqnum>0 and acknum==0 and len(flags)==1):
		halfscandb[dbdata+"_"+str(seqnum)] = dbdata+"_SYN_ACK_"+str(seqnum)+"_"+str(acknum)
	elif("RST" in flags and "ACK" in flags and len(flags)==2):
		if(halfscandb.has_key(reverse+"_"+str(acknum-1))):
			del halfscandb[reverse+"_"+str(acknum-1)]
			if(str(dip) not in blacklist):
				blacklist.append(str(dip))
			
			return True	
	elif("SYN" in flags and "ACK" in flags and len(flags)==2):
		if(halfscandb.has_key(reverse+"_"+str(acknum-1))):
			del halfscandb[reverse+"_"+str(acknum-1)]
			halfscandb[reverse+"_"+str(acknum)] = dbdata+"_RST_"+str(seqnum)+"_"+str(acknum)
	elif("RST" in flags and len(flags)==1):
		if(halfscandb.has_key(dbdata+"_"+str(seqnum))):
			if(str(dip) not in blacklist):
				blacklist.append(str(dip))
		
			return bgcolors.BOLD+bgcolors.OKBLUE+sip+":"+str(sport)+"->"+dip+":"+str(dport) +bgcolors.ENDC+ bgcolors.BOLD+bgcolors.FAIL+" => [Runtime Detection:] Half connect(SYN scan) scan detected!"+bgcolors.ENDC
	return False
	

	

def xmasscan(sip,dip,sport,dport,seqnum,acknum,flags):
	if(scannedports.has_key(dip)):
		scannedports[dip].append(str(sport))
	else:
		scannedports[dip] = []
		scannedports[dip].append(str(sport))
	
	if("FIN" in flags and "URG" in flags and "PSH" in flags and len(flags)==3):
		
		if(str(sip) not in blacklist):	
			blacklist.append(str(sip))
		return True
	return False


def finscan(sip,dip,sport,dport,seqnum,acknum,flags):
	if(scannedports.has_key(dip)):
		scannedports[dip].append(str(sport))
	else:
		scannedports[dip] = []
		scannedports[dip].append(str(sport))
	
	if(dataforthreewaycheck not in threewayhandshake):
		if("FIN" in flags and len(flags)==1):			
			if(str(sip) not in blacklist):	
				blacklist.append(str(sip))
			return True
	return False


def nullscan(sip,dip,sport,dport,seqnum,acknum,flags):
	if(scannedports.has_key(dip)):
		scannedports[dip].append(str(sport))
	else:
		scannedports[dip] = []
		scannedports[dip].append(str(sport))
	if(len(flags)==0):
		if(str(sip) not in blacklist):	
			blacklist.append(str(sip))
		return True
	return False




def ackscan(sip,dip,sport,dport,seqnum,acknum,flags):
	if(scannedports.has_key(dip)):
		scannedports[dip].append(str(sport))
	else:
		scannedports[dip] = []
		scannedports[dip].append(str(sport))

	if(dataforthreewaycheck not in threewayhandshake):
		if("ACK" in flags and len(flags)==1):
			
			if(str(sip) not in blacklist):	
				blacklist.append(str(sip))
			return True
	return False


  
if(os.name=='nt'):
    print ("[*]Doesn't work on Windows machine.")
    sys.exit()

try:
    s = socket.socket( socket.AF_PACKET , socket.SOCK_RAW , socket.ntohs(0x0003))
except socket.error as msg:
    print ('[*]Socket can\'t be created! Error Code : ' + str(msg[0]) + ' Error Message ' + msg[1])
    sys.exit()
except AttributeError:
    print ("[*]Windows OS doesn't support AF_PACKET.")
    sys.exit()
  
now = time.time()
protocol_numb = {"1":"ICMP","6":"TCP","17":"UDP"}

num = 0
scanningIPs = []
print("Detecting Scans...")
while True:
	packet = s.recvfrom(65565)
	packet = packet[0]
	eth_length = 14
	eth_header = packet[:eth_length]
	eth = unpack('!6s6sH' , eth_header)
	eth_protocol = socket.ntohs(eth[2])
	dest_mac = eth_addr(packet[0:6])
	source_mac = eth_addr(packet[6:12])

	if eth_protocol == 8 :
		ip_header = packet[eth_length:20+eth_length]
      
		iph = unpack('!BBHHHBBH4s4s' , ip_header)
 
		version_ihl = iph[0]
		version = version_ihl >> 4
		ihl = version_ihl & 0xF
 
		iph_length = ihl * 4
		protocol = iph[6]
		if(str(iph[6]) not in protocol_numb.keys()):
			protocol_name = str(iph[6])
		else:
			protocol_name = protocol_numb[str(iph[6])]
		s_addr = socket.inet_ntoa(iph[8]);
		d_addr = socket.inet_ntoa(iph[9]);
		timestamp = time.time();
		elave=None
      
        #TCP protocol
		tcph = ()
		if protocol == 6 :
			t = iph_length + eth_length
			tcp_header = packet[t:t+20]
			tcph = unpack('!HHLLBBHHH' , tcp_header)
   
			source_port = tcph[0]
			dest_port = tcph[1];
			seq_numb = tcph[2]
			dest_numb = tcph[3]
			tcp_flags = convert(tcph[5])
			testdata = s_addr+":"+str(source_port)+"->"+d_addr+":"+str(dest_port)
			if(testdata not in threewayhandshake):
				threewaycheck(s_addr,d_addr,source_port,dest_port,seq_numb,dest_numb,tcp_flags)
			yee, sip = scancheck(s_addr,d_addr,source_port,dest_port,seq_numb,dest_numb,tcp_flags)
			if (yee):
				num+=1
				if (num > 10):
					if (sip in scanningIPs):
						num = 0
						continue
					else:
						print("Scan Detected from " + sip)
						scanningIPs.append(sip)
						num = 0
			



