import src.pymanifold as pymf

sch = pymf.Schematic(dim=[0, 0, 10, 10])

sch.port('in', 'input', fluid_name='water')
sch.port('out', 'output')
sch.channel('in', 'out', min_length=1, min_width=0.9)
model = sch.solve(show=True)
print(model)
# change the computer location below to set where you want the json data to go
#  sch.to_json("Insert your file location here")
#  sch.to_json()
