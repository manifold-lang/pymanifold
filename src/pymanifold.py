from pprint import pprint
import math
import networkx as nx
#  import matplotlib.pyplot as plt  # include if you want to show graph
#  from pysmt.shortcuts import Variable, Plus, Times, Div, Pow, Equals, Real
#  from pysmt.shortcuts import Minus, GE, GT, LE, LT, And, get_model, is_sat
from build.lib.data.dreal.symbolic import Variable, logical_and, sin, cos
from build.lib.data.dreal.api import CheckSatisfiability, Minimize
#  from pysmt.typing import REAL
#  from pysmt.logics import QF_NRA


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
                      'length': Variable('_'.join([port_from, port_to, 'length'])),
                      'min_length': min_length,
                      'width': Variable('_'.join([port_from, port_to, 'width'])),
                      'min_width': min_width,
                      'height': Variable('_'.join([port_from, port_to, 'height'])),
                      'min_height': min_height,
                      'flow_rate': Variable('_'.join([port_from, port_to, 'flow_rate'])),
                      'droplet_volume': Variable('_'.join([port_from, port_to, 'Dvol'])),
                      'viscosity': Variable('_'.join([port_from, port_to, 'viscosity'])),
                      'resistance': Variable('_'.join([port_from, port_to, 'res'])),
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
             density=False,
             min_viscosity=False):
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

        # Ports are stored with nodes because ports are just a specific type of
        # node that has a constant flow rate
        # only accept ports of the right kind (input or output)
        attributes = {'kind': kind.lower(),
                      'viscosity': Variable(name+'_viscosity'),
                      'min_viscosity': min_viscosity,
                      'pressure': Variable(name+'_pressure'),
                      'min_pressure': min_pressure,
                      'flow_rate': Variable(name+'_flow_rate'),
                      'min_flow_rate': min_flow_rate,
                      'density': Variable(name+'_density'),
                      'min_density': density,
                      'x': Variable(name+'_X'),
                      'y': Variable(name+'_Y'),
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
                      'pressure': Variable(name+'_pressure'),
                      'min_pressure': None,
                      'flow_rate': Variable(name+'_flow_rate'),
                      'min_flow_rate': None,
                      'viscosity': Variable(name+'_viscosity'),
                      'min_viscosity': None,
                      'density': Variable(name+'_density'),
                      'min_density': None,
                      'x': Variable(name+'_X'),
                      'y': Variable(name+'_Y'),
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

    def retrieve(self, port_in, port_out, attr):
        if isinstance(port_in, tuple):
            return self.dg.edges[port_in][attr]
        elif isinstance(port_in, str):
            if port_out is None:
                return self.dg.nodes[port_in][attr]
            else:
                return self.dg.edges((port_in, port_out))[attr]
        else:
            raise ValueError("Tried to retrieve node or edge type and name\
                    wasn't tuple or string")

    def get_channel_kind(self, port_in, port_out=None):
        return self.retrieve(port_in, port_out, 'kind')

    def get_channel_shape(self, port_in, port_out=None):
        return self.retrieve(port_in, port_out, 'shape')

    def get_channel_length(self, port_in, port_out=None):
        return self.retrieve(port_in, port_out, 'length')

    def get_channel_min_length(self, port_in, port_out=None):
        return self.retrieve(port_in, port_out, 'min_length')

    def get_channel_width(self, port_in, port_out=None):
        return self.retrieve(port_in, port_out, 'width')

    def get_channel_min_width(self, port_in, port_out=None):
        return self.retrieve(port_in, port_out, 'min_width')

    def get_channel_height(self, port_in, port_out=None):
        return self.retrieve(port_in, port_out, 'height')

    def get_channel_min_height(self, port_in, port_out=None):
        return self.retrieve(port_in, port_out, 'min_height')

    def get_channel_flow_rate(self, port_in, port_out=None):
        return self.retrieve(port_in, port_out, 'flow_rate')

    def get_channel_droplet_volume(self, port_in, port_out=None):
        return self.retrieve(port_in, port_out, 'droplet_volume')

    def get_channel_viscosity(self, port_in, port_out=None):
        return self.retrieve(port_in, port_out, 'viscosity')

    def get_channel_resistance(self, port_in, port_out=None):
        return self.retrieve(port_in, port_out, 'resistance')

    def get_channel_phase(self, port_in, port_out=None):
        return self.retrieve(port_in, port_out, 'phase')

    def get_channel_port_from(self, port_in, port_out=None):
        return self.retrieve(port_in, port_out, 'port_from')

    def get_channel_port_to(self, port_in, port_out=None):
        return self.retrieve(port_in, port_out, 'port_to')

    def get_node_kind(self, name):
        return self.retrieve(name, None, 'kind')

    def get_node_pressure(self, name):
        return self.retrieve(name, None, 'pressure')

    def get_node_min_pressure(self, name):
        return self.retrieve(name, None, 'min_pressure')

    def get_node_flow_rate(self, name):
        return self.retrieve(name, None, 'flow_rate')

    def get_node_min_flow_rate(self, name):
        return self.retrieve(name, None, 'min_flow_rate')

    def get_node_viscosity(self, name):
        return self.retrieve(name, None, 'viscosity')

    def get_node_min_viscosity(self, name):
        return self.retrieve(name, None, 'min_viscosity')

    def get_node_density(self, name):
        return self.retrieve(name, None, 'density')

    def get_node_min_density(self, name):
        return self.retrieve(name, None, 'min_density')

    def get_node_x(self, name):
        return self.retrieve(name, None, 'x')

    def get_node_y(self, name):
        return self.retrieve(name, None, 'y')

    def get_node_min_x(self, name):
        return self.retrieve(name, None, 'min_x')

    def get_node_min_y(self, name):
        return self.retrieve(name, None, 'min_y')

    def translate_chip(self, name):
        """Create SMT expressions for bounding the nodes to be within constraints
        of the overall chip such as its area provided

        :param name: Name of the node to be constrained
        :returns: None -- no issues with translating the chip constraints
        """
        self.exprs.append(self.get_node_x(name) >= self.dim[0])
        self.exprs.append(self.get_node_y(name) >= self.dim[1])
        self.exprs.append(self.get_node_x(name) <= self.dim[2])
        self.exprs.append(self.get_node_y(name) <= self.dim[3])
        return

    def translate_node(self, name):
        """Create SMT expressions for bounding the parameters of an node
        to be within the constraints defined by the user

        :param name: Name of the node to be constrained
        :returns: None -- no issues with translating the port parameters to SMT
        """
        # Pressure at a node is the sum of the pressures flowing into it
        output_pressures = []
        for node_name in self.dg.pred[name]:
            # This returns the nodes with channels that flowing into this node
            # pressure calculated based on P=QR
            # Could modify equation based on https://www.dolomite-microfluidics.com/wp-content/uploads/Droplet_Junction_Chip_characterisation_-_application_note.pdf
            output_pressures.append(self.channel_output_pressure((node_name, name)))
        if len(self.dg.pred[name]) == 1:
            self.exprs.append(self.get_node_pressure(name) == output_pressures[0])
        elif len(self.dg.pred[name]) > 1:
            output_pressure_formulas = [a+b for a, b in
                                        zip(output_pressures,
                                            output_pressures[1:])]
            self.exprs.append(self.get_node_flow_rate(name) ==
                              logical_and(*output_pressure_formulas))

        # If parameters are provided by the user, then set the
        # their Variable equal to that value, otherwise make it greater than 0
        if self.get_node_min_pressure(name):
            # If min_pressure has a value then a user defined value was provided
            # and this variable is set equal to this value, else simply set its
            # value to be >0, same for viscosity, pressure, flow_rate, X, Y and density
            self.exprs.append(self.get_node_pressure(name) ==
                              self.get_node_min_pressure(name))
        else:
            self.exprs.append(self.get_node_pressure(name) > 0)

        if self.get_node_min_x(name):
            self.exprs.append(self.get_node_x(name) == self.get_node_min_x(name))
            self.exprs.append(self.get_node_y(name) == self.get_node_min_y(name))
        else:
            self.exprs.append(self.get_node_x(name) >= 0)
            self.exprs.append(self.get_node_y(name) >= 0)

        if self.get_node_min_flow_rate(name):
            self.exprs.append(self.get_node_flow_rate(name) == self.get_node_min_flow_rate(name))
        else:
            self.exprs.append(self.get_node_flow_rate(name) > 0)
        if self.get_node_min_viscosity(name):
            self.exprs.append(self.get_node_viscosity(name) == self.get_node_min_viscosity(name))
        else:
            self.exprs.append(self.get_node_viscosity(name) > 0)

        if self.get_node_min_density(name):
            self.exprs.append(self.get_node_density(name) == self.get_node_min_density(name))
        else:
            self.exprs.append(self.get_node_density(name) > 0)
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

        # Calculate flow rate for this port based on pressure and channels out
        # if not specified by user
        if not self.get_node_min_flow_rate(name):
            flow_rate = self.calculate_port_flow_rate(name)
            self.exprs.append(self.get_node_flow_rate(name) == flow_rate)

        # To recursively traverse, call on all successor channels
        for node_out in self.dg.succ[name]:
            self.translation_strats[self.get_channel_kind((name, node_out))]((name, node_out))
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

        # Calculate flow rate for this port based on pressure and channels out
        # if not specified by user
        if not self.get_node_min_flow_rate(name):
            # The flow rate at this node is the sum of the flow rates of the
            # the channel coming in (I think, should be verified)
            total_flow_in = []
            for channel_in in self.dg.pred[name]:
                total_flow_in.append(self.dg.edges[(channel_in, name)]
                                     ['flow_rate'])
            if len(total_flow_in) == 1:
                self.exprs.append(self.get_node_flow_rate(name) == total_flow_in[0])
            else:
                total_flow_in_formulas = [a+b for a, b in
                                          zip(total_flow_in, total_flow_in[1:])]
                self.exprs.append(self.get_node_flow_rate(name) ==
                                  logical_and(*total_flow_in_formulas))
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
            self.dg.edges[name]
        except KeyError:
            raise KeyError('Channel with ports %s was not defined' % name)

        # Create expression to force length to equal distance between end nodes
        self.exprs.append(self.pythagorean_length(name))

        # Set the length determined by pythagorean theorem equal to the user
        # provided number if provided, else assert that the length be greater
        # than 0, same for width and height
        if self.get_channel_min_length(name):
            self.exprs.append(self.get_channel_length(name) ==
                              self.get_channel_min_length(name))
        else:
            self.exprs.append(self.get_channel_length(name) > 0)
        if self.get_channel_min_width(name):
            self.exprs.append(self.get_channel_width(name) ==
                              self.get_channel_min_width(name))
        else:
            self.exprs.append(self.get_channel_width(name) > 0)
        if self.get_channel_min_height(name):
            self.exprs.append(self.get_channel_height(name) ==
                              self.get_channel_min_height(name))
        else:
            self.exprs.append(self.get_channel_height(name) > 0)

        # Assert that viscosity in channel equals input node viscosity
        # Set output viscosity to equal input since this should be constant
        # This must be performed before calculating resistance
        self.exprs.append(self.get_channel_viscosity(name) ==
                          self.get_node_viscosity(self.get_channel_port_from(name)))
        self.exprs.append(self.get_node_viscosity(self.get_channel_port_to(name)) ==
                          self.get_node_viscosity(self.get_channel_port_from(name)))

        # Pressure at end of channel is lower based on the resistance of
        # the channel as calculated by calculate_channel_resistance and
        # pressure_out = pressure_in * (flow_rate * resistance)
        resistance_list = self.calculate_channel_resistance(name)

        # First term is assertion that each channel's height is less than width
        # which is needed to make resistance formula valid, second is the SMT
        # equation for the resistance, then assert resistance is >0
        self.exprs.append(resistance_list[0])
        resistance = resistance_list[1]
        self.exprs.append(self.get_channel_resistance(name) == resistance)
        self.exprs.append(self.get_channel_resistance(name) > 0)

        # Assert flow rate equal to the flow rate coming in
        self.exprs.append(self.get_channel_flow_rate(name) ==
                          self.get_node_flow_rate(self.get_channel_port_from(name)))

        # Channels do not have pressure because it decreases across channel
        # Call translate on the output to continue traversing the channel
        self.translation_strats[self.get_node_kind(
                    self.get_channel_port_to(name))](self.get_channel_port_to(name))
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

        # Renaming for consistency with the other nodes
        junction_node_name = name
        # Since there should only be one output node, this can be found first
        # from the dict of successors
        try:
            output_node_name = list(dict(self.dg.succ[name]).keys())[0]
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
        phases = nx.get_edge_attributes(self.dg, 'phase')
        for pred_node, phase in phases.items():
            if phase == 'continuous':
                continuous_node_name = pred_node[0]
                continuous_channel_name = (continuous_node_name, junction_node_name)
                # assert width and height to be equal to output
                self.exprs.append(self.get_channel_width(continuous_channel_name) ==
                                  self.get_channel_width(output_channel_name))
                self.exprs.append(self.get_channel_height(continuous_channel_name) ==
                                  self.get_channel_height(output_channel_name))
            elif phase == 'dispersed':
                dispersed_node_name = pred_node[0]
                dispersed_channel_name = (dispersed_node_name, junction_node_name)
                # Assert that only the height of channel be equal
                self.exprs.append(self.get_channel_height(dispersed_channel_name) ==
                                  self.get_channel_height(output_channel_name))
            elif phase == 'output':
                continue
            else:
                raise ValueError("Invalid phase for T-junction: %s" % name)

        # Epsilon, sharpness of T-junc, must be greater than 0
        epsilon = Variable('epsilon')
        self.exprs.append(epsilon >= 0)

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
        self.exprs.append(self.get_node_viscosity(continuous_node_name) ==
                          self.get_node_viscosity(output_node_name))

        # Flow rate into the t-junction equals the flow rate out
        self.exprs.append(self.get_channel_flow_rate(continuous_channel_name) +
                          self.get_channel_flow_rate(dispersed_channel_name) ==
                          self.get_channel_flow_rate(output_channel_name))

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
        self.exprs.append(self.get_channel_droplet_volume(output_channel_name) ==
                          self.calculate_droplet_volume(
                              self.get_channel_height(output_channel_name),
                              self.get_channel_width(output_channel_name),
                              self.get_channel_width(dispersed_channel_name),
                              epsilon,
                              self.get_node_flow_rate(dispersed_node_name),
                              self.get_node_flow_rate(continuous_node_name)
                                  ))

        # Assert critical angle is <= calculated angle
        cosine_squared_theta_crit = math.cos(math.radians(crit_crossing_angle))**2
        # Continuous to dispersed
        self.exprs.append(cosine_squared_theta_crit <=
                          self.cosine_law_crit_angle(continuous_node_name,
                                                     junction_node_name,
                                                     dispersed_node_name
                                                     ))
        # Continuous to output
        self.exprs.append(cosine_squared_theta_crit <=
                          self.cosine_law_crit_angle(continuous_node_name,
                                                     junction_node_name,
                                                     output_node_name
                                                     ))
        # Output to dispersed
        self.exprs.append(cosine_squared_theta_crit <=
                          self.cosine_law_crit_angle(output_node_name,
                                                     junction_node_name,
                                                     dispersed_node_name
                                                     ))
        # Call translate on output
        self.translation_strats[self.get_node_kind(output_node_name)](output_node_name)

    # NOTE: Should these methods just append to exprs instead of returning the
    #       expression?
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
            self.dg.edges((node1_name, node2_name))
            self.dg.edges((node2_name, node3_name))
        except TypeError as e:
            raise TypeError("Tried asserting that 2 channels are in a straight\
                line but they aren't connected")

        # Constrain that continuous and output ports are in a straight line by
        # setting the area of the triangle formed between those two points and
        # the center of the t-junct to be 0
        # Formula for area of a triangle given 3 points
        # x_i (y_p - y_j) + x_p (y_j - y_i) + x_j (y_i - y_p) / 2
        return (((self.get_node_x(node1_name)) *
                (self.get_node_y(node3_name) - self.get_node_y(node2_name))
                + self.get_node_x(node3_name) *
                (self.get_node_y(node2_name) - self.get_node_y(node1_name))
                + self.get_node_x(node2_name) *
                (self.get_node_y(node1_name) - self.get_node_y(node3_name))) / 2 == 0)

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
        p1 = self.get_node_pressure(self.get_channel_port_from(channel_name))
        p2 = self.get_node_pressure(self.get_channel_port_to(channel_name))
        Q = self.get_channel_flow_rate(channel_name)
        R = self.get_channel_shape(channel_name)
        return ((p1 - p2) == (Q * R))

    def channel_output_pressure(self, channel_name):
        """Calculate the pressure at the output of a channel using
        P_out = R * Q - P_in
        Unit for pressure is Pascals - kg/(m*s^2)

        :param str channel_name: Name of the channel
        :returns: SMT expression of the difference between pressure
            into the channel and R*Q
        """
        P_in = self.get_node_pressure(self.get_channel_port_from(channel_name))
        R = self.get_channel_resistance(channel_name)
        Q = self.get_channel_flow_rate(channel_name)
        return (P_in - (R * Q))

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
        w = self.get_channel_width(channel_name)
        h = self.get_channel_height(channel_name)
        mu = self.get_channel_viscosity(channel_name)
        chL = self.get_channel_length(channel_name)
        return ((h < w),
                ((12 * (mu * chL)) / (w * ((h ** 3) * (1 - (0.63 * (h / w)))))))

    def pythagorean_length(self, channel_name):
        """Use Pythagorean theorem to assert that the channel length
        (hypoteneuse) squared is equal to the legs squared so channel
        length is solved for

        :param str channel_name: Name of the channel
        :returns: SMT expression of the equality of the side lengths squared
            and the channel length squared
        """
        side_a = self.get_node_x(self.get_channel_port_from(channel_name)) -\
            self.get_node_x(self.get_channel_port_to(channel_name))
        side_b = self.get_node_y(self.get_channel_port_from(channel_name)) -\
            self.get_node_y(self.get_channel_port_to(channel_name))
        a_squared_plus_b_squared = side_a ** 2 + side_b ** 2
        c_squared = (self.get_channel_length(channel_name) ** 2)
        return (a_squared_plus_b_squared == c_squared)

    def cosine_law_crit_angle(self, node1_name, node2_name, node3_name):
        """Use cosine law to find cos^2(theta) between three points
        node1---node2---node3 to assert that it is less than cos^2(thetaC)
        where thetaC is the critical crossing angle

        :param node1: Outside node
        :param node2: Middle connecting node
        :param node3: Outside node
        :returns: cos^2 as calculated using cosine law (a_dot_b^2/a^2*b^2)
        """
        # Lengths of channels
        aX = (self.get_node_x(node1_name) - self.get_node_x(node2_name))
        aY = (self.get_node_y(node1_name) - self.get_node_y(node2_name))
        bX = (self.get_node_x(node3_name) - self.get_node_x(node2_name))
        bY = (self.get_node_y(node3_name) - self.get_node_y(node2_name))
        # Dot products between each channel
        a_dot_b_squared = (((aX * bX) + (aY * bY)) ** 2)
        a_squared_b_squared = ((aX * aX) + (aY * aY)) * ((bX * bX) + (bY * bY))

        return (a_dot_b_squared / a_squared_b_squared)

    def calculate_droplet_volume(self, h, w, wIn, epsilon, qD, qC):
        """From paper DOI:10.1039/c002625e.
        Calculating the droplet volume created in a T-junction
        Unit is volume in m^3

        :param Variable h: Height of channel
        :param Variable w: Width of continuous/output channel
        :param Variable wIn: Width of dispersed_channel
        :param Variable epsilon: Equals 0.414*radius of rounded edge where
                               channels join
        :param Variable qD: Flow rate in dispersed_channel
        :param Variable qC: Flow rate in continuous_channel
        """
        q_gutter = 0.1
        # normalizedVFill = 3pi/8 - (pi/2)(1 - pi/4)(h/w)
        v_fill_simple = (3 * (math.pi) / 8) - (math.pi / 2) * (1 - math.pi / 4) * (h / w)

        hw_parallel = ((h * w) / (h + w))

        # r_pinch = w+((wIn-(hw_parallel - eps))+sqrt(2*((wIn-hw_parallel)*(w-hw_parallel))))
        r_pinch = w + ((wIn - (hw_parallel - epsilon)) +
                       (2 * ((wIn - hw_parallel) * (w - hw_parallel))) ** 0.5)
        r_fill = w
        alpha = (1 - (math.pi / 4)) * (((1 - q_gutter) ** -1) *
                     ((((r_pinch / w) ** 2) - ((r_fill / w) ** 2)) +
                     ((math.pi / 4) * (r_pinch / w) - (r_fill / w)) * (h / w)))

        return ((h * (w * w)) * (v_fill_simple + (alpha * (qD / qC))))

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
        port_pressure = self.get_node_pressure(port_name)
        port_density = self.get_node_density(port_name)
        # Calculate cross sectional area of all channels flowing into this port
        for port_out in self.dg.succ[port_name]:
            areas.append(self.get_channel_length((port_name, port_out)) *
                         self.get_channel_width((port_name, port_out))
                         )
        # Add together all these areas if multiple exist
        if len(areas) == 1:
            total_area = areas[0]
        else:
            areas = [a+b for a, b in zip(areas, areas[1:])]
            total_area = logical_and(*areas)
        return (total_area * (((2 * port_pressure) / port_density) ** 0.5))

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
        formula = logical_and(*self.exprs)
        # Prints the generated formula in full, remove serialize for shortened
        if _show:
            #  nx.draw(self.dg)
            #  plt.show()
            print(formula)
        # Return None if not solvable, returns a dict-like structure giving the
        # range of values for each Variable
        model = CheckSatisfiability(formula, 1)
        if model:
            return model
        else:
            return "No solution found"

    def solve(self, show=False):
        """Create the SMT2 equation for this schematic outlining the design
        of a microfluidic circuit and use Z3 to solve it using pysmt

        :param bool show: If true then the full SMT formula that was created is
                          printed
        :returns: dReal model showing the values for each of the parameters
        """
        self.translate_schematic()
        return self.invoke_backend(show)
