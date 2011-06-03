import types

from commander.colorprint import colorize


def cmd_status(run_time, host, cmd, pstatus):
    out = []
    out.append(
        prefixlines(host, "finished", "%s (%0.3fs)" % (cmd, run_time), "blue"))
    if pstatus.out:
        out.append(prefixlines(host, "out", pstatus.out, "yellow"))
    if pstatus.err:
        out.append(prefixlines(host, "err", pstatus.out, "red"))
    return "\n".join(out)


def listify(l):
    if isinstance(l, types.StringTypes):
        l = [l]
    return l


def prefixlines(host, t, s, color='yellow'):
    """Return a line of of the format "[host] t: line" for each line in s"""
    out = []
    for l in s.splitlines():
        out.append("[%s] %s: %s" % (colorize(host, 'green'),
                                    colorize(t, color),
                                    l.strip()))

    return "\n".join(out)
