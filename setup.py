from distutils.core import setup

setup(name='commander',
      version='0.2.3',
      author='Jeremiah Orem',
      url='http://github.com/oremj/commander',
      author_email='oremj@oremj.com',
      description='A deployment library and remote command runner.',
      packages=['commander'],
      scripts=['scripts/issue-multi-command', 'scripts/commander'],
      )
