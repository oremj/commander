from colorprint import colorize
import threading
from subprocess import Popen, PIPE


class Commander:

    def __init__(self, remote_limit=8):
        self._thread_available = threading.Semaphore(remote_limit)
        self._output_lock = threading.Lock()

    def remote(self, hosts, cmd):
        threads = []
        for host in hosts:
            ssh_cmd = """ssh -T %s <<EOF
                %s
EOF""" % (host, cmd)

            t = threading.Thread(target=self._run_command_thread, args=(host, cmd, ssh_cmd))
            t.daemon = True
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

    def _run_command_thread(self, *args, **kwargs):
        self._thread_available.acquire(True)

        try:
            self._run_command(*args, **kwargs)
        except Exception, e:
            print e
            pass

        self._thread_available.release()

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
            print '[%s] %s: %s' % (colorize(host, 'green'), out_type, l)
