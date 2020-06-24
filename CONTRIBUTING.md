# How to contribute


## New Vimar Devices

I can only support and test those devices I have currently in my installation. 
If you want to use new devices I need to know which attributes this device have and what they mean.
See below a short video of how I currently check for those attributes:

### Read out attributes

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
    1.    `<operation>SETVALUE</operation>` to indicate that it is a actual change and not a status update request
    2.    `<idobject>712</idobject>` a status identifier that define which attribute should be changed
    3.    `<payload>36</payload>` and the payload or the value to which we change that attribute (e.g. dimm the light to 36%)
    > it is possible that a single click in the webserver, changes multible attributes at once. In this case we need all the change details
10. again copy that text into the ticket and try to explain what the values mean
        
> this was done in the chrome browser - name of tabs and shortcuts may be different in other browsers but usually all modern browsers should support this

and wait for the next status update from the webserver
11. select one of the requests and switch to the "preview" or the "response" tab
12. check if the given response includes "familiar" values for the device you try to add 


## Home Assistant / HACS Support

Anything you can ;)

Currently looking for someone to explain/implement `config_flow.py` or `reproduce_state.py` and to help me get the integration into [HACS](https://hacs.xyz/).
