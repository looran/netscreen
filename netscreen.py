#!/usr/bin/env python

import sys
import argparse
import subprocess

parser = argparse.ArgumentParser(description='netscreen client')
parser.add_argument('ip', help='netscreend server IP address')
parser.add_argument('port', help='netscreend server port')
parser.add_argument('-k', dest='kill', action='store_true', help='Kill running netscreen')
parser.add_argument('-v', dest='verbose', action='store_true', help='Print verbose messages')
args = parser.parse_args()

loglevel = 'verbose' if args.verbose else 'error'

CMD_FFMPEG = """ffmpeg -y -loglevel __LOGLEVEL__ -f x11grab -s $(xrandr |awk '$0 ~ "*" {print $1}' |head -n1) -r 25 -i :0.0 -vcodec h264 -tune zerolatency -preset ultrafast -pix_fmt yuv420p -vprofile main -x264opts keyint=25:min-keyint=25 -bufsize 500k -f mpegts tcp://__IP__:__PORT__"""

cmd = CMD_FFMPEG.replace("__LOGLEVEL__", loglevel).replace("__IP__", args.ip).replace("__PORT__", args.port)

if args.kill:
    print("[+] killing running netscreen")
    subprocess.call("pkill -f \"%s\"" % cmd, shell=True)
else:
    print("[+] running '%s'" % cmd)
    subprocess.call(cmd, shell=True)
