netscreen - stream your screen over local network

= Example usage =

The following command on the server 192.168.0.1 starts a daemon waiting for incoming video stream to display :

```
server$ ./netscreend 192.168.0.1 3868
```

The following command on the client sends a video stream of the current screen to the server 192.168.0.1 :
```
client$ ./netscreen 192.168.0.1 3868
```

A web interface is also started on the server (default port 8080) with server status and instructions on how to stream from clients.

= Client side =

```
client$ ./netscreen -h
usage: netscreen [-h] [-v VERBOSE] ip port

netscreen client

positional arguments:
  ip          netscreend server IP address
  port        netscreend server port

optional arguments:
  -h, --help  show this help message and exit
  -v VERBOSE  Print verbose messages
```

== Install ==

```
sudo make install-client
```

== Dependencies ==

The following software must be installed:
* python, language in which the client is written
* ffmpeg, video software used for screen streaming

You can install all the dependecies on Ubuntu with the following commands:
```
apt install python ffmpeg
```

= Server side =

```
server$ ./netscreend -h
usage: netscreend [-h] [-f] [-k] [-v] [-w WEB_PORT] listen_ip listen_port

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
```

== Install ==

```
sudo make install-server
```

== Dependencies ==

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

