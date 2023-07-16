
import os
import sys
import importlib

import pymel.core as pm

import cg3dguru.ui as ui
import cg3dguru.user_data

WINDOW_NAME = 'User Data Editor'

       
class UserDataEditor(ui.Window):
    
    def __init__(self, windowKey, uiFilepath, *args, **kwargs):
        super(UserDataEditor, self).__init__(windowKey, uiFilepath)

        self.AddScriptJob()
        self.maya_nodes_selected = False

        self.classes = cg3dguru.user_data.Utils.get_class_names()
        keys = list(self.classes.keys())
        keys.sort()
        self.ui.createDataList.addItems(keys)
        self.ui.searchDataList.addItems(keys)
        
        self.ui.createDataList.itemSelectionChanged.connect( lambda : self.SelectionChanged(self.ui.createDataList) )
        self.ui.searchDataList.itemSelectionChanged.connect( lambda : self.SelectionChanged(self.ui.searchDataList) )
        
        self.ui.createData.clicked.connect(self.Create)
        self.ui.addData.clicked.connect(self.Add)
        self.ui.removeData.clicked.connect(self.Delete)
        self.ui.sceneSelect.clicked.connect(self.SelectFromScene)
        self.ui.filterSelection.clicked.connect(self.FindInSelection)
        
        
    def AddScriptJob(self):
        jobId   = pm.scriptJob( event=['SelectionChanged', self.MayaSelectionChanged] )
        #print 'New Job: {0}'.format(jobId)
        self.handler = lambda : self.RemoveScriptJob(jobId)
        self.jobId = jobId
        self.ui.destroyed.connect( self.handler )        
        
        
    def RemoveScriptJob(self, jobId):
        #print 'Nuke Job: {0}'.format(jobId)
        self.ui.destroyed.disconnect( self.handler )
        pm.scriptJob( kill = jobId )
        
        
    def _GetItemNames(self, listWidget):
        selection = listWidget.selectedItems()
        names = []
        for item in selection:
            names.append( item.text() )
            
        return names
        
        
    def Create(self):
        names = self._GetItemNames(self.ui.createDataList)
        newNodes = []
        
        for name in names:
            data_class = self.classes[name]
            pyNode, data = data_class.create_node(name = name)
            newNodes.append(pyNode)
                
        if newNodes:
            pm.select(newNodes, replace = True)
        else:
            self.ui.statusbar.showMessage("No Data is selected")
    
    
    def Add(self):
        names = self._GetItemNames(self.ui.createDataList)
        cg3dguru.user_data.Utils.validate_version(sl=True)
        
        for name in names:
            data_class = self.classes[name]()
            for mayaNode in pm.ls(sl=True):
                data_class.add_data( mayaNode )
                
        self.SelectionChanged(self.ui.createDataList)
    
    
    def Delete(self): 
        selection = pm.ls(sl=True)
        names = self._GetItemNames(self.ui.createDataList)
        
        for name in names:
            dataClass = self.classes[name]()
            for mayaNode in selection:
                dataClass.delete_data( mayaNode )
                
        self.MayaSelectionChanged()
    
    
    
    def _Select(self, *args, **kwargs):
        names = self._GetItemNames(self.ui.searchDataList)
        
        nodes = []
        for name in names:
            dataClass = self.classes[name]()            
            foundNodes = cg3dguru.user_data.Utils.get_nodes_with_data(data_class=dataClass, **kwargs)
            
            nodes.extend(foundNodes)
            
        pm.select(nodes, replace = True)    
        
    
    def SelectFromScene(self):
        self._Select()
            
    
    def FindInSelection(self):
        self._Select(sl=True)
    
    
    def SelectionChanged(self, listWidget):
        #is anything selected in our list?
        enable = len( listWidget.selectedItems() ) > 0
        
        if listWidget is self.ui.createDataList:
            names = self._GetItemNames(self.ui.createDataList)
            hasData  = False
            missData = False
            
            for name in names:
                data = None
                data = cg3dguru.user_data.Utils.get_nodes_with_data(data_class = self.classes[name], sl=True)
                if data:
                    hasData  = True
                
                missData = len(data) != len(pm.ls(sl=True))
            
     
            self.ui.createData.setEnabled(enable)   
            self.ui.addData.setEnabled(enable and self.maya_nodes_selected and missData)
            self.ui.removeData.setEnabled(enable and hasData)
        else:
            print ("search list")
            
            
    def MayaSelectionChanged(self):
        self.maya_nodes_selected = len( pm.ls(sl=True) ) > 0
        
        if self.ui.createDataList.isVisible():
            self.SelectionChanged(self.ui.createDataList)
        else:
            self.SelectionChanged(self.ui.searchDataList)
    
 
def run(data_module = None):
    if data_module is not None:
        if data_module not in sys.modules:
            try:
                importlib.import_module(data_module)
            except Exception as e:
                print("failed to import {}".format(data_module))
                return

    filepath = os.path.join(cg3dguru.user_data.__path__[0],  'user_data.ui' )
    editor = UserDataEditor(WINDOW_NAME, filepath)
    editor.ui.show()
    