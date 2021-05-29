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
import simplejson

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


	########################################
	# Internal utility methods. Some of these are useful to provide
	# a higher-level abstraction for accessing/changing thermostat
	# properties or states.
	######################
	def _getTempSensorCount(self, dev):
		return int(dev.pluginProps["NumTemperatureInputs"])

	def _getHumiditySensorCount(self, dev):
		return int(dev.pluginProps["NumHumidityInputs"])

	######################
	def _changeTempSensorCount(self, dev, count):
		newProps = dev.pluginProps
		newProps["NumTemperatureInputs"] = count
		dev.replacePluginPropsOnServer(newProps)

	def _changeHumiditySensorCount(self, dev, count):
		newProps = dev.pluginProps
		newProps["NumHumidityInputs"] = count
		dev.replacePluginPropsOnServer(newProps)

	def _changeAllTempSensorCounts(self, count):
		for dev in indigo.devices.iter("self"):
			self._changeTempSensorCount(dev, count)

	def _changeAllHumiditySensorCounts(self, count):
		for dev in indigo.devices.iter("self"):
			self._changeHumiditySensorCount(dev, count)

	######################
	def _changeTempSensorValue(self, dev, index, value):
		# Update the temperature value at index. If index is greater than the "NumTemperatureInputs"
		# an error will be displayed in the Event Log "temperature index out-of-range"
		#stateKey = u"temperatureInput" + str(index)
		#dev.updateStateOnServer(stateKey, value, uiValue="%d °F" % (value))
		#self.debugLog(u"\"%s\" called update %s %d" % (dev.name, stateKey, value))
		X = 1

	def _changeHumiditySensorValue(self, dev, index, value):
		# Update the humidity value at index. If index is greater than the "NumHumidityInputs"
		# an error will be displayed in the Event Log "humidity index out-of-range"
		#stateKey = u"humidityInput" + str(index)
		#dev.updateStateOnServer(stateKey, value, uiValue="%d °F" % (value))
		#self.debugLog(u"\"%s\" called update %s %d" % (dev.name, stateKey, value))
		X = 1
	def makeAPIrequest(self, dev, api):
		controller_ip = dev.pluginProps["address"]
		if dev.pluginProps["requireHTTPS"]:
			headers={"X-Daikin-uuid": dev.pluginProps["uuid"]}
			#response = requests.get(self.baseURL(dev) + api,headers=headers,ssl=False, timeout=1)
		else:
			headers={}
			#response = requests.get(self.baseURL(dev) + api, timeout=1)
		try:
			response = requests.get(self.baseURL(dev) + api, headers=headers, timeout=1)
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
		if dev.pluginProps["requireHTTPS"]:
			headers={"X-Daikin-uuid": dev.pluginProps["uuid"]}
			#response = requests.post(self.baseURL(dev) + api,headers=headers,ssl=False, timeout=1)
		else:
			headers={}
			#response = requests.post(self.baseURL(dev) + api, timeout=1)
		self.debugLog(self.baseURL(dev) + api)
		try:
			response = requests.post(self.baseURL(dev) + api, headers=headers, timeout=1)
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
#


	# Daikin request
	#
	def requestData (self, dev, command):
		# get control response data
		control_response=self.makeAPIrequest(dev,'/aircon/get_control_info')
		if control_response=="FAILED":
			indigo.server.log("Failed to update "+dev.name+" aborting state refresh")
			return
		split_control = control_response.split(',')
		returned_list = []
		for element in split_control:
			returned_list.append(element.split('='))
		#get sensor response data
		sensor_response = self.makeAPIrequest(dev, '/aircon/get_sensor_info')
		if control_response=="FAILED":
			indigo.server.log("Failed to update "+dev.name+" aborting state refresh")
			return
		split_sensor = sensor_response.split(',')
		for element in split_sensor:
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

		state_updates.append({'key': "mode", 'value': ac_data['mode']})
		state_updates.append({'key': "setpoint_temp", 'value': ac_data['stemp'], 'uiValue' : ac_data['stemp'] + stateSuffix})
		state_updates.append({'key': "cool_setpoint", 'value': ac_data['dt3'], 'uiValue' : ac_data['dt3'] + stateSuffix})
		state_updates.append({'key': "heat_setpoint", 'value': ac_data['dt4'], 'uiValue' : ac_data['dt4'] + stateSuffix})
		state_updates.append({'key': "auto_setpoint", 'value': ac_data['dt1'], 'uiValue' : ac_data['dt3'] + stateSuffix})

		state_updates.append({'key': "setpoint_humidity", 'value': ac_data['shum']})

		ui_fan_rate=ac_data['f_rate']
		if ac_data['f_rate']=='A':
			ui_fan_rate='Auto'
		elif ac_data['f_rate']=='B':
			ui_fan_rate='Silence'

		state_updates.append({'key': "fan_rate", 'value': ac_data['f_rate'], 'uiValue' : ui_fan_rate})
		state_updates.append({'key': "fan_direction", 'value': ac_data['f_dir']})
		state_updates.append({'key': "outside_temp", 'value': ac_data['otemp'], 'uiValue' :  ac_data['otemp']+ stateSuffix})

		if ac_data['mode']=='2':
			#2 IS De Humidify
			state_updates.append({'key': "hvacOperationMode", 'value': 0})
			state_updates.append({'key': "operationMode", 'value': 'De-Humidify'})
		elif ac_data['mode']=='3':
			#3 is Cool
			state_updates.append({'key': "hvacOperationMode", 'value': 2})
			state_updates.append({'key': "hvacHeaterIsOn", 'value': False})
			state_updates.append({'key': "hvacCoolerIsOn", 'value': True})
			state_updates.append({'key': "operationMode", 'value': 'Cooling'})

		elif ac_data['mode']=='4':
			#4 is heat
			state_updates.append({'key': "hvacOperationMode", 'value': 1})
			state_updates.append({'key': "hvacHeaterIsOn", 'value': True})
			state_updates.append({'key': "hvacCoolerIsOn", 'value': False})
			state_updates.append({'key': "operationMode", 'value': 'Heating'})

		elif ac_data['mode']=='6':
			#fan mode 6
			state_updates.append({'key': "hvacOperationMode", 'value': 0})
			state_updates.append({'key': "operationMode", 'value': 'Fan'})

		else:
			state_updates.append({'key': "hvacOperationMode", 'value': 3})
			state_updates.append({'key': "operationMode", 'value': 'Auto'})

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
		else:
			state_updates.append({'key': "setpointHeat", 'value': float(ac_data['stemp']), 'uiValue' : ac_data['stemp'] + stateSuffix})
			state_updates.append({'key': "setpointCool", 'value': float(ac_data['stemp']), 'uiValue' : ac_data['stemp'] + stateSuffix})

		dev.updateStatesOnServer(state_updates)


# dev.updateStateOnServer("operationMode", data['operation'])
		# dev.updateStateOnServer("autoOperation", data['autoOperation'])
		# dev.updateStateOnServer("operationTrigger", data['operationTrigger'])
		# dev.updateStateOnServer("controlPhase", data['controlPhase'])
		# dev.updateStateOnServer("boxConnected", data['boxConnected'])
		# dev.updateStateOnServer("homeId", data['homeId'])
		#
		# if data['gwConnected']:
		# 	dev.updateStateOnServer("gatewayConnected", True)
		# else:
		# 	dev.updateStateOnServer("gatewayConnected", False)
		#
		# if data['tsConnected']:
		# 	dev.updateStateOnServer("temperatureSensorConnected", True)
		# else:
		# 	dev.updateStateOnServer("temperatureSensorConnected", False)


		#	Other states that should also be updated:
		# ** IMPLEMENT ME **
		# dev.updateStateOnServer("setpointHeat", floating number here)
		# dev.updateStateOnServer("setpointCool", floating number here)
		# dev.updateStateOnServer("hvacOperationMode", some indigo.kHvacMode.* value here)
		# dev.updateStateOnServer("hvacFanMode", some indigo.kFanMode.* value here)
		# dev.updateStateOnServer("hvacCoolerIsOn", True or False here)
		# dev.updateStateOnServer("hvacHeaterIsOn", True or False here)
		# dev.updateStateOnServer("hvacFanIsOn", True or False here)
		# if logRefresh:
		# 	try:
		# 		if "setpointHeat" in dev.states:
		# 			indigo.server.log(u"received \"%s\" heat setpoint update to %.1f°" % (dev.name, dev.states["setpointHeat"]))
		# 		if "setpointCool" in dev.states:
		# 			indigo.server.log(u"received \"%s\" cool setpoint update to %.1f°" % (dev.name, dev.states["setpointCool"]))
		# 		if "hvacOperationMode" in dev.states:
		# 			indigo.server.log(u"received \"%s\" main mode update to %s" % (dev.name, _lookupActionStrFromHvacMode(dev.states["hvacOperationMode"])))
		# 		if "hvacFanMode" in dev.states:
		# 			indigo.server.log(u"received \"%s\" fan mode update to %s" % (dev.name, _lookupActionStrFromFanMode(dev.states["hvacFanMode"])))
		# 		if "hvacOperationMode" in dev.states:
		# 			indigo.server.log(u"received \"%s\" main mode update to %s" % (dev.name, _lookupActionStrFromHvacMode(dev.states["hvacOperationMode"])))
		# 	except:
		# 		X = 1 # Placeholder to just ignore this because it is likely a new device with no data yet
		#
		#
		# #if parsed_json['controlPhase'] == "COOLDOWN":

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
			mode=4
			pow=1
			setpoint=str(dev.states['heat_setpoint'])
		if 'cool' in actionStr:
			#implement set mode function
			mode=3
			pow=1
			setpoint=str(dev.states['cool_setpoint'])

		if 'auto' in actionStr:
			#implement set mode function
			mode=0
			pow=1
			setpoint=str(dev.states['auto_setpoint'])

		if 'off' in actionStr:
			#implement set mode function
			pow=0

		api_url='/aircon/set_control_info?pow='+str(pow)+'&mode='+str(mode)+'&stemp='+setpoint+'&shum=0&f_rate='+str(dev.states['fan_rate'])+'&f_dir='+str(dev.states['fan_direction'])
		if self.sendAPIrequest(dev,api_url):

			# If success then log that the command was successfully sent.
			indigo.server.log(u"sent \"%s\" mode change to %s" % (dev.name, actionStr))

			# And then tell the Indigo Server to update the state.
			if "hvacOperationMode" in dev.states:
				dev.updateStateOnServer("hvacOperationMode", newHvacMode)
		else:
			# Else log failure but do NOT update state on Indigo Server.
			indigo.server.log(u"send \"%s\" mode change to %s failed" % (dev.name, actionStr), isError=True)

	# ######################
	# # Process action request from Indigo Server to change thermostat's fan mode.
	# def _handleChangeFanModeAction(self, dev, newFanMode):
	# 	# Command hardware module (dev) to change the fan mode here:
	# 	# ** IMPLEMENT ME **
	# 	sendSuccess = True		# Set to False if it failed.
	#
	# 	actionStr = _lookupActionStrFromFanMode(newFanMode)
	# 	if sendSuccess:
	# 		# If success then log that the command was successfully sent.
	# 		indigo.server.log(u"sent \"%s\" fan mode change to %s" % (dev.name, actionStr))
	#
	# 		# And then tell the Indigo Server to update the state.
	# 		if "hvacFanMode" in dev.states:
	# 			dev.updateStateOnServer("hvacFanMode", newFanMode)
	# 	else:
	# 		# Else log failure but do NOT update state on Indigo Server.
	# 		indigo.server.log(u"send \"%s\" fan mode change to %s failed" % (dev.name, actionStr), isError=True)

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
		control_url = '/aircon/set_control_info?pow=' + pow + '&mode=' + str(dev.states['mode']) + '&stemp=' + str(newSetpoint) + '&shum=' + str(dev.states['setpoint_humidity']) + '&f_rate=' + str(dev.states['fan_rate']) + '&f_dir=' + str(dev.states['fan_direction'])
		indigo.server.log(control_url)
		if self.sendAPIrequest(dev, control_url):
			sendSuccess = True
		else:
			sendSuccess = False

		if sendSuccess:
			# If success then log that the command was successfully sent.
			indigo.server.log(u"sent \"%s\" %s to %.1f°" % (dev.name, logActionName, newSetpoint))

			# And then tell the Indigo Server to update the state.
			if stateKey in dev.states:
				dev.updateStateOnServer(stateKey, newSetpoint, uiValue="%.1f °F" % (newSetpoint))
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
		# Called when communication with the hardware should be established.
		# Here would be a good place to poll out the current states from the
		# thermostat. If periodic polling of the thermostat is needed (that
		# is, it doesn't broadcast changes back to the plugin somehow), then
		# consider adding that to runConcurrentThread() above.
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
			indigo.server.log(u"sent \"%s\" %s" % (dev.name, "energy update request"))

		###### ENERGY RESET ######
		elif action.deviceAction == indigo.kDeviceGeneralAction.EnergyReset:
			# Request that the hardware module (dev) reset its accumulative energy usage data here:
			# ** IMPLEMENT ME **
			indigo.server.log(u"sent \"%s\" %s" % (dev.name, "energy reset request"))

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


	########################################
	# Actions defined in MenuItems.xml. In this case we just use these menu actions to
	# simulate different thermostat configurations (how many temperature and humidity
	# sensors they have).
	####################
	def powerOff(self, pluginAction, dev):
		try:
			controller_ip = dev.pluginProps["address"]
		except:
			indigo.server.log("No Device specified - add to action config")
			return
		control_url = '/aircon/set_control_info?pow=0&mode=' + str(dev.states['mode']) + '&stemp=' + str(dev.states['setpoint_temp']) + '&shum=' + str(dev.states['setpoint_humidity']) + '&f_rate=' + str(dev.states['fan_rate']) + '&f_dir=' + str(dev.states['fan_direction'])
		indigo.server.log(control_url)
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
		control_url = '/aircon/set_control_info?pow=1&mode=' + str(dev.states['mode']) + '&stemp=' + str(dev.states['setpoint_temp']) + '&shum=' + str(dev.states['setpoint_humidity']) + '&f_rate=' + str(dev.states['fan_rate']) + '&f_dir=' + str(dev.states['fan_direction'])
		indigo.server.log(control_url)
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
		control_url = '/aircon/set_control_info?pow='+pow+'&mode=' + str(dev.states['mode']) + '&stemp=' + str(dev.states['setpoint_temp']) + '&shum=' + str(dev.states['setpoint_humidity']) + '&f_rate=' + new_speed + '&f_dir=' + str(dev.states['fan_direction'])
		indigo.server.log(control_url)
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
		control_url = '/aircon/set_control_info?pow='+pow+'&mode=' + str(dev.states['mode']) + '&stemp=' + str(dev.states['setpoint_temp']) + '&shum=' + str(dev.states['setpoint_humidity']) + '&f_rate=' + str(dev.states['fan_rate']+ '&f_dir=' + new_direction)
		indigo.server.log(control_url)
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
		indigo.server.log(control_url)
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
		indigo.server.log(control_url)
		if self.sendAPIrequest(dev, control_url):
			indigo.server.log(dev.name + ": set dry mode to ")
		else:
			indigo.server.log(dev.name + ": Unable to set dry mode")

	def changeTempSensorCountTo2(self):
		self._changeAllTempSensorCounts(2)

	def changeTempSensorCountTo3(self):
		self._changeAllTempSensorCounts(3)

	def changeHumiditySensorCountTo0(self):
		self._changeAllHumiditySensorCounts(0)

	def changeHumiditySensorCountTo1(self):
		self._changeAllHumiditySensorCounts(1)

	def changeHumiditySensorCountTo2(self):
		self._changeAllHumiditySensorCounts(2)

	def changeHumiditySensorCountTo3(self):
		self._changeAllHumiditySensorCounts(3)

#### Device Configuration validation

	def validateDeviceConfigUi(self, valuesDict, dev_type, dev):
		indigo.server.log(str(valuesDict))
		try:
			control_url = 'http://' + valuesDict['address'] + '/common/basic_info'
			self.debugLog(control_url)
			indigo.server.log(control_url)
			response = requests.get(control_url, timeout=1)
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
