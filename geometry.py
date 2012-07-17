# library for basic geometric elements

import math

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
    return [v[0]/div*l, v[1]/div*l]

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
            print "warning: no crossing point between parallel lines\n  %s\n  %s" % (self, line)
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
