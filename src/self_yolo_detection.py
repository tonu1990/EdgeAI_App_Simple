import sys
import gi
gi.require_version('Gst' , '1.0')
from gi.repository import Gst, GLib

def on_message(bus, message,loop):
    # Handle pipeline messages here
    if message.type == Gst.MessageType.EOS:
        loop.quit()
    elif message.type == Gst.MessageType.ERROR:
        print("Error:", message.parse_error())
        loop.quit()

def main():
    pipeline_str = ( "v4l2src device=/dev/video0 ! " 
                    "image/jpeg,width=640,height=480,framerate=30/1 ! " 
                    "jpegdec ! "
                    "xvimagesink" )