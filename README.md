# netscreen - stream your screen over local network

## Example usage

The following command on the server 192.168.1.154 starts a daemon waiting for incoming video stream to display :

```
server$ netscreend 192.168.1.154 3868
```

The following command on the client sends a video stream of the current screen to the server 192.168.1.154 :
```
client$ netscreen 192.168.1.154 3868
```

A web interface is also started on the server (default port 8080) with server status and instructions on how to stream from clients:

![netscreend web server](/demo/netscreend_web.png?raw=true "netscreend web server")

# Client side

```
$ netscreen -h
usage: netscreen [-h] [-k] [-c] [-v] ip port [source]

netscreen client, captures entire screen or single window and stream it
over the network to a netscreend instance.

netscreen <ip> <port>          : Stream the entire primary monitor
netscreen <ip> <port> HDMI-1   : Stream the entire HDMI-1 monitor
netscreen <ip> <port> list     : List active monitors
netscreen <ip> <port> select   : Select inractively a window to stream
netscreen <ip> <port> 93273232 : Stream window ID 932732
netscreen <ip> <port> list-win : List all windows

positional arguments:
  ip          netscreend server IP address
  port        netscreend server port
  source      monitor name or "list", X window ID or "select" or "list-win"

optional arguments:
  -h, --help  show this help message and exit
  -k          Kill running netscreen
  -c          Hide mouse cursor
  -v          Print verbose messages
```

## Install

```
sudo make install-client
```

## Dependencies

The following software must be installed:
* python3, language in which the client is written
* ffmpeg, video software used for screen streaming and whole screen capture
* gstreamer, only used for capturing a single window
* python xlib, library for display configuration

You can install all the dependecies on Ubuntu with the following commands:
```
apt install python3 ffmpeg gstreamer1.0-plugins-good
pip install python-xlib python-libxdo
```

# Server side

```
$ netscreend -h
usage: netscreend [-h] [-f] [-k] [-v] [-w WEB_PORT] [-B] listen_ip listen_port

netscreen daemon, listens for a video stream and displays it. it also runs a
small web interface.

positional arguments:
  listen_ip    Listen IP address
  listen_port  Listen port for ffmpeg

optional arguments:
  -h, --help   show this help message and exit
  -f           Run in foreground for debugging (default: False)
  -k           Kill running server (default: False)
  -v           Print verbose messages (default: False)
  -w WEB_PORT  Listen port for web interface (default: 8080)
  -B           Use black background in web interface (default: False)
```

## Install

```
sudo make install-server
```

## Dependencies

The following software must be installed:
* python3, language in which the server is written
* ffmpeg, video software used for screen streaming
* python Quart, a web framework (asyncio equivalent of flask)
* python libtmux, a tmux scripting library
* python psutil, a library for retrieving information on running processes and system utilization
* python daemonize, library for writing system daemons

You can install all the dependecies on Ubuntu with the following commands:
```
apt install python3 ffmpeg
pip3 install Quart libtmux psutil daemonize
```
