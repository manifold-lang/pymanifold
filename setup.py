import os
from setuptools import setup, find_packages

README_PATH = "README.md"
LONG_DESC = ""
if os.path.exists(README_PATH):
    with open(README_PATH) as readme:
        LONG_DESC = readme.read()

INSTALL_REQUIRES = ["networkx", "matplotlib"]
PACKAGE_NAME = "pymanifold"
PACKAGE_DIR = "src"

setup(
    name=PACKAGE_NAME,
    version="0.2.3",

    package_dir={PACKAGE_NAME: "src"},
    packages=[PACKAGE_NAME],

    # This project requires matplotlib to show the designed microfluidic
    # circuit and dReal SMT solver, however it's Python3 support is still
    # experimental so you need to build it from source or use the docker image
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
