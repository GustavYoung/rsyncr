import os
import time
from setuptools import setup, find_packages

lt = time.localtime()
version = (lt.tm_year, (10 + lt.tm_mon) * 100 + lt.tm_mday, (10 + lt.tm_hour) * 100 + lt.tm_min)
versionString = '.'.join(map(str, version))

# Clean up old binaries for twine upload
if os.path.exists("dist"):
  rmFiles = list(sorted(os.listdir("dist")))
  print(repr(rmFiles))
  for file in (f for f in rmFiles[:-1] if any([f.endswith(ext) for ext in (".tar.gz", "zip")])):
    print("Removing old sdist archive %s" % file)
    try: os.unlink(os.path.join("dist", file))
    except: print("Cannot remove old distribution file " + file)

setup(  # https://pypi.python.org/pypi?%3Aaction=list_classifiers
  name = 'rsyncr',
  version = versionString,  # without extra
  description = "rsyncr",
  long_description = "",  # TODO
  classifiers = [c.strip() for c in """
        Development Status :: 4 - Beta
        License :: Free To Use But Restricted
        Intended Audience :: Developers
        Intended Audience :: Other Audience
        Intended Audience :: Science/Research
        Intended Audience :: System Administrators
        License :: OSI Approved :: GNU General Public License v3 (GPLv3)
        Operating System :: OS Independent
        Programming Language :: Other
        Programming Language :: Python
        Programming Language :: Python :: 2
        Programming Language :: Python :: 3
        """.split('\n') if c.strip()],
  keywords = 'Rsync wrapper for safe backups',
  author = 'Arne Bachmann',
  author_email = 'ArneBachmann@users.noreply.github.com',
  maintainer = 'Arne Bachmann',
  maintainer_email = 'ArneBachmann@users.noreply.github.com',
  url = 'http://github.com/ArneBachmann/corrupdetect',
  license = 'GNU General Public License v3 (GPLv3)',
  packages = [""],
#  package_dir = {"": ""},
#  package_data = {"": ["check.py", "run.py"]},
#  include_package_data = False,  # if True, will *NOT* package the data!
  zip_safe = False,
  entry_points = {
    'console_scripts': [
      'rsyncr=run:main'
    ]
  },
)
