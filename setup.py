from distutils.core import setup

with open('README.rst') as f:
    long_descr = f.read()

setup(
    name='Zimbratosthenes',
    version='1.0.0',
    author='Sylvain Soliman',
    author_email='Sylvain.Soliman@inria.fr',
    description='Partial Zimbra filters to/from sieve text files converter',
    packages=['zimbratosthenes'],
    package_dir={'zimbratosthenes': ''},
    entry_points={
        'console_scripts': [
            'zbt = zimbratosthenes.zimbra:main',
        ],
    },
    license='MIT',
    long_description=long_descr,
    install_requires=[
        'sievelib >= 0.8',
        'python-zimbra >= 1.0-rc5',
    ]
)
