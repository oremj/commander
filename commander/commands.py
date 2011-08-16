import logging
import os
import time
from subprocess import Popen, PIPE
from threading import Lock, Semaphore, Thread

import commander.settings
from commander.ssh import SSHExecClient
from commander.utils import cmd_status, listify, prefixlines, PStatus


log = logging


class ThreadPool:

    def __init__(self, max_threads):
        self._thread_available = Semaphore(max_threads)
        self.threads = []

    def _thread_func(self, f):
        def func(*args, **kwargs):
            try:
                f(*args, **kwargs)
            except Exception, e:
                raise e
            finally:
                log.debug("Releasing semaphore")
                self._thread_available.release()

        return func

    def add_func(self, f, *args, **kwargs):
        t = Thread(target=self._thread_func(f),
                            args=args, kwargs=kwargs)
        t.daemon = True
        self.threads.append(t)

    def run_all(self):
        for t in self.threads:
            log.debug("Waiting for semaphore")
            self._thread_available.acquire(True)
            log.debug("Starting thread")
            t.start()

        log.debug("Waiting for threads to finish")
        for t in self.threads:
            t.join()


_output_lock = Lock()


def _remote_cmd(host, cmd, jumphost, ssh_key):
    extra = []

    if jumphost:
        extra.append('-o "ProxyCommand ssh -A %s nc %%h %%p"' % jumphost)

    if ssh_key:
        if os.path.isfile(ssh_key):
            extra.append('-i %s' % ssh_key)
        else:
            raise ValueError("ssh_key should be a valid file")
    return """ssh -T %s %s <<'EOF'
        %s
EOF""" % (" ".join(extra), host, cmd)


def remote(hosts, cmd, jumphost=None,
            remote_limit=25, ssh_key=None, run_threaded=True, output=True):

    status = {}

    hosts = listify(hosts)

    if len(hosts) == 1 or remote_limit == 1:
        run_threaded = False

    if run_threaded:
        t = ThreadPool(remote_limit)
        for host in hosts:
            ssh_client = SSHExecClient(host, ssh_key, jumphost)
            t.add_func(_threaded_run, status, ssh_client, cmd, output=output)
        t.run_all()
    else:
        for host in hosts:
            ssh_client = SSHExecClient(host, ssh_key, jumphost)
            status[host] = _run_command(host, cmd, ssh_client.run,
                                        output=output)

    return status


def _threaded_run(status, client, cmd, *args, **kwargs):
    """status: dict passed in that will be updated with the status
       of _run_command
    """
    status[client.host] = _run_command(client.host,
                                       cmd, client.run, *args, **kwargs)
    return status[client.host]


def _run_command(host, cmd, runner, output=True):
    """runner: function which runs the command, must be of the form f(cmd)
               and return a Pstatus named-tuple
    """

    if output:
        with _output_lock:
            logging.info(prefixlines(host, "running", cmd, "blue"))

    start = time.time()
    status = runner(cmd)
    end = time.time()

    if output:
        with _output_lock:
            logging.info(cmd_status(end - start, host, cmd, status))

    return status


def local(cmd, output=True):
    return _run_command("localhost", cmd, run, output=output)


def run(cmd):
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    return PStatus(out=out, err=err, code=p.returncode)
