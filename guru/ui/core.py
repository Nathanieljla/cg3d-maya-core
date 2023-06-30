
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
        #super(Window, self).__init__(*args, **kwargs)
        self.AddWindow(windowKey, self)
        
        loader = QUiLoader()
        file = QFile(uiFilepath)
        file.open(QFile.ReadOnly)
        self.mainWindow = self.GetMayaWindow()
        self.ui = loader.load( file, parentWidget = self.mainWindow )  
        file.close()     
  
    @classmethod
    def AddWindow(cls, windowKey, instance):
        if windowKey in cls.CUSTOM_WINDOWS:
            try:
                cls.CUSTOM_WINDOWS[windowKey].ui.deleteLater()     
            except:
                pass
            
        cls.CUSTOM_WINDOWS[windowKey] = instance
        
   
    @classmethod
    def GetMayaWindow(cls):
        if not cls.mayaWindow:
            _mayaMainWindowPtr = omui.MQtUtil.mainWindow()
            cls.mayaWindow     = wrapInstance( int(_mayaMainWindowPtr), QMainWindow)   #wrapInstance(long(_mayaMainWindowPtr), QWidget)   
            
        return cls.mayaWindow
    
    
    
#def Run():

    #filepath = os.path.join( os.path.dirname(__file__), r'ui\UserData.ui' )
    #userData = Window('test', filepath)
    #userData.ui.show()    