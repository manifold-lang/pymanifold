import pymanifold as pymf

sch = pymf.Schematic()
#       D
#       |
#   C---N---O
continuous_node = 'continuous'
dispersed_node = 'dispersed'
output_node = 'out'
junction_node = 't_j'
min_channel_length = 0.01
min_channel_width = 0.001
min_channel_height = 0.001

# Continuous and output node should have same flow rate
# syntax: sch.port(name, design, pressure, flow_rate, X_pos, Y_pos)
sch.port(continuous_node, 'input', 2, 7, 0, 0)
sch.port(dispersed_node, 'input', 2, 7, 1, 1)
sch.port(output_node, 'output', 1013, 7, 2, 0)

# syntax: sch.node(name, X_pos, Y_pos, kind='node')
sch.node(junction_node, 1, 0, kind='t-junction')

# syntax: sch.channel(shape, min_length, width, height, input, output)
sch.channel('rectangle',
            min_channel_length,
            min_channel_width,
            min_channel_height,
            continuous_node,
            junction_node,
            phase='continuous'
            )
sch.channel('rectangle',
            min_channel_length,
            min_channel_width,
            min_channel_height,
            dispersed_node,
            junction_node,
            phase='dispersed'
            )
sch.channel('rectangle',
            min_channel_length,
            min_channel_width,
            min_channel_height,
            junction_node,
            output_node,
            phase='output'
            )

print(sch.solve(show=True))
