
import re


def remove_namespaces(filename, remove_subdeformer_namespaces=False):
    """FBX must be saved in ACSII format otherwise the parser will error."""
    
    fbx = open(filename)
    file_string = fbx.read()
    fbx.close()
    
    #don't use \s in this otherwise it will wrap past the return character and cause issues
    expression_str = r"(?P<start>::)(?P<namespace>([ \d\w]*:)*)(?P<name>[ \d\w]*)"
    result = re.sub(expression_str, r"\g<start>\g<name>", file_string)

    if remove_subdeformer_namespaces:
        expression_str = r"(?P<start>SubDeformer::)(?P<namespace>([ \d\w]*\.)*)(?P<name>[ \d\w]*)"
        result = re.sub(expression_str, r"\g<start>\g<name>", result)
        
    new_file = open(filename, 'w')
    new_file.write(result)
    new_file.close()
    
    
    
def fbx_ascii_to_binary(filename):
    #"c:\program files\autodesk\maya2023\bin\mayapy.exe" "d:/fixIt.py"

    # Gain access to Maya in a mayapy process.
    import os

    try:
        import maya.standalone 			
        maya.standalone.initialize() 		
    except: 			
        return False

    success = False
    try:
        import json
        from maya import cmds, mel
        cmds.file(filename, i=True)

        ##https://help.autodesk.com/view/MAYAUL/2022/ENU/index.html?guid=GUID-699CDF74-3D64-44B0-967E-7427DF800290
        start = int(cmds.playbackOptions(query=True, animationStartTime=True))
        end = int(cmds.playbackOptions(query=True, animationEndTime=True))
        
        mel.eval('FBXResetExport;')
        mel.eval('FBXExportBakeComplexStart -v {};'.format(start))
        mel.eval('FBXExportBakeComplexEnd -v {};'.format(end))
        mel.eval('FBXExportSkeletonDefinitions -v true;')
        mel.eval('FBXExportBakeComplexAnimation -v false;')
        mel.eval('FBXExportBakeResampleAnimation -v true;')
        mel.eval('FBXExportSkins -v true;')
        mel.eval('FBXExportShapes -v true;')
        mel.eval('FBXExportConstraints -v false;')
        mel.eval('FBXExportInputConnections -v false;')
        mel.eval('FBXExportCameras -v false;')
        mel.eval('FBXExportLights -v false;')
        mel.eval('FBXExportInAscii -v false;')
        mel.eval('FBXExportAnimationOnly -v false;')
        mel.eval('FBXExport -s -f {};'.format(json.dumps(filename)))

        success = True
    except:
        success = False
    finally:
        try:
            maya.standalone.uninitialize() 		
        except: 			
            pass

    return success

    


