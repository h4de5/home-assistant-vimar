[![HACS Validate](https://github.com/h4de5/home-assistant-vimar/actions/workflows/validate.yml/badge.svg)](https://github.com/h4de5/home-assistant-vimar/actions/workflows/validate.yml)
[![hassfest Validate](https://github.com/h4de5/home-assistant-vimar/actions/workflows/hassfest.yml/badge.svg)](https://github.com/h4de5/home-assistant-vimar/actions/workflows/hassfest.yml)

# VIMAR By-Me / By-Web Hub

This is a home-assistant integration for the VIMAR By-me / By-web bus system.

<img title="Lights, climates, covers" src="https://user-images.githubusercontent.com/6115324/84840393-b091e100-b03f-11ea-84b1-c77cbeb83fb8.png" width="900">
<img title="Energy guards" src="https://user-images.githubusercontent.com/51525150/89122026-3a005400-d4c4-11ea-98cd-c4b340cfb4c2.jpg" width="600">
<img title="Audio player" src="https://user-images.githubusercontent.com/51525150/89122129-36b99800-d4c5-11ea-8089-18c2dcab0938.jpg" width="300">

## WARNING - BEFORE YOU UPGRADE

If you upgrade from a version earlier of May 2021 - please be aware:
The integration name has changed from `vimar_platform` to `vimar` - this requires changes in your configuration and it may effect your current dashboards as well.
In order to keep all dashboard layouts, automations and groups intact, you may want to follow this upgrade guide:

- DO NOT update the files in your `custom_components` directory right away
- stop home-assistant
- find and backup the file: `.storage/core.entity_registry` within your home-assistant config directory
- open that file in a proper text-editor
- replace all `vimar_platform` occurrences to `vimar` (only replace with that exact notation)
- save that file in it's original place
- open your configuration.yaml and replace `vimar_platform:` with `vimar:` as well
- remove the directory `custom_components/vimar_platform/` and checkout the source under `custom_components/vimar/`
- start up home-assistant again

## Vimar requirements

Hardware:
- [Vimar - 01945 - Web server By-me](https://www.vimar.com/en/int/catalog/product/index/code/R01945)
or
- [Vimar - 01946 - Web server Light By-me](https://www.vimar.com/en/int/catalog/product/index/code/R01946)

Software:
- [By-me Web Server Firmware](https://www.vimar.com/en/int/by-me-web-server-4014162.html)
    
    I have only tested it with the firmware version v2.5 to v2.8 - if you plan to update the firmware of your web server, please make sure you have a full backup of your vimar database (complete db and exported xml file) ready.

## home-assistant requirements

See installation guides [Home-Assistant.io](http://home-assistant.io/)

### installation

- Use [HACS](https://hacs.xyz/) !
- Otherwise, download the zip from the latest release and copy `vimar` folder inside your custom_components folder.

You will end up with something like this:

- on docker/hassio: `/config/custom_components/vimar/`

- on hassbian/virtualenv: `/home/homeassistant/.homeassistant/custom_components/vimar/`

### configuration

example configuration to put into `configuration.yaml`:

#### minimal

this will try to connect to your webserver using https, will save the webservers CA certificate in your home-assistants config folder

    vimar:
      username: your-login-user
      password: your-login-password
      host: IP-OR-HOSTNAME

#### existing CA certificate

You can manualy download the CA certificate from the webserver (see settings > network) and place it in the home-assistants directory. If the file does not exist on the given filename, the integration will try to download and place it there. (Advanced usage: If you have placed your webserver behind a reverse proxy you may need to place whatever CA certificate you used to generate your proxy servers certificate.)

    vimar:
      username: your-login-user
      password: your-login-password
      host: IP-OR-HOSTNAME
      certificate: rootCA.VIMAR.crt

#### problems with ssl connection

if the above settings do not work for you and you keep getting errors like

> SSLError("bad handshake: Error([('SSL routines', 'tls_process_server_certificate', 'certificate verify failed')])")

you can try to force ignoring any ssl errors during communicating to the webserver by keeping the path to the certificate empty.

    vimar:
      username: your-login-user
      password: your-login-password
      host: IP-OR-HOSTNAME
      certificate:

#### trying to connect via http

it possible to connect to the webserver via http as well. While it may be necessary for some setups, a direct connection to the webserver via http will not be possible, as the login process will always forward requests to https.

    vimar:
      username: your-login-user
      password: your-login-password
      host: IP-OR-HOSTNAME
      schema: http
      port: 80

#### existing CA certificate

You can manualy download the CA certificate from the webserver (see settings > network) and place it in the home-assistants directory. If the file does not exist on the given filename, the integration will try to download and place it there. (Advanced usage: If you have placed your webserver behind a reverse proxy you may need to place whatever CA certificate you used to generate your proxy servers certificate.)

    vimar:
      username: your-login-user
      password: your-login-password
      host: IP-OR-HOSTNAME
      certificate: rootCA.VIMAR.crt

#### ignore platforms

You can ignore certain platforms that should not be added to home-assistant. Just list those platforms you want to ignore in the configuration:

    vimar:
      username: your-login-user
      password: your-login-password
      host: IP-OR-HOSTNAME
      ignore:
        - light
        - switch
        - cover
        - climate
        - sensor
        - media_player
        - scene

#### entities customization

You can override entities attribute:
filter_vimar_name is the filter for match entity.
In this example, i use object_name_as_vimar for all entities, i prefer a original name without custom formatter.
After, i change a entity 'Cancello' as switches, default is readed as lights.
you can override device_type, device_class, icon.

    vimar:
      username: your-login-user
      password: your-login-password
      host: IP-OR-HOSTNAME
      device_override:
        - filter_vimar_name: '*'
          object_name_as_vimar: true
        - filter_vimar_name: Cancello
          device_type: switches
          #device_class: garage
          #icon: ''
          #icon:
    	  # - mdi:toggle-switch
    	  # - mdi:toggle-switch-off
          icon: mdi:garage-open,mdi:garage

`username` and `password` are those from the local vimar webserver reachable under `host`. `schema`, `port`, and `certificate` is optional - if left out, the integration will use https calls on port 443 to the given host. The `certificate` can be a writeable filename. If there is no file found, the integration will download the current CA certificate from the local vimar webserver and save it under that given file name for sub sequent calls. (e.g. `certificate: rootCA.VIMAR.crt`). `timeout` will allow to tweak the timeout for connection and transmition of data to the webserver (default 6 seconds). if only some platforms should be added to home-assistant you list them in the `ignore` area.

The hostname or the IP has to match the settings screen on the vimar web server:

![image](https://user-images.githubusercontent.com/6115324/83895464-04a0e980-a753-11ea-8c6c-a55dffba5b83.png)

## limitations

The integration can currently list and control all lights, rgb dimmers, audio devices, energie guards, covers/shades, fans, switches, climates and scenes. Other devices are not yet implemented. The python module behind the communication mimics the http calls to the webserver that are usually made through the By-me Webinterface. Generally speaking: **THIS IS A BETA VERSION** Use at your own risk. So far I could only test it on a single installation, which is my own. If you want to try it out, and need help, please create a "Request Support" ticket.

## Command line usage

You can use the vimarlink library in the command line like this:

```bash
# install python3.9
# install some requirements
python3.9 -m pip install async_timeout homeassistant
# see examples
cd examples
# copy credentials.cfg.dist to credentials.cfg and add your credentials
# run the example script - print help
python3.9 example.py -h
# run the example script - list all lights
python3.9 example.py --platform lights
# run the example script - change a specific cover to open
python3.9 example.py --platform covers --device 721 "up/down"=0
```

## contribution

If you want to help see some examples of how to read out data for new devies in [contribution](CONTRIBUTING.md).

## troubleshooting

**When you install, update or uninstall the integration, you need to restart Home Assistant.**

Enable more logging for vimar - add to your `configuration.yaml`:

    logger:
      default: warning
      logs:
        custom_components.vimar: debug

have a look into your home-assistant log files - usually named `home-assitant.log` in the directory where your `configuration.yaml` is located.

      WARNING (MainThread) [homeassistant.loader] You are using a custom integration for vimar which has not been tested by Home Assistant. This component might cause stability problems, be sure to disable it if you experience issues with Home Assistant.

> the Vimar platform code and the configuration was found. The warning is been shown for all custom components. This is GOOD!

      ERROR (MainThread) [custom_components.vimar] Could not connect to Vimar Webserver home-assistant

> Vimar By-me Webserver was not found under the given address.

      ERROR (MainThread) [homeassistant.setup] Setup failed for vimar: Integration not found

> You have put the content of this repository into the wrong directory - see above for an example.

      ERROR (SyncWorker_4) [custom_components.vimar.vimarlink] Other error occurred: SSLError(MaxRetryError('HTTPSConnectionPool(host='***', port=443): Max retries exceeded with url: /vimarbyweb/modules/system/user_login.php?sessionid=&username=***&password=***&remember=0&op=login (Caused by SSLError(SSLError("bad handshake: Error([('SSL routines', 'tls_process_server_certificate', 'certificate verify failed')])")))'))

> There seems to a problem with the SSL connection. Try if it works with the config setting `certificate: ` (empty certificate option)

      ERROR (SyncWorker_5) [custom_components.vimar.vimarlink] Error parsing XML: TypeError("a bytes-like object is required, not 'bool'")

> This message paired with a web server that needs manual restarting: You may have too many devices connected to the installation. I am currently working on a fix. Latest version will simple limit it to 300 devices (and status attributes of those devices)

      Some entities are listed as "not available" with a red exclamation mark in the entity list.

> See the explanation and the fix in: https://github.com/h4de5/home-assistant-vimar/issues/15#issuecomment-665635305

## thanks

thanks to everybody who was helping me developing and testing this integration. special thanks to user @felisida for his endless patience ;)
