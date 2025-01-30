#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import glob
import sys
import numpy

from setuptools import setup, find_packages, Extension

# from distutils.extension import Extension
from Cython.Distutils import build_ext

with open('README.md') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    "Cython>=0.29.32,<1.0",
    "numpy>=1.25.2,<2.0",
    "pandas>=1.0,<2.0",
]

test_requirements = [
    "pytest"
]

# make sure we're using GCC
if "CC" not in os.environ:
    os.environ["CC"] = "gcc"

if sys.platform == 'darwin':
    from distutils import sysconfig
    vars = sysconfig.get_config_vars()
    vars['LDSHARED'] = vars['LDSHARED'].replace('-bundle', '-dynamiclib')
    extra_cc_args = [
        '-Xpreprocessor', '-fopenmp', '-lomp', '-O3', '-L./pointsnobal'
    ]
else:
    extra_cc_args = ['-fopenmp', '-O3', '-L./pointsnobal']

# ------------------------------------------------------------------------------
# Compiling the C code for the Snobal library

loc = 'pointsnobal/c_snobal/libsnobal'
cwd = os.getcwd()
sources = glob.glob(os.path.join(loc, '*.c'))

loc = 'pointsnobal/c_snobal'

sources += [os.path.join(loc, val) for val in ["snobal.pyx"]]
extensions = [
    Extension(
        "pointsnobal.c_snobal.snobal",
        sources,
        # libraries=["snobal"],
        include_dirs=[
            numpy.get_include(),
            'pointsnobal/c_snobal',
            'pointsnobal/c_snobal/h'
        ],
        extra_compile_args=extra_cc_args,
        extra_link_args=extra_cc_args,
    )
]

setup(
    name='pointsnobal',
    version='0.1.0',
    description="Python wrapper of the Snobal mass and "
                "energy balance snow model",
    long_description=readme + '\n\n' + history,
    author="M3 Works",
    author_email='info@m3works.io',
    url='https://github.com/m3works/pointsnobal',
    packages=find_packages(exclude=["tests"]),
    include_package_data=True,
    install_requires=requirements,
    license="BSD license",
    zip_safe=False,
    keywords='pointsnobal',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.9'
        'Programming Language :: Python :: 3.10'
        'Programming Language :: Python :: 3.11'
    ],
    test_suite='tests',
    tests_require=test_requirements,
    cmdclass={
        'build_ext': build_ext
    },
    ext_modules=extensions,
)