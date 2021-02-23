#!/usr/bin/env python3

import os
import sys
import argparse
import subprocess

from Xlib import X, display
from Xlib.ext import randr
from xdo import Xdo

PROGRAM_DESCRIPTION = """netscreen client, captures entire screen or single window and stream it
over the network to a netscreend instance.

netscreen <ip> <port>          : Stream the entire primary monitor
netscreen <ip> <port> HDMI-1   : Stream the entire HDMI-1 monitor
netscreen <ip> <port> list-mon : List active monitors
netscreen <ip> <port> select   : Select interactively a window to stream
netscreen <ip> <port> 93273232 : Stream window ID 932732
netscreen <ip> <port> list-win : List all windows
"""

FRAMERATE = 25
FFMPEG_OUTPUT = """-vcodec h264 -tune zerolatency -preset ultrafast -pix_fmt yuv420p -vprofile main -x264opts keyint=25:min-keyint=25 -bufsize 500k -f mpegts tcp://{ip}:{port}"""
CMD_CAPTURE_SCREEN = """ffmpeg -y -loglevel {loglevel} -f x11grab{capture_flags} -s {size_width}x{size_height} -r {framerate} -i {source} -vf 'pad=ceil(iw/2)*2:ceil(ih/2)*2'""" + " " + FFMPEG_OUTPUT
CMD_CAPTURE_WINDOW = """gst-launch-1.0 -q ximagesrc xid={source} use-damage=0{capture_flags} ! video/x-raw,framerate={framerate}/1 ! videoconvert ! filesink location=/dev/stdout |ffmpeg -y -loglevel {loglevel} -f rawvideo -pix_fmt bgra -s:v {size_width}:{size_height} -r {framerate} -i - -vf 'pad=ceil(iw/2)*2:ceil(ih/2)*2'""" + " " + FFMPEG_OUTPUT

def list_monitors(monitors_list):
    s = "active monitors list:\n"
    s += '\n'.join([ '    %s: %dx%d+%d+%d%s' % (name, m['width'], m['height'], m['x'], m['y'], " primary" if m['primary'] else "") for name, m in monitors_list.items() ])
    s += "\ninactive monitors list:\n"
    s += '    ' + ' '.join(monitors_list_inactive)
    return s

def list_windows(windows_list):
    s = "windows list:\n"
    for xid in windows_list:
        s += "%d:\t%s\n" % (xid, xdo.get_window_name(xid))
    return s

parser = argparse.ArgumentParser(description=PROGRAM_DESCRIPTION, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('ip', help='netscreend server IP address')
parser.add_argument('port', help='netscreend server port')
parser.add_argument('source', nargs='?', help='monitor name, list-mon, X window ID, list-win, select, focus')
parser.add_argument('-k', dest='kill', action='store_true', help='Kill running netscreen')
parser.add_argument('-c', dest='hide_cursor', action='store_true', help='Hide mouse cursor')
parser.add_argument('-v', dest='verbose', action='store_true', help='Print verbose messages')
args = parser.parse_args()

if args.kill:
    print("[+] killing running netscreen to %s:%s" % (args.ip, args.port))
    cmd = "ffmpeg .*" + FFMPEG_OUTPUT.format(ip=args.ip, port=args.port)
    subprocess.call("pkill -f \"%s\"" % cmd, shell=True)
    sys.exit(0)

loglevel = 'verbose' if args.verbose else 'error'
monitors_list = dict()
monitors_list_inactive = list()
primary_monitor = None

if 'DISPLAY' not in os.environ:
    print("error: DISPLAY variable not set")
    sys.exit(1)

# list monitors and get active monitor
display_num = os.environ['DISPLAY']
d = display.Display(display_num)
root_window = d.screen().root
primary_output_id = randr.get_output_primary(root_window).output
for output_id in randr.get_screen_resources(root_window).outputs:
    o = randr.get_output_info(root_window, output_id, 0)
    if o.crtc != 0:
        c = randr.get_crtc_info(root_window, o.crtc, 0)
        monitors_list[o.name] = { 'width': c.width, 'height': c.height, 'x': c.x, 'y': c.y, 'primary': False }
        if output_id == primary_output_id:
            monitors_list[o.name]['primary'] = True
            primary_monitor = o.name
    else:
        monitors_list_inactive.append(o.name)

# list windows
xdo = Xdo()
windows_list = xdo.search_windows(winname = b'.*')
windows_list.sort()

# getting informations about monitor / window to capture
monitor = None
window = None
if args.source:
    try:
        source_int = int(args.source)
    except:
        source_int = None
    if args.source == 'list-mon':
        print(list_monitors(monitors_list))
        sys.exit(0)
    elif args.source == 'list-win':
        print(list_windows(windows_list))
        sys.exit(0)
    elif args.source == 'select':
        window = xdo.select_window_with_click()
    elif args.source == 'focus':
        window = xdo.get_focused_window()
    elif args.source in monitors_list:
        monitor = monitors_list[args.source]
    elif source_int is None:
        print("error: monitor '%s' not found !" % args.source)
        print(list_monitors(monitors_list))
        sys.exit(1)
    elif source_int in windows_list:
        window = source_int
    else:
        print("error: window '%s' not found !" % args.source)
        print(list_windows(windows_list))
        sys.exit(2)
else:
    if primary_monitor is None:
        print("error: primary monitor not found !")
        print(list_monitors(monitors_list))
        sys.exit(3)
    monitor = monitors_list[primary_monitor]

# building ffmpeg / gstreamer streaming command
capture_flags = ""
if monitor:
    cmd = CMD_CAPTURE_SCREEN
    size_width = monitor['width']
    size_height = monitor['height']
    if args.hide_cursor:
        capture_flags = " -draw_mouse 0"
    source = "%s+%d,%d" % (display_num, monitor['x'], monitor['y'])
else:
    cmd = CMD_CAPTURE_WINDOW
    size = xdo.get_window_size(window)
    size_width = size.width
    size_height = size.height
    if args.hide_cursor:
        capture_flags = " show-pointer=0"
    source = window
cmd = cmd.format(framerate=FRAMERATE, size_width=size_width, size_height=size_height,
        loglevel=loglevel, ip=args.ip, port=args.port, source=source, capture_flags=capture_flags)

# execute ffmpeg / gstreamer command
print("[+] running '%s'" % cmd)
subprocess.call(cmd, shell=True)

