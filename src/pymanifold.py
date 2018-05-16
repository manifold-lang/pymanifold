import sys
from pysmt.shortcuts import Symbol, Int, Plus, Times, Div, Pow, is_sat


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

        # Add new node types and their validation method to this dict
        # to maintain consistent checking across all methods
        self.translate_ports = {'input': self.translate_input,
                                'output': self.translate_output
                                }
        self.translate_nodes = {'t-junction': self.translate_tjunc
                                }

    # should length, width, height have default values to simplify startup
    def channel(self, shape, length, width, height, port_from, port_to, phase='None'):
        """Create new connection between two nodes/ports with attributes
        consisting of the dimensions of the channel to be used to create the
        SMT2 equation to calculate solvability of the circuit
        """
        valid_shapes = ("rectangle")
        # Checking that arguments are valid
        if not isinstance(shape, str) or not isinstance(port_from, str)\
                or not isinstance(port_to, str):
            tb = sys.exc_info()[2]
            raise TypeError("shape of channel, input and output ports must be\
                    strings").with_traceback(tb)
        if shape not in valid_shapes:
            tb = sys.exc_info()[2]
            raise ValueError("Valid channel shapes are: %s"
                             % valid_shapes).with_traceback(tb)
        if port_from not in self.nodes.keys():
            tb = sys.exc_info()[2]
            raise ValueError("port_from node doesn't exist")
        elif port_to not in self.nodes.keys():
            tb = sys.exc_info()[2]
            raise ValueError("port_to node doesn't exist")

        # If that fluid entry node already exists then that means there is
        # another node that it flows out to so append that exit node to list
        try:
            # Can't have two of the same channel
            if port_to in self.connections[port_from]:
                tb = sys.exc_info()[2]
                raise ValueError("Channel already exists between these nodes")\
                    .with_traceback(tb)
            self.connections[port_from].append(port_to)
        except KeyError:
            self.connections[port_from] = [port_to]

        # Add the information about that connection to another dict
        # TODO this needs to have both from and to ports to make it unique,
        # but checking for keys would require checking both combinations,
        # refactor the code to make port, node and channel objects instead of methods!
        self.channels[port_from] = {'length': length,
                                    'width': width,
                                    'height': height,
                                    'phase': phase
                                    }
        return

    def port(self, name, direction, viscosity=1):
        """Create new port where fluids can enter or exit the circuit, viscosity
        and directions needs to be specified
        """
        # Checking that arguments are valid
        if not isinstance(name, str) or not isinstance(direction, str):
            tb = sys.exc_info()[2]
            raise TypeError("name and direction must be strings")\
                .with_traceback(tb)
        if name in self.nodes.keys():
            tb = sys.exc_info()[2]
            raise ValueError("Must provide a unique name")\
                .with_traceback(tb)

        # Ports are stores with nodes because ports are just a specific type of
        # node that has a constant flow rate
        if direction.lower() in self.translate_ports.keys():
            self.nodes[name] = [direction.lower(), viscosity]
        else:
            tb = sys.exc_info()[2]
            raise ValueError("direction must be %s" %
                             self.translate_ports.keys()).with_traceback(tb)

    def node(self, name, design):
        """Create new node where fluids merge or split, design of the node
        (T-junction, Y-junction, cross, etc.) needs to be specified
        """
        # Checking that arguments are valid
        if not isinstance(name, str) or not isinstance(design, str):
            tb = sys.exc_info()[2]
            raise TypeError("design must be a string")\
                .with_traceback(tb)
        if name in self.nodes.keys():
            tb = sys.exc_info()[2]
            raise ValueError("Must provide a unique name")\
                .with_traceback(tb)

        if design.lower() in self.translate_nodes.keys():
            self.nodes[name] = [design.lower()]
        else:
            tb = sys.exc_info()[2]
            raise ValueError("design name not valid, only %s are valid" %
                             self.translate_nodes.keys()).with_traceback(tb)

    def translate_input(self, name):
        # Validate input
        num_connections = len(self.connections[name])
        if num_connections <= 0:
            tb = sys.exc_info()[2]
            raise ValueError("Port %s must have 1 or more connections" % name)\
                .with_traceback(tb)

    def translate_output(self, name):
        # Validate input
        num_connections = len(self.connections[name])
        if num_connections <= 0:
            tb = sys.exc_info()[2]
            raise ValueError("Port %s must have 1 or more connections" % name)\
                .with_traceback(tb)

    def translate_tjunc(self, name):
        # Validate input
        num_connections = len(self.connections[name]) +\
            len([key for key, value in self.connections.items()
                if name in value])
        if num_connections != 3:
            tb = sys.exc_info()[2]
            raise ValueError("T-junction %s must have 3 connections" % name)\
                .with_traceback(tb)

        # TODO: May want to refactor code to make nodes objects that have a
        # getFrom and getTo method to save iterating over list of connections
        # however this would require a separate method for creating JSON IR
        epsilon = Symbol('epsilon', long)
        output = self.connections[name]
        for key, value in self.connections.items():
            if name in value:
                if self.channels[key]['phase'] == 'continuous':
                    continuous = key
                elif self.channels[key]['phase'] == 'dispersed':
                    dispersed = key
                else:
                    tb = sys.exc_info()[2]
                    raise ValueError("Invalid phase for T-junction: %s" %
                                     name).with_traceback(tb)


    def translate_schematic(self):
        """Validates that each node has the correct input and output
        conditions met then translates it into pysmt syntax
        """
        for name, attributes in self.nodes.items():
            try:
                self.translate_nodes[name](name)
            except KeyError:
                self.translate_ports[name](name)

    def invoke_backend(self):

    def solve(self):
        """Create the SMT2 equation for this schematic outlining the design
        of a microfluidic circuit and use Z3 to solve it using pysmt
        """
        # TODO translate schematic method
        # TODO convert schematic to SMT2 expressions method
        self.translate_schematic()
        return self.invoke_backend()

