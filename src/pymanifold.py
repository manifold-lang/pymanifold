from pprint import pprint
import math
import networkx as nx
import matplotlib.pyplot as plt  # just for testing to show graph, may not keep
from pysmt.shortcuts import Symbol, Plus, Times, Div, Pow, Equals, Real
from pysmt.shortcuts import Minus, GE, GT, LE, LT, And, get_model, is_sat
from pysmt.typing import REAL
from pysmt.logics import QF_NRA


class Schematic():
    """Create new schematic which contains all of the connections and ports
    within a microfluidic circuit to be solved for my an SMT solver to
    determine solvability of the circuit and the range of the parameters where
    it is still solvable
    """
    # TODO schematic to JSON method following Manifold IR syntax

    def __init__(self, dim=[0, 0, 10, 10]):
        """Store the connections as a dictionary to form a graph where each
        value is a list of all nodes/ports that a node flows out to, store
        information about each of the channels in a separate dictionary
        dim - dimensions of the chip, [X_min, Y_min, X_max, X_min]
        """
        self.exprs = []
        self.dim = dim

        # Add new node types and their validation method to this dict
        # to maintain consistent checking across all methods
        self.translation_strats = {'input': self.translate_input,
                                   'output': self.translate_output,
                                   't-junction': self.translate_tjunc,
                                   'rectangle': self.translate_rec_channel
                                   }

        # DiGraph that will contain all nodes and channels
        self.dg = nx.DiGraph()

    # TODO: All parameters for channel and ports need to have units documented
    #       depending on the formula
    def channel(self,
                min_length,
                min_width,
                min_height,
                port_from,
                port_to,
                min_channel_length=0,
                shape='rectangle',
                phase='None'):
        """Create new connection between two nodes/ports with attributes
        consisting of the dimensions of the channel to be used to create the
        SMT2 equation to calculate solvability of the circuit

        min_length - constaint the chanell to be at least this long
        width - width of the cross section of the channel
        height - height of the cross section of the channel
        port_from - port where fluid comes into the channel from
        port_to - port at the end of the channel where fluid exits
        shape - shape of cross section of the channel
        phase - for channels connecting to a T-junction this must be either
                continuous, dispersed or output
        """
        valid_shapes = ("rectangle")
        # Checking that arguments are valid
        if shape not in valid_shapes:
            raise ValueError("Valid channel shapes are: %s"
                             % valid_shapes)
        if port_from not in self.dg.nodes:
            raise ValueError("port_from node doesn't exist")
        elif port_to not in self.dg.nodes():
            raise ValueError("port_to node doesn't exist")
        try:
            # Each value must be greater than 0
            if min_length < 0 or min_width < 0 or min_height < 0 or min_channel_length < 0:
                raise ValueError
        except TypeError as e:
            raise TypeError("This port parameter must be int %s" % e)
        except ValueError as e:
            raise ValueError("This port parameter must be > 0 %s" % e)

        # Can't have two of the same channel
        if (port_from, port_to) in self.dg.nodes:
            raise ValueError("Channel already exists between these nodes")
        # Create this edge in the graph
        self.dg.add_edge(port_from, port_to)

        # Add the information about that connection to another dict
        # There's extra parameters in here than in the arguments because they
        # are values calculated by later methods when creating the SMT eqns
        attributes = {'shape': shape,
                      'length': Symbol(port_from
                                       + port_to
                                       + '_length',
                                       REAL),
                      'min_length': min_length,
                      'width': Symbol(port_from
                                      + port_to
                                      + '_width',
                                      REAL),
                      'min_width': min_width,
                      'height': Symbol(port_from
                                       + port_to
                                       + '_height',
                                       REAL),
                      'min_height': min_height,
                      'flow_rate': Symbol(port_from + port_to + '_flow_rate', REAL),
                      'droplet_volume': Symbol(port_from
                                               + port_to
                                               + '_Dvol',
                                               REAL),
                      'viscosity': Symbol(port_from
                                          + port_to
                                          + '_viscosity',
                                          REAL),
                      'resistance': Symbol(port_from
                                           + port_to
                                           + '_res',
                                           REAL),
                      'phase': phase.lower(),
                      }
        for key, attr in attributes.items():
            # Store as False instead of 0 to prevent any further
            # operations from accepting this value by mistake
            if attr == 0:
                self.dg.edges[port_from, port_to][key] = False
            else:
                self.dg.edges[port_from, port_to][key] = attr
        return

    # TODO: Add ability to specify a fluid type in the node (ie. water) and
    #       have this method automatically fill in the parameters for water
    # TODO: Should X and Y be forced to be >0 for triangle area calc?
    # TODO: There are similar arguments for both port and node that could be
    #       simplified if they were inhereted from a common object
    def port(self, name, kind, min_pressure=0, min_flow_rate=0, x=0, y=0,
             density=1, min_viscosity=0):
        """Create new port where fluids can enter or exit the circuit, any
        optional tag left empty will be converted to a variable for the SMT
        solver to solve for a give a value
        :param str name: The name of the port to use when defining channels
        :param str kind: Define if this is an 'input' or 'output' port
        :param float Density: Density of fluid in g/cm^3, default is 1(water)
        :param float min_viscosity: Viscosity of the fluid, units are Pa.s
        :param float min_pressure: Pressure of the input fluid, units are Pa
        :param float min_flow_rate - flow rate of input fluid, units are m^3/s
                                     (may want to make it smaller, um^3/s)
        :param float X: x-position of port on chip schematic
        :param float Y: y-position of port on chip schematic
        """
        # Checking that arguments are valid
        if not isinstance(name, str) or not isinstance(kind, str):
            raise TypeError("name and kind must be strings")
        if name in self.dg.nodes:
            raise ValueError("Must provide a unique name")
        if kind.lower() not in self.translation_strats.keys():
            raise ValueError("kind must be %s" % self.translation_strats.keys())

        # Ports are stored with nodes because ports are just a specific type of
        # node that has a constant flow rate
        # only accept ports of the right kind (input or output)
        attributes = {'kind': kind.lower(),
                      'viscosity': Symbol(name+'_viscosity', REAL),
                      'min_viscosity': min_viscosity,
                      'pressure': Symbol(name+'_pressure', REAL),
                      'min_pressure': min_pressure,
                      'flow_rate': Symbol(name+'_flow_rate', REAL),
                      'min_flow_rate': min_flow_rate,
                      'density': density,  # Density will always be defined
                      'x': Symbol(name+'_X', REAL),
                      'y': Symbol(name+'_Y', REAL),
                      'min_x': x,
                      'min_y': y
                      }

        # list of values that should all be positive numbers
        not_neg = ['min_x', 'min_y', 'min_pressure', 'min_flow_rate', 'min_viscosity',
                   'density']
        try:
            for param in not_neg:
                if attributes[param] < 0:
                    raise ValueError("port '%s' parameter '%s' must be > 0" %
                                     (name, param))
        except TypeError as e:
            raise TypeError("port '%s' parameter must be int %s" % (name, e))
        except ValueError as e:
            raise ValueError(e)

        # Create this node in the graph
        self.dg.add_node(name)
        for key, attr in attributes.items():
            if attr == 0:
                # Store as False instead of 0 to prevent any further
                # operations from accepting this value by mistake
                self.dg.nodes[name][key] = False
            else:
                self.dg.nodes[name][key] = attr

    def node(self, name, x=0, y=0, kind='node'):
        """Create new node where fluids merge or split, kind of node
        (T-junction, Y-junction, cross, etc.) can be specified
        if not then a basical node connecting multiple channels will be created
        """
        # Checking that arguments are valid
        if not isinstance(name, str) or not isinstance(kind, str):
            raise TypeError("name and kind must be strings")
        if name in self.dg.nodes:
            raise ValueError("Must provide a unique name")
        if kind.lower() not in self.translate_nodes.keys():
            raise ValueError("kind must be %s" % self.translate_nodes.keys())

        # Ports are stored with nodes because ports are just a specific type of
        # node that has a constant flow rate
        # only accept ports of the right kind (input or output)
        attributes = {'kind': kind.lower(),
                      'pressure': Symbol(name+'_pressure', REAL),
                      'flow_rate': Symbol(name+'_flow_rate', REAL),
                      'viscosity': Symbol(name+'_viscosity', REAL),
                      'x': Symbol(name+'_X', REAL),
                      'y': Symbol(name+'_Y', REAL),
                      'min_x': x,
                      'min_y': y
                      }

        # list of values that should all be positive numbers
        not_neg = ['min_x', 'min_y', 'min_pressure', 'min_flow_rate', 'min_viscosity',
                   'density']
        try:
            for param in not_neg:
                if attributes[param] < 0:
                    raise ValueError("port '%s' parameter '%s' must be > 0" %
                                     (name, param))
        except TypeError as e:
            raise TypeError("This port parameter must be int %s" % e)
        except ValueError as e:
            raise ValueError(e)

        # Create this node in the graph
        self.dg.add_node(name)
        for key, attr in attributes.items():
            if attr == 0:
                # Store as False instead of 0 to prevent any further
                # operations from accepting this value by mistake
                self.dg.nodes[name][key] = False
            else:
                self.dg.nodes[name][key] = attr

    def translate_chip(self, name):
        """Create SMT2 expressions for bounding the chip area provided when
        initializing the schematic object
        """
        named_node = self.dg.nodes[name]
        self.exprs.append(GE(named_node['x'], Real(self.dim[0])))
        self.exprs.append(GE(named_node['y'], Real(self.dim[1])))
        self.exprs.append(LE(named_node['x'], Real(self.dim[2])))
        self.exprs.append(LE(named_node['y'], Real(self.dim[3])))

    def translate_input(self, name):
        """Generate equations to simulate a fluid input port
        """
        if len(list(self.dg.neighbors(name))) <= 0:
            raise ValueError("Port %s must have 1 or more connections" % name)

        # Since input is just a specialized node, call translate node
        self.translate_node(name)

        named_node = self.dg.nodes[name]
        # If parameters are provided by the user, then set the
        # their Symbol equal to that value, otherwise make it greater than 0
        if named_node['min_pressure']:
            # named_node['pressure'] returns variable for node for pressure
            # where 'min_pressure' returns the user defined value if provided,
            # else its 0, same is true for viscosity and x and y position
            self.exprs.append(Equals(named_node['pressure'],
                                     Real(named_node['min_pressure'])
                                     ))
        else:
            self.exprs.append(GE(named_node['pressure'], Real(0)))
        if named_node['min_flow_rate']:
            self.exprs.append(Equals(named_node['flow_rate'],
                                     Real(named_node['min_flow_rate'])
                                     ))
        else:
            self.exprs.append(GE(named_node['flow_rate'], Real(0)))
        if named_node['min_viscosity']:
            self.exprs.append(Equals(named_node['viscosity'],
                                     Real(named_node['min_viscosity'])
                                     ))
        else:
            self.exprs.append(GE(named_node['viscosity'], Real(0)))

    # TODO: Find out how output and input need to be different, currently they
    #       are exactly the same, perhaps change how translation happens to
    #       have it traverse the graph, starting at inputs and calling
    #       channel and output translation methods recursively
    def translate_output(self, name):
        """Generate equations to simulate a fluid output port
        """
        if self.dg.size(name) <= 0:
            raise ValueError("Port %s must have 1 or more connections" % name)

        # Since input is just a specialized node, call translate node
        self.translate_node(name)

        named_node = self.dg.nodes[name]
        # If parameters are provided by the user, then set the
        # their Symbol equal to that value, otherwise make it greater than 0
        if named_node['min_pressure']:
            # named_node['pressure'] returns variable for node for pressure
            # where 'min_pressure' returns the user defined value if provided,
            # else its 0, same is true for viscosity and position (position_sym
            # provides the symbol in this case)
            self.exprs.append(Equals(named_node['pressure'],
                                     Real(named_node['min_pressure'])
                                     ))
        else:
            self.exprs.append(GE(named_node['pressure'], Real(0)))
        if named_node['min_flow_rate']:
            self.exprs.append(Equals(named_node['flow_rate'],
                                     Real(named_node['min_flow_rate'])
                                     ))
        else:
            self.exprs.append(GE(named_node['flow_rate'], Real(0)))
        if named_node['min_viscosity']:
            self.exprs.append(Equals(named_node['viscosity'],
                                     Real(named_node['min_viscosity'])
                                     ))
        else:
            self.exprs.append(GE(named_node['viscosity'], Real(0)))

    # TODO: Refactor this to be just translate_channel and have it use the
    #       correct formula depending on the shape of the given channel
    #       Also some port parameters are calcualted here like flow rate which
    #       could be confusing to debug since one would look for port parameter
    #       issues in translate input or output, not here, making these
    #       method be called only when traversing the graph would rectify this
    def translate_rec_channel(self, name):
        """Create SMT2 expressions for a given channel (edges in networkx naming)
        currently only works for channels with a rectangular shape, but should
        be expanded to include circular and parabolic
        name - the name of the channel to have SMT equations created for
        """
        try:
            named_channel = self.dg.edges[name]
        except KeyError:
            raise KeyError('Channel %s does not exist' % name)
        port_in_name = name[0]
        port_out_name = name[1]

        # Use pythagorean theorem to assert that the channel be greater than
        # the min_channel_length if no value is provided, or set the length
        # equal to the user provided number
        if named_channel['min_length']:
            self.exprs.append(GT(named_channel['length'],
                              Real(named_channel['min_length'])))
        else:
            # If values isn't provided assert that length must be greater than
            # than 0
            self.exprs.append(GT(named_channel['length'], Real(0)))

        # Create expression to force length to equal distance between end nodes
        self.exprs.append(self.pythagorean_length(port_in_name,
                                                  port_out_name,
                                                  named_channel['length']
                                                  ))

        # Assert that viscosity in channel equals input node viscosity
        # set output viscosity to equal input since this should be constant
        self.exprs.append(Equals(named_channel['viscosity'],
                                 self.dg.nodes[port_in_name]['viscosity']))
        self.exprs.append(Equals(self.dg.nodes[port_out_name]['viscosity'],
                                 self.dg.nodes[port_in_name]['viscosity']))

        # Assert channel width, height viscosity and resistance greater
        # than 0
        self.exprs.append(GE(named_channel['width'], Real(0)))
        self.exprs.append(GE(named_channel['height'], Real(0)))

        # Assert pressure at end of channel is lower based on the resistance of
        # the channel as calculated by calculate_channel_resistance and
        # delta(P) = flow_rate * resistance
        # pressure_out = pressure_in - delta(P)
        resistance_list = self.calculate_channel_resistance(named_channel)

        # First term is assertion that each channel's height is less than width
        # which is needed to make resistance formula valid, second is the SMT
        # equation of the resistance
        self.exprs.append(resistance_list[0])
        resistance = resistance_list[1]
        flow_rate = self.calculate_port_flow_rate(port_in_name)
        output_pressure = self.channel_output_pressure(
                              self.dg.nodes[port_in_name]['pressure'],
                              resistance,
                              flow_rate)

        # Assert resistance to equal value calculated for rectangular channel
        self.exprs.append(Equals(named_channel['resistance'], resistance))
        self.exprs.append(GE(named_channel['resistance'], Real(0)))
        named_channel['resistance'] = resistance

        # Assert flow rate equal to calcuated value, in channel and ports
        self.exprs.append(Equals(named_channel['flow_rate'], flow_rate))
        self.exprs.append(Equals(self.dg.nodes[port_in_name]['flow_rate'],
                                 flow_rate))
        self.exprs.append(Equals(self.dg.nodes[port_out_name]['flow_rate'],
                                 flow_rate))

        # Assert pressure in output to equal calcualted value based on P=QR
        self.exprs.append(Equals(self.dg.nodes[port_out_name]['pressure'],
                                 output_pressure))
        self.exprs.append(GE(self.dg.nodes[port_out_name]['pressure'],
                             Real(0)))
        self.dg.nodes[port_out_name]['pressure'] = output_pressure
        return

    # TODO: assert node position here and for ports
    # TODO: need way for sum of flow_in to equal flow out for input and output
    #       ports
    def translate_node(self, name):
        """Generate equations to simulate a basic node connecting two or more
        channels
        """
        # Flow rate in and out of the node must be equal
        # Assume flow rate is the same at the start and end of a channel
        named_node = self.dg.nodes[name]
        # Position x and y symbols must equal their assigned value, if not
        # assigned then set to be greater than 0
        if named_node['min_x']:
            self.exprs.append(Equals(named_node['x'], named_node['min_x']))
            self.exprs.append(Equals(named_node['y'], named_node['min_y']))
        else:
            self.exprs.append(GE(named_node['x'], Real(0)))
            self.exprs.append(GE(named_node['y'], Real(0)))
        return

    # TODO: Migrate this to work with NetworkX
    # TODO: Refactor some of these calculations so they can be reused by other
    #       translation methods
    def translate_tjunc(self, name, critCrossingAngle=0.5):
        # Validate input
        if len(self.connections[name]) > 1:
            raise ValueError("T-Junction must only have one output")
        output_node = self.connections[name][0]
        outputs = [key for key, value in self.connections.items()
                   if name in value]
        num_connections = len(outputs) + 1  # +1 to include the output node
        if num_connections != 3:
            raise ValueError("T-junction %s must have 3 connections" % name)

        # Since T-junction is just a specialized node, call translate node
        self.translate_node(name)

        junction_node = name
        continuous_node = ''
        dispersed_node = ''
        output_channel = self.channels[name+output_node]
        continuous_channel = ''
        dispersed_channel = ''
        for node_from, node_to_list in self.connections.items():
            if name in node_to_list:
                if self.channels[node_from+name]['phase'] == 'continuous':
                    continuous_node = node_from
                    continuous_channel = self.channels[continuous_node+name]
                    # assert width and height to be equal to output
                    self.exprs.append(Equals(continuous_channel['width'],
                                             output_channel['width']
                                             ))
                    self.exprs.append(Equals(continuous_channel['height'],
                                             output_channel['height']
                                             ))
                elif self.channels[node_from+name]['phase'] == 'dispersed':
                    dispersed_node = node_from
                    dispersed_channel = self.channels[dispersed_node+name]
                    # Assert that only the height of channel be equal
                    self.exprs.append(Equals(dispersed_channel['height'],
                                             output_channel['height']
                                             ))
                else:
                    raise ValueError("Invalid phase for T-junction: %s" %
                                     name)

        # Epsilon, sharpness of T-junc, must be greater than 0
        epsilon = Symbol('epsilon', REAL)
        self.exprs.append(GE(epsilon, Real(0)))

        # Pressure at each of the 4 nodes must be equal
        self.exprs.append(Equals(self.nodes[name]['pressure'],
                                 self.nodes[continuous_node]['pressure']
                                 ))
        self.exprs.append(Equals(self.nodes[name]['pressure'],
                                 self.nodes[dispersed_node]['pressure']
                                 ))
        self.exprs.append(Equals(self.nodes[name]['pressure'],
                                 self.nodes[output_node]['pressure']
                                 ))

        # Viscosity in continous phase equals viscosity at output
        self.exprs.append(Equals(self.nodes[continuous_node]['viscosity'],
                                 self.nodes[output_node]['viscosity']
                                 ))

        # Droplet volume in channel equals calculated droplet volume
        # TODO: Manifold also has a table of constraints in the Schematic and
        # sets ChannelDropletVolume equal to dropletVolumeConstraint, however
        # the constraint is void (new instance of RealTypeValue) and I think
        # could conflict with calculated value, so ignoring it for now but
        # may be necessary to add at a later point if I'm misunderstand why
        # its needed
        v_output = output_channel['droplet_volume']
        self.exprs.append(Equals(v_output,
                                 self.calculate_droplet_volume(
                                     output_channel['height'],
                                     output_channel['width'],
                                     dispersed_channel['width'],
                                     epsilon,
                                     self.nodes[dispersed_node]['flow_rate'],
                                     self.nodes[continuous_node]['flow_rate']
                                 )))

        # Retrieve symbols for each node
        nxC = self.nodes[continuous_node]['position_sym'][0]
        nyC = self.nodes[continuous_node]['position_sym'][1]
        nxO = self.nodes[output_node]['position_sym'][0]
        nyO = self.nodes[output_node]['position_sym'][1]
        nxJ = self.nodes[junction_node]['position_sym'][0]
        nyJ = self.nodes[junction_node]['position_sym'][1]
        nxD = self.nodes[dispersed_node]['position_sym'][0]
        nyD = self.nodes[dispersed_node]['position_sym'][1]
        # Retrieve symbols for channel lengths
        lenC = continuous_channel['length']
        lenO = output_channel['length']
        lenD = dispersed_channel['length']

        # Constrain that continuous and output ports are in a straight line by
        # setting the area of the triangle formed between those two points and
        # the center of the t-junct to be 0
        # Formula for area of a triangle given 3 points
        # x_i (y_p − y_j ) + x_p (y_j − y_i ) + x_j (y_i − y_p ) / 2
        self.exprs.append(Equals(Real(0),
                                 Div(Plus(Times(nxC,
                                                Minus(nyJ, nyO)
                                                ),
                                          Plus(Times(nxJ,
                                                     Minus(nyO, nyC)
                                                     ),
                                               Times(nxO,
                                                     Minus(nyC, nyJ)
                                                     ))),
                                     Real(2)
                                     )))

        # Assert critical angle is <= calculated angle
        cosine_squared_theta_crit = Real(math.cos(
            math.radians(critCrossingAngle))**2)
        # Continuous to dispersed
        self.exprs.append(LE(cosine_squared_theta_crit,
                             self.cosine_law_crit_angle([nxC, nyC],
                                                        [nxJ, nyJ],
                                                        [nxD, nyD]
                                                        )))
        # Continuous to output
        self.exprs.append(LE(cosine_squared_theta_crit,
                             self.cosine_law_crit_angle([nxC, nyC],
                                                        [nxJ, nyJ],
                                                        [nxO, nyO]
                                                        )))
        # Output to dispersed
        self.exprs.append(LE(cosine_squared_theta_crit,
                             self.cosine_law_crit_angle([nxO, nyO],
                                                        [nxJ, nyJ],
                                                        [nxD, nyD]
                                                        )))

        # Assert channel length equal to the sum of the squares of the legs
        self.exprs.append(self.pythagorean_length([nxC, nyC], [nxJ, nyJ], lenC))
        self.exprs.append(self.pythagorean_length([nxD, nyD], [nxJ, nyJ], lenD))
        self.exprs.append(self.pythagorean_length([nxJ, nyJ], [nxO, nyO], lenO))

    # TODO: In Manifold this has the option for worst case analysis, need to
    #       understand when this is needed and implement it if needed
    def simple_pressure_flow(self, _channel):
        """Assert difference in pressure at the two end nodes for a channel
        equals the flow rate in the channel times the channel resistance
        More complicated calculation available through
        analytical_pressure_flow method
        """
        p1 = self.nodes[_channel['port_from']]['pressure']
        p2 = self.nodes[_channel['port_to']]['pressure']
        chV = _channel['flow_rate']
        chR = _channel['resistance']
        return Equals(Minus(p1, p2),
                      Times(chV, chR)
                      )

    def channel_output_pressure(self, P_in, chR, chV):
        """Calculate the pressure at the output of a channel
        P_in - pressure at beginning of channel
        chR - channel resistance
        chV - channel flow rate
        """
        return Minus(P_in,
                     Times(chR, chV))

    def calculate_channel_resistance(self, _channel):
        """Calculate the droplet resistance in a channel using:
        R = (12 * mu * L) / (w * h^3 * (1 - 0.630 (h/w)) )
        This formula assumes that channel height < width, so
        the first term returned is the assertion for that
        """
        w = _channel['width']
        h = _channel['height']
        mu = _channel['viscosity']
        chL = _channel['length']
        return (LT(h, w),
                Div(Times(Real(12),
                          Times(mu, chL)
                          ),
                    Times(w,
                          Times(Pow(h, Real(3)),
                                Minus(Real(1),
                                      Times(Real(0.63),
                                            Div(h, w)
                                            ))))))

    # TODO: Could redesign this to just take in the name of a channel
    #       and have it get the input and output ports and length
    def pythagorean_length(self, node_a, node_b, ch_len):
        """Use Pythagorean theorem to assert that the channel length
        (hypoteneuse) squared is equal to the legs squared so channel
        length is solved for
        :param str node1: Name of one node for the channel
        :param str node2: Name of the other node for the channel
        :param Real ch_len: Channel length, must be a pysmt Real or variable
        """
        node1 = self.dg.nodes[node_a]
        node2 = self.dg.nodes[node_b]
        side_a = Minus(node1['x'], node2['x'])
        side_b = Minus(node1['y'], node2['y'])
        a_squared = Pow(side_a, Real(2))
        b_squared = Pow(side_b, Real(2))
        a_squared_plus_b_squared = Plus(a_squared, b_squared)
        c_squared = Pow(ch_len, Real(2))
        return Equals(a_squared_plus_b_squared, c_squared)

    def cosine_law_crit_angle(self, node1, node2, node3):
        """Use cosine law to find cos^2(theta) between three points
        node1---node2---node3 to assert that it is less than cos^2(thetaC)
        where thetaC is the critical crossing angle
        """
        # Lengths of channels
        aX = Minus(node1[0], node2[0])
        aY = Minus(node1[1], node2[1])
        bX = Minus(node3[0], node2[0])
        bY = Minus(node3[1], node2[1])
        # Dot products between each channel
        a_dot_b_squared = Pow(Plus(Times(aX, bX),
                                   Times(aY, bY)
                                   ),
                              Real(2)
                              )
        a_squared_b_squared = Times(Plus(Times(aX, aX),
                                         Times(aY, aY)
                                         ),
                                    Plus(Times(bX, bX),
                                         Times(bY, bY)
                                         ),
                                    )
        return Div(a_dot_b_squared, a_squared_b_squared)

    def calculate_droplet_volume(self, h, w, wIn, epsilon, qD, qC):
        """From paper DOI:10.1039/c002625e.
        h=height of channel
        w=width of continuous/output channel
        wIn=width of dispersed_channel
        epsilon=0.414*radius of rounded edge where channels join
        qD=flow rate in dispersed_channel
        qC=flow rate in continuous_channel
        """
        q_gutter = Real(0.1)
        # normalizedVFill = 3pi/8 - (pi/2)(1 - pi/4)(h/w)
        v_fill_simple = Minus(
                Times(Real((3, 8)), Real(math.pi)),
                Times(Times(
                            Div(Real(math.pi), Real(2)),
                            Minus(Real(1),
                                  Div(Real(math.pi), Real(4)))),
                      Div(h, w)))

        hw_parallel = Div(Times(h, w), Plus(h, w))

        # r_pinch = w+((wIn-(hw_parallel - eps))+sqrt(2*((wIn-hw_parallel)*(w-hw_parallel))))
        r_pinch = Plus(w,
                       Plus(Minus(
                                  wIn,
                                  Minus(hw_parallel, epsilon)),
                            Pow(Times(
                                      Real(2),
                                      Times(Minus(wIn, hw_parallel),
                                            Minus(w, hw_parallel)
                                            )),
                                Real(0.5))))
        r_fill = w
        alpha = Times(Minus(
                            Real(1),
                            Div(Real(math.pi), Real(4))
                            ),
                      Times(Pow(
                                Minus(Real(1), q_gutter),
                                Real(-1)
                                ),
                            Plus(Minus(
                                       Pow(Div(r_pinch, w), Real(2)),
                                       Pow(Div(r_fill, w), Real(2))
                                       ),
                                 Times(Div(Real(math.pi), Real(4)),
                                       Times(Minus(
                                                   Div(r_pinch, w),
                                                   Div(r_fill, w)
                                                   ),
                                             Div(h, w)
                                             )))))

        return Times(Times(h, Times(w, w)),
                     Plus(v_fill_simple, Times(alpha, Div(qD, qC))))

    def calculate_port_flow_rate(self, port_in):
        """Calculate the flow rate into a port based on the cross sectional
        area of the channel it flows into, the pressure and the density
        eqn from https://en.wikipedia.org/wiki/Hagen-Poiseuille_equation
        flow_rate = area * sqrt(2*pressure/density)
        """
        areas = []
        port_in_named = self.dg.nodes[port_in]
        for port_out in self.dg.succ[port_in]:
            areas.append(Times(self.dg[port_in][port_out]['length'],
                               self.dg[port_in][port_out]['width']
                               ))
        total_area = Plus(areas)
        return Times(total_area,
                     Pow(Div(Times(Real(2),
                                   port_in_named['pressure']
                                   ),
                             Real(port_in_named['density'])
                             ),
                         Real(0.5)
                         ))

    def translate_schematic(self):
        """Validates that each node has the correct input and output
        conditions met then translates it into pysmt syntax
        Generates SMT formulas to simulate specialized nodes like T-junctions
        and stores them in self.exprs
        """
        # The translate method names are stored in a dictionary name where
        # the key is the name of that node or port kind, also run on channels
        # (Edges) and finish by constaining nodes to be within chip area
        for name in self.dg.nodes:
            self.translation_strats[self.dg.nodes[name]['kind']](name)
        for name in self.dg.edges:
            self.translation_strats[self.dg.edges[name]['shape']](name)
        for name in self.dg.nodes:
            self.translate_chip(name)

    def invoke_backend(self, _show):
        """Combine all of the SMT expressions into one expression to sent to Z3
        solver to determine solvability
        """
        formula = And(self.exprs)
        # Prints the generated formula in full, remove serialize for shortened
        if _show:
            pprint(formula.serialize())
            #  nx.draw(self.dg)
            #  plt.show()
        # Return None if not solvable, returns a dict-like structure giving the
        # range of values for each Symbol
        model = get_model(formula, solver_name='z3', logic=QF_NRA)
        if model:
            return model
        else:
            return "No solution found"

    def solve(self, show=False):
        """Create the SMT2 equation for this schematic outlining the design
        of a microfluidic circuit and use Z3 to solve it using pysmt
        """
        self.translate_schematic()
        return self.invoke_backend(show)
