#!/usr/bin/env python3

# 2019, Laurent Ghigonis <ooookiwi@gmail.com>

import os
import sys
import atexit
import signal
import logging
import asyncio
import argparse
from logging.config import dictConfig

import psutil
import libtmux
import daemonize
from quart import Quart, templating, redirect

PROGRAM_DESCRIPTION = """netscreen daemon, listens for a video stream and displays it. it also runs a small web interface."""

class Netscreend(object):
    TMUX_NAME = "netscd"
    PIDFILE = "/tmp/netscreend.pid"
    LOGFILE = "/tmp/netscreend.log"
    CMD_TAIL_LOG = "tail -f %s" % LOGFILE
    CMD_FFMPEG = "ffplay -framedrop -probesize 32 -sync ext -fs -fflags nobuffer __PROTO__://__IP__:__PORT__?listen=1"
    STATE_IDLE = "Idle"
    STATE_STREAM = "Stream"

    TEMPLATE_INDEX = """
<!DOCTYPE html>
<html>
<head>
    <style>
    pre {
        white-space: pre-wrap;
    }
    small {
        font-size: x-small;
    }
{% if web_black %}
    body, a {
        background-color: #101010;
        color: #cecece;
    }
    pre {
        background-color: #202020;
    }
{% else %}
    body, a {
        background-color: #efefef;
        color: #000000;
    }
    pre {
        background: lightgrey;
    }
{% endif %}
    </style>
    <title>Netscreend http://{{ ip }}:{{ web_port }}</title>
    <meta http-equiv="refresh" content="5">
</head>
<body>
    <h1>Netcreend http://{{ ip }}:{{ web_port }}</h1>

    <h2>Streaming status</h2>

    <p>
    {% if state == "Idle" %}
    No streaming in progress on port {{ port }}.
    {% else %}
    Receiving stream from {{ client_ip }}.
    {% endif %}
    </p>
    <form action="/restart">
        <input type="submit" value="restart server" />
    </form>

    <h2>How to stream</h2>
        <h3>From Linux</h3>
Use <a href="https://github.com/looran/netscreen/">netscreen</a>:
<pre>
$ netscreen {{ ip }} {{ port }}
$ netscreen {{ ip }} {{ port }} HDMI-1
$ netscreen {{ ip }} {{ port }} list
</pre>
or directly <a href="https://www.ffmpeg.org/">ffmpeg</a>:
<pre>
$ ffmpeg -y -f x11grab -s $(xrandr |awk '$0 ~ "*" {print $1}' |head -n1) \\
    -r 25 -i :0.0 -vcodec h264 -tune zerolatency -preset ultrafast \\
    -pix_fmt yuv420p -vprofile main -x264opts keyint=25:min-keyint=25 \\
    -bufsize 500k -f mpegts {{ proto }}://{{ ip }}:{{ port }}
</pre>
    <h3>From Windows</h3>
Use <a href="https://www.ffmpeg.org/">ffmpeg</a>:
<pre>
> ffmpeg -y -f gdigrab -framerate 30 -i desktop -r 25 ^
    -vf "scale=1920x1080" -vcodec h264 -tune zerolatency -preset ultrafast ^
    -pix_fmt yuv420p -vprofile main -x264opts keyint=25:min-keyint=25 ^
    -bufsize 500k -f mpegts {{ proto }}://{{ ip }}:{{ port }}
</pre>
<small>powered by <a href="https://github.com/looran/netscreen/">netscreend</a></small>
</body>
</html>
"""

    def __init__(self, proto, ip, port, web_port, web_black=False, verbose=False):
        self.state = self.STATE_IDLE
        self.proto = proto
        self.ip = ip
        self.port = port
        self.web_port = web_port
        self.web_black = web_black
        self.loglevel = logging.DEBUG if verbose else logging.INFO
        self.client_ip = None
        self.ffmpeg_cmd = self.CMD_FFMPEG.replace("__PROTO__", self.proto).replace("__IP__", self.ip).replace("__PORT__", "%s" % self.port)

    def _run(self):
        atexit.register(self.kill)

        dictConfig({ 'version': 1,
                'formatters': { 'ts': { 'class': 'logging.Formatter', 'format': '[%(asctime)s] %(message)s' } },
                'handlers': { 'file': { 'class': 'logging.FileHandler', 'filename': self.LOGFILE, 'formatter': 'ts', } },
                'loggers': {
                    'quart.app': {'handlers': ['file'], 'level': self.loglevel },
                    'quart.serving': {'handlers': ['file'], 'level': self.loglevel } } })
        self.log = logging.getLogger('quart.app')

        tmux_srv = libtmux.Server()
        tmux = tmux_srv.find_where({ "session_name": self.TMUX_NAME })
        if tmux:
            self.log.error("server already running in tmux session '%s'" % self.TMUX_NAME)
            sys.exit(1)

        self.tmux = tmux_srv.new_session(self.TMUX_NAME, window_name="log")
        # libtmux select_window() is broken, use find_where() instead. see https://github.com/tmux-python/libtmux/issues/161 (lgs 20191207)
        p = self.tmux.find_where({ "window_name": "log" }).select_pane(0)
        p.send_keys(self.CMD_TAIL_LOG)
        self.tmux.new_window(attach=False, window_name="ffmpeg")
        self.ffmpeg_restart()

        self.web = Quart(__name__)
        @self.web.route('/')
        async def web_root():
            return await templating.render_template_string(self.TEMPLATE_INDEX, proto=self.proto, ip=self.ip, port=self.port, web_port=self.web_port, web_black=self.web_black, state=self.state, client_ip=self.client_ip)
        @self.web.route('/restart')
        async def web_restart():
            self.ffmpeg_restart()
            return redirect('/')

        loop = asyncio.get_event_loop()
        task = loop.create_task(self.ffmpeg_watch())

        self.log.info("starting web server listening on %s:%d" % (self.ip, self.web_port))
        self.web.run(host=self.ip, port=self.web_port, loop=loop)

    def run(self, foreground):
        sys.stderr.write("logging to %s\n" % self.LOGFILE)
        sys.stderr.write("running in tmux session '%s'\n" % self.TMUX_NAME)
        sys.stderr.write("use -k to kill the server\n")
        daemon = daemonize.Daemonize(app="netscreend", pid=self.PIDFILE, action=self._run, foreground=foreground, verbose=True)
        daemon.start()

    def ffmpeg_restart(self):
        self.log.info("restarting ffmpeg")
        p = self.tmux.find_where({ "window_name": "ffmpeg" }).select_pane(0)
        p.send_keys('C-c', enter=False, suppress_history=False)
        p.send_keys(self.ffmpeg_cmd)

    async def ffmpeg_watch(self):
        """ Since ffplay does not correctly close and restart after a client has finished streaming, we need to do it manually here.
            Additionnaly, we are logging and changing our internal state """
        while True:
            connections = [ c for c in psutil.net_connections(kind=self.proto) if (c.status == 'ESTABLISHED' and type(c.raddr) is psutil._common.addr and c.laddr.port == self.port) ]
            self.log.debug("%s - connections: %d" % (self.state, len(connections)))
            if self.state == self.STATE_STREAM and len(connections) == 0:
                self.log.info("client %s stopped stream" % self.client_ip)
                self.ffmpeg_restart()
                self.state = self.STATE_IDLE
            elif self.state == self.STATE_IDLE and len(connections) > 0:
                self.state = self.STATE_STREAM
                self.client_ip = connections[0].laddr.ip
                self.log.info("client %s started stream" % self.client_ip)
            await asyncio.sleep(1)

    @classmethod
    def kill(self):
        tmux_srv = libtmux.Server()
        tmux = tmux_srv.find_where({ "session_name": self.TMUX_NAME })
        if tmux:
            print("killing tmux session '%s'" % self.TMUX_NAME)
            tmux.kill_session()
        else:
            print("server not running, no tmux session '%s'" % self.TMUX_NAME)
        if os.path.isfile(self.PIDFILE):
            with open(self.PIDFILE) as f: 
                pid = int(f.read())
                print("killing server process %d" % pid)
                os.kill(pid, signal.SIGTERM)
        else:
            print("server not running, no server pidfile found (%s)" % self.PIDFILE)

parser = argparse.ArgumentParser(description=PROGRAM_DESCRIPTION, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('listen_ip', help='Listen IP address')
parser.add_argument('listen_port', type=int, help='Listen port for ffmpeg')
parser.add_argument('-f', dest='foreground', action='store_true', help='Run in foreground for debugging')
parser.add_argument('-k', dest='kill', action='store_true', help='Kill running server')
parser.add_argument('-v', dest='verbose', action='store_true', help='Print verbose messages')
parser.add_argument('-w', dest='web_port', type=int, default=8080, help='Listen port for web interface')
parser.add_argument('-B', dest='web_black', action='store_true', help='Use black background in web interface')
args = parser.parse_args()

if args.kill:
    Netscreend.kill()
else:
    nsd = Netscreend("tcp", args.listen_ip, args.listen_port, args.web_port, web_black=args.web_black, verbose=args.verbose)
    nsd.run(args.foreground)
