#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

from distutils.extension import Extension
from Cython.Distutils import build_ext

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    # TODO: put package requirements here
]

test_requirements = [
    # TODO: put package test requirements here
]

ext_isnobal = Extension(
                        "pysnobal.libsnobal.isnobal",
                        [ "pysnobal/libsnobal/isnobal.pyx" ],
                        extra_compile_args=['-fopenmp'],
                        extra_link_args=['-fopenmp'],
                        )

setup(
    name='pysnobal',
    version='0.1.0',
    description="Python implementation of the Snobal model",
    long_description=readme + '\n\n' + history,
    author="Scott Havens",
    author_email='scott.havens@ars.usda.gov',
    url='https://gitlab.com/ars-snow/pysnobal',
    packages=[
        'pysnobal',
    ],
    package_dir={'pysnobal':
                 'pysnobal'},
    include_package_data=True,
    install_requires=requirements,
    license="ISCL",
    zip_safe=False,
    keywords='pysnobal',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    cmdclass = {'build_ext': build_ext},
    ext_modules= [
        Extension("pysnobal.libsnobal.libsnobal", [ "pysnobal/libsnobal/libsnobal.pyx" ]),
        Extension("pysnobal.libsnobal.snobal", [ "pysnobal/libsnobal/snobal.pyx" ]),
        ext_isnobal,
    ]
)
