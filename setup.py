from distutils.core import setup
import py2exe

setup(
        console=['ogorod.py'],
        data_files=[(".", ["config.ini"])]
)
