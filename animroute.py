#!/usr/bin/python

# by Roman Hoog Antink, (c) 2012
#
# Animated route generator
#
# constructs each frame using python PIL (image library) and merges them into 
# an AVI file using mencoder

import os, sys
import re
import shlex
from shutil import rmtree
import Image, ImageDraw

# populate global config settings in dictionary params and
# return stack of animation operations
def parse_config(config):
    global params
    token_list = shlex.split(config, True)
    operator_stack = list()

    while len(token_list) > 0:
        token = token_list.pop(0)
        if token == "set":
            name = token_list.pop(0)
            value = token_list.pop(0)
            params[name] = convert_varlist(value)
            #print "global conf " + name + "=" + str(params[name])

        elif token == "anim":
            duration = convert_timespec(token_list.pop(0))
            operator = token_list.pop(0)
            argc = peek_args(token_list)
            if argc > 0:
                args = token_list[:argc]
                del token_list[:argc]
                args = convert_nested(args)
            else:
                args = list()
            operator_stack.append((operator, duration, args))

        else:
            abort("unknown config instruction " + token)

    return operator_stack

# count how many tokens until the next instruction (identified by 'anim' or end of file)
def peek_args(token_list):
    count = 0
    for t in token_list:
        if t == 'anim':
            return count
        count+=1
    return count

# convert '[12.5]' into float
def convert_timespec(t):
    re_timespec = re.compile('^\[-?[0-9.]+\]$');
    if not re_timespec.match(t):
        abort("invalid timespec: " + t)
    return float(t[1:-1])

# convert '(3,-4,5.9)' into list of floats
def convert_varlist(string_value):
    re_tuple = re.compile('^\(-?[0-9.]+(,-?[0-9.]+)+\)$')
    re_int   = re.compile('^-?[0-9]+$')
    re_float = re.compile('^-?[0-9.]+$')
    if re_tuple.match(string_value):
        values = string_value[1:-1].split(',')
        values = map(lambda v: int(v), values)
        return values
    
    elif re_int.match(string_value):
        return int(string_value)

    elif re_float.match(string_value):
        return float(string_value)

    return string_value

# convert ('(2,3)', '4,5') into nested list ((2,3),(4,5))
def convert_nested(arg_list):
    arg_list = map(lambda element: convert_varlist(element), arg_list)
    return arg_list

# fatal error occured
def abort(msg):
    print msg
    sys.exit(1)

# write out a single frame, scaling it down
def write_frame(frame_no, image):
    global params
    frame_filename = '%s/frame_%06d.png' % (params['tmpdir'], frame_no)
    scaled_copy = image.copy()
    # thumbnail() maintains the aspect ratio. See also http://stackoverflow.com/questions/273946/how-do-i-resize-an-image-using-pil-and-maintain-its-aspect-ratio
    scaled_copy.thumbnail(params['resolution'], Image.ANTIALIAS)
    scaled_copy.save(frame_filename)

# print out a line indicating overall and local progress
def progress_update(local_frame_no, local_frame_sum, name):
    global frame_no
    global frame_sum
    total_frames_done = frame_no + local_frame_sum
    total_progress = float(total_frames_done) / frame_sum * 100
    local_progress = float(local_frame_no) / local_frame_sum * 100
    print 'Progress: %.1f Current task: %.1f %s' % (total_progress, local_progress, name)

# anim operation pause
# keeps the image still for a while
# TODO optimize by creating hard links
def anim_op_pause(duration):
    global frame
    global frame_no
    global params

    frame_count = int(duration * params['fps'])
    for i in range(frame_no+1, frame_no+frame_count+1):
        write_frame(i, frame)
        if i % (frame_count/20+1) == 0:
            progress_update(i-frame_no, frame_count, 'pause')

    frame_no += frame_count 


# anim operation bars
# animate four bars closing in on the given area
# args: (x1,y1) (x2,y2)
def anim_op_bars(duration, args):
    global frame
    global frame_no
    global params

    frame_count = int(duration * params['fps'])

    # pick up arguments
    if len(args) != 4:
        abort("bars: invalid number of arguments")

    # color_triple is the color to paint, thickness is thickness of the bars
    # upper_left and lower_right are 2-tuples of the corner coordinates of the
    # inner region
    (color_triple, thickness, upper_left, lower_right) = args

    # convert color tuple to string "str(23, 54, 0)"
    color_triple='rgb(' + str(color_triple)[1:-1] + ')'

    if len(upper_left) != 2 or len(lower_right) != 2:
        abort("bars: coordinate parameter error")
    
    for step in range(1,frame_count+1):
        frame_i = frame_no + step

        # copy original image, to draw the bars of each sub frame onto
        my_frame = frame.copy()
        draw = ImageDraw.Draw(my_frame)

        # draw upper horizontal bar
        draw.line((map (lambda v: int(v), (
                    my_frame.size[0] - (my_frame.size[0]-upper_left[0]+thickness) * float(step)/frame_count,
                    upper_left[1] - thickness,
                    my_frame.size[0],
                    upper_left[1] - thickness
                  ))), fill=color_triple, width=thickness)
        
        # draw lower horizontal bar
        draw.line(map (lambda v: int(v), (
                    0,
                    lower_right[1] + thickness,
                    (lower_right[0] + thickness) * float(step)/frame_count,
                    lower_right[1] + thickness
                  )), fill=color_triple, width=thickness)

        # draw left vertical bar
        draw.line(map (lambda v: int(v), (
                    upper_left[0] - thickness,
                    0,
                    upper_left[0] - thickness,
                    (lower_right[1] + thickness) * float(step)/frame_count
                  )), fill=color_triple, width=thickness)

        # draw right vertical bar
        draw.line(map (lambda v: int(v), (
                    lower_right[0] + thickness,
                    my_frame.size[1] - (my_frame.size[1]-upper_left[1]+thickness) * float(step)/frame_count,
                    lower_right[0] + thickness,
                    my_frame.size[1]
                  )), fill=color_triple, width=thickness)

        del draw
        write_frame(frame_i, my_frame)

        if step % (frame_count/20+1) == 0:
            progress_update(step, frame_count, 'bars')


    frame_no += frame_count
    # leave bars on final position for next animation operations
    frame = my_frame


# anim operation outer blue shadow
# animate shadowing outer region
# args: duration (x1,y1) (x2,y2)
def anim_op_outer_shadow(duration, args):
    global frame
    global frame_no
    global params

    frame_count = int(duration * params['fps'])

    # pick up arguments
    if len(args) != 2:
        abort("outer_shadow: invalid number of arguments")

    # upper_left and lower_right are 2-tuples of the corner coordinates of the
    # inner region
    (upper_left, lower_right) = args

    if len(upper_left) != 2 or len(lower_right) != 2:
        abort("outer_shadow: coordinate parameter error")
    
    # save inner region (has to be pasted over running frame)
    inner = frame.copy().crop(upper_left + lower_right)

    for step in range(1,frame_count+1):
        frame_i = frame_no + step

        my_frame = frame.copy()
        (width,height) = my_frame.size
        pix = my_frame.load()
        # TODO accelerate, by leaving out inner region 
        for row in range(height):
            for col in range(width):
                p = pix[col,row]
                (r,g,b) = p

                # compute average color value over all channels
                avg = (float(r) + g + b)/3

                # target factor goes from 0 to 1
                tf = float(step)/frame_count

                # source factor goes from 1 to 0, inversion of target factor
                sf = 1 - tf

                # blue channel goes towards average value
                b = int( (avg * tf + b * sf) / 2 )

                # other channels only go 2/3 way to 0
                r = int(r * (2*sf + 1)/3)
                g = int(g * (2*sf + 1)/3)
                pix[col,row] = (r,g,b)
        my_frame.paste(inner, upper_left + lower_right)

        write_frame(frame_i, my_frame)

        if step % (frame_count/20+1) == 0:
            progress_update(step, frame_count, 'outer_shadow')

    frame_no += frame_count
    # leave image in final state for next animation operations
    frame = my_frame


# anim operation zoom in
# args: duration (x1,y1) (x2,y2)
def anim_op_zoom_in(duration, args):
    global frame
    global frame_no
    global params

    frame_count = int(duration * params['fps'])

    # pick up arguments
    if len(args) != 2:
        abort("zoom_in: invalid number of arguments")

    # upper_left and lower_right are 2-tuples of the corner coordinates of the
    # inner region
    (upper_left, lower_right) = args

    if len(upper_left) != 2 or len(lower_right) != 2:
        abort("zoom_in: coordinate parameter error")

    (width, height) = frame.size

    for step in range(1,frame_count+1):
        frame_i = frame_no + step

        from_x = int(float(step)/frame_count * upper_left[0])
        from_y = int(float(step)/frame_count * upper_left[1])
        to_x = int((1-float(step)/frame_count) * (width-lower_right[0]) + lower_right[0])
        to_y = int((1-float(step)/frame_count) * (height-lower_right[1]) + lower_right[1])
        my_frame = frame.crop((from_x, from_y, to_x, to_y))
        write_frame(frame_i, my_frame)

        if step % (frame_count/20+1) == 0:
            progress_update(step, frame_count, 'zoom_in')

    frame_no += frame_count
    # leave image in final state for next animation operations
    frame = my_frame

# ===============================================================
#              MAIN  PROGRAM
# ===============================================================

# global python variables
# params: global configuration settings
# frame: an image object containing the current frame
# frame_no: the number of the last frame written to disk
frame_no = 0
params = dict()

# check for config file
if len(sys.argv) < 2:
    abort("missing argument: configuration filename")
params['configfile'] = sys.argv[1]
if not os.path.exists(params['configfile']):
    abort("config file not found'" + params['configfile'] + "'")

# parse configuration file
config_content = file(sys.argv[1], 'rt').read()
ops = parse_config(config_content)

# check for mandatory settings
for par in ('resolution', 'mapfile', 'fps'):
    if not par in params:
        abort("'set " + par + " VALUE' is missing in configuration file: ")

# deduce output file name from config file name
if not 'outfile' in params:
    re_basename = re.compile('^(.*)\.[a-zA-Z]+$')
    m = re_basename.match(params['configfile'])
    if m:
        params['outfile'] = m.group(1) + '.avi'
    else:
        params['outfile'] = params['configfile'] + '.avi'
    print "output filename", params['outfile']
    

# set default values
if not 'tmpdir' in params:
    params['tmpdir'] = 'tmp'

# open map image
print "opening mapfile", params['mapfile']
try:
	frame = Image.open(params['mapfile'])
except IOError:
	print "can not open map image", params['mapfile']

# create temporary output directory
if os.path.exists(params['tmpdir']):
    rmtree(params['tmpdir'])   
os.mkdir(params['tmpdir'])

# initialize progress indication
frame_sum = 0
for op in ops:
    (name, duration, args) = op
    frame_sum += int(duration * params['fps'])


# =================================================
#               MAIN  LOOP
# =================================================

# process operators
for op in ops:
    (name, duration, args) = op
    if name == 'pause':
        anim_op_pause(duration)
    elif name == 'bars':
        anim_op_bars(duration, args)
    elif name == 'outer_shadow':
        anim_op_outer_shadow(duration, args)
    elif name == 'zoom_in':
        anim_op_zoom_in(duration, args)
    elif name == 'bezier':
        print 'anim_op_bezier(duration, args)'
    else:
        abort("unknown operation " + name)


# terminate progress line
print ""
print "running mencoder to produce", params['outfile']

# build avi file from frames
command = ('mencoder',
           "mf://" + params['tmpdir'] + "/*.png",
           '-mf',
           "type=png:w=%d:h=%d:fps=%d" % (params['resolution'][0], 
                params['resolution'][1], params['fps']),
           '-ovc',
           'lavc',
           '-lavcopts',
           'vcodec=mpeg4',
           '-oac',
           'copy',
           '-o',
           params['outfile'])

os.spawnvp(os.P_WAIT, 'mencoder', command)
