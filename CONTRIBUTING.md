# How to contribute

## New Vimar Devices

I can only support and test those devices I have currently in my installation.
If you want to use new devices I need to know which attributes this device have and what they mean.
See below a short video of how I currently check for those attributes:

### Read out attributes from Home-Assistant Log

Most of the devices are forwarded to home-assistant already - therefore the first place to look at the data should be the home-assistant log file. This is usually located in the config directory having the name `home-assistant.log`. To increase the verbosity for the Vimar extension add this to your `configuration.yaml`:

```
logger:
  default: warning
  logs:
    custom_components.vimar: debug
```

this will output lots of additional information of how vimar devices are handled by the integration. What we are looking is something like this:

```
WARNING (SyncWorker_10) [custom_components.vimar.vimarlink] Unknown object returned from web server: CH_HVAC_RiscaldamentoNoZonaNeutra / NAME OF CLIMATE
DEBUG (SyncWorker_10) [custom_components.vimar.vimarlink] Unknown object has states: {'allarme_massetto': {'status_id': '2129', 'status_value': '0', 'status_range': 'min=0|max=1'}, 'regolazione': {'status_id': '2131', 'status_value': '2', 'status_range': ''}, 'modalita_fancoil': {'status_id': '2135', 'status_value': '0', 'status_range': 'min=0|max=1'}, 'velocita_fancoil': {'status_id': '2137', 'status_value': '0', 'status_range': 'min=0|max=100'}, 'funzionamento': {'status_id': '2139', 'status_value': '6', 'status_range': ''}, 'setpoint': {'status_id': '2146', 'status_value': '21.00', 'status_range': 'min=-273|max=670760'}, 'temporizzazione': {'status_id': '2152', 'status_value': '1', 'status_range': 'min=0|max=65535'}, 'temperatura_misurata': {'status_id': '2160', 'status_value': '24.40', 'status_range': 'min=-273|max=670760'}, 'stato_boost on/off': {'status_id': '2163', 'status_value': '0', 'status_range': 'min=0|max=1'}, 'stato_principale_condizionamento on/off': {'status_id': '2164', 'status_value': '0', 'status_range': 'min=0|max=1'}, 'stato_principale_riscaldamento on/off': {'status_id': '2165', 'status_value': '0', 'status_range': 'min=0|max=1'}, 'uscita4': {'status_id': '2944', 'status_value': 'non_utilizzata', 'status_range': 'principale_riscaldamento=0|boost_riscaldamento=0|principale_condizionamento=0|boost_condizionamento=0'}, 'uscita3': {'status_id': '2945', 'status_value': 'non_utilizzata', 'status_range': 'principale_riscaldamento=0|boost_riscaldamento=0|principale_condizionamento=0|boost_condizionamento=0'}, 'uscita2': {'status_id': '2946', 'status_value': 'non_utilizzata', 'status_range': 'principale_riscaldamento=0|boost_riscaldamento=0|principale_condizionamento=0|boost_condizionamento=0'}, 'uscita1': {'status_id': '2947', 'status_value': 'CH_Uscita_ValvolaOnOff', 'status_range': 'principale_riscaldamento=1|boost_riscaldamento=0|principale_condizionamento=0|boost_condizionamento=0'}, 'forzatura off': {'status_id': '3282', 'status_value': '0', 'status_range': ''}}
```

it says there was an unknown object returned from the vimar web server and it shows all available attributes and its current values. This would be a great starting point for me to add it to the integration. Next you can check for yourself and try to give an explanation and possible values for each of the attributes. Also you can try to change the state of an attribute through the Vimar Webserver, restart Home-assistant and see which how the `status_value` has adapted.

Please note that is log entry only shows up during home-assistant start up.

### Read out attributes from Vimar Webserver

The Webserver will update the status of all devices currently shown on screen regulary.
We are trying to monitor that communication to see how that device is used internally.

![2020-06-19_215047_x_76rR](https://user-images.githubusercontent.com/6115324/85175601-15d01700-b278-11ea-8352-0827030e139b.gif)

1. open up the vimar webserver
2. press F12 / Ctrl+Shift+i to open the Webdeveloper tools
3. switch to the Network tab and make sure the record button (red dot) is active
4. open a page on the webserver where (preferable only) that device is shown
5. clear the network tab and wait for the next status update from the webserver
6. select one of the requests and switch to the "preview" or the "response" tab
7. check if the given response includes "familiar" values for the device you try to add
   > e.g. the climate should include the current temperature. It's possible that additional status updates are sent along regulary from the webserver. If unsure, check and compare several requests
8. copy that response text and insert it into a new ticket
9. if possible try to explain the values as well. This works best if you switch any state of the device and check how the attributes adapt.
   > e.g. `temperatura` is the current temperature, `stagione` is 1 for cooling and 0 for heating etc.)

> this was done in the chrome browser - name of tabs and shortcuts may be different in other browsers but usually all modern browsers should support this

### Set attributes

The way to find out how attributes are set, is similar. The main difference is, that we do not look for the response but the request payload to see what we send _to_ the webserver, instead of what we get _from_ the webserver.

![2020-06-19_222915_x_xUSh](https://user-images.githubusercontent.com/6115324/85178252-5337a300-b27e-11ea-9daa-712025add5df.gif)

1. open up the vimar webserver
2. press F12 / Ctrl+Shift+i to open the Webdeveloper tools
3. switch to the Network tab and make sure the record button (red dot) is active
4. Filter the network requests to only include XHR requests - so you don't get flooded with image or javascript requests
5. open a page on the webserver where (preferable only) that device is shown
6. clear the network tab
7. click on the device and change the status/attribute
   > e.g. change the dimming value of the light
8. the network tab will show many requests that do look almost identical
   > in addition to the status updates (see above) that we still get regulary, every status change trigger another request
9. instead of switching to the response tab as above, stay in the `Headers` or the `Request` tab to see what the browser sends to the webserver
   > such a change request should include the following:
   1. `<operation>SETVALUE</operation>` to indicate that it is a actual change and not a status update request
   2. `<idobject>712</idobject>` a status identifier that define which attribute should be changed
   3. `<payload>36</payload>` and the payload or the value to which we change that attribute (e.g. dimm the light to 36%)
      > it is possible that a single click in the webserver, changes multible attributes at once. In this case we need all the change details
10. again copy that text into the ticket and try to explain what the values mean

> this was done in the chrome browser - name of tabs and shortcuts may be different in other browsers but usually all modern browsers should support this

## Home Assistant / HACS Support

Anything you can ;)

Currently looking for someone to explain/implement `config_flow.py` or `reproduce_state.py` and to help me get the integration into [HACS](https://hacs.xyz/).
