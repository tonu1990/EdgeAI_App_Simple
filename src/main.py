import sys
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget

# STEP 1: Create application
app = QApplication(sys.argv)

# STEP 2: Create the main window container
window = QWidget()
window.setWindowTitle("Camera App")  # Optional: Give it a title

# STEP 3: Create widgets
label = QLabel("Welcome to Tonu Edge AI")
button = QPushButton('Start Cam Preview')

# STEP 4: Define button action
def on_button_clicked():
    if button.text()== "Start Cam Preview" :
        label.setText("Camera Preview starting")
        button.setText("Stop Cam Preview")
    else :
        label.setText("Welcome to Tonu Edge AI")
        button.setText("Start Cam Preview")        

# STEP 5: Connect button to action
button.clicked.connect(on_button_clicked)

# STEP 6: Create layout and add widgets
layout = QVBoxLayout()
layout.addWidget(label)
layout.addWidget(button)

# STEP 7: Attach layout to window
window.setLayout(layout)

# STEP 8: Show the window (only this one call needed!)
window.show()

# STEP 9: Start event loop
sys.exit(app.exec())