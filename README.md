# Daikin-Wifi-indigo
An indigo plugin to connect to Daikin Wifi AC Controllers.  This was developed against the BRP069B41 model unit that uses the Daikin Online Controller iOS App.  It is based on the work from https://github.com/ael-code/daikin-control and should work with other models.  This version has untested and hidden functionality to support versions of the controller that require https but this will reqiure someone with such a unit to work with me to test.  For more information on that check out https://github.com/ael-code/daikin-control/issues/27 and let me know via the Indigo forum at https://forums.indigodomo.com/viewforum.php?f=358 as well as any other requests for help.

The plugin allows you to create a device for each connected unit, and simply requires an IP address to be configured, these units do not have any form of local security or authentication.

I have mapped the functionality as closely as possible to the Indigo Thermostat model, and this appears to work but as my knowledge improves I will refine this.

The thermostat specific actions should work as per a native Indigo thermostat.  For the Fan and Auto modes, they do not map to the indigo device cleanly so they are implemented via custom device states and actions.

# Known issues

  The wifi controller may throw intermittent timeout errors to the log, these are now properly trapped and the default timeout has been increased and made configurable
  Testing has been limited, so be prepared to find bugs
  
  Documentation via the wiki https://github.com/neilkplugins/Daikin-Wifi-indigo-plugin/wiki, that covers the customs states and actions and configuration options.
