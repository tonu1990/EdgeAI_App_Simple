import sys
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget

from gstreamer_manager import start_preview

############## LOGGING ###############
# Setup logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s' ,

    handlers=[
        logging.FileHandler('camera_app.log'),  # Save to file
        logging.StreamHandler()  # Also print to console
    ]
)
logger = logging.getLogger(__name__)
############## LOGGING ENDS ###############

# STEP 1: Create application
app = QApplication(sys.argv)
logger.info("Application started")

# STEP 2: Create the main window container
window = QWidget()
window.resize(800, 600)
window.setWindowTitle("Camera App")  # Optional: Change the title
logger.info("Main window created")

# STEP 3: Create widgets

# Buttons . At start keep Object detetcion button disabled
preview_button = QPushButton('Start Cam Preview')
detect_button =  QPushButton('Start Object Detection')
detect_button.setEnabled(False)

logger.info("Elements/Widgets - Buttons loaded")
logger.info("Initial App View fully Loaded . Rady for next steps ")

# STEP 4: Define button action

def on_preview_button_clicked():
    if preview_button.text()== "Start Cam Preview" :
        preview_button.setText("Stop Cam Preview")

        #Gstreamer part 
        success = start_preview(camera_device="/dev/video0")

        if success : 
            logger.info("App in Preview Mode")     
            detect_button.setEnabled(True)
            logger.info("Detection button enabled. Ready for detection") 

    else : # when Stop preview clicked flip text, also disable and reset Object det button
 
        logger.info("App set to Initial App View. Ready for preview")
        preview_button.setText("Start Cam Preview") 

        detect_button.setText("Start Object Detection")
        detect_button.setEnabled(False)    
        logger.info("Detection button disabled")

def on_detection_button_clicked():
    if detect_button.text()=="Start Object Detection" :
        detect_button.setText("Stop Object Detection")
        logger.info("Object detection starting")
    else :
        detect_button.setText("Start Object Detection")
        logger.info("Object detection stopping")
    

# STEP 5: Connect button to action
preview_button.clicked.connect(on_preview_button_clicked)
detect_button.clicked.connect(on_detection_button_clicked)

# STEP 6: Create layout and add widgets
layout = QVBoxLayout()
layout.addWidget(preview_button)
layout.addWidget(detect_button)

# STEP 7: Attach layout to window
window.setLayout(layout)

# STEP 8: Show the window (only this one call needed!)
window.show()

# STEP 9: Start event loop
sys.exit(app.exec())