Commander
=========
Commander is two things:
1) A deployment library modeled after fabric
2) A remote command runner


Deployment Libary
-----------------
A simple deployment example <example.py>::
    from commander.deploy import hosts, local_command

    @hosts(["host1", "host2", "host3"])
    def hostname(ctx):
        ctx.remote("hostname")

And then from the commandline::
    # commander -l example.py 
    Available commands:

        hostname

    # commander example.py hostname
    Running 'hostname'
    [host1] run: hostname
    [host1] out: host1
    [host2] run: hostname
    [host2] out: host2
    [host3] run: hostname
    [host3] out: host3

Your deployment definitions can also be called directly from another python script <example2.py>::
    from example import hostname
    hostname()

And then::
    # python2.6 example2.py
    [host1] run: hostname
    [host1] out: host1
    [host2] run: hostname
    [host2] out: host2
    [host3] run: hostname
    [host3] out: host3

Remote Command Runner
---------------------
After defining a dictionary of hosts in /etc/commanderconfig.py e.g.,::
    hostgroups = {
        'hostgroup1': ['host1', 'host2', 'host3'],
    }

From the commandline::
    # issue-multi-command hostgroup1 hostname
    [host1] run: hostname
    [host1] out: host1
    [host2] run: hostname
    [host2] out: host2
    [host3] run: hostname
    [host3] out: host3
