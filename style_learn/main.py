import sys 
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, 
                             QWidget, QVBoxLayout,QHBoxLayout,QGridLayout,
                             QPushButton, QCheckBox, QRadioButton,
                             QButtonGroup, QLineEdit)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt


class MainWindow (QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My cool first GUI")
        self.setGeometry(700,300,500,500)
        self.line_edit = QLineEdit(self)
        self.button = QPushButton("Save",self)
        # self.radio1 = QRadioButton("Visa",self)
        # self.radio2 = QRadioButton("Master Card",self)
        # self.button_gr1 = QButtonGroup(self)
        # self.button_gr2 = QButtonGroup(self)
        # self.checkbox = QCheckBox("Do you like food?",self)
        
        # self.btn = QPushButton("click me",self)
        # self.label = QLabel("Hello",self)
        self.initUi()
        self.setWindowIcon(QIcon('logo.png'))
        
        # label = QLabel("Hello",self)
        # label.setFont(QFont("Arial",30))
        # label.setGeometry(0,0,500,100)
        # label.setStyleSheet("color:blue;"
        #                     "background-color:red;"
        #                     "font-weight:bold;"
        #                     "font-style:italic"
        #                     )
        # label.setAlignment(Qt.AlignCenter|Qt.AlignBottom)
        # img = QLabel(self)
        # img.setGeometry(0,0,250,250)
        # pixmap = QPixmap("logo.png")
        # img.setPixmap(pixmap)
        # img.setScaledContents(True)
    def initUi(self):
        # # Layout 
        # central_widget = QWidget()
        # self.setCentralWidget(central_widget)
        # label1 = QLabel("#1",self)
        # label2 = QLabel("#2",self)
        # label3 = QLabel("#3",self)
        # label4 = QLabel("#4",self)
        # label5 = QLabel("#5",self)

        # label1.setStyleSheet("background-color:red;")
        # label2.setStyleSheet("background-color:yellow;")
        # label3.setStyleSheet("background-color:green;")
        # label4.setStyleSheet("background-color:blue;")
        # label5.setStyleSheet("background-color:purple;")

        # vbox = QGridLayout()
        # vbox.addWidget(label1,0,0)
        # vbox.addWidget(label2,0,1)
        # vbox.addWidget(label3,1,0)
        # vbox.addWidget(label4,1,1)
        # vbox.addWidget(label5,1,2)
        # central_widget.setLayout(vbox)

        # push button 
        # self.btn.setGeometry(150,200,200,100)
        # self.btn.setStyleSheet("font-size:30px;")
        # self.btn.clicked.connect(self.on_click)

        # self.label.setGeometry(150,300,200,100)
        # self.label.setStyleSheet("font-size:30px;")

        # Check boxes
    #     self.checkbox.setGeometry(10,0,500,100)
    #     self.checkbox.setStyleSheet("font-size:20px;"
    #                                 "font-family: Arial;")
    #     self.checkbox.setChecked(False)
    #     self.checkbox.stateChanged.connect(self.checkbox_changed)
    
    # def checkbox_changed(self,state):
    #     if state == Qt.Checked:
    #         print("You like food")
    #     else:
    #         print("You don't like food")

    # Radio button
        # self.setStyleSheet("QRadioButton{"
        #                    "font-size:40px;"
        #                    "font-family: Arial;"
        #                    "padding: 10px;"
        #                    "}")
       

        # central_widget = QWidget()
        # self.setCentralWidget(central_widget)
        # vbox = QVBoxLayout()
        # vbox.addWidget(self.radio1)
        # vbox.addWidget(self.radio2)
        # central_widget.setLayout(vbox)
        # self.button_gr1.addButton(self.radio1)
        # self.button_gr2.addButton(self.radio2)
        # self.radio1.toggled.connect(self.radio_button_changed)
        
        # Line edit widget
        self.line_edit.setGeometry(10,20,200,40)
        self.button.setGeometry(210,20,100,40)
        self.line_edit.setStyleSheet("font-size:25px;"
                                     "font-family: Arial;")
        self.button.clicked.connect(self.save)
    def radio_button_changed(self): 
        radio_button = self.sender()
        
    def on_click(self):
        print("Button clicked")
        self.btn.setText("Unclick")
        self.label.setText("Good bye")
        self.btn.setDisabled(True)

    def save(self):
        text = self.line_edit.text()
        print(text)
def main(): 
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()