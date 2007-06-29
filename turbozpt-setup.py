from setuptools import setup, find_packages
from turbogears.finddata import find_package_data

setup(
    name="TurboZpt",
    version="0.1.4",
    description="TurboGears plugin to support use of Zope Page Templates",
    author="Bas van Oostveen",
    author_email="v.oostveen@gmail.com",
    url="http://ido.nl.eu.org/turbozpt/",
    download_url="http://ido.nl.eu.org/turbozpt/TurboZpt-0.1.2.tar.gz",
    license="MIT",
#    install_requires = ["TurboGears >= 0.9a0dev", "ZopePageTemplates"],
    install_requires = ["TurboGears >= 0.9a0dev"],
    zip_safe=False,
    packages=find_packages(),
    classifiers = [
        'Development Status :: 3 - Alpha',
        #'Environment :: TurboGears',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'License :: OSI Approved :: MIT License',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    entry_points="""
    [python.templating.engines]
    zpt = turbozpt.zptsupport:TurboZpt
    """,
    test_suite = 'nose.collector',
    )
    
