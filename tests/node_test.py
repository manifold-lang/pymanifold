import src.pymanifold as pymf

sch = pymf.Schematic(dim=[0, 0, 10, 10])

sch.port('in', 'input', x=0.03, y=0.03, fluid_name='water')
sch.port('out', 'output', x=0.01, y=0.01)
sch.node('middle node', x=0.03, y=0.01)
sch.channel('in', 'middle node', min_length=0.02, min_width=0.009)
sch.channel('middle node', 'out', min_width=0.009)
model = sch.solve(show=True)
print(model)


def test_answer():
    assert model != "No solution found"
