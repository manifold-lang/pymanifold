import src.pymanifold as pymf

sch = pymf.Schematic(dim=[0, 0, 10, 10])

sch.port('in', kind='input', x=0.02, y=0.01, min_pressure=50, fluid_name='water')
sch.port('out', kind='output', x=0.03, y=0.02)
sch.channel('in', 'out')
model = sch.solve(show=True)
print(model)
# change the computer location below to set where you want the json data to go
#  sch.to_json("Insert your file location here")
#  sch.to_json()


def test_answer():
    assert model != "No solution found"
