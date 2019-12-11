#!/usr/bin/env python

import sys
import argparse
import subprocess

parser = argparse.ArgumentParser(description='netscreen client')
parser.add_argument('ip', help='netscreend server IP address')
parser.add_argument('port', help='netscreend server port')
parser.add_argument('-v', dest='verbose', default=False,
                    help='Print verbose messages')
args = parser.parse_args()

cmd = """ffmpeg -y -f x11grab -s $(xrandr |awk '$0 ~ "*" {print $1}') -r 25 -i :0.0 -vcodec h264 -tune zerolatency -preset ultrafast -pix_fmt yuv420p -vprofile main -x264opts keyint=25:min-keyint=25 -bufsize 500k -f mpegts tcp://%s:%d""" % (args.ip, int(args.port))

subprocess.call(cmd, shell=True)
