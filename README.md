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

The code to create a simple T-Junction droplet generator should look approximately as
follows, but is still early in development:

```
import pymanifold as pymf

sch = pymf.Schematic()
in1 = pymf.Input('water')
in2 = pymf.Input('oil')
out1 = pymf.Output()
n1 = pymf.Node('t-junc')
# syntax: sch.rect_channel(length, width, height, input, output)
sch.rect_channel(100, 10, 10, in1, n1, phase='continuous')
sch.rect_channel(50, 5, 5, in2, n1, phase='dispersed')
sch.rect_channel(200, 10, 10, n1, out1, phase='output')

sch.solve()

# Return: Solution found, range of flow rates: in1: [10, 40]ul/min, in2: [1, 3.2]ul/min
```


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
