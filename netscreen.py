#!/usr/bin/env python

import os
import sys
import argparse
import subprocess

from Xlib import X, display
from Xlib.ext import randr

CMD_FFMPEG = """ffmpeg -y -loglevel __LOGLEVEL__ -f x11grab -s __SIZE__ -r 25 -i __DISPLAY__ -vcodec h264 -tune zerolatency -preset ultrafast -pix_fmt yuv420p -vprofile main -x264opts keyint=25:min-keyint=25 -bufsize 500k -f mpegts tcp://__IP__:__PORT__"""

def list_monitors(monitors):
    s = "active monitors list:\n"
    s += '\n'.join([ '    %s: %dx%d+%d+%d%s' % (name, m['width'], m['height'], m['x'], m['y'], " primary" if m['primary'] else "") for name, m in monitors.items() ])
    s += "\ninactive monitors list:\n"
    s += '    ' + ' '.join(monitors_inactive)
    return s

parser = argparse.ArgumentParser(description='netscreen client')
parser.add_argument('ip', help='netscreend server IP address')
parser.add_argument('port', help='netscreend server port')
parser.add_argument('monitor', nargs='?', help='monitor output name, or "list"')
parser.add_argument('-k', dest='kill', action='store_true', help='Kill running netscreen')
parser.add_argument('-v', dest='verbose', action='store_true', help='Print verbose messages')
args = parser.parse_args()

loglevel = 'verbose' if args.verbose else 'error'

cmd = CMD_FFMPEG.replace("__LOGLEVEL__", loglevel).replace("__IP__", args.ip).replace("__PORT__", args.port)

monitors = dict()
monitors_inactive = list()
primary_monitor = None

if 'DISPLAY' not in os.environ:
    print("error: DISPLAY variable not set")
    sys.exit(0)
display_num = os.environ['DISPLAY']
d = display.Display(display_num)
s = d.screen()
#w = s.root.create_window(0, 0, 1, 1, 1, s.root_depth)
w = s.root
primary_output_id = randr.get_output_primary(w).output
for output_id in randr.get_screen_resources(w).outputs:
    o = randr.get_output_info(w, output_id, 0)
    if o.crtc != 0:
        c = randr.get_crtc_info(w, o.crtc, 0)
        monitors[o.name] = { 'width': c.width, 'height': c.height, 'x': c.x, 'y': c.y, 'primary': False }
        if output_id == primary_output_id:
            monitors[o.name]['primary'] = True
            primary_monitor = o.name
    else:
        monitors_inactive.append(o.name)

if args.monitor:
    if args.monitor == 'list':
        print(list_monitors(monitors))
        sys.exit(0)
    if args.monitor not in monitors:
        print("error: monitor '%s' not found !" % args.monitor)
        print(list_monitors(monitors))
        sys.exit(0)
    monitor = monitors[args.monitor]
else:
    if primary_monitor is None:
        print("error: primary monitor not found !")
        print(list_monitors(monitors))
        sys.exit(0)
    monitor = monitors[primary_monitor]
size = "%dx%d" % (monitor['width'], monitor['height'])
display_spec = "%s+%d,%d" % (display_num, monitor['x'], monitor['y'])
cmd = cmd.replace("__SIZE__", size).replace("__DISPLAY__", display_spec)

if args.kill:
    print("[+] killing running netscreen")
    subprocess.call("pkill -f \"%s\"" % cmd, shell=True)
else:
    print("[+] running '%s'" % cmd)
    subprocess.call(cmd, shell=True)

