import logging
from subprocess import Popen, PIPE
from threading import Lock, Semaphore, Thread

from commander.colorprint import colorize


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
                print e
                pass

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

def remote(hosts, cmd, jumphost=None, remote_limit=8):
    t = ThreadPool(remote_limit)
    extra = []
    if jumphost:
        extra.append('-o "ProxyCommand ssh -A %s nc %%h %%p"' % jumphost)
    for host in hosts:
        ssh_cmd = """ssh -T %s %s <<EOF
            %s
EOF""" % (" ".join(extra), host, cmd)
        t.add_func(_run_command, host, cmd, ssh_cmd)

    t.run_all()

def _run_command(host, cmd, full_cmd=None):
    if not full_cmd:
        full_cmd = cmd

    stdout, stderr = run(full_cmd)

    _output_lock.acquire(True)
    _log_lines(host, colorize("run", "blue"), cmd)
    _log_lines(host, colorize("out", "yellow"), stdout)
    _log_lines(host, colorize("err", "red"), stderr)
    _output_lock.release()

def local(cmd):
    _run_command("localhost", cmd)

def run(cmd):
    return Popen(cmd, shell=True,
                    stdout=PIPE, stderr=PIPE).communicate()

def _log_lines(host, out_type, output):
    for l in output.splitlines():
        print '[%s] %s: %s' % (colorize(host, 'green'), out_type, l.strip())
