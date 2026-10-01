from __future__ import annotations

import re
import enum
from maya import cmds
from maya.api import OpenMaya as om

from ..maya import Node, node_name


class Comp_Type(enum.Flag):
    VERTEX = enum.auto()
    EDGE = enum.auto()
    FACE = enum.auto()
    ALL = VERTEX | EDGE | FACE


def get_component_selection( comp_type: Comp_Type ):
    if not isinstance(comp_type, Comp_Type):
        om.MGlobal.displayError("Component_type must be of type Comp_Type")
        return
    
    abbr = ''
    if Comp_Type.VERTEX in comp_type:
        abbr = 'vtx'
    elif Comp_Type.EDGE in comp_type:
        abbr = 'e'
    else:
        abbr = 'f'
        

    expression = re.compile( r'{0}\[((?P<num1>\d+):(?P<num2>\d+)\]|(?P<num3>\d+)\])'.format( abbr ) )
    selection = cmds.ls(sl=True)
    indices = []

    for item in selection:
        components = expression.search( item )

        if components:
            components = components.groupdict( )

            if components['num1'] is not None:
                for i in range( int( components['num1'] ), int( components['num2'] ) + 1 ):
                    indices.append( i )

            elif components['num3'] is not None:
                indices.append( int( components['num3'] ) )


    indices.sort()

    return indices



def  get_component_selections():
    results = {
        Comp_Type.VERTEX: get_component_selection(Comp_Type.VERTEX),
        Comp_Type.EDGE: get_component_selection(Comp_Type.EDGE),
        Comp_Type.FACE: get_component_selection(Comp_Type.FACE),
    }
    
    return results



def plot_percent_on_curve(curve: str | Node, percent: float, marker: str | Node):
    
    #I use a motion path constraint, because the percents are correct even
    #in cases where the curve isn't uniform.  E.g. one long span and two
    #short spans will put 50% 1/2 through span 2 when using PointOnCurve
    
    curve_name = node_name(curve)
    marker_name = node_name(marker)
    motion_path = cmds.createNode('motionPath')
    cmds.setAttr(motion_path + '.fractionMode', True)
    cmds.connectAttr(curve_name + '.worldSpace[0]', motion_path + '.geometryPath')
    cmds.setAttr(motion_path + '.uValue', percent)
    cmds.connectAttr(motion_path + '.allCoordinates', marker_name + '.translate')
    cmds.disconnectAttr(motion_path + '.allCoordinates', marker_name + '.translate')
    cmds.delete(motion_path)
        
