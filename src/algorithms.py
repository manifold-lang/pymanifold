import math
from dreal.symbolic import logical_and


def retrieve(dg, port_in, attr):
    if isinstance(port_in, tuple):
        return dg.edges[port_in][attr]
    elif isinstance(port_in, str):
        return dg.nodes[port_in][attr]
    else:
        raise ValueError("Tried to retrieve node or edge type and name\
                wasn't tuple or string")


# NOTE: Should these methods just append to exprs instead of returning the
#       expression?
def channels_in_straight_line(dg, node1_name, node2_name, node3_name):
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
        dg.edges((node1_name, node2_name))
        dg.edges((node2_name, node3_name))
    except TypeError as e:
        raise TypeError("Tried asserting that 2 channels are in a straight\
            line but they aren't connected")

    # Constrain that continuous and output ports are in a straight line by
    # setting the area of the triangle formed between those two points and
    # the center of the t-junct to be 0
    # Formula for area of a triangle given 3 points
    # x_i (y_p - y_j) + x_p (y_j - y_i) + x_j (y_i - y_p) / 2
    return (((retrieve(dg, node1_name, 'x')) *
            (retrieve(dg, node3_name, 'y') - retrieve(dg, node2_name, 'y')) +
            retrieve(dg, node3_name, 'x') *
            (retrieve(dg, node2_name, 'y') - retrieve(dg, node1_name, 'y')) +
            retrieve(dg, node2_name, 'x') *
            (retrieve(dg, node1_name, 'y') - retrieve(dg, node3_name, 'y'))) / 2 == 0)


# TODO: In Manifold this has the option for worst case analysis, which is
#       used to adjust the constraints in the case when there is no
#       solution to try and still find a solution, should implement
def simple_pressure_flow(dg, channel_name):
    """Assert difference in pressure at the two end nodes for a channel
    equals the flow rate in the channel times the channel resistance
    More complicated calculation available through
    analytical_pressure_flow method (TBD)

    :param str channel_name: Name of the channel
    :returns: SMT expression of equality between delta(P) and Q*R
    """
    p1 = retrieve(dg, retrieve(dg, channel_name, 'port_from'), 'pressure')
    p2 = retrieve(dg, retrieve(dg, channel_name, 'port_to'), 'pressure')
    Q = retrieve(dg, channel_name, 'flow_rate')
    R = retrieve(dg, channel_name, 'resistance')
    return ((p1 - p2) == (Q * R))


def channel_output_pressure(dg, channel_name):
    """Calculate the pressure at the output of a channel using
    P_out = R * Q - P_in
    Unit for pressure is Pascals - kg/(m*s^2)

    :param str channel_name: Name of the channel
    :returns: SMT expression of the difference between pressure
        into the channel and R*Q
    """
    P_in = retrieve(dg, retrieve(dg, channel_name, 'port_from'), 'pressure')
    R = retrieve(dg, channel_name, 'resistance')
    Q = retrieve(dg, channel_name, 'flow_rate')
    return (P_in - (R * Q))


def calculate_channel_resistance(dg, channel_name):
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
    w = retrieve(dg, channel_name, 'width')
    h = retrieve(dg, channel_name, 'height')
    mu = retrieve(dg, channel_name, 'viscosity')
    chL = retrieve(dg, channel_name, 'length')
    return ((h < w),
            ((12 * (mu * chL)) / (w * ((h ** 3) * (1 - (0.63 * (h / w)))))))


def pythagorean_length(dg, channel_name):
    """Use Pythagorean theorem to assert that the channel length
    (hypoteneuse) squared is equal to the legs squared so channel
    length is solved for

    :param str channel_name: Name of the channel
    :returns: SMT expression of the equality of the side lengths squared
        and the channel length squared
    """
    side_a = retrieve(dg, retrieve(dg, channel_name, 'port_from'), 'x') -\
        retrieve(dg, retrieve(dg, channel_name, 'port_to'), 'x')
    side_b = retrieve(dg, retrieve(dg, channel_name, 'port_from'), 'y') -\
        retrieve(dg, retrieve(dg, channel_name, 'port_to'), 'y')
    a_squared_plus_b_squared = side_a ** 2 + side_b ** 2
    c_squared = (retrieve(dg, channel_name, 'length') ** 2)
    return (a_squared_plus_b_squared == c_squared)


def cosine_law_crit_angle(dg, node1_name, node2_name, node3_name):
    """Use cosine law to find cos^2(theta) between three points
    node1---node2---node3 to assert that it is less than cos^2(thetaC)
    where thetaC is the critical crossing angle

    :param node1: Outside node
    :param node2: Middle connecting node
    :param node3: Outside node
    :returns: cos^2 as calculated using cosine law (a_dot_b^2/a^2*b^2)
    """
    # Lengths of channels
    aX = (retrieve(dg, node1_name, 'x') - retrieve(dg, node2_name, 'x'))
    aY = (retrieve(dg, node1_name, 'y') - retrieve(dg, node2_name, 'y'))
    bX = (retrieve(dg, node3_name, 'x') - retrieve(dg, node2_name, 'x'))
    bY = (retrieve(dg, node3_name, 'y') - retrieve(dg, node2_name, 'y'))
    # Dot products between each channel
    a_dot_b_squared = (((aX * bX) + (aY * bY)) ** 2)
    a_squared_b_squared = ((aX * aX) + (aY * aY)) * ((bX * bX) + (bY * bY))

    return (a_dot_b_squared / a_squared_b_squared)


def calculate_droplet_volume(dg, h, w, wIn, epsilon, qD, qC):
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


def calculate_port_flow_rate(dg, port_name):
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
    port_pressure = retrieve(dg, port_name, 'pressure')
    port_density = retrieve(dg, port_name, 'density')
    port_flow_rate = retrieve(dg, port_name, 'flow_rate')
    # Calculate cross sectional area of all channels flowing into this port
    for port_out in dg.succ[port_name]:
        areas.append(retrieve(dg, (port_name, port_out), 'height') *
                     retrieve(dg, (port_name, port_out), 'width')
                     )
    # Add together all these areas if multiple exist
    if len(areas) == 1:
        total_area = areas[0]
    else:
        areas = [a + b for a, b in zip(areas, areas[1:])]
        total_area = logical_and(*areas)

    return (port_flow_rate ** 2 == (total_area ** 2) * ((2 * port_pressure) / port_density))


def find_path(dg, start_node, end_node):
    """ Find a path between two nodes in the directed graph

    :param str start_node: name of node from which path should start
    :param str end_node: name of node where path should end
    :returns: a list of node names, denoting the path from the start node to the end node
            [start_node, node1, node2, ... , end_node]

             ** returns None if no path is found
    """
    path = []
    path = path + [start_node]

    if start_node == end_node:
        return path

    else:
        successor_nodes = list((dg.successors(start_node)))  # successor_nodes = dict(dg[start_node]).keys();
        # print(successor_nodes)
        for node in successor_nodes:
            if node not in path:
                extended_path = find_path(dg, node, end_node)

            if extended_path:
                path = path + extended_path
                return path
            return None


def calculate_electric_field(dg, anode_node_name, cathode_node_name):
    """Calculate the electric field strength between 2 nodes with applied voltage
    Written for calculating the field between the anode and cathode in the ep_cross.
    Assumes constant electric field: http://hyperphysics.phy-astr.gsu.edu/hbase/electric/elewor.html
    E = V/d
    Unit for electric field is V/m

    :param str anode_node_name: Name of the node with the higher voltage
    :param str cathode_node_name: Name of the node with the lower voltage
    :returns: strength of the electric field between the two nodes
    """
    voltage_1 = retrieve(dg, cathode_node_name, 'voltage')
    voltage_2 = retrieve(dg, anode_node_name, 'voltage')
    delta_voltage = voltage_2 - voltage_1

    # find path between the 2 nodes (there should only be 1 possible path)
    channel_path = dg.edges(find_path(dg, cathode_node_name, anode_node_name))
    if channel_path is None:
        raise ValueError("No path found between %s and %s" % (cathode_node_name, anode_node_name))

    # add check to make sure the path is a straight line?

    # length = sum of all the lengths of the edges that form the path
    length = 0
    for edge in channel_path:
        length = length + retrieve(dg, edge, 'length')

    return (delta_voltage / length)


def calculate_mobility(dg, channel_name, q, r):
    """Calculate the mobility (mu) of a charged analyte
    Based on Stephen Chou's paper, for an analyte that consists of spherical
    charged polymer molecules:
    mu_electrophoretic = q / (4*pi*eta*r),
        where eta is the viscosity of the bulk fluid (q and r are defined below)

    BUT in general
    mu_electrophoretic = eps_r*eps_0*zeta/eta
    where,
        eta is the viscosity of the bulk fluid (Pa s)
        eps_r is the dielectric constant of the dispersion medium
        eps_0 is the permittivity of free space (~8.85e-12 C^2 N^-1 m^-2)
        zeta is the zeta potential
    https://en.wikipedia.org/wiki/Electrophoresis
    this equation is not implemented used, but I wrote it here for future reference
    (should it be implemented?)

    mu = mu_electrophoretic + mu_electroosmotic
    units of mu: m^2 / (V s)

    :param str channel_name: Name of the channel
    :param Variable/float? q: charge of a spherical polymer molecule
    :param Variable/float? r: radius of a spherical polymer molecule
    :returns: Flow rate determined from port pressure and area of
              connected channels
    """
    # define way to put q and r in info for channel?, then retreive from channel
    # instead of from function arguments?
    eta = retrieve(dg, channel_name, 'viscosity')

    # EP = electrophoretic
    mu_EP = q / (4 * math.pi * eta * r)

    # EOF = electroosmotic
    # from Stephen Chou's paper, rule of thumb
    mu_EOF = 1.0 * 10**8

    return mu_EP + mu_EOF


def calculate_charged_particle_velocity(dg, mu, E):
    """Calculate the velocity of an analyte based on the mobility (mu) and applied
    electric field (E)
    eqn from Stephen Chou's papers
    velocity = mu * E
    Unit for velocity is m/s

    :param Variable/float? mu: mobility of the analyte
    :param Variable E: applied electric field in the channel
    :returns: velocity of the charged analyte moving in the electric field
    """
    # does this need to be a separate function?  it's really simple
    return mu * E


def erf_approximation(x):
    """Calculate the approximate value of the error function (erf) at a given
    value x. This approximation is used because the SMT solver likely cannot
    handle the exact function.
    Used to calculate the concentration profile for the ep_cross

    :param float/Variable? x: a number
    :returns: erf(x)
    """
    # the coefficients for the approximate function, copied from Stephen Chou's paper
    a1 = 0.278393
    a2 = 0.230389
    a3 = 0.000972
    a4 = 0.078108

    return (1 - (1 + a1 * x + a2 * x**2 + a3 * x**3 + a4 * x**4)**(-4))


def calculate_concentration(dg, C0, D, W, v, x, t):
    """Calculate the concentration of a sample at time t (since being injected)
    and at position x in the channel.
    This is the equation for rectangular channel, and assumes the sample is
    originally confined to a width W.

    :param float/Variable? C0: initial concentration of sample
    :param float/Variable? D: diffusion coefficient of sample
    :param Variable W: width of injection channel
    :param Variable v: velocity of particles in sample, moving in the (separation) channel
    :param Variable x: coordinate in channel (m)
    :param Variable? t: time since injection (s)
    :returns: concentration
    """

    # note the square root(will hopefully work with SMT solver)
    return C0 / 2.0 * (erf_approximation((W - x + v * t) / (2 * (D * t) ** (0.5))) +
                       erf_approximation((W + x - v * t) / (2 * (D * t) ** (0.5)))
                       )
