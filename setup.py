#!/usr/bin/env python3
from setuptools import setup

__version__ = '1.0.dev0'

INSTALL_REQUIREMENTS = ['networkx', 'lxml', 'regex==2015.06.10']

setup(
    classifiers=('Natural Language :: English',
                 'Programming Language :: Python',
                 'Topic :: Text Processing',
                 'Topic :: Scientific/Engineering', ),
    data_files=[('share',
                 ['static/view_tree.html', 'static/xml2tree-sonar.xsl',
                  'static/simplify_alpino_xml.xsl', 'share/email@.service',
                  'share/legal_nlp_pipeline@.service', 'share/README.adoc',
                  'share/README.html', 'share/pipeline.args'])],
    install_requires=INSTALL_REQUIREMENTS,
    license='GPLv3',
    maintainer='Sander Maijers',
    maintainer_email='S.N.Maijers@gmail.com',
    name='legal-nlp-pipeline',
    packages=('legal_nlp_pipeline', ),
    scripts=('bin/legal_nlp_pipeline.sh', ),
    setup_requires=(),
    url='about:blank',
    version=__version__,
    zip_safe=True)
