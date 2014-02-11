# from distutils.core import setup
from setuptools import setup
from setuptools.command.test import test as TestCommand
import sys


class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        #import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)


with open('README.txt') as f:
    long_descr = f.read()

setup(
    name='Zimbratosthenes',
    version='1.0.0',
    author='Sylvain Soliman',
    author_email='Sylvain.Soliman@inria.fr',
    url='http://lifeware.inria.fr/~soliman',
    description='Partial Zimbra filters to/from sieve text files converter',
    py_modules=['zimbra'],
    entry_points={
        'console_scripts': [
            'zbt = zimbra:main',
        ],
    },
    license='MIT',
    long_description=long_descr,
    install_requires=[
        'sievelib >= 0.8',
        'python-zimbra >= 1.0-rc5',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
    ],
    keywords='zimbra mail sieve filters',
    tests_require=['pytest'],
    cmdclass={'test': PyTest},
)
