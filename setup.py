#
# CADRE setup
#

from setuptools import setup

kwargs = {'author': 'Herb Schilling',
 'author_email': 'hschilling@nasa.gov',
 'classifiers': ['Intended Audience :: Science/Research',
                 'Topic :: Scientific/Engineering'],
 'description': 'An ExternalComponent that wraps and runs code on the NASA NAS Pleiades supercomputer',
 'download_url': 'http://github.com/OpenMDAO/NAS_Access.git',
 'include_package_data': True,
 'install_requires': ['openmdao'],
 'keywords': ['openmdao', 'NAS_Access'],
 'license': 'Apache 2.0',
 'maintainer': 'Herb Schilling',
 'maintainer_email': 'hschilling@nasa.gov',
 'name': 'NAS_Access',
 'package_dir': {'': 'src'},
 'packages': ['NAS_Access','NAS_Access.test' , 'NAS_Access.examples'],
 'include_package_data': True,
 'url': 'http://github.com/OpenMDAO/NAS_Access.git',
 'version': '0.1',
 'zip_safe': False}


setup(**kwargs)

# 'package_data': {'NAS_Access': ['input.dat','examples/OTAC_nas_access.py']},


 # 'data_files':[('', ['examples/OTAC_nas_access.py', 'doe_input.dat', 'read_doe_csv.py', 'run_OTAC_DOE_comp_nas_access.py']),
 #                  ],



