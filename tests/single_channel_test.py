import src.pymanifold as pymf

sch = pymf.Schematic(dim=[0, 0, 10, 10])


sch.port('in', 'input', min_pressure=100, fluid_name='water')
sch.port('out', 'output')
sch.channel('in', 'out', min_length=1, min_width=0.9)
model = sch.solve()
print(model)
