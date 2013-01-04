#!/usr/bin/python
import sys

from colorprint import colorize


added_to_path = False
if '/etc' not in sys.path:
    sys.path.insert(0, '/etc')
    added_to_path = True

try:
    from commanderconfig import hostgroups
except ImportError:
    hostgroups = {}

if added_to_path:
    del sys.path[0]


def get_systems(host_group):
    return hostgroups.get(host_group, [])


def list_groups(color=True):
    groups = sorted(hostgroups.keys())
    for g in groups:
        group = g
        if color:
            g = colorize(g, 'green')
        print "%s: %s" % (g, ",".join(get_systems(group)))
