import pymanifold as pymf
from pprint import pprint

sch = pymf.Schematic()

sch.port('in', 'input', min_pressure=100)
sch.port('out', 'output', min_pressure=100)
sch.channel(0.01, 0.01, 0.01, 'in', 'out')
model = sch.solve(show=True)
print(model)
