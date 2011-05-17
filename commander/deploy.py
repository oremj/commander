import os
import sys
from contextlib import contextmanager
from functools import wraps

from commander.hosts import get_systems
from commander.commands import local, remote, ThreadPool


class Context(object):

    def __init__(self):
        self.host = None
        self.remote_cwd = ""
        self.local_cwd = ""

    def set_host(self, host):
        self.host = host

    def _wrap_remote_cmd(self, cmd):
        if self.remote_cwd:
            cmd = "cd %s && %s" % (self.remote_cwd, cmd)
        return cmd

    def _wrap_local_cmd(self, cmd):
        if self.local_cwd:
            cmd = "cd %s && %s" % (self.local_cwd, cmd)
        return cmd

    def remote(self, cmd, *args, **kwargs):
        cmd = self._wrap_remote_cmd(cmd)
        return remote([self.host], cmd, *args, **kwargs)

    def local(self, cmd, *args, **kwargs):
        cmd = self._wrap_local_cmd(cmd)
        return local(cmd, *args, **kwargs)

    @contextmanager
    def _set_path(self, path, var):
        prev_path = getattr(self, var)
        setattr(self, var, os.path.join(prev_path, path))
        yield
        setattr(self, var, prev_path)

    def cd(self, path):
        return self._set_path(path, "remote_cwd")

    def lcd(self, path):
        return self._set_path(path, "local_cwd")


def hostgroup(group, remote_limit=25):
    def wrapper(f):
        @wraps(f)
        def inner_wrapper(*args, **kwargs):
            t = ThreadPool(remote_limit)
            for host in get_systems(group):
                ctx = Context()
                ctx.set_host(host)
                t.add_func(f, ctx, *args, **kwargs)
            t.run_all()

        return inner_wrapper
    return wrapper


def hosts(hosts, remote_limit=25):
    def wrapper(f):
        @wraps(f)
        def inner_wrapper(*args, **kwargs):
            t = ThreadPool(remote_limit)
            for host in hosts:
                ctx = Context()
                ctx.set_host(host)
                t.add_func(f, ctx, *args, **kwargs)
            t.run_all()

        return inner_wrapper
    return wrapper

def local_command(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        f(Context(), *args, **kwargs)

def main():
    pass

if __name__ == "__main__":
    main()
