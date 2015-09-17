import re
from setuptools import find_packages, setup
from setuptools.command.test import test as TestCommand
import sys


version = ''
with open('mcrunner/__init__.py', 'r') as fd:
    version = re.search(
        r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
        fd.read(),
        re.MULTILINE
    ).group(1)


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = ''

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run(self):
        import pytest
        errno = pytest.main(self.pytest_args)
        raise SystemExit(errno)

install_requires = []
if sys.version_info < (3,2):
    install_requires.append('subprocess32==3.2.6')

setup(
    name='mcrunner',
    version=version,
    description='Minecraft server monitoring and control system for UNIX',
    url='https://github.com/sbezboro/mcrunner',
    author='Sergei Bezborodko',
    author_email='sergei.b.ru@gmail.com',
    license='MIT',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    keywords='minecraft server runner',
    install_requires=install_requires,
    packages=find_packages(),
    cmdclass = {'test': PyTest},
    tests_require=['mock', 'pytest', 'pytest-cov'],
    test_suite='py.test',
    data_files=[('/etc/mcrunner', ['config/mcrunner.sample.conf'])],
    entry_points={
        'console_scripts': [
            'mcrunnerd=mcrunner.mcrunnerd:main',
            'mcrunner=mcrunner.mcrunner:main'
        ],
    },
)