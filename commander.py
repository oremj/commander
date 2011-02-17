import logging
from colorprint import colorize
from subprocess import Popen, PIPE
from threading import Lock, Semaphore, Thread


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
        

class Commander:

    def __init__(self, remote_limit=8):
        self.remote_limit = remote_limit
        self._output_lock = Lock()

    def remote(self, hosts, cmd, jumphost=None):
        t = ThreadPool(self.remote_limit)
        extra = []
        if jumphost:
            extra.append('-o "ProxyCommand ssh -A %s nc %%h %%p"' % jumphost)
        for host in hosts:
            ssh_cmd = """ssh -T %s %s <<EOF
                %s
EOF""" % (" ".join(extra), host, cmd)
            t.add_func(self._run_command, host, cmd, ssh_cmd)

        t.run_all()

    def _run_command(self, host, cmd, full_cmd=None):
        if not full_cmd:
            full_cmd = cmd

        stdout, stderr = self.run(full_cmd)

        self._output_lock.acquire(True)
        self._log_lines(host, colorize("run", "blue"), cmd)
        self._log_lines(host, colorize("out", "yellow"), stdout)
        self._log_lines(host, colorize("err", "red"), stderr)
        self._output_lock.release()

    def local(self, cmd):
        self._run_command("localhost", cmd)

    def run(self, cmd):
        return Popen(cmd, shell=True,
                        stdout=PIPE, stderr=PIPE).communicate()

    def _log_lines(self, host, out_type, output):
        for l in output.splitlines():
            print '[%s] %s: %s' % (colorize(host, 'green'), out_type, l.strip())
