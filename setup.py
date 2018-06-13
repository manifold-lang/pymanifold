import os
from setuptools import setup, find_packages

README_PATH = "README.md"
LONG_DESC = ""
if os.path.exists(README_PATH):
    with open(README_PATH) as readme:
        LONG_DESC = readme.read()

INSTALL_REQUIRES = ["matplotlib"]
PACKAGE_NAME = "pymanifold"
PACKAGE_DIR = "src"

setup(
    name=PACKAGE_NAME,
    version="0.1",

    packages=find_packages(),
    package_data={"": ["*.so", "*.pyc"]},
    #  packages=["src", "data/dreal", "data/dreal/api", "data/dreal/symbolic", "tests"],
    #  package_dir={"src": "src",
    #               "dreal": "data/dreal",
    #               "api": "data/dreal/api",
    #               "symbolic": "data/dreal/symbolic",
    #               "tests": "tests"
    #               },
    #  package_data={"data/dreal": ["*.so"],
    #                "data/dreal/api": ["*.so"],
    #                "data/dreal/symbolic": ["*.so"]
    #                },

    # This project requires matplotlib to show the designed microfluidic
    # circuit and dReal SMT solver, however it's Python3 support is still
    # experimental so a stable version is included under packages
    install_requires=INSTALL_REQUIRES,

    # metadata for upload to PyPI
    author="Josh Reid",
    author_email="js2reid@uwaterloo.ca",
    description="Python-Manifold is a Python implementation of Derek Rayside's\
    Manifold microfluidic simulation tool",
    long_description=LONG_DESC,
    license="GPLv3",
    keywords="Python Manifold microfluidics simulation",
    url="https://github.com/manifold-lang/pymanifold",
    project_urls={
        "Project": "https://github.com/manifold-lang",
    }
)
