#!/usr/bin/python
import sys

from colorprint import colorize


added_to_path = False
if '/etc' not in sys.path:
    sys.path.insert(0, '/etc')
    added_to_path = True

try:
    import commanderconfig
except ImportError:
    print "Couldn't import config. Please create /etc/commanderconfig.py"
    sys.exit(1)

if added_to_path:
    del sys.path[0]


def get_systems(host_group):
    return commanderconfig.hostgroups[host_group]


def list_groups(color=True):
    groups = sorted(commanderconfig.hostgroups.keys())
    for g in groups:
        group = g
        if color:
            g = colorize(g, 'green')
        print "%s: %s" % (g, ",".join(get_systems(group)))
