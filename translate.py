import math
import networkx as nx
import algorithms
from dreal.symbolic import Variable, logical_and


def translate_chip(dg, name, dim):
    """Create SMT expressions for bounding the nodes to be within constraints
    of the overall chip such as its area provided

    :param name: Name of the node to be constrained
    :returns: None -- no issues with translating the chip constraints
    """
    exprs = []
    exprs.append(algorithms.retrieve(dg, name, 'x') >= dim[0])
    exprs.append(algorithms.retrieve(dg, name, 'y') >= dim[1])
    exprs.append(algorithms.retrieve(dg, name, 'x') <= dim[2])
    exprs.append(algorithms.retrieve(dg, name, 'y') <= dim[3])
    return exprs


def translate_node(dg, name):
    """Create SMT expressions for bounding the parameters of an node
    to be within the constraints defined by the user

    :param name: Name of the node to be constrained
    :returns: None -- no issues with translating the port parameters to SMT
    """
    exprs = []
    # Pressure at a node is the sum of the pressures flowing into it
    output_pressures = []
    for node_name in dg.pred[name]:
        # This returns the nodes with channels that flowing into this node
        # pressure calculated based on P=QR
        # Could modify equation based on
        # https://www.dolomite-microfluidics.com/wp-content/uploads/
        # Droplet_Junction_Chip_characterisation_-_application_note.pdf
        output_pressures.append(algorithms.channel_output_pressure(dg, (node_name, name)))
    if len(dg.pred[name]) == 1:
        exprs.append(algorithms.retrieve(dg, name, 'pressure') == output_pressures[0])
    elif len(dg.pred[name]) > 1:
        output_pressure_formulas = [a + b for a, b in
                                    zip(output_pressures,
                                        output_pressures[1:])]
        exprs.append(algorithms.retrieve(dg, name, 'pressure') ==
                     logical_and(*output_pressure_formulas))

    # If parameters are provided by the user, then set the
    # their Variable equal to that value, otherwise make it greater than 0
    if algorithms.retrieve(dg, name, 'min_pressure'):
        # If min_pressure has a value then a user defined value was provided
        # and this variable is set equal to this value, else simply set its
        # value to be >0, same for viscosity, pressure, flow_rate, X, Y and density
        exprs.append(algorithms.retrieve(dg, name, 'pressure') ==
                     algorithms.retrieve(dg, name, 'min_pressure'))
    else:
        exprs.append(algorithms.retrieve(dg, name, 'pressure') > 0)

    if algorithms.retrieve(dg, name, 'min_density'):
        exprs.append(algorithms.retrieve(dg, name, 'x') ==
                     algorithms.retrieve(dg, name, 'min_x'))
        exprs.append(algorithms.retrieve(dg, name, 'y') ==
                     algorithms.retrieve(dg, name, 'min_y'))
    else:
        exprs.append(algorithms.retrieve(dg, name, 'x') >= 0)
        exprs.append(algorithms.retrieve(dg, name, 'y') >= 0)

    if algorithms.retrieve(dg, name, 'min_flow_rate'):
        exprs.append(algorithms.retrieve(dg, name, 'flow_rate') ==
                     algorithms.retrieve(dg, name, 'min_flow_rate'))
    else:
        exprs.append(algorithms.retrieve(dg, name, 'flow_rate') > 0)
    if algorithms.retrieve(dg, name, 'min_viscosity'):
        exprs.append(algorithms.retrieve(dg, name, 'viscosity') ==
                     algorithms.retrieve(dg, name, 'min_viscosity'))
    else:
        exprs.append(algorithms.retrieve(dg, name, 'viscosity') > 0)

    if algorithms.retrieve(dg, name, 'min_density'):
        exprs.append(algorithms.retrieve(dg, name, 'density') ==
                     algorithms.retrieve(dg, name, 'min_density'))
    else:
        exprs.append(algorithms.retrieve(dg, name, 'density') > 0)
    return exprs


def translate_input(dg, name):
    """Create SMT expressions for bounding the parameters of an input port
    to be within the constraints defined by the user

    :param name: Name of the port to be constrained
    :returns: None -- no issues with translating the port parameters to SMT
    """
    exprs = []
    if dg.size(name) <= 0:
        raise ValueError("Port %s must have 1 or more connections" % name)
    # Currently don't support this, and I don't think it would be the case
    # in real circuits, an input port is the beginning of the traversal
    if len(list(dg.predecessors(name))) != 0:
        raise ValueError("Cannot have channels into input port %s" % name)

    # If input is a type of node, call translate node
    translate_node(dg, name)

    # Calculate flow rate for this port based on pressure and channels out
    # if not specified by user
    if not algorithms.retrieve(dg, name, 'min_flow_rate'):
        flow_rate = algorithms.calculate_port_flow_rate(dg, name)
        exprs.append(algorithms.retrieve(dg, name, 'flow_rate') == flow_rate)

    # To recursively traverse, call on all successor channels
    for node_out in dg.succ[name]:
        translation_strats[
            algorithms.retrieve(dg, (name, node_out), 'kind')](dg, (name, node_out))
    return exprs


def translate_output(dg, name):
    """Create SMT expressions for bounding the parameters of an output port
    to be within the constraints defined by the user

    :param str name: Name of the port to be constrained
    :returns: None -- no issues with translating the port parameters to SMT
    """
    exprs = []
    if dg.size(name) <= 0:
        raise ValueError("Port %s must have 1 or more connections" % name)
    # Currently don't support this, and I don't think it would be the case
    # in real circuits, an output port is considered the end of a branch
    if len(list(dg.succ[name])) != 0:
        raise ValueError("Cannot have channels out of output port %s" % name)

    # Since input is just a specialized node, call translate node
    translate_node(dg, name)

    # Calculate flow rate for this port based on pressure and channels out
    # if not specified by user
    if not algorithms.retrieve(dg, name, 'min_flow_rate'):
        # The flow rate at this node is the sum of the flow rates of the
        # the channel coming in (I think, should be verified)
        total_flow_in = []
        for channel_in in dg.pred[name]:
            total_flow_in.append(dg.edges[(channel_in, name)]
                                 ['flow_rate'])
        if len(total_flow_in) == 1:
            exprs.append(algorithms.retrieve(dg, name, 'flow_rate') == total_flow_in[0])
        else:
            total_flow_in_formulas = [a + b for a, b in
                                      zip(total_flow_in, total_flow_in[1:])]
            exprs.append(algorithms.retrieve(dg, name, 'flow_rate') ==
                         logical_and(*total_flow_in_formulas))
    return exprs


# TODO: Refactor to use different formulas depending on the kind of the channel
def translate_channel(dg, name):
    """Create SMT expressions for a given channel (edges in NetworkX naming)
    currently only works for channels with a rectangular shape, but should
    be expanded to include circular and parabolic

    :param str name: The name of the channel to generate SMT equations for
    :returns: None -- no issues with translating channel parameters to SMT
    :raises: KeyError, if channel is not found in the list of defined edges
    """
    exprs = []
    try:
        dg.edges[name]
    except KeyError:
        raise KeyError('Channel with ports %s was not defined' % name)

    # Create expression to force length to equal distance between end nodes
    exprs.append(algorithms.pythagorean_length(dg, name))

    # Set the length determined by pythagorean theorem equal to the user
    # provided number if provided, else assert that the length be greater
    # than 0, same for width and height
    if algorithms.retrieve(dg, name, 'min_length'):
        exprs.append(algorithms.retrieve(dg, name, 'length') ==
                     algorithms.retrieve(dg, name, 'min_length'))
    else:
        exprs.append(algorithms.retrieve(dg, name, 'length') > 0)
    if algorithms.retrieve(dg, name, 'min_width'):
        exprs.append(algorithms.retrieve(dg, name, 'width') ==
                     algorithms.retrieve(dg, name, 'min_width'))
    else:
        exprs.append(algorithms.retrieve(dg, name, 'width') > 0)
    if algorithms.retrieve(dg, name, 'min_height'):
        exprs.append(algorithms.retrieve(dg, name, 'height') ==
                     algorithms.retrieve(dg, name, 'min_height'))
    else:
        exprs.append(algorithms.retrieve(dg, name, 'height') > 0)

    # Assert that viscosity in channel equals input node viscosity
    # Set output viscosity to equal input since this should be constant
    # This must be performed before calculating resistance
    exprs.append(algorithms.retrieve(dg, name, 'viscosity') ==
                 algorithms.retrieve(dg, algorithms.retrieve(dg, name, 'port_from'), 'viscosity'))
    exprs.append(algorithms.retrieve(dg, algorithms.retrieve(dg, name, 'port_to'), 'viscosity') ==
                 algorithms.retrieve(dg, algorithms.retrieve(dg, name, 'port_from'), 'viscosity'))

    # Pressure at end of channel is lower based on the resistance of
    # the channel as calculated by calculate_channel_resistance and
    # pressure_out = pressure_in * (flow_rate * resistance)
    resistance_list = algorithms.calculate_channel_resistance(dg, name)

    # First term is assertion that each channel's height is less than width
    # which is needed to make resistance formula valid, second is the SMT
    # equation for the resistance, then assert resistance is >0
    exprs.append(resistance_list[0])
    resistance = resistance_list[1]
    exprs.append(algorithms.retrieve(dg, name, 'resistance') == resistance)
    exprs.append(algorithms.retrieve(dg, name, 'resistance') > 0)

    # Assert flow rate equal to the flow rate coming in
    exprs.append(algorithms.retrieve(dg, name, 'flow_rate') ==
                 algorithms.retrieve(dg, algorithms.retrieve(dg, name, 'port_from'), 'flow_rate'))

    # Channels do not have pressure because it decreases across channel
    # Call translate on the output to continue traversing the channel
    translation_strats[algorithms.retrieve(dg,
        algorithms.retrieve(dg, name, 'port_to'), 'kind')](dg, algorithms.retrieve(dg, name, 'port_to'))
    return exprs


def translate_tjunc(dg, name, crit_crossing_angle=0.5):
    """Create SMT expressions for a t-junction node that generates droplets
    Must have 2 input channels (continuous and dispersed phases) and one
    output channel where the droplets leave the node. Continuous is usually
    oil and dispersed is usually water

    :param str name: The name of the channel to generate SMT equations for
    :param crit_crossing_angle: The angle of the dispersed channel to
        the continuous must be great than this to have droplet generation
    :returns: None -- no issues with translating channel parameters to SMT
    :raises: KeyError, if channel is not found in the list of defined edges
    """
    exprs = []
    # Validate input
    if dg.size(name) != 3:
        raise ValueError("T-junction %s must have 3 connections" % name)

    # Since T-junction is just a specialized node, call translate node
    translate_node(dg, name)

    # Renaming for consistency with the other nodes
    junction_node_name = name
    # Since there should only be one output node, this can be found first
    # from the dict of successors
    try:
        output_node_name = list(dict(dg.succ[name]).keys())[0]
        output_channel_name = (junction_node_name, output_node_name)
    except KeyError as e:
        raise KeyError("T-junction must have only one output")
    # these will be found later from iterating through the dict of
    # predecessor nodes to the junction node
    continuous_node_name = ''
    continuous_channel_name = ''
    dispersed_node_name = ''
    dispersed_channel_name = ''

    # NetworkX allows for the creation of dicts that contain all of
    # the edges containing a certain attribute, in this case phase is
    # of interest
    phases = nx.get_edge_attributes(dg, 'phase')
    for pred_node, phase in phases.items():
        if phase == 'continuous':
            continuous_node_name = pred_node[0]
            continuous_channel_name = (continuous_node_name, junction_node_name)
            # assert width and height to be equal to output
            exprs.append(algorithms.retrieve(dg, continuous_channel_name, 'width') ==
                         algorithms.retrieve(dg, output_channel_name, 'width'))
            exprs.append(algorithms.retrieve(dg, continuous_channel_name, 'height') ==
                         algorithms.retrieve(dg, output_channel_name, 'height'))
        elif phase == 'dispersed':
            dispersed_node_name = pred_node[0]
            dispersed_channel_name = (dispersed_node_name, junction_node_name)
            # Assert that only the height of channel be equal
            exprs.append(algorithms.retrieve(dg, dispersed_channel_name, 'height') ==
                         algorithms.retrieve(dg, output_channel_name, 'height'))
        elif phase == 'output':
            continue
        else:
            raise ValueError("Invalid phase for T-junction: %s" % name)

    # Epsilon, sharpness of T-junc, must be greater than 0
    epsilon = Variable('epsilon')
    exprs.append(epsilon >= 0)

    # TODO: Figure out why original had this cause it doesn't seem true
    #  # Pressure at each of the 4 nodes must be equal
    #  exprs.append(Equals(junction_node['pressure'],
    #                           continuous_node['pressure']
    #                           ))
    #  exprs.append(Equals(junction_node['pressure'],
    #                           dispersed_node['pressure']
    #                           ))
    #  exprs.append(Equals(junction_node['pressure'],
    #                           output_node['pressure']
    #                           ))

    # Viscosity in continous phase equals viscosity at output
    exprs.append(algorithms.retrieve(dg, continuous_node_name, 'viscosity') ==
                 algorithms.retrieve(dg, output_node_name, 'viscosity'))

    # Flow rate into the t-junction equals the flow rate out
    exprs.append(algorithms.retrieve(dg, continuous_channel_name, 'flow_rate') +
                 algorithms.retrieve(dg, dispersed_channel_name, 'flow_rate') ==
                 algorithms.retrieve(dg, output_channel_name, 'flow_rate'))

    # Assert that continuous and output channels are in a straight line
    exprs.append(algorithms.channels_in_straight_line(dg,
                                                      continuous_node_name,
                                                      junction_node_name,
                                                      output_node_name
                                                      ))

    # Droplet volume in channel equals calculated droplet volume
    # TODO: Manifold also has a table of constraints in the Schematic and
    # sets ChannelDropletVolume equal to dropletVolumeConstraint, however
    # the constraint is void (new instance of RealTypeValue) and I think
    # could conflict with calculated value, so ignoring it for now but
    # may be necessary to add at a later point if I'm misunderstand why
    # its needed
    exprs.append(algorithms.retrieve(dg, output_channel_name, 'droplet_volume') ==
                 algorithms.calculate_droplet_volume(
                     dg,
                     algorithms.retrieve(dg, output_channel_name, 'height'),
                     algorithms.retrieve(dg, output_channel_name, 'width'),
                     algorithms.retrieve(dg, dispersed_channel_name, 'width'),
                     epsilon,
                     algorithms.retrieve(dg, dispersed_node_name, 'flow_rate'),
                     algorithms.retrieve(dg, continuous_node_name, 'flow_rate')
                 ))

    # Assert critical angle is <= calculated angle
    cosine_squared_theta_crit = math.cos(math.radians(crit_crossing_angle))**2
    # Continuous to dispersed
    exprs.append(cosine_squared_theta_crit <=
                 algorithms.cosine_law_crit_angle(dg,
                                                  continuous_node_name,
                                                  junction_node_name,
                                                  dispersed_node_name
                                                  ))
    # Continuous to output
    exprs.append(cosine_squared_theta_crit <=
                 algorithms.cosine_law_crit_angle(dg,
                                                  continuous_node_name,
                                                  junction_node_name,
                                                  output_node_name
                                                  ))
    # Output to dispersed
    exprs.append(cosine_squared_theta_crit <=
                 algorithms.cosine_law_crit_angle(dg,
                                                  output_node_name,
                                                  junction_node_name,
                                                  dispersed_node_name
                                                  ))
    # Call translate on output
    translation_strats[algorithms.retrieve(dg,
                                           output_node_name,
                                           'kind'
                                           )](dg, output_node_name)
    return exprs


translation_strats = {'input': translate_input,
                      'output': translate_output,
                      't-junction': translate_tjunc,
                      'rectangle': translate_channel
                      }
