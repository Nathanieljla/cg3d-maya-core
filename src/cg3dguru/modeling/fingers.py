import os
import enum
import cg3dguru_v2.ui as ui
from maya import cmds
from maya.api import OpenMaya as om
import cg3dguru_v2.utils.modeling as mu


class Finger(enum.Enum):
    THUMB = 0,
    INDEX = 1,
    MIDDLE = 2,
    RING = 3,
    PINKY = 4,
    
    
class Joint(enum.Enum):
    METACARPAL = 0,
    PROXIMAL = 1,
    MEDIAL = 2,
    DISTAL = 3
    
    
JOINT_PERCENTS = {
    Finger.THUMB : {
        Joint.METACARPAL : -0.44,
        Joint.PROXIMAL : 0,
        Joint.DISTAL : 0.54
    }, 
    Finger.INDEX : {
        Joint.METACARPAL : -0.45,
        Joint.PROXIMAL : 0,
        Joint.MEDIAL : 0.49,
        Joint.DISTAL : 0.76
    },
    Finger.MIDDLE : {
        Joint.METACARPAL : -0.41,
        Joint.PROXIMAL : 0,
        Joint.MEDIAL : 0.48,
        Joint.DISTAL : 0.77
    },
    Finger.RING : {
        Joint.METACARPAL : -0.40,
        Joint.PROXIMAL : 0,
        Joint.MEDIAL : 0.47,
        Joint.DISTAL : 0.76
    },
    Finger.PINKY : {
        Joint.METACARPAL : -0.43,
        Joint.PROXIMAL : 0,
        Joint.MEDIAL : 0.46,
        Joint.DISTAL : 0.72
    }  
}



WINDOW_NAME = 'Plot Finger Percents'

class Fingers_Window(ui.Window):
    
    def __init__(self, windowKey, uiFilepath, *args, **kwargs):
        super(Fingers_Window, self).__init__(windowKey, uiFilepath)
        
        self.ui.thumb.pressed.connect( lambda: self.plot_joint(Finger.THUMB) )
        self.ui.index.pressed.connect( lambda: self.plot_joint(Finger.INDEX) )
        self.ui.middle.pressed.connect( lambda: self.plot_joint(Finger.MIDDLE) )
        self.ui.ring.pressed.connect( lambda: self.plot_joint(Finger.RING) )
        self.ui.pinky.pressed.connect( lambda: self.plot_joint(Finger.PINKY) )
        
        #I don't have support in for metacarpals
        self.ui.createMeta.setVisible(False)
        
                
        
    def plot_joint(self, finger : Finger):
        sel = cmds.ls(sl=True) or []

        if len(sel) != 1:
            om.MGlobal.displayError('One nurbsCurve transform must be selected.')
            return

        shapes = cmds.listRelatives(sel[0], shapes=True, fullPath=True) or []
        if not shapes or cmds.nodeType(shapes[0]) != 'nurbsCurve':
            return
         
        curve = shapes[0]
        percents = JOINT_PERCENTS[finger]   
        for id in Joint:
            if id is Joint.METACARPAL and not self.ui.createMeta.isChecked():
                continue
            
            if id in percents:
                #create locator
                locator = cmds.createNode('locator')
                marker = cmds.listRelatives(locator, parent=True, fullPath=True)[0]
                
                name =  (finger.name + '_' + id.name).lower()
                marker = cmds.rename(marker, name)
                
                if id is Joint.METACARPAL:
                    mu.plot_percent_on_curve(curve, percents[id], marker)
                else:
                    mu.plot_percent_on_curve(curve, percents[id], marker)
                    
                    
        
        
def run():
    filepath = os.path.join( os.path.dirname(__file__), r'fingers.ui' )
    joint_utils_window = Fingers_Window(WINDOW_NAME, filepath)
    joint_utils_window.ui.show()
