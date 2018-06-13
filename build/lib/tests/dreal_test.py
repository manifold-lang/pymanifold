from build.lib.data.dreal.symbolic import Variable, logical_and, sin, cos
from build.lib.data.dreal.api import CheckSatisfiability, Minimize

x = Variable("x")
y = Variable("y")
z = Variable("z")

f_sat = logical_and(0 <= x, x <= 10,
                    0 <= y, y <= 10,
                    0 <= z, z <= 10,
                    sin(x) + cos(y) == z)

result = CheckSatisfiability(f_sat, 0.001)
print(result)
