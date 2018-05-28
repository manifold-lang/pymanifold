import pymanifold as pymf
from pprint import pprint

sch = pymf.Schematic()

sch.port('in', 'input', min_pressure=100, min_viscosity=0.00089)
sch.port('out', 'output')
sch.channel(0.01, 0.01, 0.01, 'in', 'out')
model = sch.solve()
print(model)
