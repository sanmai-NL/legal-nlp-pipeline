#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

__version__ = '1.0.dev0'

from setuptools import setup
from sys import version_info

MIN_REQUIRED_PYTHON_VERSION = (3, 4, 3)
MAX_REQUIRED_PYTHON_VERSION = (3, 4, 3)

basic_version_info = version_info[0:3]

if not (MIN_REQUIRED_PYTHON_VERSION <= basic_version_info <= MAX_REQUIRED_PYTHON_VERSION):
    raise RuntimeError(
        'Under Python version {version_info[0]:d}.{version_info[1]:d}.{version_info[2]:d}, while version '
        '>= {min_required_python_version[0]:d}.{min_required_python_version[1]:d}.{min_required_python_version[2]:d} '
        'and '
        '<= {max_required_python_version[0]:d}.{max_required_python_version[1]:d}.{max_required_python_version[2]:d} '
        'required. '.format(
            version_info=basic_version_info,
            min_required_python_version=MIN_REQUIRED_PYTHON_VERSION,
            max_required_python_version=MAX_REQUIRED_PYTHON_VERSION))

install_requirements = ['networkx', 'lxml', 'regex==2015.06.10']
# setup_requirements = ['cython'] # TODO: ensure that cython is installed before lxml

setup(classifiers=('Natural Language :: English', 'Programming Language :: Python', 'Topic :: Text Processing',
                   'Topic :: Scientific/Engineering',),
      data_files=[('share', ['static/view_tree.html', 'static/xml2tree-sonar.xsl', 'static/simplify_alpino_xml.xsl',
                             'share/email@.service', 'share/legal_nlp_pipeline@.service', 'share/README.adoc',
                             'share/README.html', 'share/pipeline.args'])],
      install_requires=install_requirements,
      license='GPLv3',
      maintainer='Sander Maijers',
      maintainer_email='S.N.Maijers@gmail.com',
      name='legal-nlp-pipeline',
      packages=('legal_nlp_pipeline',),
      scripts=('bin/legal_nlp_pipeline.sh',),
      setup_requires=(),
      url='about:blank',
      version=__version__,
      zip_safe=True
      )
