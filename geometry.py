# library for basic geometric elements

import math

# compute angle between two angles
def angle(phi1, phi2):
    # always return smallest angle between the two phi
    a = phi2 - phi1
    if a > math.pi:
        return phi2 - phi1 - math.pi*2
    elif a < -math.pi:
        return phi2 - phi1 + math.pi*2
    return a

# convert polar (phi, r=1) to cartesian (x, y)
def polar2cartesian(phi, r=1.0):
    x = r * math.cos(phi)
    y = r * math.sin(phi)

    return [ x, y ]

# convert cartesian vector (x, y) to (r, angle)
def cartesian2polar(v):
    if v[0] == 0 and v[1] == 0:
        abort("vector2polar: can't convert null vector")

    r = math.sqrt(v[0]**2 + v[1]**2)

    if v[0] != 0:
        phi = math.atan2(v[1], v[0])
    elif v[1] > 0:
        phi = math.pi / 2
    else:
        phi = -math.pi / 2

    return [ r, phi ]

# compute gradient between two points
# None means vertical
def gradient(p1, p2):
    if(p1[0] == p2[0]):
        return None
    else:
        return float(p2[1]-p1[1]) / (p2[0]-p1[0])

# return normalized vector pointing from p1 to p2
def direction(p1, p2):
    v = [ p2[0]-p1[0], p2[1]-p1[1] ]
    return normalize(v)

# normalize the given vector, so length becomes 1.0
def normalize(v):
    return scale(v, 1.0)

# scale a vector to match length
def scale(v, l):
    div = distance((0,0), v)
    return [ v[0]/div*l, v[1]/div*l ]

# return the distance between two points
def distance(p1, p2):
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

# special cases: m=None, so b represents x at y=0 instead of y at x=0
class Line:
    def __init__(self, m, point):
        if m == None:
            self.m = m
            self.b = float(point[0]) # vertical
        else:
            self.m = float(m)
            self.b = point[1] - float(m) * point[0]

    def crosspoint(self, line):
        # return crossing point if any
        if self.m == line.m:
            print("warning: no crossing point between parallel lines\n  %s\n  %s" % (self, line))
            return (None, None)
        elif self.m == None:
            x = self.b
            y = line.m * x + line.b
        elif line.m == None:
            x = line.b
            y = self.m * x + self.b
        else:
            x = (line.b-self.b) / (self.m-line.m)
            y = self.m * x + self.b
            return (x, y)

    def perpendicular(self, point):
        # crate new line perpendicular to this line and running through point
        if self.m == None:
            m = 0
        elif self.m == 0:
            m = None
        else:
            m = -1 / self.m

        return Line(m, point)

    def __str__(self):
        return "y = " + str(self.m) + " * x + " + str(self.b)
