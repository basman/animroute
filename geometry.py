# library for basic geometric elements

import ImageDraw

# compute gradient between two points
# None means vertical
def gradient(p1, p2):
    if(p1[0] == p2[0]):
        return None
    else:
        return float(p2[1]-p1[1]) / (p2[0]-p1[0])


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

    def draw(self, frame, color, thickness):
        draw = ImageDraw.Draw(frame)
        if self.m != None:
            draw.line((map (lambda v: int(v), (
                    0,
                    self.b,
                    frame.size[0],
                    self.m * frame.size[0] + self.b,
                    ))), fill=color, width=thickness)
        else:
            # vertical line
            draw.line((map (lambda v: int(v), (
                    self.b,
                    0,
                    self.b,
                    frame.size[0],
                    ))), fill=color, width=thickness)

        del(draw)

    def __str__(self):
        return "y = " + str(self.m) + " * x + " + str(self.b)
