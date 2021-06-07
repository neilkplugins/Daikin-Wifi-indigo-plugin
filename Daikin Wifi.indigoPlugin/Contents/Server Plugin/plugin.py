#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Copyright (c) 2013, Perceptive Automation, LLC. All rights reserved.
# http://www.perceptiveautomation.com

import indigo

import os
import sys
import random
import requests

# Note the "indigo" module is automatically imported and made available inside
# our global name space by the host process.

################################################################################
kHvacModeEnumToStrMap = {
	indigo.kHvacMode.Cool				: u"cool",
	indigo.kHvacMode.Heat				: u"heat",
	indigo.kHvacMode.HeatCool			: u"auto",
	indigo.kHvacMode.Off				: u"off",
	indigo.kHvacMode.ProgramHeat		: u"program heat",
	indigo.kHvacMode.ProgramCool		: u"program cool",
	indigo.kHvacMode.ProgramHeatCool	: u"program auto"
}

kFanModeEnumToStrMap = {
	indigo.kFanMode.AlwaysOn			: u"always on",
	indigo.kFanMode.Auto				: u"auto"
}

def _lookupActionStrFromHvacMode(hvacMode):
	return kHvacModeEnumToStrMap.get(hvacMode, u"unknown")

def _lookupActionStrFromFanMode(fanMode):
	return kFanModeEnumToStrMap.get(fanMode, u"unknown")

################################################################################
class Plugin(indigo.PluginBase):
	########################################
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		self.debug = pluginPrefs.get("showDebugInfo", False)

	def __del__(self):
		indigo.PluginBase.__del__(self)
	
	def baseURL(self, dev):
		if dev.pluginProps["requireHTTPS"]:
			prefix = "https://"
		else:
			prefix = "http://"
		return prefix+dev.pluginProps['address']


###################################################################################
# Plugin specific functions
###################################################################################

# Base functions to make the api call and return a raw response
# This includes the code necessary to support https based devices, but this will require someone with such a device to test it

	def makeAPIrequest(self, dev, api):
		controller_ip = dev.pluginProps["address"]
		try:
			timeout = int(self.pluginPrefs['timeout'])
		except:
			timeout = 2
		if dev.pluginProps["requireHTTPS"]:
			headers={"X-Daikin-uuid": dev.pluginProps["uuid"]}
			#response = requests.get(self.baseURL(dev) + api,headers=headers,ssl=False, timeout=1)
		else:
			headers={}
			#response = requests.get(self.baseURL(dev) + api, timeout=1)
		try:
			response = requests.get(self.baseURL(dev) + api, headers=headers, timeout=timeout)
			response.raise_for_status()
		except requests.exceptions.HTTPError as err:
		 	indigo.server.log("HTTP Error getting "+api+" from Daikin Unit "+dev.name)
		 	self.debugLog("Error is " + str(err))
			return "FAILED"

		except Exception as err:
		 	indigo.server.log("Unknown/Other Error getting "+api+" from Daikin Unit "+dev.name)
		 	self.debugLog("Error is " + str(err))
			return "FAILED"
		return response.text
	#
	def sendAPIrequest(self, dev, api):
		controller_ip = dev.pluginProps["address"]
		try:
			timeout = int(self.pluginPrefs['timeout'])
		except:
			timeout = 2
		if dev.pluginProps["requireHTTPS"]:
			headers={"X-Daikin-uuid": dev.pluginProps["uuid"]}
			#response = requests.post(self.baseURL(dev) + api,headers=headers,ssl=False, timeout=1)
		else:
			headers={}
			#response = requests.post(self.baseURL(dev) + api, timeout=1)
		self.debugLog(self.baseURL(dev) + api)
		try:
			response = requests.post(self.baseURL(dev) + api, headers=headers, timeout=timeout)
			response.raise_for_status()
		except requests.exceptions.HTTPError as err:
		 	indigo.server.log("HTTP Error posting "+api+" from Daikin Unit "+dev.name, isError=True)
		 	self.debugLog("Error is " + str(err))
			return False

		except Exception as err:
		 	indigo.server.log("Unknown/Other Error setting "+api+" from Daikin Unit "+dev.name, isError=True)
		 	self.debugLog("Error is " + str(err))
			return False
		self.debugLog(response.text)
		if response.text=="ret=PARAM NG":
			indigo.server.log("Request to update was processed but not sucessful " + api + " from Daikin Unit " + dev.name, isError=True)
			return False

		return True

	# Extract consumption values and return consumption in kWh for day and year
	def calculate_consumption(self, consumption):
		consumption_list = consumption.split('/')
		raw_sum = sum([int(item) for item in consumption_list])
		energy=round((raw_sum*0.1),1)
		return energy

	# Extract consumption values and return consumption in kWh for week to date
	# needs extra parameter as weekly data is returned on a rolling 14 day basis so need to trim off the days we don't need and just total the days this week starting Monday
	# consumption API returns this as s_wday
	def calculate_week_consumption(self, consumption, day):
		consumption_list = consumption.split('/')
		raw_sum=0
		for days in range(int(day)):
			raw_sum=raw_sum + int(consumption_list[days])
		energy = round((raw_sum * 0.1), 1)
		return energy

	#get the various sensor and control status as well as consumption data and parse it passing back a dictionary will all information
	#
	def requestData (self, dev, command):
		# get control response data
		control_response=self.makeAPIrequest(dev,'/aircon/get_control_info')
		if control_response=="FAILED":
			indigo.server.log("Failed to update control info "+dev.name+" aborting state refresh", isError=True)
			return
		split_control = control_response.split(',')
		returned_list = []
		for element in split_control:
			returned_list.append(element.split('='))
		#get sensor response data
		sensor_response = self.makeAPIrequest(dev, '/aircon/get_sensor_info')
		if sensor_response=="FAILED":
			indigo.server.log("Failed to update sensor "+dev.name+" aborting state refresh", isError=True)
			return
		split_sensor = sensor_response.split(',')
		for element in split_sensor:
			returned_list.append(element.split('='))
		self.debugLog(str(returned_list))


		day_consump=self.makeAPIrequest(dev,'/aircon/get_day_power_ex')
		if day_consump=="FAILED":
			indigo.server.log("Failed to update consumption "+dev.name+" aborting state refresh", isError=True)
			return
		split_day_consump=day_consump.split(',')
		for element in split_day_consump:
			returned_list.append(element.split('='))

		week_consump = self.makeAPIrequest(dev, '/aircon/get_week_power_ex')
		if week_consump == "FAILED":
			indigo.server.log("Failed to update consumption " + dev.name + " aborting state refresh", isError=True)
			return
		split_week_consump = week_consump.split(',')
		for element in split_week_consump:
			returned_list.append(element.split('='))
		year_consump = self.makeAPIrequest(dev, '/aircon/get_year_power_ex')
		if year_consump == "FAILED":
			indigo.server.log("Failed to update consumption " + dev.name + " aborting state refresh", isError=True)
			return
		split_year_consump = year_consump.split(',')
		for element in split_year_consump:
			returned_list.append(element.split('='))

		self.debugLog(str(returned_list))
		returned_dict = {}
		for element in returned_list:
			returned_dict[element[0]] = element[1]
		return returned_dict
		

	######################
	# Poll all of the states from the thermostat and pass new values to
	# Indigo Server.
	def _refreshStatesFromHardware(self, dev, logRefresh, commJustStarted):
		ac_data = self.requestData (dev, "getCurrentState")

		if type(ac_data) != dict:
			self.debugLog("Empty data aborting state updates")
			return

		if dev.pluginProps["measurement"] == "C":
			stateSuffix = u" °C"
		else:
			stateSuffix = u" °F"


		state_updates = []
		# Update the states necessary to make mode change (some duplication with the native device but potentially useful to have visible)

		#Calculate consumption & update states
		#day
		today_cool_consump = self.calculate_consumption(ac_data['curr_day_cool'])
		state_updates.append({'key': "today_cool_consump", 'value': today_cool_consump, 'uiValue' : str(today_cool_consump) + " kWh"})
		today_heat_consump = self.calculate_consumption(ac_data['curr_day_heat'])
		state_updates.append({'key': "today_heat_consump", 'value': today_heat_consump, 'uiValue' : str(today_heat_consump) + " kWh"})
		#week
		week_cool_consump = self.calculate_week_consumption(ac_data['week_cool'],ac_data['s_dayw'])
		state_updates.append({'key': "week_cool_consump", 'value': week_cool_consump, 'uiValue' : str(week_cool_consump) + " kWh"})
		week_heat_consump = self.calculate_week_consumption(ac_data['week_heat'],ac_data['s_dayw'])
		state_updates.append({'key': "week_heat_consump", 'value': week_heat_consump, 'uiValue' : str(week_heat_consump) + " kWh"})
		#year
		year_cool_consump = self.calculate_consumption(ac_data['curr_year_cool'])
		state_updates.append({'key': "year_cool_consump", 'value': year_cool_consump, 'uiValue' : str(year_cool_consump) + " kWh"})
		year_heat_consump = self.calculate_consumption(ac_data['curr_year_heat'])
		state_updates.append({'key': "year_heat_consump", 'value': round(year_heat_consump,1), 'uiValue' : str(round(year_heat_consump,1)) + " kWh"})
		total_consump=year_heat_consump+year_cool_consump+self.calculate_consumption(ac_data['prev_year_cool'])+self.calculate_consumption(ac_data['prev_year_heat'])
		state_updates.append({'key': "accumEnergyTotal", 'value': total_consump, 'uiValue' : str(total_consump) + " kWh"})


		# Update control and sensor info

		state_updates.append({'key': "mode", 'value': ac_data['mode']})
		state_updates.append({'key': "setpoint_temp", 'value': ac_data['stemp'], 'uiValue' : ac_data['stemp'] + stateSuffix})
		state_updates.append({'key': "last_cool_setpoint", 'value': ac_data['dt3'], 'uiValue' : ac_data['dt3'] + stateSuffix})
		state_updates.append({'key': "last_heat_setpoint", 'value': ac_data['dt4'], 'uiValue' : ac_data['dt4'] + stateSuffix})
		# if initial update the sepoints will be zero, so we need to set them to the last value stored on the device
		if dev.states["setpointCool"] < 10:
			state_updates.append({'key': "setpointCool", 'value': float(ac_data['dt3']), 'uiValue' : ac_data['dt3'] + stateSuffix})
		if dev.states["setpointHeat"] < 10:
			state_updates.append({'key': "setpointHeat", 'value': float(ac_data['dt4']), 'uiValue' : ac_data['dt4'] + stateSuffix})
		if dev.states["auto_setpoint"] < 10:
			state_updates.append({'key': "auto_setpoint", 'value': float(ac_data['dt1']), 'uiValue' : ac_data['dt1'] + stateSuffix})


		state_updates.append({'key': "setpoint_humidity", 'value': ac_data['shum']})

		ui_fan_rate=ac_data['f_rate']
		if ac_data['f_rate']=='A':
			ui_fan_rate='Auto'
		elif ac_data['f_rate']=='B':
			ui_fan_rate='Silence'
		ui_fan_dir=ac_data['f_dir']
		if ac_data['f_dir']=="0":
			ui_fan_dir="Stopped"
		elif ac_data['f_dir']=="1":
			ui_fan_dir="Vertical Motion"
		elif ac_data['f_dir'] == "2":
			ui_fan_dir = "Horizontal Motion"
		elif ac_data['f_dir'] == "3":
			ui_fan_dir = "Horizontal and Vertical Motion"



		state_updates.append({'key': "fan_rate", 'value': ac_data['f_rate'], 'uiValue' : ui_fan_rate})
		state_updates.append({'key': "fan_direction", 'value': ac_data['f_dir'],'uiValue' : ui_fan_dir })
		state_updates.append({'key': "outside_temp", 'value': ac_data['otemp'], 'uiValue' :  ac_data['otemp']+ stateSuffix})

		if ac_data['mode']=='2':
			#2 IS De Humidify
			state_updates.append({'key': "hvacOperationMode", 'value': 0})
			state_updates.append({'key': "operationMode", 'value': 'De-Humidify'})
			dev.updateStateImageOnServer(indigo.kStateImageSel.DehumidifierOn)

		elif ac_data['mode']=='3':
			#3 is Cool
			state_updates.append({'key': "hvacOperationMode", 'value': 2})
			state_updates.append({'key': "hvacHeaterIsOn", 'value': False})
			state_updates.append({'key': "hvacCoolerIsOn", 'value': True})
			state_updates.append({'key': "operationMode", 'value': 'Cooling'})
			if dev.pluginProps['sync_setpoints']:
				state_updates.append({'key': "setpointCool", 'value': float(ac_data['stemp']), 'uiValue' : ac_data['stemp'] + stateSuffix})
			dev.updateStateImageOnServer(indigo.kStateImageSel.HvacCoolMode)


		elif ac_data['mode']=='4':
			#4 is heat
			state_updates.append({'key': "hvacOperationMode", 'value': 1})
			state_updates.append({'key': "hvacHeaterIsOn", 'value': True})
			state_updates.append({'key': "hvacCoolerIsOn", 'value': False})
			state_updates.append({'key': "operationMode", 'value': 'Heating'})
			if dev.pluginProps['sync_setpoints']:
				state_updates.append({'key': "setpointHeat", 'value': float(ac_data['stemp']), 'uiValue' : ac_data['stemp'] + stateSuffix})
			dev.updateStateImageOnServer(indigo.kStateImageSel.HvacHeatMode)


		elif ac_data['mode']=='6':
			#fan mode 6
			state_updates.append({'key': "hvacOperationMode", 'value': 0})
			state_updates.append({'key': "operationMode", 'value': 'Fan'})
			dev.updateStateImageOnServer(indigo.kStateImageSel.FanHigh)


		else:
			# Then the unit must be in auto mode
			state_updates.append({'key': "hvacOperationMode", 'value': 3})
			state_updates.append({'key': "operationMode", 'value': 'Auto'})
			dev.updateStateImageOnServer(indigo.kStateImageSel.HvacAutoMode)
			if dev.pluginProps['sync_setpoints']:
				state_updates.append({'key': "auto_setpoint", 'value': float(ac_data['stemp']), 'uiValue' : ac_data['stemp'] + stateSuffix})


		# Order here is important as if the power is off then these states must be the last to update as "cooling" etc is reported even when off
		if ac_data['pow']=='1':
			state_updates.append({ 'key' : "unit_power", 'value' : 'on'})
		else:
			state_updates.append({ 'key' : "unit_power", 'value' : 'off'})
			state_updates.append({'key': "operationMode", 'value': 'Off'})
			state_updates.append({'key': "hvacOperationMode", 'value': 0})
			state_updates.append({'key': "hvacHeaterIsOn", 'value': False})
			state_updates.append({'key': "hvacCoolerIsOn", 'value': False})

		#
		state_updates.append({'key': 'temperatureInput1', 'value': float(ac_data['htemp']), 'uiValue': ac_data['htemp']+ stateSuffix})

		#
		if (ac_data['stemp'] == '--' or ac_data['stemp'] == 'M'):
			self.debugLog("No setpoint in fan or dry mode")


		dev.updateStatesOnServer(state_updates)

		return

	######################
	# Process action request from Indigo Server to change main thermostat's main mode.
	def _handleChangeHvacModeAction(self, dev, newHvacMode):
		# Command hardware module (dev) to change the thermostat mode here:
		# ** IMPLEMENT ME **
		indigo.server.log(str(newHvacMode))
		actionStr = _lookupActionStrFromHvacMode(newHvacMode)
		indigo.server.log(actionStr)

		# take a copy of the current states for overall power and mode
		pow = dev.states['unit_power']
		mode = dev.states['mode']
		setpoint=str(dev.states['setpoint_temp'])
		self.debugLog("action string is "+actionStr)
		if 'heat' in actionStr:
			#implement set mode function
			mode="4"
			pow=1
			setpoint=str(dev.states['setpointHeat'])
		if 'cool' in actionStr:
			#implement set mode function
			mode="3"
			pow=1
			setpoint=str(dev.states['setpointCool'])

		if 'auto' in actionStr:
			#implement set mode function
			mode="0"
			pow=1
			setpoint=str(dev.states['auto_setpoint'])
			dev.updateStateImageOnServer(indigo.kStateImageSel.HvacAutoMode)


		if 'off' in actionStr:
			#implement set mode function
			pow=0

		api_url='/aircon/set_control_info?pow='+str(pow)+'&mode='+mode+'&stemp='+setpoint+'&shum=0&f_rate='+str(dev.states['fan_rate'])+'&f_dir='+str(dev.states['fan_direction'])
		if self.sendAPIrequest(dev,api_url):

			# If success then log that the command was successfully sent.
			indigo.server.log(u"sent \"%s\" mode change to %s" % (dev.name, actionStr))

			# And then tell the Indigo Server to update the state.
			if "hvacOperationMode" in dev.states:
				dev.updateStateOnServer("hvacOperationMode", newHvacMode)
		else:
			# Else log failure but do NOT update state on Indigo Server.
			indigo.server.log(u"send \"%s\" mode change to %s failed" % (dev.name, actionStr), isError=True)



	######################
	# Process action request from Indigo Server to change a cool/heat setpoint.
	def _handleChangeSetpointAction(self, dev, newSetpoint, logActionName, stateKey):
		if dev.pluginProps["measurement"] == "C":
			if newSetpoint < 10.0:
				newSetpoint = 10.0		# Arbitrary -- set to whatever hardware minimum setpoint value is.
			elif newSetpoint > 30.0:
				newSetpoint = 30.0		# Arbitrary -- set to whatever hardware maximum setpoint value is.
		else:
			if newSetpoint < 50.0:
				newSetpoint = 50.0		# Arbitrary -- set to whatever hardware minimum setpoint value is.
			elif newSetpoint > 86.0:
				newSetpoint = 86.0		# Arbitrary -- set to whatever hardware maximum setpoint value is.

		sendSuccess=True
		if dev.states['unit_power']=="on":
			pow='1'
		else:
			pow='0'
		control_url = '/aircon/set_control_info?pow=' + pow + '&mode=' + dev.states['mode'] + '&stemp=' + str(newSetpoint) + '&shum=' + str(dev.states['setpoint_humidity']) + '&f_rate=' + str(dev.states['fan_rate']) + '&f_dir=' + str(dev.states['fan_direction'])
		self.debugLog(control_url)
		if self.sendAPIrequest(dev, control_url):
			sendSuccess = True
		else:
			sendSuccess = False

		if sendSuccess:
			# If success then log that the command was successfully sent.
			indigo.server.log(u"sent \"%s\" %s to %.1f°" % (dev.name, logActionName, newSetpoint))

			# And then tell the Indigo Server to update the state.
			if stateKey in dev.states:
				if dev.pluginProps["measurement"] == "C":
					stateSuffix = u" °C"
				else:
					stateSuffix = u" °F"
				dev.updateStateOnServer(stateKey, newSetpoint, uiValue=str(newSetpoint)+stateSuffix)
		else:
			# Else log failure but do NOT update state on Indigo Server.
			indigo.server.log(u"send \"%s\" %s to %.1f° failed" % (dev.name, logActionName, newSetpoint), isError=True)

	########################################
	def startup(self):
		self.debugLog(u"startup called")

	def shutdown(self):
		self.debugLog(u"shutdown called")

	########################################
	def runConcurrentThread(self):
		self.debugLog("Starting concurrent thread")
		try:
			pollingFreq = int(self.pluginPrefs['pollingFrequency'])
		except:
			pollingFreq = 15

		try:
			while True:
				for dev in indigo.devices.iter("self"):
					if not dev.enabled or not dev.configured:
						continue

					self._refreshStatesFromHardware(dev, False, False)


				self.sleep(pollingFreq)
		except self.StopThread:
			pass	# Optionally catch the StopThread exception and do any needed cleanup.

	########################################
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):
		return (True, valuesDict)

	########################################
	def deviceStartComm(self, dev):

		dev.stateListOrDisplayStateIdChanged()
		self._refreshStatesFromHardware(dev, True, True)

	def deviceStopComm(self, dev):
		# Called when communication with the hardware should be shutdown.
		pass

	########################################
	# Thermostat Action callback
	######################
	# Main thermostat action bottleneck called by Indigo Server.
	def actionControlThermostat(self, action, dev):
		indigo.server.log(str(action))
		###### SET HVAC MODE ######
		if action.thermostatAction == indigo.kThermostatAction.SetHvacMode:
			self._handleChangeHvacModeAction(dev, action.actionMode)

		###### SET FAN MODE ######
		elif action.thermostatAction == indigo.kThermostatAction.SetFanMode:
			self._handleChangeFanModeAction(dev, action.actionMode)

		###### SET COOL SETPOINT ######
		elif action.thermostatAction == indigo.kThermostatAction.SetCoolSetpoint:
			newSetpoint = action.actionValue
			self._handleChangeSetpointAction(dev, newSetpoint, u"change cool setpoint", u"setpointCool")

		###### SET HEAT SETPOINT ######
		elif action.thermostatAction == indigo.kThermostatAction.SetHeatSetpoint:
			newSetpoint = action.actionValue
			self._handleChangeSetpointAction(dev, newSetpoint, u"change heat setpoint", u"setpointHeat")

		###### DECREASE/INCREASE COOL SETPOINT ######
		elif action.thermostatAction == indigo.kThermostatAction.DecreaseCoolSetpoint:
			newSetpoint = dev.coolSetpoint - action.actionValue
			self._handleChangeSetpointAction(dev, newSetpoint, u"decrease cool setpoint", u"setpointCool")

		elif action.thermostatAction == indigo.kThermostatAction.IncreaseCoolSetpoint:
			newSetpoint = dev.coolSetpoint + action.actionValue
			self._handleChangeSetpointAction(dev, newSetpoint, u"increase cool setpoint", u"setpointCool")

		###### DECREASE/INCREASE HEAT SETPOINT ######
		elif action.thermostatAction == indigo.kThermostatAction.DecreaseHeatSetpoint:
			newSetpoint = dev.heatSetpoint - action.actionValue
			self._handleChangeSetpointAction(dev, newSetpoint, u"decrease heat setpoint", u"setpointHeat")

		elif action.thermostatAction == indigo.kThermostatAction.IncreaseHeatSetpoint:
			newSetpoint = dev.heatSetpoint + action.actionValue
			self._handleChangeSetpointAction(dev, newSetpoint, u"increase heat setpoint", u"setpointHeat")

		###### REQUEST STATE UPDATES ######
		elif action.thermostatAction in [indigo.kThermostatAction.RequestStatusAll, indigo.kThermostatAction.RequestMode,
		indigo.kThermostatAction.RequestEquipmentState, indigo.kThermostatAction.RequestTemperatures, indigo.kThermostatAction.RequestHumidities,
		indigo.kThermostatAction.RequestDeadbands, indigo.kThermostatAction.RequestSetpoints]:
			self._refreshStatesFromHardware(dev, True, False)

	########################################
	# General Action callback
	######################
	def actionControlGeneral(self, action, dev):
		###### BEEP ######
		if action.deviceAction == indigo.kDeviceGeneralAction.Beep:
			# Beep the hardware module (dev) here:
			# ** IMPLEMENT ME **
			indigo.server.log(u"sent \"%s\" %s" % (dev.name, "beep request"))

		###### ENERGY UPDATE ######
		elif action.deviceAction == indigo.kDeviceGeneralAction.EnergyUpdate:
			# Request hardware module (dev) for its most recent meter data here:
			# ** IMPLEMENT ME **
			indigo.server.log(u"sent \"%s\" %s" % (dev.name, "energy update request not supported"))

		###### ENERGY RESET ######
		elif action.deviceAction == indigo.kDeviceGeneralAction.EnergyReset:
			# Request that the hardware module (dev) reset its accumulative energy usage data here:
			# ** IMPLEMENT ME **
			indigo.server.log(u"sent \"%s\" %s" % (dev.name, "energy reset request not supported"))

		###### STATUS REQUEST ######
		elif action.deviceAction == indigo.kDeviceGeneralAction.RequestStatus:
			# Query hardware module (dev) for its current status here. This differs from the 
			# indigo.kThermostatAction.RequestStatusAll action - for instance, if your thermo
			# is battery powered you might only want to update it only when the user uses
			# this status request (and not from the RequestStatusAll). This action would
			# get all possible information from the thermostat and the other call
			# would only get thermostat-specific information:
			# ** GET BATTERY INFO **
			# and call the common function to update the thermo-specific data
			self._refreshStatesFromHardware(dev, True, False)
			indigo.server.log(u"sent \"%s\" %s" % (dev.name, "status request"))


	def setAutoSetpoint(self,pluginAction,dev):
		if dev.pluginProps["measurement"] == "C":
			stateSuffix = u" °C"
		else:
			stateSuffix = u" °F"
		#first update setpoint
		dev.updateStateOnServer('auto_setpoint', float(pluginAction.props.get("setpoint")), uiValue=str(float(pluginAction.props.get("setpoint"))) + stateSuffix)
		# and if in auto mode also apply that to stemp to change the current setpoint
		if dev.states['operationMode']=="Auto":
			if dev.states['unit_power']=="on":
				pow='1'
			else:
				pow='0'

			api_url = '/aircon/set_control_info?pow=' + str(pow) + '&mode=' + "0" + '&stemp=' + pluginAction.props.get('setpoint') + '&shum=0&f_rate=' + str(dev.states['fan_rate']) + '&f_dir=' + str(dev.states['fan_direction'])
			if self.sendAPIrequest(dev, api_url):
				# If success then log that the command was successfully sent.
				indigo.server.log(u"Updated Auto Setpoint to "+ pluginAction.props.get('setpoint')+ " for "+dev.name)

			else:
				# Else log failure but do NOT update state on Indigo Server.
				indigo.server.log(u"send setpoint change to "+pluginAction.props.get('setpoint')+" for "+dev.name)

	def increaseAutoSetpoint(self, pluginAction, dev):
		if dev.pluginProps["measurement"] == "C":
			stateSuffix = u" °C"
		else:
			stateSuffix = u" °F"
		# first update setpoint
		newsetpoint=float(dev.states['auto_setpoint'])+float(pluginAction.props.get("delta"))
		if dev.pluginProps["measurement"] == "C":
			if newsetpoint < 10.0:
				newsetpoint = 10.0		# Arbitrary -- set to whatever hardware minimum setpoint value is.
			elif newsetpoint > 30.0:
				newsetpoint = 30.0		# Arbitrary -- set to whatever hardware maximum setpoint value is.
		else:
			if newsetpoint < 50.0:
				newsetpoint = 50.0		# Arbitrary -- set to whatever hardware minimum setpoint value is.
			elif newsetpoint > 86.0:
				newsetpoint = 86.0		# Arbitrary -- set to whatever hardware maximum setpoint value is.

		indigo.server.log("New Auto Setpoint is "+str(newsetpoint))
		dev.updateStateOnServer('auto_setpoint', newsetpoint,uiValue=str(newsetpoint) + stateSuffix)
		# and if in auto mode also apply that to stemp to change the current setpoint
		if dev.states['operationMode'] == "Auto":
			if dev.states['unit_power'] == "on":
				pow = '1'
			else:
				pow = '0'

			api_url = '/aircon/set_control_info?pow=' + str(pow) + '&mode=' + "0" + '&stemp=' + str(newsetpoint) + '&shum=0&f_rate=' + str(dev.states['fan_rate']) + '&f_dir=' + str(
				dev.states['fan_direction'])
			if self.sendAPIrequest(dev, api_url):
				# If success then log that the command was successfully sent.
				indigo.server.log(
					u"Updated Auto Setpoint to " + str(newsetpoint) + " for " + dev.name)

			else:
				# Else log failure but do NOT update state on Indigo Server.
				indigo.server.log(u"send setpoint change to " + str(newsetpoint) + " for " + dev.name)

	def decreaseAutoSetpoint(self, pluginAction, dev):
		if dev.pluginProps["measurement"] == "C":
			stateSuffix = u" °C"
		else:
			stateSuffix = u" °F"
		# first update setpoint
		newsetpoint=float(dev.states['auto_setpoint'])-float(pluginAction.props.get("delta"))
		if dev.pluginProps["measurement"] == "C":
			if newsetpoint < 10.0:
				newsetpoint = 10.0		# Arbitrary -- set to whatever hardware minimum setpoint value is.
			elif newsetpoint > 30.0:
				newsetpoint = 30.0		# Arbitrary -- set to whatever hardware maximum setpoint value is.
		else:
			if newsetpoint < 50.0:
				newsetpoint = 50.0		# Arbitrary -- set to whatever hardware minimum setpoint value is.
			elif newsetpoint > 86.0:
				newsetpoint = 86.0		# Arbitrary -- set to whatever hardware maximum setpoint value is.

		indigo.server.log("New Auto Setpoint is "+str(newsetpoint))
		dev.updateStateOnServer('auto_setpoint', newsetpoint,uiValue=str(newsetpoint) + stateSuffix)
		# and if in auto mode also apply that to stemp to change the current setpoint
		if dev.states['operationMode'] == "Auto":
			if dev.states['unit_power'] == "on":
				pow = '1'
			else:
				pow = '0'

			api_url = '/aircon/set_control_info?pow=' + str(pow) + '&mode=' + "0" + '&stemp=' + str(newsetpoint) + '&shum=0&f_rate=' + str(dev.states['fan_rate']) + '&f_dir=' + str(
				dev.states['fan_direction'])
			if self.sendAPIrequest(dev, api_url):
				# If success then log that the command was successfully sent.
				indigo.server.log(u"Updated Auto Setpoint to " + str(newsetpoint) + " for " + dev.name)

			else:
				# Else log failure but do NOT update state on Indigo Server.
				indigo.server.log(u"send setpoint change to " + str(newsetpoint) + " for " + dev.name)

	def powerOff(self, pluginAction, dev):
		try:
			controller_ip = dev.pluginProps["address"]
		except:
			indigo.server.log("No Device specified - add to action config")
			return
		control_url = '/aircon/set_control_info?pow=0&mode=' + dev.states['mode'] + '&stemp=' + str(dev.states['setpoint_temp']) + '&shum=' + str(dev.states['setpoint_humidity']) + '&f_rate=' + str(dev.states['fan_rate']) + '&f_dir=' + str(dev.states['fan_direction'])
		self.debugLog(control_url)
		if self.sendAPIrequest(dev, control_url):
			indigo.server.log(dev.name + ": switched off")
		else:
			indigo.server.log(dev.name + ": Unable to switch Daikin unit off, check IP Address")

	def powerOn(self, pluginAction, dev):
		try:
			controller_ip = dev.pluginProps["address"]
		except:
			indigo.server.log("No Device specified - add to action config")
			return
		control_url = '/aircon/set_control_info?pow=1&mode=' + dev.states['mode'] + '&stemp=' + str(dev.states['setpoint_temp']) + '&shum=' + str(dev.states['setpoint_humidity']) + '&f_rate=' + str(dev.states['fan_rate']) + '&f_dir=' + str(dev.states['fan_direction'])
		self.debugLog(control_url)
		if self.sendAPIrequest(dev, control_url):
			indigo.server.log(dev.name + ": switched on")
		else:
			indigo.server.log(dev.name + ": Unable to switch Daikin unit on, check IP Address")

	def fanSpeed(self, pluginAction, dev):
		new_speed=pluginAction.props.get("speed")
		try:
			controller_ip = dev.pluginProps["address"]
		except:
			indigo.server.log("No Device specified - add to action config")
			return
		if dev.states['unit_power']=="on":
			pow='1'
		else:
			pow='0'
		control_url = '/aircon/set_control_info?pow='+pow+'&mode=' + dev.states['mode'] + '&stemp=' + str(dev.states['setpoint_temp']) + '&shum=' + str(dev.states['setpoint_humidity']) + '&f_rate=' + new_speed + '&f_dir=' + str(dev.states['fan_direction'])
		self.debugLog(control_url)
		if self.sendAPIrequest(dev, control_url):
			indigo.server.log(dev.name + ": set fan speed to "+new_speed)
		else:
			indigo.server.log(dev.name + ": Unable to set fan speed")

	def fanDirection(self, pluginAction, dev):
		new_direction=pluginAction.props.get("direction")
		try:
			controller_ip = dev.pluginProps["address"]
		except:
			indigo.server.log("No Device specified - add to action config")
			return
		if dev.states['unit_power']=="on":
			pow='1'
		else:
			pow='0'
		control_url = '/aircon/set_control_info?pow='+pow+'&mode=' +dev.states['mode'] + '&stemp=' + str(dev.states['setpoint_temp']) + '&shum=' + str(dev.states['setpoint_humidity']) + '&f_rate=' + str(dev.states['fan_rate']+ '&f_dir=' + new_direction)
		self.debugLog(control_url)
		if self.sendAPIrequest(dev, control_url):
			indigo.server.log(dev.name + ": set fan mode to " + new_direction)
		else:
			indigo.server.log(dev.name + ": Unable to set fan mode")

	def fanOnly(self, pluginAction, dev):
		try:
			controller_ip = dev.pluginProps["address"]
		except:
			indigo.server.log("No Device specified - add to action config")
			return
		if dev.states['unit_power']=="on":
			pow='1'
		else:
			pow='0'
		control_url = '/aircon/set_control_info?pow='+pow+'&mode=6&stemp=' + str(dev.states['setpoint_temp']) + '&shum=' + str(dev.states['setpoint_humidity']) + '&f_rate=' + str(dev.states['fan_rate']) + '&f_dir=' + str(dev.states['fan_direction'])
		self.debugLog(control_url)
		if self.sendAPIrequest(dev, control_url):
			indigo.server.log(dev.name + ": set to fan only mode to ")
		else:
			indigo.server.log(dev.name + ": Unable to set fan only mode")

	def deHum(self, pluginAction, dev):
		try:
			controller_ip = dev.pluginProps["address"]
		except:
			indigo.server.log("No Device specified - add to action config")
			return
		if dev.states['unit_power']=="on":
			pow='1'
		else:
			pow='0'
		control_url = '/aircon/set_control_info?pow='+pow+'&mode=2&stemp=' + str(dev.states['setpoint_temp']) + '&shum=' + str(dev.states['setpoint_humidity']) + '&f_rate=' + str(dev.states['fan_rate']) + '&f_dir=' + str(dev.states['fan_direction'])
		self.debugLog(control_url)
		if self.sendAPIrequest(dev, control_url):
			indigo.server.log(dev.name + ": set dry mode to ")
		else:
			indigo.server.log(dev.name + ": Unable to set dry mode")


#### Device Configuration validation

	def validateDeviceConfigUi(self, valuesDict, dev_type, dev):
		try:
			control_url = 'http://' + valuesDict['address'] + '/common/basic_info'
			self.debugLog(control_url)
			response = requests.get(control_url, timeout=3)
			if response.status_code != 200:
				self.debugLog("Failed to retrieve " + control_url + " for " + dev.name, isError=True)
				raise Exception("No connection")


		except:
			indigo.server.log("Unknown error connecting to Daikin Unit at "+valuesDict['address'],isError=True)
			errorsDict = indigo.Dict()
			errorsDict['address'] = "Failed to Connection to AC Unit - Check IP Address and if HTPPS required"
			return (False, valuesDict, errorsDict)

		return (True, valuesDict)

	########################################
	# Menu Methods
	########################################
	def toggleDebugging(self):
		if self.debug:
			indigo.server.log("Turning off debug logging")
			self.pluginPrefs["showDebugInfo"] = False
		else:
			indigo.server.log("Turning on debug logging")
			self.pluginPrefs["showDebugInfo"] = True
		self.debug = not self.debug
