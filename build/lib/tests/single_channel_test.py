import sys
import os
path = os.path.dirname(os.path.realpath(__file__)) + "/.."
print(path)
sys.path.append(path)
from src import pymanifold as pymf
from pprint import pprint

sch = pymf.Schematic(dim=[0, 0, 10, 10])


sch.port('in', 'input', min_pressure=100, min_viscosity=0.00089, density=1)
sch.port('out', 'output')
sch.channel('in', 'out', min_length=1, min_width=0.9)
model = sch.solve()
print(model)
