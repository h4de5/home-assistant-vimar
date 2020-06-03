# Home-assistant VIMAR Hub

This is an integration of the VIMAR bus system into the home-assistant environment.

## Vimar requirements

Hardware:
[Vimar - 01945 - Web server By-me](https://www.vimar.com/en/int/catalog/product/index/code/01945)

Software:
[By-me Web Server Firmware](https://www.vimar.com/en/int/by-me-web-server-4014162.html)

## home-assistant requirements

See installation guides [Home-Assistant.io](http://home-assistant.io/)

### installation (linux)

1. create a the following directory within your home-assistant config folder:
   > `mkdir custom_components`
2. go there
   > `cd custom_components`
3. clone this repository
   > `git clone git@github.com:h4de5/home-assistant-vimar.git vimar_platform`

example configuration to put into `configuration.yaml`:

    vimar_platform:
      username: your-login-user
      password: your-login-password
      host: IP-OR-HOSTNAME
      schema: https
      port: 443
      certificate: path-to-vimar-ca-certificate.pem

`username` and `password` are those from the local vimar webserver reachable under `host`. `schema`, `port`, and `certificate` is optional - if left out, the integration will use normal http calls on port 80 to the given IP. The `certificate` can be just a writeable file-path. If there is no file there, the integration will download the current CA certificate from the local vimar webserver and save it there for sub sequent calls.

## limitations

The integration can currently list and control all lights, shades, fans and switches. climates and other devices are not yet implemented. Generally speaking: **THIS IS A BETA VERSION** Use at your own risk. So far I could only test it on a single installation, which is my own. If you want to try it out, and need help, please create a "Request Support" ticket.

## troubleshooting

enable more logging for vimar_platform:

    logger:
      default: warning
      logs:
        custom_components.vimar_platform: info
