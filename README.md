# pymanifold

<table>
<tr>
  <td>Build Status</td>
  <td>
    <a href="https://circleci.com/gh/manifold-lang/pymanifold/tree/master">
    <img src="https://circleci.com/gh/manifold-lang/pymanifold/tree/master.svg?style=svg" alt="CircleCI build status" />
    </a>
  </td>
</tr>
</table>

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
However this will require building [dReal4 from source](https://github.com/dreal/dreal4) 
and installing OMPython from [GitHub](https://github.com/OpenModelica/OMPython) along
with [OpenModelica](https://openmodelica.org/) if you need electrical simulations, 
alternatively we provide a Docker image which contains all of these libraries baked in.
You can get the docker image by running:
``` 
docker pull jsreid13/pymanifold:latest 
```
Run the single\_channel\_test,py script within this image using:
```
docker container run -it --rm -v $(pwd):/tmp -v $(pwd)/src:/tmp/src -w /tmp -e PYTHONPATH=/tmp pymanifold:pip python3 tests/t_junction_test.py
```
_Note: You need to run this command in your terminal while in the root of this repository_

Any script within this repo can be run using this command, to run your own script you need to
change the directory that you run this command from within your terminal to the directory 
containing that script and change *tests/single_channel_test.py* to the name of your script

## Usage
The code to create a simple T-Junction droplet generator is as follows found in this
[test script](src/t_junction_test.py), but is still in development:

```python
import src.pymanifold as pymf

sch = pymf.Schematic([0, 0, 10, 10])
#       D
#       |
#   C---N---O
continuous_node = 'continuous'
dispersed_node = 'dispersed'
output_node = 'out'
junction_node = 't_j'

# Continuous and output node should have same flow rate
# syntax: sch.port(name, design[, pressure, flow_rate, density, X_pos, Y_pos])
sch.port(continuous_node, 'input', min_pressure=1, fluid_name='mineraloil')
sch.port(dispersed_node, 'input', min_pressure=1, fluid_name='water')
sch.port(output_node, 'output')

# syntax: sch.node(name, X_pos, Y_pos, kind='node')
sch.node(junction_node, 1, 0, kind='t-junction')

# syntax: sch.channel(shape, min_length, width, height, input, output)
sch.channel(junction_node, output_node, phase='output')
sch.channel(continuous_node, junction_node, phase='continuous')
sch.channel(dispersed_node, junction_node, phase='dispersed')

print(sch.solve())
```
Output:\
continuous_viscosity : [4.494232837155789769e+307, 4.494232837155789769e+307]\
continuous_pressure : [1, 1]\
continuous_flow_rate : [1.518258991506101335e-158, 1.518258991506101538e-158]\
continuous_density : [1.797693134862315708e+308, 1.797693134862315708e+308]\
continuous_x : [8.281615407309315018e-12, 9.937377602372895258e-12]\
continuous_y : [5, 5.000000000003019807]\
dispersed_viscosity : [4.494232837155789769e+307, 4.494232837155789769e+307]\
dispersed_pressure : [1, 1]\
dispersed_flow_rate : [2.101318454051882251e-158, 2.101318454051882655e-158]\
dispersed_density : [1.35216994135785263e+308, 1.35216994135785263e+308]\
dispersed_x : [4.999999999996980193, 5]\
dispersed_y : [9.999999999996980193, 10]\
out_viscosity : [4.494232837155789769e+307, 4.494232837155789769e+307]\
out_pressure : [1.797693134862315708e+308, 1.797693134862315708e+308]\
out_flow_rate : [3.619577445557983788e-158, 3.619577445557984193e-158]\
out_density : [3.370674627866841329e+307, 3.370674627866841329e+307]\
out_x : [2.500406901035603369, 2.500406901037877105]\
out_y : [7.499594818069040159, 7.499594818071313895]\
t_j_pressure : [1.797693134862315509e+308, 1.797693134862315509e+308]\
t_j_viscosity : [4.494232837155789769e+307, 4.494232837155789769e+307]\
t_j_density : [3.370674627866841329e+307, 3.370674627866841329e+307]\
t_j_x : [3.31275985767466778e-12, 6.331823954042192781e-12]\
t_j_y : [4.999999999993668176, 4.999999999996687983]\
t_j_out_width : [0.4993559777345346617, 0.4993559777345347173]\
t_j_out_height : [0.0003451038031080025511, 0.0003451038031080026053]\
t_j_out_flow_rate : [3.619577445557983788e-158, 3.619577445557984193e-158]\
t_j_out_droplet_volume : [1.741515224397868536e+308, 1.741515224397868536e+308]\
t_j_out_resistance : [-1.741515224397868536e+308, -1.741515224397868536e+308]\
continuous_t_j_length : [6.624617698794350717e-12, 6.624617698794351525e-12]\
continuous_t_j_width : [0.4993559777345346617, 0.4993559777345347173]\
continuous_t_j_height : [0.0003451038031080025511, 0.0003451038031080026053]\
continuous_t_j_flow_rate : [1.518258991506101335e-158, 1.518258991506101538e-158]\
continuous_t_j_viscosity : [4.494232837155789769e+307, 4.494232837155789769e+307]\
continuous_t_j_resistance : [1.741515224397868536e+308, 1.741515224397868536e+308]\
dispersed_t_j_length : [7.071067811865476394, 7.071067811865477282]\
dispersed_t_j_width : [0.5006598565867919071, 0.5006598565867920181]\
dispersed_t_j_height : [0.0003451038031080025511, 0.0003451038031080026053]\
dispersed_t_j_flow_rate : [2.101318454051882251e-158, 2.101318454051882655e-158]\
dispersed_t_j_viscosity : [4.494232837155789769e+307, 4.494232837155789769e+307]\
dispersed_t_j_resistance : [1.797693134862315708e+308, 1.797693134862315708e+308]\
epsilon : [1.685337313933419667e+307, 1.685337313933419667e+307]\
epsilon : [1.797693134862315708e+308, 1.797693134862315708e+308]

## Development

This project is still in development, features that need to be added are:

* Add an elecrophoretic cross as a new node type with voltages at two ends and pressure driven flow on
the other two short ends. Steps:
  * Create a new translate method named translate\_ep\_cross
    * This requires 4 connections, two must have a voltage constraint and the other two have a pressure
	constraint
	  * This will require the creation of a new port type that is a voltage input, currently only
	  fluid injection ports exist with a pressure and flow rate, this will have a voltage and no flow
	* Needs to append correct SMT expressions based on those in Stephen Chou's report to simulate an
	electropheretic cross(EP cross) https://drive.google.com/open?id=1UF-Jun4-ppJHyb1wMQFqFzaUNbZSdkzl
  * Add the name of that translation method to the translate\_nodes under the name ep\_cross
* Feature to output electrical characteristics of chip to MapleSim(or something similar)
  * Produce Modelica code using [OMPython](https://github.com/OpenModelica/OMPython) 
  to feed into MapleSim
* Create a website to outline usage using [read the docs](https://readthedocs.org/)
  * Fill in the content to match other readthedocs like [pysmt](http://pysmt.readthedocs.io)
  or [Jupyter](http://jupyter.readthedocs.io)
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
