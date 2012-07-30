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
from time import time
from shutil import rmtree
import Image, ImageDraw
from math import pi,asin
from geometry import *

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
            #print("global conf " + name + "=" + str(params[name]))

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
            #print("anim_op_" + operator + " [" + str(duration) + "] " + str(args))

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
    print(msg)
    sys.exit(1)

# copy frame file by symlinking
# args: source_frame_index, target_frame_index
def copy_frame(orig_i, target_i):
    global params
    global last_frame_no

    if last_frame_no+1 != target_i:
        abort("copy_frame: invalid frame_no %d, expected %d" % (target_i, last_frame_no+1))

    frame1_filename = '%s/frame_%06d.png' % (params['tmpdir'], orig_i)
    frame1_symlink   = 'frame_%06d.png' % (orig_i)
    frame2_filename = '%s/frame_%06d.png' % (params['tmpdir'], target_i)

    # try creating a symlink
    if not os.path.exists(frame1_filename):
        abort("copy_frame: file not found '%s', last_frame_no=%d, new_frame_no=%d" % (frame1_filename, last_frame_no, target_i))
    if os.path.exists(frame2_filename):
        abort("copy_frame: file exists '" + frame2_filename + "'")

    last_frame_no = target_i

    try:
        os.symlink(frame1_symlink, frame2_filename)
    except:
        print("copy_frame: os.symlink() failed. Trying to copy.")
        shutil.copy(frame1_filename, frame2_filename)

# write out a single frame, scaling it down
def write_frame(frame_no, image):
    global params
    global last_frame_no

    frame_filename = '%s/frame_%06d.png' % (params['tmpdir'], frame_no)

    if last_frame_no+1 != frame_no:
        abort("write_frame: invalid frame_no %d, expected %d" % (frame_no, last_frame_no+1))
    if os.path.exists(frame_filename):
        abort("write_frame: duplicate frame written: " % (frame_no))

    last_frame_no = frame_no

    scaled_copy = image.copy()
    # thumbnail() maintains the aspect ratio. See also http://stackoverflow.com/questions/273946/how-do-i-resize-an-image-using-pil-and-maintain-its-aspect-ratio
    scaled_copy.thumbnail(params['resolution'], Image.ANTIALIAS)
    scaled_copy.save(frame_filename)

# print out a line indicating overall and local progress
def progress_update(local_frame_no, local_frame_sum, name):
    global frame_no
    global frame_sum
    global start_time

    now = time()

    total_frames_done = frame_no + local_frame_no
    total_progress = float(total_frames_done) / frame_sum * 100
    local_progress = float(local_frame_no) / local_frame_sum * 100

    remaining = (now-start_time) / total_frames_done * float(frame_sum-total_frames_done)
    if remaining >= 60:
        remaining = '%d:%02d' % (remaining//60, remaining % 60)
    else:
        remaining = '%ds' % (remaining)
        

    print('Progress: %.1f%%, Current task: %.1f%% %s, Remaining: %s' % (total_progress, local_progress, name, remaining))

# anim operation pause
# keeps the image still for a while
def anim_op_pause(duration):
    global frame
    global frame_no
    global params

    frame_count = int(duration * params['fps'])
    for i in range(frame_no+1, frame_no+frame_count+1):
        copy_frame(frame_no, i)
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
        for row in range(height):
            for col in range(width):

                # skip inner region
                if col > upper_left[0] and col < lower_right[0] and \
                   row > upper_left[1] and row < lower_right[1]:
                    continue

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

def anim_op_route(duration, args):
    global frame
    global frame_no
    global params

    if len(args) < 4:
        abort("route: not enough arguments (color, thickness, pt1, pt2, ...)")

    frames_total = int(duration * params['fps'])
    start_frame_no = frame_no

    color = args.pop(0)
    color_triple='rgb(' + str(color)[1:-1] + ')'
    thickness = args.pop(0)

    if len(args) < 2:
        abort("route: requires at least 2 points")

    if len(args[0]) != 2:
        abort("route: third and later argument needs to be a point (x,y)")

    args[0] = map(lambda v: float(v), args[0])

    # STEP 1: compute pixels

    pixels = list()

    # initialize run values
    pos      = list(args[0])
    heading  = direction(args[0], args[1])

    pixels.append(list(pos))

    base_inertia = 2 * pi / 360 * 5 # rotational inertia in radiant/frame

    # the distance for each iteration
    distance_per_step = 2.2

    # loop over route points
    for i in range(1,len(args)):
        if len(args[i]) != 2:
            abort("route: third and later argument needs to be a point (x,y)")

        args[i] = map(lambda v: float(v), args[i])

        step_i = 0

        # walk towards next route point
        while distance(pos,args[i]) >= distance_per_step:
            # turn direction towards next point, considering inertia
            target_heading = cartesian2polar(direction(pos, args[i]))[1]
            current_heading = cartesian2polar(heading)[1]

            if target_heading != current_heading:
                bearing = angle(current_heading, target_heading)

                # start slow, then increase until the angle per frame is 2.5 fold
                inertia = base_inertia * (1 + 1.5 * min(step_i, 50) / 50)
                # in case of near target, assure minimum agility
                inertia = max(inertia, asin(distance_per_step / distance(pos,args[i])))

                if abs(bearing) <= inertia:
                    current_heading += bearing
                elif bearing > 0:
                    current_heading += inertia
                else:
                    current_heading -= inertia

                heading = polar2cartesian(current_heading)


            # rescale direction to correct step length
            heading = scale(heading, distance_per_step)

            # move towards next point
            pos[0] += heading[0]
            pos[1] += heading[1]

            # store current position into pixel list
            pixels.append(list(pos))
            # append index of current waypoint to position vector for debugging
            pixels[-1].append(i)
            step_i  += 1

    # STEP 2: draw

    draw = ImageDraw.Draw(frame)

    frames_per_step = float(frames_total) / len(pixels) 
    #print "route debug: %d pixels, %d frames_total, %d frames per pixel" % (len(pixels), frames_total, frames_per_step)

    frame_i = 1
    for i in range(1,len(pixels)):
        last_pos = pixels[i-1]
        pos = pixels[i]

        # draw
        draw.line(( 
            (int(last_pos[0]), int(last_pos[1])),
            (int(pos[0]), int(pos[1]))
        ), fill=color_triple, width=thickness)

        #print("anim_op_route: p(%d,%d->%d,%d) t(%d,%d [%d]) dis(%.2f)" % \
        #    (last_pos[0], last_pos[1], pos[0], pos[1], args[pos[2]][0], args[pos[2]][1], pos[2], \
        #     distance(pos, args[-1])))

        while frame_i/i <= frames_per_step:

            if frame_i % 20 == 0:
                progress_update(frame_i, frames_total, 'route')

            write_frame(frame_no+frame_i, frame)
            frame_i += 1

    progress_update(frame_i, frames_total, 'route')
    del(draw)
    frame_no += frame_i-1

# ===============================================================
#              MAIN  PROGRAM
# ===============================================================

# global python variables
# params: global configuration settings
# frame: an image object containing the current frame
# frame_no: the number of the last frame written to disk (not always up-to-date during anim operations)
# last_frame_no: the number of the last frame written to disk
# phase: what processing steps to perform
#         1: parsing of config file
#         2: process animation operators
#         3: compile AVI file
frame_no = 0
last_frame_no = -1
params = dict()
phase  = 3

# check for config file
if len(sys.argv) < 2:
    abort("missing argument: configuration filename")

while len(sys.argv) > 1:
    a = sys.argv.pop(1)
    if a == '-p':
        phase = int(sys.argv.pop(1))
    elif a == '-c':
        params['configfile'] = sys.argv.pop(1)
    elif a == '-h':
        help()
        sys.exit(0)
    elif a[0] == '-':
        abort("unknown parameter: " + a)
    else:
        params['configfile'] = a


if not 'configfile' in params:
    abort("missing argument: configuration filename")
if not os.path.exists(params['configfile']):
    abort("config file not found'" + params['configfile'] + "'")

# parse configuration file
config_content = file(params['configfile'], 'rt').read()
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
    print("output filename", params['outfile'])
    

# set default values
if not 'tmpdir' in params:
    params['tmpdir'] = 'tmp'

# open map image
print("opening mapfile", params['mapfile'])
try:
	frame = Image.open(params['mapfile'])
except IOError:
	print("can not open map image", params['mapfile'])

# create temporary output directory
if os.path.exists(params['tmpdir']):
    rmtree(params['tmpdir'])   
os.mkdir(params['tmpdir'])

# initialize progress indication
start_time = time()
frame_sum = 0
for op in ops:
    (name, duration, args) = op
    frame_sum += int(duration * params['fps'])


# =================================================
#               MAIN  LOOP
# =================================================

if phase < 2:
    abort("last phase reached: config file parsed")

# write first frame (required in case first op is pause)
write_frame(frame_no, frame);

# process operators
for op in ops:
    (name, duration, args) = op
    print("processing animation " + name + " [" + str(duration) + "] " + str(args))
    if name == 'pause':
        anim_op_pause(duration)
    elif name == 'bars':
        anim_op_bars(duration, args)
    elif name == 'outer_shadow':
        anim_op_outer_shadow(duration, args)
    elif name == 'zoom_in':
        anim_op_zoom_in(duration, args)
    elif name == 'route':
        anim_op_route(duration, args)
    else:
        abort("unknown operation " + name)

if phase < 3:
    abort("last phase reached: animation operators applied")

# complete progress line
print("")
print("running mencoder to produce", params['outfile'])

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
