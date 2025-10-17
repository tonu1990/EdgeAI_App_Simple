import logging
import threading
logger = logging.getLogger(__name__)

def start_preview():
    global pipeline, camera_active
    try:
        import gi
        gi.require_version('Gst', '1.0')
        from gi.repository import Gst, GLib

        # Initialize GStreamer
        Gst.init(None)

        pipeline_str = "v4l2src device=/dev/video0 ! videoconvert ! autovideosink"
        pipeline = Gst.parse_launch(pipeline_str)
        pipeline.set_state(Gst.State.PLAYING)
        camera_active = True
        logger.info("GStreamer pipeline started successfully")

    except Exception as e:
                logger.error(f"Failed to start camera: {e}")
                camera_active = False