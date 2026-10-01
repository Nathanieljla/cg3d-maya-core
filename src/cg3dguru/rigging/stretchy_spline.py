"""Create a stretch network for selected spline IK handles."""

from maya import cmds


def create_stretchy_spline():
    selection = cmds.ls(selection=True, type="ikHandle") or []

    decompose = cmds.createNode("decomposeMatrix")
    nearest = cmds.createNode("nearestPointOnCurve")
    cmds.connectAttr(decompose + ".outputTranslate", nearest + ".inPosition")

    try:
        for handle in selection:
            curves = cmds.listConnections(handle + ".inCurve", source=True, destination=False) or []
            if not curves:
                continue
            curve = curves[0]

            start_joint = cmds.ls(
                cmds.ikHandle(handle, query=True, startJoint=True), long=True
            )[0]
            end_effector = cmds.ikHandle(handle, query=True, endEffector=True)
            end_joints = cmds.listConnections(
                end_effector + ".translateX", source=True, destination=False
            ) or []
            if not end_joints:
                continue

            cmds.connectAttr(curve + ".worldSpace[0]", nearest + ".inputCurve", force=True)
            current_joint = cmds.ls(end_joints[0], long=True)[0]
            last_distance = None

            while current_joint != start_joint:
                parents = cmds.listRelatives(current_joint, parent=True, fullPath=True) or []
                if not parents:
                    break
                current_joint = parents[0]

                cmds.connectAttr(current_joint + ".worldMatrix[0]", decompose + ".inputMatrix", force=True)
                point = cmds.createNode("pointOnCurveInfo")
                cmds.connectAttr(curve + ".worldSpace[0]", point + ".inputCurve")

                cmds.connectAttr(nearest + ".parameter", point + ".parameter", force=True)
                cmds.disconnectAttr(nearest + ".parameter", point + ".parameter")

                distance = cmds.createNode("distanceBetween")
                cmds.connectAttr(point + ".position", distance + ".point1")
                if last_distance:
                    cmds.connectAttr(point + ".position", last_distance + ".point2")
                    divide = cmds.createNode("multiplyDivide")
                    cmds.connectAttr(last_distance + ".distance", divide + ".input1X")
                    cmds.setAttr(divide + ".input2X", cmds.getAttr(last_distance + ".distance"))
                    cmds.setAttr(divide + ".operation", 2)
                    cmds.connectAttr(divide + ".outputX", current_joint + ".scaleX")

                last_distance = distance
    finally:
        cmds.delete(decompose, nearest)
        cmds.select(selection, replace=True)


def run():
    create_stretchy_spline()
