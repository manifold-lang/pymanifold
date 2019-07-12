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
docker container run -it --rm -v $(pwd):/tmp -v $(pwd)/src:/tmp/src -w /tmp -e PYTHONPATH=/tmp jsreid13/pymanifold python3 tests/t_junction_test.py
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

sch = pymf.Schematic([0, 0, 1, 1])
#       D
#       |
#   C---N---O
continuous_node = 'continuous'
dispersed_node = 'dispersed'
output_node = 'out'
junction_node = 't_j'

# Continuous and output node should have same flow rate
# syntax: sch.port(name, design[, pressure, flow_rate, density, X_pos, Y_pos])
sch.port(continuous_node, kind='input', fluid_name='mineraloil')
sch.port(dispersed_node, kind='input', fluid_name='water')
sch.port(output_node, kind='output')

# syntax: sch.node(name, X_pos, Y_pos, kind='node')
sch.node(junction_node, kind='tjunc')

# syntax: sch.channel(shape, min_length, width, height, input, output)
sch.channel(junction_node, output_node, min_height=0.0002, min_width=0.00021, phase='output')
sch.channel(continuous_node, junction_node, min_height=0.0002, min_width=0.00021, phase='continuous')
sch.channel(dispersed_node, junction_node, min_height=0.0002, min_width=0.00021, phase='dispersed')

print(sch.solve())
```

Output:\
continuous\_viscosity : [0.0003050999999999999893, 0.0003050999999999999893]\
continuous\_pressure : [500.2152984093409032, 501.8325784839180415]\
continuous\_flow\_rate : [4.696753629886489994e-08, 4.704340199341540629e-08]\
continuous\_density : [800, 800]\
continuous\_x : [0.9999999995343387127, 1]\
continuous\_y : [0, 4.635954403007642003e-11]\
dispersed\_viscosity : [0.001000000000000000021, 0.001000000000000000021]\
dispersed\_pressure : [984782.4393873409135, 984784.0566674155416]\
dispersed\_flow\_rate : [1.864071931417897898e-06, 1.864073462073317849e-06]\
dispersed\_density : [999.8700000000000045, 999.8700000000000045]\
dispersed\_x : [0.9999999995343387127, 1]\
dispersed\_y : [0, 4.635954403007642003e-11]\
out\_viscosity : [0.0003050999999999999893, 0.0003050999999999999893]\
out\_pressure : [983856.6639627817785, 983858.2812428564066]\
out\_flow\_rate : [1.911039467716762791e-06, 1.911116864066733473e-06]\
out\_density : [999.8700000000000045, 999.8700000000000045]\
out\_x : [0.9999999995343387127, 1]\
out\_y : [0, 4.635954403007642003e-11]\
t\_j\_pressure : [984373.6733107801992, 984375.2905908548273]\
t\_j\_flow\_rate : [1.911039467716762791e-06, 1.911116864066733473e-06]\
t\_j\_viscosity : [65.62503437499998427, 68.75003124999999216]\
t\_j\_density : [999.8700000000000045, 999.8700000000000045]\
t\_j\_x : [0.9999999995343387127, 1]\
t\_j\_y : [8.849630305854020956e-10, 9.313225746154785156e-10]\
t\_j\_out\_length : [1.000000000000000269e-09, 1.041250292910165269e-09]\
t\_j\_out\_width : [0.0002100000000000000087, 0.0002100000000000000087]\
t\_j\_out\_height : [0.0002000000000000000096, 0.0002000000000000000096]\
t\_j\_out\_flow\_rate : [1.911039467716762791e-06, 1.911116864066733473e-06]\
t\_j\_out\_droplet\_volume : [4.054812791117536518e-10, 4.061243617092562122e-10]\
t\_j\_out\_viscosity : [65.62503437499998427, 68.75003124999999216]\
t\_j\_out\_resistance : [270538289.0999316573, 270538292.8252219558]\
continuous\_t\_j\_length : [1.000000000000000269e-09, 1.041250292910165269e-09]\
continuous\_t\_j\_width : [0.0002100000000000000087, 0.0002100000000000000087]\
continuous\_t\_j\_height : [0.0002000000000000000096, 0.0002000000000000000096]\
continuous\_t\_j\_flow\_rate : [4.696753629886489994e-08, 4.704340199341540629e-08]\
continuous\_t\_j\_viscosity : [0.0003050999999999999893, 0.0003050999999999999893]\
continuous\_t\_j\_resistance : [588836707.1747778654, 588836709.0374230146]\
dispersed\_t\_j\_length : [1.000000000000000269e-09, 1.041250292910165269e-09]\
dispersed\_t\_j\_width : [0.0002100000000000000087, 0.0002100000000000000087]\
dispersed\_t\_j\_height : [0.0002000000000000000096, 0.0002000000000000000096]\
dispersed\_t\_j\_flow\_rate : [1.864071931417897898e-06, 1.864073462073317849e-06]\
dispersed\_t\_j\_viscosity : [0.001000000000000000021, 0.001000000000000000021]\
dispersed\_t\_j\_resistance : [473663290.9625768065, 473663292.8252219558]\
epsilon : [2.099999999999999799e-06, 2.100000000000000223e-06]\
epsilon : [2.099999999999999799e-06, 2.100000000000000223e-06]

## Development

This project is still in development, features that need to be added are:

* Create models of more components in Modelica to simulate in MapleSim
  * Produce Modelica code using [OMPython](https://github.com/OpenModelica/OMPython) 
* Create a website to outline usage using [read the docs](https://readthedocs.org/)
  * Fill in the content to match other readthedocs like [pysmt](http://pysmt.readthedocs.io)
  or [Jupyter](http://jupyter.readthedocs.io)

## Authors

* **Josh Reid** - *Creator of Python implementation* - [jsreid13](https://github.com/jsreid13)
* **Murphy Berzish** - *Creator of Manifold* - [mtrberzi](https://github.com/mtrberzi)
* **Derek Rayside** - *Owner of Manifold* - [drayside](https://github.com/drayside)
* **Chris Willar** - *Contributor to Manifold* - [cwillgit](https://github.com/cwillgit)
* **Shubham Verma** - *Contributor to Manifold* - [VermaSh](https://github.com/VermaSh)
* **Yifan Mo** - *Contributor to Manifold* - [ymo13](https://github.com/ymo13)
* **Devika Khosla** - *Contributor to Manifold* - [DevikaKhosla](https://github.com/DevikaKhosla)
* **Ali Abdullah** - *Contributor to Manifold* - [ali-abdullah](https://github.com/ali-abdullah)
* **Tyson Andre** - *Contributor to Manifold* - [TysonAndre](https://github.com/TysonAndre)
* **Max Chen** - *Contributor to Manifold* - [maxqchen](https://github.com/maxqchen)
* **Nik Klassen** - *Contributor to Manifold* - [nikklassen](https://github.com/nikklassen)
* **Peter Socha** - *Contributor to Manifold* - [psocha](https://github.com/psocha)

## License

This project is licensed under the GNU General Public License v3.0 - see the
[LICENSE](LICENSE) file for details
