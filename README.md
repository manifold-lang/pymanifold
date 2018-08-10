# pymanifold
Python implementation of the Manifold microfluidic simulation language

This library allows you to design a microfluidic circuit as a schematic consisting of:

* **Nodes** - consist of elementary devices such as logic gates or fluid input channels
* **Connections** - connect two nodes together
* **Ports** - a type of node that allows for the input or output of fluids
* **Constraints** - describe design rules or goals that are too complex to be described
in terms of the other three primitives

Once the circuit has been designed you can call solve on the schematic which will use
a Satisfiability Modulo Theory (SMT) solver to determine if the given design and
parameters has a solution (meaning that the circuit will work) and if so, provide
the range of parameters (dimensions of the connections, flow rates, pressures, etc.)
that the circuit will remain functional

## Getting Started

These instructions will get you a copy of the project up and running on your local
machine for development and testing purposes.

### Installing

This can be installed within Python 3 using ` pip install --user pymanifold `
However this will require building dReal4 from source and OMPython from [GitHub](https://github.com/OpenModelica/OMPython) and [OpenModelica](https://openmodelica.org/), alternatively we provide a Docker image which contains all of these libraries baked in.
Build the docker image using in the base directory of this repo:
` docker build -t pymanifold . `
or clone using ` docker pull jsreid13/pymanifold:latest `
And run the project within Docker using in the root folder off of pyManifold's Repo:
` docker run -it --rm -v $(pwd):/tmp -w /tmp  pymanifold python3 src/pymanifold.py `
For access to OpenModelica on top of pymanifold, run:
` docker container run -it --user $(id -u):$(id -g) --rm pymf-om:jessie bash `

## Usage
The code to create a simple T-Junction droplet generator is as follows found in this
[test script](src/test.py), but is still in development:

```
import pymanifold as pymf

sch = pymf.Schematic()
#       D
#       |
#   C---N---O
continuous_node = 'continuous'
dispersed_node = 'dispersed'
output_node = 'out'
junction_node = 't_j'
# Continuous and output node should have same flow rate
# syntax: sch.port(name, design, pressure, flow_rate, X_pos, Y_pos)
sch.port(continuous_node, 'input', 2, 5, 0, 0)
sch.port(dispersed_node, 'input', 2, 2, 1, 1)
sch.port(output_node, 'output', 2, 5, 2, 0)
sch.node(junction_node, 2, 1, 0, kind='t-junction')
# syntax: sch.channel(shape, min_length, width, height, input, output)
sch.channel('rectangle', 0.5, 0.1, 0.1, continuous_node,
            junction_node, phase='continuous')
sch.channel('rectangle', 0.5, 0.1, 0.1, dispersed_node,
            junction_node, phase='dispersed')
sch.channel('rectangle', 0.5, 0.1, 0.1, junction_node,
            output_node, phase='output')

print(sch.solve())

# Return: Model object from dReal with dictionary like mapping of each variable to a range of values
```

## Development

This project is still in development, features that need to be added are:

* Add an elecrophoretic cross as a new node type with voltages at two ends and pressure driven flow on
the other two short ends. Steps:
  * Create a new translate method named translate_ep_cross
    * This requires 4 connections, two must have a voltage constraint and the other two have a pressure
	constraint
	  * This will require the creation of a new port type that is a voltage input, currently only
	  fluid injection ports exist with a pressure and flow rate, this will have a voltage and no flow
	* Needs to append correct SMT expressions based on those in Stephen Chou's report to simulate an
	electropheretic cross(EP cross) https://drive.google.com/open?id=1UF-Jun4-ppJHyb1wMQFqFzaUNbZSdkzl
  * Add the name of that translation method to the translate_nodes under the name ep_cross
* Feature to output electrical characteristics of chip to MapleSim(or something similar)
  * Possibly use this library from Dassault Systems [FMPy](https://github.com/CATIA-Systems/FMPy)
  * Or produce Modelica code using [OMPython](https://github.com/OpenModelica/OMPython) 
  to feed into MapleSim
* Create a website to outline usage using [read the docs](https://readthedocs.org/)
  * Fill in the content to match other readthedocs like [pysmt](http://pysmt.readthedocs.io)
  or [Jupyter](http://jupyter.readthedocs.io)
* Put this library on pip to simplify installation
* Gather a database of real world microfluidic chip designs and information about their output
* Implement a machine learning algorithm on this database to improve the library's accuracy in
determining if different designs will work
* Implement abstraction refinement from original project

## Authors

* **Josh Reid** - *Creator of Python implementation* - [jsreid13](https://github.com/jsreid13)
* **Murphy Berzish** - *Creator of Manifold* - [mtrberzi](https://github.com/mtrberzi)
* **Derek Rayside** - *Owner of Manifold* - [drayside](https://github.com/drayside)
* **Chris Willar** - *Contributor to Manifold* - [cwillgit](https://github.com/cwillgit)
* **Shubham Verma** - *Contributor to Manifold* - [VermaSh](https://github.com/VermaSh)
* **Yifan Mo** - *Contributor to Manifold* - [ymo13](https://github.com/ymo13)
* **Tyson Andre** - *Contributor to Manifold* - [TysonAndre](https://github.com/TysonAndre)
* **Max Chen** - *Contributor to Manifold* - [maxqchen](https://github.com/maxqchen)
* **Nik Klassen** - *Contributor to Manifold* - [nikklassen](https://github.com/nikklassen)
* **Peter Socha** - *Contributor to Manifold* - [psocha](https://github.com/psocha)

## License

This project is licensed under the GNU General Public License v3.0 - see the
[LICENSE](LICENSE) file for details
