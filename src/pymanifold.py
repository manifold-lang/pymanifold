from pprint import pprint
import math
import json
import networkx as nx
from networkx.readwrite import json_graph
#  import matplotlib.pyplot as plt  # include if you want to show graph
from pysmt.shortcuts import Symbol, Plus, Times, Div, Pow, Equals, Real
from pysmt.shortcuts import Minus, GE, GT, LE, LT, And, get_model, is_sat
from pysmt.typing import REAL
from pysmt.logics import QF_NRA

import Constants

class Fluid():
    
  def __init__(self, fluid):
    self.min_density = Constants.FluidProperties().getDensity(fluid)
    self.min_resistivity = Constants.FluidProperties().getResistivity(fluid)
    self.min_viscosity = Constants.FluidProperties().getViscosity(fluid)
    self.min_pressure = False

  def updateFluidProperties(self, min_density=False, min_viscosity=False, min_pressure=False, min_resistivity=False):
    self.min_density = min_density
    self.min_resistivity = min_resistivity
    self.min_viscosity = min_viscosity
    self.min_pressure = min_pressure

  def __repr__(self):
    return repr((self.min_density, self.min_resistivity, self.min_viscosity, self.min_pressure))


class Schematic():
    """Create new schematic which contains all of the connections and ports
    within a microfluidic circuit to be solved for my an SMT solver to
    determine solvability of the circuit and the range of the parameters where
    it is still solvable
    """
    def __init__(self, dim):
        """Store the connections as a dictionary to form a graph where each
        value is a list of all nodes/ports that a node flows out to, store
        information about each of the channels in a separate dictionary

        :param list dim: dimensions of the chip, [X_min, Y_min, X_max, X_min] (m)
        """
        self.exprs = []
        self.dim = dim

        # Add new node types and their validation method to this dict
        # to maintain consistent checking across all methods
        self.translation_strats = {'input': self.translate_input,
                                   'output': self.translate_output,
                                   't-junction': self.translate_tjunc,
                                   'rectangle': self.translate_channel
                                   }

        # DiGraph that will contain all nodes and channels
        self.dg = nx.DiGraph()

    def channel(self,
                port_from,
                port_to,
                min_length=False,
                min_width=False,
                min_height=False,
                kind='rectangle',
                phase='None'):
        """Create new connection between two nodes/ports with attributes
        consisting of the dimensions of the channel to be used to create the
        SMT equations to calculate solvability of the circuit
        Units are in brackets

        :param str port_from: Port where fluid comes into the channel from
        :param str port_to: Port at the end of the channel where fluid exits
        :param float min_length: Constrain channel to be this long (m)
        :param float width: Constrain channel to be this wide (m)
        :param float height: Constrain channel to be this wide (m)
        :param str kind: Kind of cross section of the channel (rectangle)
        :param str phase: For channels connecting to a T-junction this must be
            either continuous, dispersed or output
        :returns: None -- no issues with creating this channel
        :raises: TypeError if an input parameter is wrong type
                 ValueError if an input parameter has an invalid value
        """
        # Collection of the kinds for which there are methods to calculate their
        # channel resistance
        valid_kinds = ("rectangle")

        # Checking that arguments are valid
        if kind not in valid_kinds:
            raise ValueError("Valid channel kinds are: %s" % valid_kinds)
        if port_from not in self.dg.nodes:
            raise ValueError("port_from node doesn't exist")
        elif port_to not in self.dg.nodes():
            raise ValueError("port_to node doesn't exist")

        # Add the information about that connection to another dict
        # There's extra parameters in here than in the arguments because they
        # are values calculated by later methods when creating the SMT eqns
        # Channels do not have pressure though, since it decreases linearly
        # across the channel
        attributes = {'kind': kind,
                      'length': Symbol('_'.join([port_from, port_to, 'length']),
                                       REAL),
                      'min_length': min_length,
                      'width': Symbol('_'.join([port_from, port_to, 'width']),
                                      REAL),
                      'min_width': min_width,
                      'height': Symbol('_'.join([port_from, port_to, 'height']),
                                       REAL),
                      'min_height': min_height,
                      'flow_rate': Symbol('_'.join([port_from, port_to, 'flow_rate']),
                                          REAL),
                      'droplet_volume': Symbol('_'.join([port_from, port_to, 'Dvol']),
                                               REAL),
                      'viscosity': Symbol('_'.join([port_from, port_to, 'viscosity']),
                                          REAL),
                      'resistance': Symbol('_'.join([port_from, port_to, 'res']),
                                           REAL),
                      'phase': phase.lower(),
                      'port_from': port_from,
                      'port_to': port_to
                      }

        # list of values that should all be positive numbers
        not_neg = ['min_length', 'min_width', 'min_height']
        for param in not_neg:
            try:
                if attributes[param] is False:
                    continue
                elif attributes[param] < 0:
                    raise ValueError("channel '%s' parameter '%s' must be >= 0"
                                     % (param))
            except TypeError as e:
                raise TypeError("channel %s parameter must be int" % param)
            except ValueError as e:
                raise ValueError(e)

        # Can't have two of the same channel
        if (port_from, port_to) in self.dg.edges:
            raise ValueError("Channel already exists between these nodes")
        # Create this edge in the graph
        self.dg.add_edge(port_from, port_to)

        # Add argument to attributes within NetworkX
        for key, attr in attributes.items():
            self.dg.edges[port_from, port_to][key] = attr
        return

    def port(self,
             name,
             kind,
             min_pressure=False,
             min_flow_rate=False,
             x=False,
             y=False,
             fluid_name='default'):
        """Create new port where fluids can enter or exit the circuit, any
        optional tag left empty will be converted to a variable for the SMT
        solver to solve for a give a value, units in brackets

        :param str name: The name of the port to use when defining channels
        :param str kind: Define if this is an 'input' or 'output' port
        :param float density: Density of fluid (kg/m^3)
        :param float min_viscosity: Viscosity of the fluid (Pa*s)
        :param float min_pressure: Pressure of the input fluid, (Pa)
        :param float min_flow_rate - flow rate of input fluid, (m^3/s)
        :param float X: x-position of port on chip schematic (m)
        :param float Y: y-position of port on chip schematic (m)
        :returns: None -- no issues with creating this port
        :raises: TypeError if an input parameter is wrong type
                 ValueError if an input parameter has an invalid value
        """
        # Checking that arguments are valid
        if not isinstance(name, str) or not isinstance(kind, str):
            raise TypeError("name and kind must be strings")
        if name in self.dg.nodes:
            raise ValueError("Must provide a unique name")
        if kind.lower() not in self.translation_strats.keys():
            raise ValueError("kind must be %s" % self.translation_strats.keys())

        # Initialize fluid properties
        fluid_properties = Fluid(fluid_name)

        # Ports are stored with nodes because ports are just a specific type of
        # node that has a constant flow rate
        # only accept ports of the right kind (input or output)
        attributes = {'kind': kind.lower(),
                      'viscosity': Symbol(name+'_viscosity', REAL),
                      'min_viscosity': fluid_properties.min_viscosity,
                      'pressure': Symbol(name+'_pressure', REAL),
                      'min_pressure': min_pressure,
                      'flow_rate': Symbol(name+'_flow_rate', REAL),
                      'min_flow_rate': min_flow_rate,
                      'density': Symbol(name+'_density', REAL),
                      'min_density': fluid_properties.min_density,
                      'x': Symbol(name+'_X', REAL),
                      'y': Symbol(name+'_Y', REAL),
                      'min_x': x,
                      'min_y': y
                      }

        # list of values that should all be positive numbers
        not_neg = ['min_x', 'min_y', 'min_pressure', 'min_flow_rate',
                   'min_viscosity', 'min_density']
        for param in not_neg:
            try:
                if attributes[param] is False:
                    continue
                elif attributes[param] < 0:
                    raise ValueError("port '%s' parameter '%s' must be >= 0" %
                                     (name, param))
            except TypeError as e:
                raise TypeError("port '%s' parameter '%s' must be int" %
                                (name, param))
            except ValueError as e:
                raise ValueError(e)

        # Create this node in the graph
        self.dg.add_node(name)
        # Add argument to attributes within NetworkX
        for key, attr in attributes.items():
            self.dg.nodes[name][key] = attr
        return

    def node(self, name, x=False, y=False, kind='node'):
        """Create new node where fluids merge or split, kind of node (T-junction,
        Y-junction, cross, etc.) can be specified if not then a basic node
        connecting multiple channels will be created, units in brackets

        :param str name: Name of the node to use when connecting to a channel
        :param float x:  Set the X position of this node (m)
        :param float y:  Set the Y position of this node (m)
        :param str kind: The type of node this is, default is node, other
            option is t-junction
        :returns: None -- no issues with creating this node
        :raises: TypeError if an input parameter is wrong type
                 ValueError if an input parameter has an invalid value
        """
        # Checking that arguments are valid
        if not isinstance(name, str) or not isinstance(kind, str):
            raise TypeError("name and kind must be strings")
        if name in self.dg.nodes:
            raise ValueError("Must provide a unique name")
        if kind.lower() not in self.translation_strats.keys():
            raise ValueError("kind must be %s" % self.translation_strats.keys())

        # Ports are stored with nodes because ports are just a specific type of
        # node that has a constant flow rate only accept ports of the right
        # kind (input or output)
        # While the user can't define most parameters for a node because it
        # doesnt take an input from outside the chip, they're still added
        # and set to zero so checks to each node to see if there is a min
        # value for each node doesn't raise a KeyError
        attributes = {'kind': kind.lower(),
                      'pressure': Symbol(name+'_pressure', REAL),
                      'min_pressure': None,
                      'flow_rate': Symbol(name+'_flow_rate', REAL),
                      'min_flow_rate': None,
                      'viscosity': Symbol(name+'_viscosity', REAL),
                      'min_viscosity': None,
                      'density': Symbol(name+'_density', REAL),
                      'min_density': None,
                      'x': Symbol(name+'_X', REAL),
                      'y': Symbol(name+'_Y', REAL),
                      'min_x': x,
                      'min_y': y
                      }

        # list of values that should all be positive numbers
        not_neg = ['min_x', 'min_y']
        for param in not_neg:
            try:
                if attributes[param] < 0:
                    raise ValueError("port '%s' parameter '%s' must be >= 0" %
                                     (name, param))
            except TypeError as e:
                raise TypeError("Port '%s' parameter '%s' must be int" %
                                (name, param))
            except ValueError as e:
                raise ValueError(e)

        # Create this node in the graph
        self.dg.add_node(name)
        # Add argument to attributes within NetworkX
        for key, attr in attributes.items():
                self.dg.nodes[name][key] = attr
        return

    def translate_chip(self, name):
        """Create SMT expressions for bounding the nodes to be within constraints
        of the overall chip such as its area provided

        :param name: Name of the node to be constrained
        :returns: None -- no issues with translating the chip constraints
        """
        named_node = self.dg.nodes[name]
        self.exprs.append(GE(named_node['x'], Real(self.dim[0])))
        self.exprs.append(GE(named_node['y'], Real(self.dim[1])))
        self.exprs.append(LE(named_node['x'], Real(self.dim[2])))
        self.exprs.append(LE(named_node['y'], Real(self.dim[3])))
        return

    def translate_node(self, name):
        """Create SMT expressions for bounding the parameters of an node
        to be within the constraints defined by the user

        :param name: Name of the node to be constrained
        :returns: None -- no issues with translating the port parameters to SMT
        """
        # Name is just a string, this gets the corresponding dictionary of
        # attributes and their values stored by NetworkX
        named_node = self.dg.nodes[name]

        # Pressure at a node is the sum of the pressures flowing into it
        output_pressures = []
        for node_name in self.dg.pred[name]:
            # This returns the nodes with channels that flowing into this node
            # pressure calculated based on P=QR
            # Could modify equation based on https://www.dolomite-microfluidics.com/wp-content/uploads/Droplet_Junction_Chip_characterisation_-_application_note.pdf
            output_pressures.append(self.channel_output_pressure((node_name, name)))
        if len(self.dg.pred[name]) == 1:
            self.exprs.append(Equals(named_node['pressure'],
                                     output_pressures[0]
                                     ))
        elif len(self.dg.pred[name]) > 1:
            self.exprs.append(Equals(named_node['pressure'],
                                     Plus(output_pressures)
                                     ))

        # If parameters are provided by the user, then set the
        # their Symbol equal to that value, otherwise make it greater than 0
        if named_node['min_pressure']:
            # named_node['pressure'] returns a variable for that node for its
            # pressure to be solved for by SMT solver, if min_pressure has a
            # value then a user defined value was provided and this variable
            # is set equal to this value, else simply set its value to be > 0
            # same is true for viscosity, pressure, flow_rate, X, Y and density
            self.exprs.append(Equals(named_node['pressure'],
                                     Real(named_node['min_pressure'])
                                     ))
        else:
            self.exprs.append(GT(named_node['pressure'], Real(0)))

        if named_node['min_x']:
            self.exprs.append(Equals(named_node['x'], Real(named_node['min_x'])))
            self.exprs.append(Equals(named_node['y'], Real(named_node['min_y'])))
        else:
            self.exprs.append(GE(named_node['x'], Real(0)))
            self.exprs.append(GE(named_node['y'], Real(0)))

        if named_node['min_flow_rate']:
            self.exprs.append(Equals(named_node['flow_rate'],
                                     Real(named_node['min_flow_rate'])
                                     ))
        else:
            self.exprs.append(GT(named_node['flow_rate'], Real(0)))
        if named_node['min_viscosity']:
            self.exprs.append(Equals(named_node['viscosity'],
                                     Real(named_node['min_viscosity'])
                                     ))
        else:
            self.exprs.append(GT(named_node['viscosity'], Real(0)))

        if named_node['min_density']:
            self.exprs.append(Equals(named_node['density'],
                                     Real(named_node['min_density'])
                                     ))
        else:
            self.exprs.append(GT(named_node['density'], Real(0)))
        return

    def translate_input(self, name):
        """Create SMT expressions for bounding the parameters of an input port
        to be within the constraints defined by the user

        :param name: Name of the port to be constrained
        :returns: None -- no issues with translating the port parameters to SMT
        """
        if self.dg.size(name) <= 0:
            raise ValueError("Port %s must have 1 or more connections" % name)
        # Currently don't support this, and I don't think it would be the case
        # in real circuits, an input port is the beginning of the traversal
        if len(list(self.dg.predecessors(name))) != 0:
            raise ValueError("Cannot have channels into input port %s" % name)

        # Since input is a type of node, call translate node
        self.translate_node(name)

        # Name is just a string, this gets the corresponding dictionary of
        # attributes and their values stored by NetworkX
        named_node = self.dg.nodes[name]

        # Calculate flow rate for this port based on pressure and channels out
        # if not specified by user
        if not named_node['min_flow_rate']:
            flow_rate = self.calculate_port_flow_rate(name)
            self.exprs.append(Equals(named_node['flow_rate'], flow_rate))

        # To recursively traverse, call on all successor channels
        for node_out in self.dg.succ[name]:
            self.translation_strats[self.dg.edges[(name, node_out)]['kind']](
                    (name, node_out))
        return

    def translate_output(self, name):
        """Create SMT expressions for bounding the parameters of an output port
        to be within the constraints defined by the user

        :param str name: Name of the port to be constrained
        :returns: None -- no issues with translating the port parameters to SMT
        """
        if self.dg.size(name) <= 0:
            raise ValueError("Port %s must have 1 or more connections" % name)
        # Currently don't support this, and I don't think it would be the case
        # in real circuits, an output port is considered the end of a branch
        if len(list(self.dg.succ[name])) != 0:
            raise ValueError("Cannot have channels out of output port %s" % name)

        # Since input is just a specialized node, call translate node
        self.translate_node(name)

        # Name is just a string, this gets the corresponding dictionary of
        # attributes and their values stored by NetworkX
        named_node = self.dg.nodes[name]
        # Calculate flow rate for this port based on pressure and channels out
        # if not specified by user
        if not named_node['min_flow_rate']:
            # The flow rate at this node is the sum of the flow rates of the
            # the channel coming in (I think, should be verified)
            total_flow_in = []
            for channel_in in self.dg.pred[name]:
                total_flow_in.append(self.dg.edges[(channel_in, name)]
                                     ['flow_rate'])
            if len(total_flow_in) == 1:
                self.exprs.append(Equals(named_node['flow_rate'],
                                         total_flow_in[0]))
            else:
                self.exprs.append(Equals(named_node['flow_rate'],
                                         Plus(total_flow_in)))
        return

    # TODO: Refactor to use different formulas depending on the kind of the channel
    def translate_channel(self, name):
        """Create SMT expressions for a given channel (edges in NetworkX naming)
        currently only works for channels with a rectangular shape, but should
        be expanded to include circular and parabolic

        :param str name: The name of the channel to generate SMT equations for
        :returns: None -- no issues with translating channel parameters to SMT
        :raises: KeyError, if channel is not found in the list of defined edges
        """
        try:
            named_channel = self.dg.edges[name]
        except KeyError:
            raise KeyError('Channel with ports %s was not defined' % name)

        # Name is just a string, this gets the corresponding dictionary of
        # attributes and their values stored by NetworkX
        port_in_name = named_channel['port_from']
        port_out_name = named_channel['port_to']
        port_in = self.dg.nodes[port_in_name]
        port_out = self.dg.nodes[port_out_name]

        # Create expression to force length to equal distance between end nodes
        self.exprs.append(self.pythagorean_length(name))

        # Set the length determined by pythagorean theorem equal to the user
        # provided number if provided, else assert that the length be greater
        # than 0, same for width and height
        if named_channel['min_length']:
            self.exprs.append(Equals(named_channel['length'],
                                     Real(named_channel['min_length'])))
        else:
            self.exprs.append(GT(named_channel['length'], Real(0)))
        if named_channel['min_width']:
            self.exprs.append(Equals(named_channel['width'],
                                     Real(named_channel['min_width'])))
        else:
            self.exprs.append(GT(named_channel['width'], Real(0)))
        if named_channel['min_height']:
            self.exprs.append(Equals(named_channel['height'],
                                     Real(named_channel['min_height'])))
        else:
            self.exprs.append(GT(named_channel['height'], Real(0)))

        # Assert that viscosity in channel equals input node viscosity
        # Set output viscosity to equal input since this should be constant
        # This must be performed before calculating resistance
        self.exprs.append(Equals(named_channel['viscosity'],
                                 port_in['viscosity']))
        self.exprs.append(Equals(port_out['viscosity'],
                                 port_in['viscosity']))

        # Pressure at end of channel is lower based on the resistance of
        # the channel as calculated by calculate_channel_resistance and
        # pressure_out = pressure_in * (flow_rate * resistance)
        resistance_list = self.calculate_channel_resistance(name)

        # First term is assertion that each channel's height is less than width
        # which is needed to make resistance formula valid, second is the SMT
        # equation for the resistance, then assert resistance is >0
        self.exprs.append(resistance_list[0])
        resistance = resistance_list[1]
        self.exprs.append(Equals(named_channel['resistance'], resistance))
        self.exprs.append(GT(named_channel['resistance'], Real(0)))

        # Assert flow rate equal to the flow rate coming in
        self.exprs.append(Equals(named_channel['flow_rate'],
                                 port_in['flow_rate']))

        # Channels do not have pressure because it decreases across channel
        # Call translate on the output to continue traversing the channel
        self.translation_strats[port_out['kind']](port_out_name)
        return

    def translate_tjunc(self, name, crit_crossing_angle=0.5):
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
        # Validate input
        if self.dg.size(name) != 3:
            raise ValueError("T-junction %s must have 3 connections" % name)

        # Since T-junction is just a specialized node, call translate node
        self.translate_node(name)

        # Since there should only be one output node, this can be found first
        # from the dict of successors
        try:
            output_node_name = list(dict(self.dg.succ[name]).keys())[0]
            output_node = self.dg.nodes[output_node_name]
            output_channel = self.dg[name][output_node_name]
        except KeyError as e:
            raise KeyError("T-junction must have only one output")
        # Renaming for consistency with the other nodes
        junction_node_name = name
        junction_node = self.dg.nodes[name]
        # these will be found later from iterating through the dict of
        # predecessor nodes to the junction node
        continuous_node = ''
        continuous_node_name = ''
        continuous_channel = ''
        dispersed_node = ''
        dispersed_node_name = ''
        dispersed_channel = ''

        # NetworkX allows for the creation of dicts that contain all of
        # the edges containing a certain attribute, in this case phase is
        # of interest
        phases = nx.get_edge_attributes(self.dg, 'phase')
        for pred_node, phase in phases.items():
            if phase == 'continuous':
                continuous_node_name = pred_node[0]
                continuous_node = self.dg.nodes[continuous_node_name]
                continuous_channel = self.dg[continuous_node_name][junction_node_name]
                # assert width and height to be equal to output
                self.exprs.append(Equals(continuous_channel['width'],
                                         output_channel['width']
                                         ))
                self.exprs.append(Equals(continuous_channel['height'],
                                         output_channel['height']
                                         ))
            elif phase == 'dispersed':
                dispersed_node_name = pred_node[0]
                dispersed_node = self.dg.nodes[dispersed_node_name]
                dispersed_channel = self.dg[dispersed_node_name][junction_node_name]
                # Assert that only the height of channel be equal
                self.exprs.append(Equals(dispersed_channel['height'],
                                         output_channel['height']
                                         ))
            elif phase == 'output':
                continue
            else:
                raise ValueError("Invalid phase for T-junction: %s" % name)

        # Epsilon, sharpness of T-junc, must be greater than 0
        epsilon = Symbol('epsilon', REAL)
        self.exprs.append(GE(epsilon, Real(0)))

        # TODO: Figure out why original had this cause it doesn't seem true
        #  # Pressure at each of the 4 nodes must be equal
        #  self.exprs.append(Equals(junction_node['pressure'],
        #                           continuous_node['pressure']
        #                           ))
        #  self.exprs.append(Equals(junction_node['pressure'],
        #                           dispersed_node['pressure']
        #                           ))
        #  self.exprs.append(Equals(junction_node['pressure'],
        #                           output_node['pressure']
        #                           ))

        # Viscosity in continous phase equals viscosity at output
        self.exprs.append(Equals(continuous_node['viscosity'],
                                 output_node['viscosity']
                                 ))

        # Flow rate into the t-junction equals the flow rate out
        self.exprs.append(Equals(Plus(continuous_channel['flow_rate'],
                                      dispersed_channel['flow_rate']
                                      ),
                                 output_channel['flow_rate']
                                 ))

        # Assert that continuous and output channels are in a straight line
        self.exprs.append(self.channels_in_straight_line(continuous_node_name,
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
        v_output = output_channel['droplet_volume']
        self.exprs.append(Equals(v_output,
                                 self.calculate_droplet_volume(
                                     output_channel['height'],
                                     output_channel['width'],
                                     dispersed_channel['width'],
                                     epsilon,
                                     dispersed_node['flow_rate'],
                                     continuous_node['flow_rate']
                                 )))

        # Assert critical angle is <= calculated angle
        cosine_squared_theta_crit = Real(math.cos(
            math.radians(crit_crossing_angle))**2)
        # Continuous to dispersed
        self.exprs.append(LE(cosine_squared_theta_crit,
                             self.cosine_law_crit_angle(continuous_node_name,
                                                        junction_node_name,
                                                        dispersed_node_name
                                                        )))
        # Continuous to output
        self.exprs.append(LE(cosine_squared_theta_crit,
                             self.cosine_law_crit_angle(continuous_node_name,
                                                        junction_node_name,
                                                        output_node_name
                                                        )))
        # Output to dispersed
        self.exprs.append(LE(cosine_squared_theta_crit,
                             self.cosine_law_crit_angle(output_node_name,
                                                        junction_node_name,
                                                        dispersed_node_name
                                                        )))
        # Call translate on output
        self.translation_strats[output_node['kind']](output_node_name)

    def channels_in_straight_line(self, node1_name, node2_name, node3_name):
        """Create expressions to assert that 2 channels are in a straight
        line with each other by asserting that a triangle between the 2
        end nodes and the middle node has zero area

        :channel_name1: Name of one of the channels
        :channel_name2: Name of the other channel
        :returns: Expression asserting area of triangle formed between all
            three nodes to be 0
        """
        # Check that these nodes connect
        try:
            self.dg[node1_name][node2_name]
            self.dg[node2_name][node3_name]
        except TypeError as e:
            raise TypeError("Tried asserting that 2 channels are in a straight\
                line but they aren't connected")

        node1_named = self.dg.nodes[node1_name]
        node2_named = self.dg.nodes[node2_name]
        node3_named = self.dg.nodes[node3_name]

        # Constrain that continuous and output ports are in a straight line by
        # setting the area of the triangle formed between those two points and
        # the center of the t-junct to be 0
        # Formula for area of a triangle given 3 points
        # x_i (y_p − y_j ) + x_p (y_j − y_i ) + x_j (y_i − y_p ) / 2
        return Equals(Real(0),
                      Div(Plus(Times(node1_named['x'],
                                     Minus(node3_named['y'], node2_named['y'])
                                     ),
                               Plus(Times(node3_named['x'],
                                          Minus(node2_named['y'], node1_named['y'])
                                          ),
                                    Times(node2_named['x'],
                                          Minus(node1_named['y'], node3_named['y'])
                                          ))),
                          Real(2)
                          ))

    # TODO: In Manifold this has the option for worst case analysis, which is
    #       used to adjust the constraints in the case when there is no
    #       solution to try and still find a solution, should implement
    def simple_pressure_flow(self, channel_name):
        """Assert difference in pressure at the two end nodes for a channel
        equals the flow rate in the channel times the channel resistance
        More complicated calculation available through
        analytical_pressure_flow method (TBD)

        :param str channel_name: Name of the channel
        :returns: SMT expression of equality between delta(P) and Q*R
        """
        channel = self.dg.edges[channel_name]
        port_from_name = channel['port_from']
        port_from = self.dg.nodes[port_from_name]
        port_to_name = channel['port_to']
        port_to = self.dg.nodes[port_to_name]
        p1 = port_from['pressure']
        p2 = port_to['pressure']
        Q = channel['flow_rate']
        R = channel['resistance']
        return Equals(Minus(p1, p2),
                      Times(Q, R)
                      )

    def channel_output_pressure(self, channel_name):
        """Calculate the pressure at the output of a channel using
        P_out = R * Q - P_in
        Unit for pressure is Pascals - kg/(m*s^2)

        :param str channel_name: Name of the channel
        :returns: SMT expression of the difference between pressure
            into the channel and R*Q
        """
        channel = self.dg.edges[channel_name]
        P_in = self.dg.nodes[channel_name[0]]['pressure']
        R = channel['resistance']
        Q = channel['flow_rate']
        return Minus(P_in,
                     Times(R, Q))

    def calculate_channel_resistance(self, channel_name):
        """Calculate the droplet resistance in a channel using:
        R = (12 * mu * L) / (w * h^3 * (1 - 0.630 (h/w)) )
        This formula assumes that channel height < width, so
        the first term returned is the assertion for that
        Unit for resistance is kg/(m^4*s)

        :param str channel_name: Name of the channel
        :returns: list -- two SMT expressions, first asserts
            that channel height is less than width, second
            is the above expression in SMT form
        """
        channel = self.dg.edges[channel_name]
        w = channel['width']
        h = channel['height']
        mu = channel['viscosity']
        chL = channel['length']
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

    def pythagorean_length(self, channel_name):
        """Use Pythagorean theorem to assert that the channel length
        (hypoteneuse) squared is equal to the legs squared so channel
        length is solved for

        :param str channel_name: Name of the channel
        :returns: SMT expression of the equality of the side lengths squared
            and the channel length squared
        """
        channel = self.dg.edges[channel_name]
        port_from = self.dg.nodes[channel_name[0]]
        port_to = self.dg.nodes[channel_name[1]]
        side_a = Minus(port_from['x'], port_to['x'])
        side_b = Minus(port_from['y'], port_to['y'])
        a_squared = Pow(side_a, Real(2))
        b_squared = Pow(side_b, Real(2))
        a_squared_plus_b_squared = Plus(a_squared, b_squared)
        c_squared = Pow(channel['length'], Real(2))
        return Equals(a_squared_plus_b_squared, c_squared)

    def cosine_law_crit_angle(self, node1_name, node2_name, node3_name):
        """Use cosine law to find cos^2(theta) between three points
        node1---node2---node3 to assert that it is less than cos^2(thetaC)
        where thetaC is the critical crossing angle

        :param node1: Outside node
        :param node2: Middle connecting node
        :param node3: Outside node
        :returns: cos^2 as calculated using cosine law (a_dot_b^2/a^2*b^2)
        """
        node1 = self.dg.nodes[node1_name]
        node2 = self.dg.nodes[node2_name]
        node3 = self.dg.nodes[node3_name]
        # Lengths of channels
        aX = Minus(node1['x'], node2['x'])
        aY = Minus(node1['y'], node2['y'])
        bX = Minus(node3['x'], node2['x'])
        bY = Minus(node3['y'], node2['y'])
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
        Calculating the droplet volume created in a T-junction
        Unit is volume in m^3

        :param Symbol h: Height of channel
        :param Symbol w: Width of continuous/output channel
        :param Symbol wIn: Width of dispersed_channel
        :param Symbol epsilon: Equals 0.414*radius of rounded edge where
                               channels join
        :param Symbol qD: Flow rate in dispersed_channel
        :param Symbol qC: Flow rate in continuous_channel
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

    def calculate_port_flow_rate(self, port_name):
        """Calculate the flow rate into a port based on the cross sectional
        area of the channel it flows into, the pressure and the density
        eqn from https://en.wikipedia.org/wiki/Hagen-Poiseuille_equation
        flow_rate = area * sqrt(2*pressure/density)
        Unit for flow rate is m^3/s

        :param str port_name: Name of the port
        :returns: Flow rate determined from port pressure and area of
                  connected channels
        """
        areas = []
        port_named = self.dg.nodes[port_name]
        for port_out in self.dg.succ[port_name]:
            areas.append(Times(self.dg[port_name][port_out]['length'],
                               self.dg[port_name][port_out]['width']
                               ))
        total_area = Plus(areas)
        return Times(total_area,
                     Pow(Div(Times(Real(2),
                                   port_named['pressure']
                                   ),
                             port_named['density']
                             ),
                         Real(0.5)
                         ))

    def translate_schematic(self):
        """Validates that each node has the correct input and output
        conditions met then translates it into pysmt syntax
        Generates SMT formulas to simulate specialized nodes like T-junctions
        and stores them in self.exprs
        """
        # if schematic has no input then it is invalid
        has_input = False

        # The translate method names are stored in a dictionary name where
        # the key is the kind of that node and Call on all input nodes and it
        # will recursive traverse the circuit
        for name in self.dg.nodes:
            kind = self.dg.nodes[name]['kind']
            if kind == 'input':
                has_input = True
                # first ensure that it has an output
                has_output = False
                # TODO: Need to create list of output + input nodes to see if
                #       they connect
                for x, y in self.dg.nodes(data=True):
                    if y['kind'] == 'output':
                        has_output = True
                        # Input has output, so call translate on input
                        self.translation_strats[kind](name)
                if not has_output:
                    raise ValueError('Schematic input %s has no output' % name)
        if not has_input:
            raise ValueError('Schematic has no input')

        # finish by constraining nodes to be within chip area
        for name in self.dg.nodes:
            self.translate_chip(name)
        return

    def invoke_backend(self, _show):
        """Combine all of the SMT expressions into one expression to sent to Z3
        solver to determine solvability

        :param bool show: If true then the full SMT formula that was created is
                          printed
        :returns: pySMT model showing the values for each of the parameters
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

        :param bool show: If true then the full SMT formula that was created is
                          printed
        :returns: pySMT model showing the values for each of the parameters
        """
        self.translate_schematic()
        return self.invoke_backend(show)

    def to_json(self):
        
        """Converts designed schematic to a json file following Manifold IR grammar"""
        json_out = json_graph.node_link_data(self.dg)
        stuff = [str(i) for i in json_out['links']] 
        edits = dict(self.solve())
        edits1 = {str(key):str(value) for key, value in edits.items()}
        fin_edits = {str(key):str(value) for key, value in edits.items()}
		
        for key, value in edits1.items():
            if value[-1] == '?':
                final_val1 = float(value[:-1])
                fin_edits[key] = final_val1
            if '/' in value:
                s_list = value.split('/')
                val_list = [float(i) for i in s_list]
                final_val2 = val_list[0] / val_list[1]
                fin_edits[key] = final_val2
        
        for key, value in fin_edits.items():
            if type(value) == str:
                fin_edits[key] = float(value)
        pprint(fin_edits)

        for sub in json_out['links']:
            for key in sub:
                if type(sub[key]) != bool and type(sub[key]) != int and type(sub[key]) != float:
                    sub[key] = str(sub[key])
		
        for sub in json_out['nodes']:
            for key in sub:
                if type(sub[key]) != bool and type(sub[key]) != int and type(sub[key]) != float:
                    sub[key] = str(sub[key])

        for key, value in fin_edits.items():
            for sub in json_out['links']:
                for stuff in sub:
                    if key == sub[stuff]:
                        sub[stuff] = value
            for sub in json_out['nodes']:
                for stuff in sub:
                    if key == sub[stuff]:
                        sub[stuff] = value

        pprint(json_out)

        wow = {
                "name": "Json Data",
                "userDefinedTypes": {...},
                "portTypes": { 
                    "name": { 
                        "signalType": "...", 
                        "attributes": {...}
		             },
                 },
                "nodeTypes": { 
                    "name": { 
                        "attributes": {...},
                        "ports": {...}
                     },
                 },
                "constraintTypes": {...},
                "nodes": { 
                    "name": { 
                        "type": "...",
                        "attributes": {...},
                        "portAttrs": {...}
                     },
                 },
                "connections": { 
                    "name": { 
                        "attributes": {...},
                        "from": "...",
                        "to": "..."
                     },
                 },
                "constraints": {...}
            }
        pprint(wow)

        path = "C:\\Users\\msacw\\AppData\\Local\\Programs\\Python\\Python36\\test.json"
        with open(path, 'w') as outfile:
            json.dump(json_out, outfile, separators=(',', ':'))
