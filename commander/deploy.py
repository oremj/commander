import os
import time
from contextlib import contextmanager
from functools import wraps
from threading import Lock

from commander.hosts import get_systems
from commander.commands import local, remote, ThreadPool
from commander.utils import cmd_status, listify, prefixlines
from commander.settings import config


commands = {}
_output_lock = Lock()


class BadReturnCode(Exception):
    pass


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

    def _output(self, out):
        """Default: print to stdout"""
        with _output_lock:
            print out

    def set_host(self, host):
        self.env['host'] = host

    def _check_status(self, status):
        if config['failonerror'] and status.code != 0:
            raise BadReturnCode("Returncode was %d" % status.code)

    def _wrap_cmd(self, cmd, which):
        if self.env[which]:
            cmd = "cd %s && %s" % (self.env[which], cmd)
        return cmd

    def remote(self, cmd, *args, **kwargs):
        remote_kwargs = self.remote_kwargs.copy()
        remote_kwargs.update(kwargs)

        cmd = self._wrap_cmd(cmd, 'cwd')

        self._output(prefixlines(self.env['host'], "running", cmd, "blue"))

        start = time.time()
        status = remote(self.env['host'], cmd, output=False, *args, **remote_kwargs).values()[0]
        end = time.time()

        self._output(cmd_status(end - start, self.env['host'], cmd, status))
        self._check_status(status)
        return status

    def local(self, cmd, *args, **kwargs):
        cmd = self._wrap_cmd(cmd, 'lcwd')
        self._output(prefixlines('localhost', "running", cmd, "blue"))
        start = time.time()
        status = local(cmd, output=False, *args, **kwargs)
        end = time.time()
        self._output(cmd_status(end - start, 'localhost', cmd, status))
        self._check_status(status)
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
    groups = listify(groups)
    hs = reduce(lambda x, y: x + y, [get_systems(group) for group in groups])
    return hosts(hs, remote_limit, remote_kwargs)


def hosts(hosts, remote_limit=25, remote_kwargs=None):
    """Wraps a deployment function of the form def task1(ctx, *args, **kwargs).
       After task is wrapped it will be called as task1(*args, **kwargs).

       The passed ctx objects will be set with a host from the hosts arg
    """
    hosts = listify(hosts)

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
