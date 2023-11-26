import pymel.core
import os
import cg3dguru.utils

#http://tech-artists.org/forum/showthread.php?4988-Problem-doing-an-FBX-export-with-PyMEL
#http://download.autodesk.com/global/docs/maya2014/en_us/index.html?url=files/GUID-377B0ACE-CEC8-4D13-81E9-E8C9425A8B6E.htm,topicNumber=d30e145135

_EXPORT_NODES = None

EXPORT_ANIM = 0x01
EXPORT_RIG  = 0x01 << 1
EXPORT_ANIM_RIG = EXPORT_ANIM | EXPORT_RIG

#Eventually get the save location from the node, if one doesn't exist add the attr to store the result
def get_save_filename(export_node=None):
    basicFilter = "*.fbx"
    filename = pymel.core.system.fileDialog2(fileFilter = basicFilter, cap='Export Animation')
    
    if filename:
        return filename[0]
    else:
        return None


def set_export_options(export_type, remove_namespaces=False):
    ##https://help.autodesk.com/view/MAYAUL/2022/ENU/index.html?guid=GUID-699CDF74-3D64-44B0-967E-7427DF800290
    start = int(pymel.core.animation.playbackOptions(query=True, animationStartTime=True))
    end   = int( pymel.core.animation.playbackOptions(query=True, animationEndTime = True))
    bake_anims = bool(export_type & EXPORT_ANIM)
    export_rig = bool(export_type & EXPORT_RIG)
    
    print('export animations:{0} export rig:{1}'.format(bake_anims, export_rig))
    print('start:{0} end:{1}'.format(start, end))
    
    pymel.core.mel.FBXResetExport()
    
    pymel.core.mel.FBXExportBakeComplexStart(v=start)
    pymel.core.mel.FBXExportBakeComplexEnd(v=end)
    pymel.core.mel.FBXExportBakeComplexAnimation(v= bake_anims )    
    pymel.core.mel.FBXExportBakeResampleAnimation (v= True )
    pymel.core.mel.FBXExportSkins(v=export_rig )
    
    pymel.core.mel.FBXExportShapes(v=True)
    
    pymel.core.mel.FBXExportConstraints(v=False)
    pymel.core.mel.FBXExportInputConnections(v=False)
    #pymel.core.mel.FBXExportUseSceneName(v=True)   //This uses the maya filename for the clip being exported
    pymel.core.mel.FBXExportCameras(v=False)
    pymel.core.mel.FBXExportLights(v=False)
    
    pymel.core.mel.FBXExportInAscii(v=remove_namespaces)
    #pymel.core.mel.FBXExportFileVersion(v='FBX201300')
    
    pymel.core.mel.FBXExportAnimationOnly(v=not export_rig)
    


def export(export_type=EXPORT_ANIM_RIG, filename='', remove_namespaces=False):
    set_export_options(export_type, remove_namespaces=remove_namespaces)
    
    if not filename:
        filename = get_save_filename()
        
    if filename:
        pymel.core.mel.FBXExport(s=True, f=filename)
        if os.path.exists(filename) and remove_namespaces:
            cg3dguru.utils.remove_namespaces(filename)  
    

def export_anim(*args, **kwargs):
    export(export_type = EXPORT_ANIM_RIG, *args, **kwargs)
    
def export_rig(*args, **kwargs):
    export(export_type=EXPORT_RIG, *args, **kwargs)
    

def import_fbx(filepath):
    ##https://help.autodesk.com/view/MAYAUL/2022/ENU/index.html?guid=GUID-699CDF74-3D64-44B0-967E-7427DF800290
    pymel.core.mel.FBXImportMode(v='merge')
    pymel.core.mel.FBXImportFillTimeline(v=True)
    pymel.core.mel.FBXImportSkins(v=True)
    pymel.core.mel.FBXImport(f=filepath)


    