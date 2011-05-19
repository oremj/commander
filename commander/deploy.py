import os
import types
from contextlib import contextmanager
from functools import wraps

from commander.hosts import get_systems
from commander.commands import local, remote, ThreadPool


commands = {}


def _listify(l):
    if isinstance(l, types.StringTypes):
        l = [l]
    return l


class Context(object):

    def __init__(self):
        self.env = {'host': None,
                    'cwd': "",
                    'lcwd': ""}

    def set_host(self, host):
        self.env['host'] = host

    def _wrap_cmd(self, cmd, which):
        if self.env[which]:
            cmd = "cd %s && %s" % (self.env[which], cmd)
        return cmd

    def remote(self, cmd, *args, **kwargs):
        cmd = self._wrap_cmd(cmd, 'cwd')
        return remote(self.env['host'], cmd, *args, **kwargs)

    def local(self, cmd, *args, **kwargs):
        cmd = self._wrap_cmd(cmd, 'lcwd')
        return local(cmd, *args, **kwargs)

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


def hostgroups(groups, remote_limit=25):
    groups = _listify(groups)
    hs = reduce(lambda x, y: x + y, [get_systems(group) for group in groups])
    return hosts(hs, remote_limit)


def hosts(hosts, remote_limit=25):
    hosts = _listify(hosts)

    def wrapper(f):

        @wraps(f)
        def inner_wrapper(*args, **kwargs):
            t = ThreadPool(remote_limit)
            for host in hosts:
                ctx = Context()
                ctx.set_host(host)
                t.add_func(f, ctx, *args, **kwargs)
            t.run_all()

        commands[f.__name__] = inner_wrapper
        return inner_wrapper
    return wrapper


def local_command(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        f(Context(), *args, **kwargs)

    commands[f.__name__] = wrapper
    return wrapper
