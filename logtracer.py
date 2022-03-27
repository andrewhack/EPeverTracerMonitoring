#!/usr/bin/python3
import sys
import os
from datetime import datetime
import time
import minimalmodbus
from influxdb import InfluxDBClient
import modules.SolarTracer as ep
import logging

# '/' is mandatory at the end of the basepath
_BASEPATH=os.getcwd()+'/'
# Check if the main program is executed from the daemon or from bash script
for i in sys.path:
    if "epever_stat" in i:
        _BASEPATH=i+'/'
        break
       
_DBFILE=_BASEPATH+"influx.db"
_LOGFILE=_BASEPATH+"log/error.log"
_EXCFILE=_BASEPATH+"log/exceptions.log"

#### Standard logging 
logger = logging.getLogger("Log")
logger.setLevel(logging.INFO)
# create a file handler
handler = logging.FileHandler(_LOGFILE)
handler.setLevel(logging.INFO)
# create a logging format
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(handler)
#### Exceptions
logger1 = logging.getLogger("Exception")
logger1.setLevel(logging.ERROR)
# create a file handler
handler1 = logging.FileHandler(_EXCFILE)
handler1.setLevel(logging.ERROR)
# create a logging format
formatter1 = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler1.setFormatter(formatter1)
# add the handlers to the logger
logger1.addHandler(handler1)

class Logger(object):
    '''
    Logging facility
    '''
    def __init__(self, debug, module, error_str, show=True):
        self.debug=debug
        self.error_str=error_str
        self.module=module
            
        self.now=datetime.now()
        if self.debug == 1 and show == True:
            self.show=True
        elif self.debug == 0 and show == True:    
            self.show=False
        else:
            self.show=show
                    
        logger.info(self.module+': '+self.error_str)
                
    def __str__(self):
        if self.show:
            return str(self.now)+'  '+self.module+': '+self.error_str
        else:
            return ''    

class Excp(object):
    '''
    Logging facility
    '''
    def __init__(self, error_str):
        self.error_str=error_str        
        logger1.error(self.error_str, exc_info=True) 
        
def logh(logstr):
    '''
    Correcting the output from Logger
    '''
    if len(str(logstr))>0:
        print(str(logstr))

debug=0                    
epever_title="\nEpever Tracer loging script v1.0 - ITCom Solutions - 2022"
epever_params="./logtracer.py <device id> <check name> -> console output\n./logtracer.py <device id>,<device id> filesnap/dbsnap -> /tmp/ep_tracer_<id>.log / influxdb(grafana) (agregated kW, other stats from first id)"

ep_checks = []

from modules.conf_pars import *
# Parse db configuration file
cnf1=Config_Parser(_DBFILE)
validdbconf=cnf1.dbvalidate()
if not validdbconf:
	print (epever_title)
	print (epever_params)
	print('\nERROR: DB configuration file is not valid.')
	sys.exit(-1)

if len(sys.argv) >= 3:
	def deviceid_check(id):
		try:
			if not isinstance(int(id), int):
				print (epever_title)
				print (epever_params)
				print ("\nERROR: Device id must be integer.\n")
				sys.exit(-1)
		except ValueError as ve:
			print (epever_title)
			print (epever_params)
			print ("\nERROR: Device id must be integer.\n")
			sys.exit(-1)
		if int(id) < 1:
			print (epever_title)
			print (epever_params)
			print ("\nERROR: Device id can't be less than 1.\n")
			sys.exit(-1)
	if sys.argv[2]=='dbsnap' or sys.argv[2]=='filesnap':
		ep_IDs=sys.argv[1].split(',')
		for ep_id in ep_IDs:
			deviceid_check(ep_id)
	else:
		deviceid_check(sys.argv[1])			
	# Build available checks list
	for key in ep.regs.keys():
		if 'watt' in key:
			if not key[:-1] in ep_checks:
				ep_checks.append(key[:-1])
		else:
			ep_checks.append(key)
	def EP_Connect (id):
		# Init Epever Tracer 
		up = ep.SolarTracer(debug, logh, Logger, serialid=int(id))
	
		# Connect to Epever Tracer
		if up.connect() < 0:
			print (epever_title)
			print ("\nERROR: Could not connect to the device\n")
			sys.exit(-2)
		return up
	def DB_Submit (body_solar):
		#print (body_solar)
		try:
			# connect to influx
			ifclient = InfluxDBClient(validdbconf['INFLUXDB']['Host'],int(validdbconf['INFLUXDB']['Port']),validdbconf['INFLUXDB']['User'],validdbconf['INFLUXDB']['Pass'],validdbconf['INFLUXDB']['DB'])
			# write the measurement
			ifclient.write_points(body_solar)
		except Exception as e:
			Excp('INFLUXDB: '+str(e))
	def File_Submit (id, body_solar):
		fn='/tmp/ep_tracer_'+id+'.log'
		try:
			with open(fn, 'w') as f: 
				for key, value in body_solar.items(): 
					f.write('%s:%s\n' % (key, value))
		except Exception as e:
			Excp('FILEDB: '+str(e))
	def Get_RegVal(func, reg): # re-check if communication issue; reducing -2 values collection 
		wl=1;
		while wl < 3: 
			ret_val=func(reg)
			if ret_val != -2:
				return ret_val
			wl=wl+1
			time.sleep (0.5) # delay in case of comm. issue
		return -2 
	if sys.argv[2] == 'filesnap' or sys.argv[2] == 'dbsnap':
		#ToDo - check all provided ids - separate files for filesnap; agregated kw for dbsnap
		if sys.argv[2] == 'filesnap':
			#ToDo
			for ep_id in ep_IDs:
	            # connect to Epever
				up=EP_Connect(ep_id)
				body_solar = {}
				body_solar['pvvolt']=float(Get_RegVal(up.readReg, ep.regs['pvvolt']))
				body_solar['pvamps']=float(Get_RegVal(up.readReg, ep.regs['pvamps']))
				body_solar['bavolt']=float(Get_RegVal(up.readReg, ep.regs['bavolt']))
				body_solar['baamps']=float(Get_RegVal(up.readReg, ep.regs['baamps']))
				body_solar['baperc']=float(Get_RegVal(up.readReg, ep.regs['baperc'])*100) # Conversion of the value - orig: 1 or less
				body_solar['batemp']=float(Get_RegVal(up.readReg, ep.regs['batemp']))
				body_solar['bastat']=int(Get_RegVal(up.readReg, ep.regs['bastat']))
				body_solar['dcvolt']=float(Get_RegVal(up.readReg, ep.regs['dcvolt']))
				body_solar['dcamps']=float(Get_RegVal(up.readReg, ep.regs['dcamps']))
				body_solar['epstat']=int(Get_RegVal(up.readReg, ep.regs['epstat']))
				body_solar['eptemp1']=float(Get_RegVal(up.readReg, ep.regs['eptemp1']))
				body_solar['eptemp2']=float(Get_RegVal(up.readReg, ep.regs['eptemp2']))
				up.disconnect()
				File_Submit(ep_id, body_solar)
				del body_solar
				time.sleep (1)
			sys.exit(0)
		elif sys.argv[2] == 'dbsnap':
			# ToDo - check all ids
			# get timestamps
			timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
			id_indx=0
			PVwatt=0
			PVkwh=0
			PVkwh2d=0
			DCwatt=0
			DCkwh=0
			DCkwh2d=0
			for ep_id in ep_IDs:
	            # connect to Epever
				up=EP_Connect(ep_id)
				# Get data - agregste pvwatt, pvkwh, pvkwh2d, dcwatt, dckwh, dckwh2d from all controlers
				if id_indx==0:
					pvvolt_val=float(Get_RegVal(up.readReg, ep.regs['pvvolt']))
					pvamp_val=float(Get_RegVal(up.readReg, ep.regs['pvamps']))
					bavolt_val=float(Get_RegVal(up.readReg, ep.regs['bavolt']))
					baapms_val=float(Get_RegVal(up.readReg, ep.regs['baamps']))
					baperc_val=float(Get_RegVal(up.readReg, ep.regs['baperc']))
					dcvolt_val=float(Get_RegVal(up.readReg, ep.regs['dcvolt']))
					dcamp_val=float(Get_RegVal(up.readReg, ep.regs['dcamps']))               
				PVwatt_tmp=Get_RegVal(up.readReg, ep.regs['pvwatth'])
				PVwatt=PVwatt+((int(PVwatt_tmp) << 16) + Get_RegVal(up.readReg, ep.regs['pvwattl']))
				DCwatt_tmp = Get_RegVal(up.readReg, ep.regs['dcwatth'])
				DCwatt = DCwatt+((int(DCwatt_tmp) << 16) + Get_RegVal(up.readReg, ep.regs['dcwattl']))
				PVkwh_tmp=Get_RegVal(up.readReg, ep.regs['pvkwhtotal'])
				PVkwh=PVkwh+PVkwh_tmp
				PVkwh2d_tmp=Get_RegVal(up.readReg, ep.regs['pvkwhtoday'])
				PVkwh2d=PVkwh2d+PVkwh2d_tmp
				DCkwh_tmp=Get_RegVal(up.readReg, ep.regs['dckwhtotal'])
				DCkwh=DCkwh+DCkwh_tmp
				DCkwh2d_tmp=Get_RegVal(up.readReg, ep.regs['dckwhtoday'])
				DCkwh2d=DCkwh2d+DCkwh2d_tmp
				up.disconnect()
				id_indx=ep_id
				time.sleep (1)
			# Data collected for grafana use
			body_solar = [
			{
			"measurement": validdbconf['INFLUXDB']['Measurement'],
			"time": timestamp,
			"fields": {
			"PVvolt": pvvolt_val,
			"PVamps": pvamp_val,
			"PVwatt": float(PVwatt),
			"PVkwh": float(PVkwh),
			"PVkwh2d": float(PVkwh2d),
			"BAvolt": bavolt_val,
			"BAamps": baapms_val,
			"BAperc": baperc_val,
			"DCvolt": dcvolt_val,
			"DCamps": dcamp_val,
			"DCwatt": float(DCwatt),
			"DCkwh": float(DCkwh),
			"DCkwh2d": float(DCkwh2d),}
			}]
			DB_Submit(body_solar)	
			sys.exit(0)
			
	if sys.argv[2] not in ep_checks:
		# form a data record
		print (epever_title)
		print (epever_params)
		print ("\nAvailable checks: ", end="", flush=True)
		for v in ep_checks:
			print (v+' ', end="", flush=True)
		print ("")
		sys.exit(-1)
	#Connect to Epever	
	up=EP_Connect(sys.argv[1])
	def factory(*args, **kwargs):
		def f():
			if args[0] == 'pvwatt':
				ret_val=Get_RegVal(up.readReg, ep.regs['pvwatth'])
				ret_val=((int(ret_val) << 16) + Get_RegVal(up.readReg, ep.regs['pvwattl']))
			elif args[0] == 'dcwatt':
				ret_val = Get_RegVal(up.readReg, ep.regs['dcwatth'])
				ret_val = ((int(ret_val) << 16) + Get_RegVal(up.readReg, ep.regs['dcwattl']))
			elif args[0] == 'bawatt':
				ret_val = Get_RegVal(up.readReg, ep.regs['bawatth'])
				ret_val = ((int(ret_val) << 16) + Get_RegVal(up.readReg, ep.regs['bawattl']))
			else:
				ret_val=Get_RegVal(up.readReg, ep.regs[args[0]])
			return ret_val
		return f
	try:
		exec(f"f_{sys.argv[2]} = factory(sys.argv[2])")
		exec(f"ret_val=f_{sys.argv[2]}()")
	except Exception as e:
		Excp('FACTORY: '+str(e))
	print (ret_val)
	up.disconnect()
	sys.exit(0)
else:
	print (epever_title)
	print (epever_params+'\n')
	sys.exit(-1)
    
    
