import setuptools
import os

REQUIREMENTS = [
    'PyYAML>=5.1.2',
    'numpy==1.19.1',
    'pandas==1.2.2',
    'SPARQLWrapper>=1.8.5',
    'ftfy>=5.8',
    'requests>=2.24.0',
    'xlrd>=1.0.0',
    'text-unidecode==1.3',
    'munkres==1.1.4'
]

setuptools.setup(
    name="t2wml-api", 
    version="0.2.11",
    description="Programming API for T2WML, a cell-based Language for mapping tables into wikidata records",
	author="USC ISI and The Research Software Company",
    url="https://github.com/usc-isi-i2/t2wml/",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3"

    ],
    python_requires='>=3.6',
    install_requires=REQUIREMENTS,
    include_package_data=True
)