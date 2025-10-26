import gi
gi.require_version('Gst' , '1.0')
from gi.repository import Gst, GLib

pipeline_str = ( "v4l2src device=/dev/video0 ! " 
                "image/jpeg,width=640,height=480,framerate=30/1 !" 
                "jpegdec !"
                "xvimagesink" )

print("starting Gstreamer pipeline ")

# create pipeline from String
pipeline = Gst.parse_launch(pipeline_str)

#start Playing
pipeline.set_state(Gst.state.PLAYING)
print("Pipeline started Playing")

# create a Main loop for running Pipeline 
loop=GLib.MainLoop()

try :
    loop.run()
except KeyboardInterrupt:
        print("\n\nReceived interrupt signal. Stopping pipeline...")

pipeline.set_state(Gst.state.NULL)
print("Pipeline stopped..")
