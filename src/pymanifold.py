from pprint import pprint
import math
from pysmt.shortcuts import Symbol, Plus, Times, Div, Pow, Equals, Real
from pysmt.shortcuts import Minus, GE, LE, LT, And, get_model
from pysmt.typing import REAL
from pysmt.logics import QF_NRA


class Schematic():
    """Create new schematic which contains all of the connections and ports
    within a microfluidic circuit to be solved for my an SMT solver to
    determine solvability of the circuit and the range of the parameters where
    it is still solvable
    """
    # TODO schematic to JSON method

    def __init__(self):
        """Store the connections as a dictionary to form a graph where each
        value is a list of all nodes/ports that a node flows out to, store
        information about each of the channels in a separate dictionary
        """
        self.connections = {}
        self.channels = {}
        self.nodes = {}
        self.exprs = []

        # Add new node types and their validation method to this dict
        # to maintain consistent checking across all methods
        self.translate_ports = {'input': self.translate_input,
                                'output': self.translate_output
                                }
        self.translate_nodes = {'t-junction': self.translate_tjunc
                                }

    def channel(self,
                shape,
                min_length,
                min_width,
                min_height,
                port_from,
                port_to,
                phase='None'):
        """Create new connection between two nodes/ports with attributes
        consisting of the dimensions of the channel to be used to create the
        SMT2 equation to calculate solvability of the circuit

        shape - shape of cross section of the channel
        min_length - constaint the chanell to be at least this long
        width - width of the cross section of the channel
        height - height of the cross section of the channel
        port_from - port where fluid comes into the channel from
        port_to - port at the end of the channel where fluid exits
        phase - for channels connecting to a T-junction this must be either
                continuous, dispersed or output
        """
        valid_shapes = ("rectangle")
        # Checking that arguments are valid
        if not isinstance(shape, str) or not isinstance(port_from, str)\
                or not isinstance(port_to, str):
            raise TypeError("shape of channel, input and output ports must be\
                    strings")
        if not isinstance(min_length, (int, float))\
                or not isinstance(min_width, (int, float))\
                or not isinstance(min_height, (int, float)):
            raise TypeError("length, width and height must be numbers")
        if shape not in valid_shapes:
            raise ValueError("Valid channel shapes are: %s"
                             % valid_shapes)
        if port_from not in self.nodes.keys():
            raise ValueError("port_from node doesn't exist")
        elif port_to not in self.nodes.keys():
            raise ValueError("port_to node doesn't exist")

        # If that fluid entry node already exists then that means there is
        # another node that it flows out to so append that exit node to list
        try:
            # Can't have two of the same channel
            if port_to in self.connections[port_from]:
                raise ValueError("Channel already exists between these nodes")
            self.connections[port_from].append(port_to)
        except KeyError:
            self.connections[port_from] = [port_to]

        # Add the information about that connection to another dict
        self.channels[port_from+port_to] = {'port_from': port_from,
                                            'port_to': port_to,
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
                                            'flow_rate': Symbol(port_from
                                                                + port_to
                                                                + '_flow_rate',
                                                                REAL),
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
        return

    # TODO: Should X and Y be forced to be >0 for triangle area calc?
    # TODO: There are similar arguments for both port and node that could be
    #       simplified if they were inhereted from a common object
    def port(self, name, kind, min_pressure, min_flow_rate, X, Y,
             min_viscosity=1):
        """Create new port where fluids can enter or exit the circuit, viscosity
        and kind('input' or 'output') needs to be specified
        """
        # Checking that arguments are valid
        if not isinstance(name, str) or not isinstance(kind, str):
            raise TypeError("name and kind must be strings")
        if not isinstance(min_pressure, (int, float)):
            raise TypeError("pressure must be a number")
        if not isinstance(min_flow_rate, (int, float)):
            raise TypeError("flow rate must be a number")
        if not isinstance(X, (int, float)) or\
                not isinstance(Y, (int, float)):
            raise TypeError("X and Y pos must be numbers")
        if name in self.nodes.keys():
            raise ValueError("Must provide a unique name")

        # Ports are stores with nodes because ports are just a specific type of
        # node that has a constant flow rate
        if kind.lower() in self.translate_ports.keys():
            self.nodes[name] = {'kind': kind.lower(),
                                'viscosity': Symbol(name+'_viscosity', REAL),
                                'min_viscosity': min_viscosity,
                                'pressure': Symbol(name+'_pressure', REAL),
                                'min_pressure': min_pressure,
                                'flow_rate': Symbol(name+'_flow_rate', REAL),
                                'min_flow_rate': min_flow_rate,
                                'position': [X, Y],
                                'position_sym': [Symbol(name+'_X', REAL),
                                                 Symbol(name+'_Y', REAL)]
                                }
        else:
            raise ValueError("kind must be %s" % self.translate_ports.keys())

    def node(self, name, min_pressure, X, Y, kind='node'):
        """Create new node where fluids merge or split, kind of node
        (T-junction, Y-junction, cross, etc.) can be specified
        if not then a basical node connecting multiple channels will be created
        """
        # Checking that arguments are valid
        if not isinstance(name, str) or not isinstance(kind, str):
            raise TypeError("name and kind must be strings")
        if not isinstance(min_pressure, (int, float)):
            raise TypeError("pressure must be a number")
        if not isinstance(X, (int, float)) or\
                not isinstance(Y, (int, float)):
            raise TypeError("X and Y pos must be numbers")
        if name in self.nodes.keys():
            raise ValueError("Must provide a unique name")

        if kind.lower() in self.translate_nodes.keys():
            self.nodes[name] = {'kind': kind.lower(),
                                'pressure': Symbol(name+'_pressure', REAL),
                                'flow_rate': Symbol(name+'_flow_rate', REAL),
                                'viscosity': Symbol(name+'_viscosity', REAL),
                                'min_pressure': min_pressure,
                                'position': [X, Y],
                                'position_sym': [Symbol(name+'_X', REAL),
                                                 Symbol(name+'_Y', REAL)]
                                }
        else:
            raise ValueError("kind name not valid, only %s are valid" %
                             self.translate_nodes.keys())

    def translate_input(self, name):
        """Generate equations to simulate a fluid input port
        """
        num_connections = len(self.connections[name])
        if num_connections <= 0:
            raise ValueError("Port %s must have 1 or more connections" % name)
        # Node pressure greater than 0
        self.exprs.append(GE(self.nodes[name]['pressure'], Real(0)))

    def translate_output(self, name):
        """Generate equations to simulate a fluid output port
        """
        for port_in, ports_out in self.connections.items():
            if name in ports_out:
                return True
        raise ValueError("Port %s must have 1 or more connections" % name)
        # Node pressure greater than 0
        self.exprs.append(GE(self.nodes[name]['pressure'], Real(0)))

    # TODO: assert node position here and for ports
    def translate_node(self, name):
        """Generate equations to simulate a basic node connecting two or more channels
        """
        outputs = self.connections[name]
        for output in outputs:
            channel = self.channels[name+output]
            # PressureFlow strategies here:

            # Assert channel width, height viscosity and resistance greater
            # than 0 Also asserts that each channel's height is less than width
            # to make resistance calculation valid
            self.exprs.append(self.calculate_channel_resistance(channel))
            # Assert difference in pressure at the two end nodes for a channel
            # equals the flow rate in the channel times the channel resistance
            self.exprs.append(self.simple_pressure_flow(channel))
            # Channel viscosity in channel equal to viscosity of port_from
            self.exprs.append(Equals(channel['viscosity'],
                                     self.nodes[channel['port_from']][
                                         'viscosity']))

        # Flow rate in and out of the node must be equal
        flow_in = []
        for port_from, ports_to in self.connections.items():
            if name in ports_to:
                flow_in.append(self.nodes[port_from]['flow_rate'])
        flow_out = self.nodes[name]['flow_rate']
        self.exprs.append(Equals(Plus(flow_in), flow_out))

    # TODO: Refactor some of these calculations so they can be reused by other
    # tanslation methods
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

        # Placement Translation set methods here

        # Retrieve value of position for each node
        xC = Real(self.nodes[continuous_node]['position'][0])
        yC = Real(self.nodes[continuous_node]['position'][1])
        xO = Real(self.nodes[output_node]['position'][0])
        yO = Real(self.nodes[output_node]['position'][1])
        xJ = Real(self.nodes[junction_node]['position'][0])
        yJ = Real(self.nodes[junction_node]['position'][1])
        xD = Real(self.nodes[dispersed_node]['position'][0])
        yD = Real(self.nodes[dispersed_node]['position'][1])
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

        # Assert positions equal their provided position, like in
        # controlPointPlacement from Manifold
        self.exprs.append(Equals(nxC, xC))
        self.exprs.append(Equals(nyC, yC))
        self.exprs.append(Equals(nxO, xO))
        self.exprs.append(Equals(nyO, yO))
        self.exprs.append(Equals(nxJ, xJ))
        self.exprs.append(Equals(nyJ, yJ))
        self.exprs.append(Equals(nxD, xD))
        self.exprs.append(Equals(nyD, yD))

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

    def calculate_channel_resistance(self, _channel):
        """Calculate the droplet resistance in a channel using:
        R = (12 * mu * L) / (w * h^3 * (1 - 0.630 (h/w)) )
        """
        chR = _channel['resistance']
        w = _channel['width']
        h = _channel['height']
        mu = _channel['viscosity']
        chL = _channel['length']
        return And(LT(h, w),
                   Equals(chR,
                          Div(Times(Real(12),
                                    Times(mu, chL)
                                    ),
                              Times(w,
                                    Times(Pow(h, Real(3)),
                                          Minus(Real(1),
                                                Times(Real(0.63),
                                                      Div(h, w)
                                                      )))))))

    def pythagorean_length(self, node1, node2, ch_len):
        """Use Pythagorean theorem to assert that the channel length
        (hypoteneuse) squared is equal to the legs squared so channel
        length is solved for
        """
        side_a = Minus(node1[0], node2[0])
        side_b = Minus(node1[1], node2[1])
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

    def translate_schematic(self):
        """Validates that each node has the correct input and output
        conditions met then translates it into pysmt syntax
        Generates SMT formulas to simulate specialized nodes like T-junctions
        and stores them in self.exprs
        """
        for name, attributes in self.nodes.items():
            # The translate method names are stored in a dictionary name where
            # the key is the name of that node or port kind
            try:
                self.translate_nodes[self.nodes[name]['kind']](name)
            except KeyError:
                self.translate_ports[self.nodes[name]['kind']](name)

    def invoke_backend(self):
        """Combine all of the SMT expressions into one expression to sent to Z3
        solver to determine solvability
        """
        formula = And(self.exprs)
        # Prints the generated formula in full, remove serialize for shortened
        pprint(formula.serialize())
        # Return None if not solvable, returns a dict-like structure giving the
        # range of values for each Symbol
        return get_model(formula, solver_name='z3', logic=QF_NRA)

    def solve(self):
        """Create the SMT2 equation for this schematic outlining the design
        of a microfluidic circuit and use Z3 to solve it using pysmt
        """
        self.translate_schematic()
        return self.invoke_backend()
