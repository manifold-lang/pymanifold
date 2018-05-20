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

### Prerequisites

This library requires installaion of [pysmt](https://github.com/pysmt/pysmt), an SMT
solver library for python used to determine if the designed microfluidic circuit will
work and if so within what range of parameters.

Once this is installed (remember to call ``` pysmt-install --z3 ``` to install the
Z3 SMT solver within pysmt so it has a solver to use to solve the SMT2 equations this
library generates) then you can use this library.

### Installing

Currently this is not on pip so to use it clone the repository using ```
git clone https://github.com/jsreid13/pymanifold.git ``` and put the project within
your python3 site packages (C:\\python35\Lib\site-packages on Windows, 
/usr/local/lib/python3.5/dist-packages on Linux).

## Usage

The code to create a simple T-Junction droplet generator is as follows found in this
[test script](src/test.py), but is still in development:

```
sch = pymf.Schematic()
#       D
#       |
#   C---N---O
continuous_node = 'continuous'
dispersed_node = 'dispersed'
output_node = 'out'
junction_node = 't-j'
# Continuous and output node should have same flow rate
# syntax: sch.port(name, design, pressure, flow_rate, X_pos, Y_pos)
sch.port(continuous_node, 'input', 2, 5, 0, 0)
sch.port(dispersed_node, 'input', 2, 2, 1, 1)
sch.port(output_node, 'output', 2, 5, 2, 0)
sch.node(junction_node, 't-junction', 2, 1, 0)
# syntax: sch.channel(shape, min length, width, height, input, output)
sch.channel('rectangle', 0.5, 0.1, 0.1, continuous_node,
            junction_node, phase='continuous')
sch.channel('rectangle', 0.5, 0.1, 0.1, dispersed_node,
            junction_node, phase='continuous')
sch.channel('rectangle', 0.5, 0.1, 0.1, junction_node,
            output_node, phase='continuous')

sch.solve()


# Return: Solution found, range of flow rates: in1: [10, 40]ul/min, in2: [1, 3.2]ul/min
```

## Development

This project is still in development, features that need to be added are:

* Add an elecrophoretic cross as a new node type with voltages at two ends
* Feature to output electrical characteristics of chip to maple
* Create a to_json method to convert designed schematic to a json file following Manifold IR grammar
* Gather a database of real world microfluidic chip designs and information about their output
* Implement a machine learning algorithm on this database to improve the library's accuracy in
determining if different designed will work
* Put this library on pip to simplify installation, and create a website to outline usage using
[read the docs](https://readthedocs.org/)

## Authors

* **Josh Reid** - *Creator of Python implementation* - [jsreid13](https://github.com/jsreid13)
* **Murphy Berzish** - *Creator of Manifold* - [mtrberzi](https://github.com/mtrberzi)
* **Derek Rayside** - *Owner of Manifold* - [drayside](https://github.com/drayside)
* **Tyson Andre** - *Contributor to Manifold* - [TysonAndre](https://github.com/TysonAndre)
* **Max Chen** - *Contributor to Manifold* - [maxqchen](https://github.com/maxqchen)
* **Nik Klassen** - *Contributor to Manifold* - [nikklassen](https://github.com/nikklassen)
* **Peter Socha** - *Contributor to Manifold* - [psocha](https://github.com/psocha)

## License

This project is licensed under the GNU General Public License v3.0 - see the
[LICENSE](LICENSE) file for details
