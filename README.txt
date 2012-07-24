This script creates travel route animations.
See link below for a complete example.


Requirements
------------

- Python 2.7 (3.x wont work) with PIL (Ubuntu package python-imaging)
- mencoder (mplayerhq.hu)
- Image file of the map you want the travel route to be drawn on


How to use
----------

- Write your own conf script, see day_01.conf
- run ./animroute.py YOUR.conf

The resulting video file will be YOUR.avi.
You can find the generated frames in tmp/.

Example video: http://www.youtube.com/watch?v=S8zzsXbOd8c
