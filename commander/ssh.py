import os
from subprocess import Popen, PIPE

from commander.utils import PStatus


class SSHClient(object):
    def __init__(self, host, identity_file=None, jumphost=None):
        self.host = host
        self.identity_file = identity_file
        self.jumphost = jumphost

    def run(self, cmd):
        raise NotImplementedError() 


class SSHExecClient(SSHClient):
    def run(self, cmd):
        extra = []
        if self.jumphost:
            extra.append('-o "ProxyCommand ssh -A %s nc %%h %%p' % self.jumphost)

        if self.identity_file:
            if os.path.isfile(self.identity_file):
                extra.append('-i %s' % self.identity_file)
            else:
                raise ValueError("identity_file should be a valid file")

        cmd = """ssh -T %s %s <<'EOF'
            %s
EOF""" % (" ".join(extra), self.host, cmd)
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        return PStatus(out=out, err=err, code=p.returncode)
