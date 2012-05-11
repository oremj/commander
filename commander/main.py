#!/usr/bin/python
import imp
import sys
from commander.deploy import commands
from commander.settings import config
from optparse import OptionParser


def _escape_split(sep, argstr):
    """
Allows for escaping of the separator: e.g. task:arg='foo\, bar'

It should be noted that the way bash et. al. do command line parsing, those
single quotes are required.
"""
    escaped_sep = r'\%s' % sep

    if escaped_sep not in argstr:
        return argstr.split(sep)

    before, _, after = argstr.partition(escaped_sep)
    startlist = before.split(sep)  # a regular split is fine here
    unfinished = startlist[-1]
    startlist = startlist[:-1]

    # recurse because there may be more escaped separators
    endlist = _escape_split(sep, after)

    # finish building the escaped value. we use endlist[0] becaue the first
    # part of the string sent in recursion is the rest of the escaped value.
    unfinished += sep + endlist[0]

    return startlist + [unfinished] + endlist[1:]  # put together all the parts


def parse_arguments(arguments):
    cmds = []
    for cmd in arguments:
        args = []
        kwargs = {}
        if ':' in cmd:
            cmd, argstr = cmd.split(':', 1)
            for pair in _escape_split(',', argstr):
                k, _, v = pair.partition('=')
                if _:
                    kwargs[k] = v
                else:
                    args.append(k)
        cmds.append((cmd, args, kwargs))
    return cmds


def list_commands(docstring):
    if docstring:
        trailer = "\n" if not docstring.endswith("\n") else ""
        print(docstring + trailer)
    print("Available commands:\n")
    # Want separator between name, description to be straight col
    max_len = reduce(lambda a, b: max(a, len(b)), commands.keys(), 0)
    sep = ' '
    trail = '...'
    for name in sorted(commands.keys()):
        output = None
        # Print first line of docstring
        func = commands[name]
        if func.__doc__:
            lines = filter(None, func.__doc__.splitlines())
            first_line = lines[0].strip()
            # Truncate it if it's longer than N chars
            size = 75 - (max_len + len(sep) + len(trail))
            if len(first_line) > size:
                first_line = first_line[:size] + trail
            output = name.ljust(max_len) + sep + first_line
        # Or nothing (so just the name)
        else:
            output = name
        print("%s%s" % (' ' * 4, output))
    sys.exit(0)


def import_cmdfile(cmdfile):
    return imp.load_source('cmdfile', cmdfile)


def main():
    parser = OptionParser(usage='commander [options] <cmdfile> '
                                '<command>[:arg1,arg2=val2,...] ...')
    parser.add_option('-l', '--list',
        action='store_true',
        dest='list_commands',
        default=False,
        help="print list of possible commands and exit")
    parser.add_option('--nofail',
        action='store_true',
        default=False,
        help="Do not fail on non-zero return codes")
    opts, args = parser.parse_args()
    if not args:
        parser.error("Please specify a cmdfile.")
    cmdfile = args.pop(0)
    cmd_mod = import_cmdfile(cmdfile)
    cmds = parse_arguments(args)

    if opts.list_commands or not cmds:
        list_commands(cmd_mod.__doc__)

    if opts.nofail:
        config['failonerror'] = False

    for cmd, args, kwargs in cmds:
        commands[cmd](*args, **kwargs)

if __name__ == "__main__":
    main()
