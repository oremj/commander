import logging
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
    """This class is passed to every deployment command as the first arg."""

    def __init__(self, remote_kwargs=None):
        self.env = {'host': None,
                    'cwd': "",
                    'lcwd': ""}

        if not remote_kwargs:
            self.remote_kwargs = {}
        else:
            self.remote_kwargs = remote_kwargs

    def _output(self, out, log=logging.info):
        """Default: print to stdout"""
        with _output_lock:
            log(out)

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
        status = remote(self.env['host'], cmd, output=False,
                        *args, **remote_kwargs).values()[0]
        end = time.time()

        try:
            self._check_status(status)
        except BadReturnCode:
            self._output(cmd_status(end - start, self.env['host'], cmd,
                                    status, state='failed', color="red"),
                         logging.warning)
            raise

        self._output(cmd_status(end - start, self.env['host'], cmd, status))
        return status

    def local(self, cmd, *args, **kwargs):
        cmd = self._wrap_cmd(cmd, 'lcwd')
        self._output(prefixlines('localhost', "running", cmd, "blue"))
        start = time.time()
        status = local(cmd, output=False, *args, **kwargs)
        end = time.time()
        try:
            self._check_status(status)
        except BadReturnCode:
            self._output(cmd_status(end - start, 'localhost', cmd,
                                    status, state='failed', color="red"),
                         logging.warning)
            raise

        self._output(cmd_status(end - start, 'localhost', cmd, status))
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


def catch_badreturn(f):

    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except BadReturnCode:
            exit(1)

    return wrapper


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
        f = catch_badreturn(f)

        @wraps(f)
        def inner_wrapper(*args, **kwargs):
            logging.info('Running %s' % getattr(f, '__name__', repr(f)))
            t = ThreadPool(remote_limit)
            for host in hosts:
                ctx = Context(remote_kwargs=remote_kwargs)
                ctx.set_host(host)
                t.add_func(f, ctx, *args, **kwargs)
            start = time.time()
            t.run_all()
            end = time.time()
            logging.info('Finished %s (%0.3fs)' %
                          (getattr(f, '__name__', repr(f)), end - start))

        commands[f.__name__] = inner_wrapper
        return inner_wrapper
    return wrapper


def task(f):
    """This is the same as hosts, except it does not set a host in the ctx,
    so this will be used for localhost deployment tasks
    """
    f = catch_badreturn(f)

    @wraps(f)
    def wrapper(*args, **kwargs):
        logging.info('Running %s' % getattr(f, '__name__', repr(f)))
        start = time.time()
        res = f(Context(), *args, **kwargs)
        end = time.time()
        logging.info('Finished %s (%0.3fs)' %
                     (getattr(f, '__name__', repr(f)), end - start))
        return res

    commands[f.__name__] = wrapper
    return wrapper
