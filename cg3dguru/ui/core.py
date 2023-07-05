
## how to get QT Designer
## https://stackoverflow.com/questions/30222572/how-to-install-qtdesigner
## https://build-system.fman.io/qt-designer-download
## Designer is already part of Maya (check your /bin folder)


import os

from maya import OpenMayaUI as omui 

from PySide2.QtCore import * 
from PySide2.QtWidgets import *
from PySide2.QtUiTools import *
from PySide2 import __version__
from shiboken2 import wrapInstance 


class Window(object): #QWidget):
    CUSTOM_WINDOWS = {}
    mayaWindow = None
    
    
    def __init__(self, windowKey, uiFilepath, *args, **kwargs):
        self.add_window(windowKey, self)
        
        loader = QUiLoader()
        file = QFile(uiFilepath)
        file.open(QFile.ReadOnly)
        self.mainWindow = self.get_maya_window()
        self.ui = loader.load( file, parentWidget = self.mainWindow )  
        file.close()     
  
    @classmethod
    def add_window(cls, windowKey, instance):
        if windowKey in cls.CUSTOM_WINDOWS:
            try:
                cls.CUSTOM_WINDOWS[windowKey].ui.deleteLater()     
            except:
                pass
            
        cls.CUSTOM_WINDOWS[windowKey] = instance
        
   
    @classmethod
    def get_maya_window(cls):
        if not cls.mayaWindow:
            _mayaMainWindowPtr = omui.MQtUtil.mainWindow()
            cls.mayaWindow     = wrapInstance( int(_mayaMainWindowPtr), QMainWindow) 
            
        return cls.mayaWindow
    
    
    
#def Run():

    #filepath = os.path.join( os.path.dirname(__file__), r'ui\UserData.ui' )
    #userData = Window('test', filepath)
    #userData.ui.show()    