#!/usr/bin/env python3
import setuptools
# from setuptools import setup, find_packages, Command
import distutils.command.build
from setuptools.command.test import test as TestCommand
import shlex
import sys

sys.path.append('./sphinx')
# this is only necessary when not using setuptools/distribute
from sphinx.setup_command import BuildDoc


with open('test_requirements.pip') as fd:
    test_requirements = [line.rstrip() for line in fd]


with open('requirements.pip') as fd:
    requirements = [line.rstrip() for line in fd]


class PyTest(TestCommand):

    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = ''  # <-- Source and test directories - see pytest.ini

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        sys.path.insert(0, '../')
        errno = pytest.main(shlex.split(self.pytest_args))
        sys.exit(errno)


class BuildVagrant(distutils.command.build.build):

    def run(self):
        # Run the original build command
        # distutils.command.build.build.run(self)
        # Custom build stuff goes here
        self.build_vagrant()

    def build_vagrant(self):
        import subprocess
        cmd = "cd vagrant && /usr/local/bin/vagrant up"
        print('building and starting vagrant vm with command \'%s\'...' % cmd)
        sp = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for line in sp.stdout.split(b'\n'):
            print(line.decode())
        for line in sp.stderr.split(b'\n'):
            print(line.decode())
        return


name = 'GPS NOTAMS Map tool'
author = 'amattheisen'
version = '1.0'
release = '1.0.0'
sphinx_dir = 'docs'


setuptools.setup(
    author=author,
    cmdclass={'build_sphinx': BuildDoc,
              'build_vagrant': BuildVagrant,
              'test': PyTest,
              # 'install': Install
              },
    command_options={
        'build_sphinx': {
            'project': ('setup.py', name),
            'version': ('setup.py', version),
            'release': ('setup.py', release)
        }
    },
    description='GPS NOTAMS Map tool',
    install_requires=requirements,
    name=name,
    packages=setuptools.find_packages(),
    # packages=['distutils', 'distutils.command'],
    tests_require=test_requirements,
    url="https://github.com/amattheisen/notams",
    version=release,
)
