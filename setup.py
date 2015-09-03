from setuptools import find_packages, setup
from setuptools.command.test import test as TestCommand


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
        import subprocess
        args = [
            'py.test',
            'mcrunner/tests/',
            '-rs',
            '--cov=mcrunner',
            '--cov-report=term-missing',
        ]
        if self.pytest_args:
            args.extend(self.pytest_args.split())

        errno = subprocess.call(args)
        raise SystemExit(errno)

setup(
    name='mcrunner',
    version='0.1.0-dev',
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
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    keywords='minecraft server runner',
    packages=find_packages(exclude=['mcrunner']),
    cmdclass = {'test': PyTest},
    tests_require=['mock', 'pytest', 'pytest-cov'],
    test_suite='py.test',
    data_files=[('/etc/mcrunner', ['config/mcrunner.conf'])],
    entry_points={
        'console_scripts': [
            'mcrunnerd=mcrunner.mcrunnerd:main',
            'mcrunner=mcrunner.mcrunner:main'
        ],
    },
)