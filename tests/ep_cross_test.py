import src.pymanifold as pymf

sch = pymf.Schematic([0, 0, 1, 1])
#     I
#     |
#  C--N----------A
#     |
#     W
cathode_node = 'cathode'
anode_node = 'anode'
input_node = 'in'
waste_node = 'out'
junction_node = 'ep_c'

cathode_voltage = 0
anode_voltage = 200

# syntax: sch.elec_port(name, design[, voltage, pressure, flow_rate, density, X_pos, Y_pos])
sch.elec_port(cathode_node, 'input', x=0.01, y=0.02, voltage=cathode_voltage)  # , fluid_name='water')
sch.elec_port(anode_node, 'output', x=0.1, y=0.02, voltage=anode_voltage)
# normal ports do not have voltages; syntax is otherwise the same
sch.port(input_node, 'input', x=0.02, y=0.01, fluid_name='ep_cross_test_sample')
sch.port(waste_node, 'output', x=0.02, y=0.03)

# ep_cross node
sch.node(junction_node, x=0.02, y=0.02, kind='ep_cross')

# syntax: sch.channel(shape, min_length, width, height, input, output)
sch.channel(cathode_node, junction_node, min_height=0.0002, min_width=0.00021, phase='tail')
sch.channel(junction_node, anode_node, min_height=0.0002, min_width=0.00021, min_sampling_rate=10, phase='separation')
sch.channel(input_node, junction_node, min_height=0.0002, min_width=0.00021)
sch.channel(junction_node, waste_node, min_height=0.0002, min_width=0.00021)

print(sch.solve())
