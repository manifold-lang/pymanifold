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
    port_density = retrieve(dg, port_name, 'pressure')
    # Calculate cross sectional area of all channels flowing into this port
    for port_out in dg.succ[port_name]:
        areas.append(retrieve(dg, (port_name, port_out), 'length') *
                     retrieve(dg, (port_name, port_out), 'width')
                     )
    # Add together all these areas if multiple exist
    if len(areas) == 1:
        total_area = areas[0]
    else:
        areas = [a + b for a, b in zip(areas, areas[1:])]
        total_area = logical_and(*areas)
    return (total_area * (((2 * port_pressure) / port_density) ** 0.5))
