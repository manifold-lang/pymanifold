import src.pymanifold as pymf

sch = pymf.Schematic([0, 0, 10, 10])
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

min_channel_length = 1
min_channel_width = 1
min_channel_height = 0.001
cathode_voltage = 0
anode_voltage = 2

# syntax: sch.elec_port(name, design[, voltage, pressure, flow_rate, density, X_pos, Y_pos])
sch.elec_port(cathode_node, 'input', voltage=cathode_voltage, min_pressure=1) #, fluid_name='mineraloil')
sch.elec_port(anode_node, 'output', voltage=anode_voltage)
# normal ports do not have voltages; syntax is otherwise the same
sch.port(input_node, 'input', min_pressure=1, fluid_name='ep_cross_test_sample')
sch.port(waste_node, 'output')

# ep_cross node
sch.node(junction_node, 1, 1, kind='ep_cross')

# syntax: sch.channel(shape, min_length, width, height, input, output)
sch.channel(cathode_node, junction_node,
			phase = 'tail')
sch.channel(junction_node, anode_node,
			phase = 'separation')
sch.channel(input_node, junction_node)
sch.channel(junction_node, waste_node)

print(sch.solve())
