from distutils.core import setup
import os, sys

if sys.version_info < (3,4):
    print('rshell requires Python 3.4 or newer.')
    sys.exit(1)

from shell49.version import __version__

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
  name = 'shell49',
  packages = ['shell49', 'tests'],
  version = '0.1',
  description = 'Micropython remote shell',
  license = 'MIT',
  author = 'Bernhard Boser',
  author_email = 'boser@berkeley.edu',
  url = 'https://github.com/bboser/shell49', # use the URL to the github repo
  download_url = 'https://github.com/bboser/shell49/archive/0.1.tar.gz', # I'll explain this in a second
  keywords = ['micropython', 'shell', 'rshell'], # arbitrary keywords
  classifiers = [
      'Development Status :: 3 - Alpha',
      'Environment :: Console',
      'Intended Audience :: Developers',
      'License :: OSI Approved :: MIT License',
      'Natural Language :: English',
      'Operating System :: POSIX :: Linux',
      'Programming Language :: Python',
      'Programming Language :: Python :: 3',
      'Topic :: Software Development :: Embedded Systems',
      'Topic :: System :: Shells',
      'Topic :: Terminals :: Serial',
      'Topic :: Utilities',
  ],
  install_requires=[
      'pyserial >= 2.0',
      'esptool >= 2.1',
      'zeroconf >= 0.19'
  ],
  entry_points = {
      'console_scripts': [
          'shell49=shell49.command_line:main'
      ],
  },
)
