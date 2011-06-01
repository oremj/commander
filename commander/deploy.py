import os
import types
from contextlib import contextmanager
from functools import wraps
from threading import Lock

from commander.colorprint import colorize
from commander.hosts import get_systems
from commander.commands import local, remote, ThreadPool


commands = {}
_output_lock = Lock()


def _listify(l):
    if isinstance(l, types.StringTypes):
        l = [l]
    return l


class Context(object):
    """This class is passed to every deployment command as the first argument."""

    def __init__(self, remote_kwargs=None):
        self.env = {'host': None,
                    'cwd': "",
                    'lcwd': ""}

        if not remote_kwargs:
            self.remote_kwargs = {}
        else:
            self.remote_kwargs = remote_kwargs


    def _output(self, host, cmd, pstatus):
        """Default: print to stdout"""
        output = []
        output.append("[%s] %s: %s" %
                      (colorize(host, 'green'),
                       colorize('run', 'blue'), cmd.strip()))

        for l in pstatus.out.splitlines():
            output.append("[%s] %s: %s" %
                          (colorize(host, 'green'),
                           colorize('out', 'yellow'), l.strip()))

        for l in pstatus.err.splitlines():
            output.append("[%s] %s: %s" %
                          (colorize(host, 'green'),
                           colorize('err', 'red'), l.strip()))

        _output_lock.acquire(True)
        print "\n".join(output)
        _output_lock.release()
        

    def set_host(self, host):
        self.env['host'] = host

    def _wrap_cmd(self, cmd, which):
        if self.env[which]:
            cmd = "cd %s && %s" % (self.env[which], cmd)
        return cmd

    def remote(self, cmd, *args, **kwargs):
        remote_kwargs = self.remote_kwargs.copy()
        remote_kwargs.update(kwargs)

        cmd = self._wrap_cmd(cmd, 'cwd')
        status = remote(self.env['host'], cmd, output=False, *args, **remote_kwargs).values()[0]

        self._output(self.env['host'], cmd, status)
        return status

    def local(self, cmd, *args, **kwargs):
        cmd = self._wrap_cmd(cmd, 'lcwd')
        status = local(cmd, output=False, *args, **kwargs)
        self._output('localhost', cmd, status)
        return status

    @contextmanager
    def _set_path(self, path, which):
        prev_path = self.env[which]
        self.env[which] = os.path.join(prev_path, path)
        yield
        self.env[which] = prev_path

    def cd(self, path):
        return self._set_path(path, "cwd")

    def lcd(self, path):
        return self._set_path(path, "lcwd")


def hostgroups(groups, remote_limit=25, remote_kwargs=None):
    """The same as hosts, except for it accepts a hostgroup or list of 
    hostgroups.
    """
    groups = _listify(groups)
    hs = reduce(lambda x, y: x + y, [get_systems(group) for group in groups])
    return hosts(hs, remote_limit, remote_kwargs)


def hosts(hosts, remote_limit=25, remote_kwargs=None):
    """Wraps a deployment function of the form def task1(ctx, *args, **kwargs).
       After task is wrapped it will be called as task1(*args, **kwargs).
       
       The passed ctx objects will be set with a host from the hosts arg
    """
    hosts = _listify(hosts)

    def wrapper(f):

        @wraps(f)
        def inner_wrapper(*args, **kwargs):
            t = ThreadPool(remote_limit)
            for host in hosts:
                ctx = Context(remote_kwargs=remote_kwargs)
                ctx.set_host(host)
                t.add_func(f, ctx, *args, **kwargs)
            t.run_all()

        commands[f.__name__] = inner_wrapper
        return inner_wrapper
    return wrapper


def task(f):
    """This is the same as hosts, except it does not set a host in the ctx,
    so this will be used for localhost deployment tasks
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        f(Context(), *args, **kwargs)

    commands[f.__name__] = wrapper
    return wrapper
