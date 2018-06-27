import pymanifold as pymf 

sch = pymf.Schematic([0, 0 , 10, 10])

sch.port('in', 'input', min_pressure=100, fluid_name='water')
sch.port('out', 'output')
sch.channel('in', 'out', min_length=1, min_width=0.9)

sch.node('abc', x=6, y=7, kind='t-junction')

print(sch.get_channel_kind('in', 'out'))