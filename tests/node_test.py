import src.pymanifold as pymf

sch = pymf.Schematic(dim=[0, 0, 10, 10])

sch.port('in', 'input', x=3, y=3, fluid_name='water')
sch.port('out', 'output', x=1, y=1)
sch.node('middle node', x=3, y=1)
sch.channel('in', 'middle node', min_length=2, min_width=0.9)
sch.channel('middle node', 'out', min_width=0.9)
model = sch.solve(show=True)
print(model)
