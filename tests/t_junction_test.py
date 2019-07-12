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

#  sch.solve()
model = sch.solve(show=True)
print(model)


def test_answer():
    assert model != "No solution found"
