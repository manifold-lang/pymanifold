import pymanifold as pymf

sch = pymf.Schematic()
#       D
#       |
#   C---N---O
continuous_node = 'continuous'
dispersed_node = 'dispersed'
output_node = 'out'
junction_node = 't_j'
# Continuous and output node should have same flow rate
# syntax: sch.port(name, design, pressure, flow_rate, X_pos, Y_pos)
sch.port(continuous_node, 'input', 2, 7, 0, 0)
sch.port(dispersed_node, 'input', 2, 7, 1, 1)
sch.port(output_node, 'output', 1013, 5, 2, 0)
sch.node(junction_node, 2, 1, 0, kind='t-junction')
# syntax: sch.channel(shape, min_length, width, height, input, output)
sch.channel('rectangle', 0.5, 0.1, 0.1, continuous_node,
            junction_node, phase='continuous')
sch.channel('rectangle', 0.5, 0.1, 0.1, dispersed_node,
            junction_node, phase='dispersed')
sch.channel('rectangle', 0.5, 0.1, 0.1, junction_node,
            output_node, phase='output')

print(sch.solve())
