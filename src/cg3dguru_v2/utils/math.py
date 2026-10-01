"""Transform and vector helpers using Maya Python API 2.0."""

from __future__ import annotations

import enum
import math

from maya import cmds
from maya.api import OpenMaya as om

from ..maya import Node, node_name


Vector = om.MVector
Matrix = om.MMatrix


class Axis(enum.Flag):
    X = enum.auto()
    Y = enum.auto()
    Z = enum.auto()
    ALL = X | Y | Z
    REVERSE = enum.auto()
    NEG_X = X | REVERSE
    NEG_Y = Y | REVERSE
    NEG_Z = Z | REVERSE


class Space(enum.Enum):
    OBJECT = 0
    WORLD = 1
    PARENT = 2
    CAMERA = 3
    TANGENT = 4
    UV = 5


class Direction(enum.Flag):
    FORWARD = enum.auto()
    UP = enum.auto()
    RIGHT = enum.auto()
    REVERSE = enum.auto()
    BACKWARDS = FORWARD | REVERSE
    DOWN = UP | REVERSE
    LEFT = RIGHT | REVERSE


class Flip(enum.Enum):
    FORWARD = 0
    UP = 1
    RIGHT = 2


def _vector(value) -> om.MVector:
    return om.MVector(value)


def _normal(value) -> om.MVector:
    result = _vector(value)
    result.normalize()
    return result


def _matrix_values(matrix: om.MMatrix) -> list[float]:
    return [matrix.getElement(row, column) for row in range(4) for column in range(4)]


class MatrixUtils:
    """Get and set transforms in forward/up/right terms."""

    def __init__(self, transform_node=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._transform_node = None
        self.transform_node = transform_node
        self._right_axis = Axis.X
        self._up_axis = Axis.Y
        self._forward_axis = Axis.Z
        self._flip = Flip.RIGHT
        self._space = Space.WORLD

    @property
    def transform_node(self) -> str | Node | None:
        return self._transform_node

    @transform_node.setter
    def transform_node(self, node: str | Node | None):
        if node is not None:
            name = node_name(node)
            if not cmds.objExists(name) or not cmds.objectType(name, isAType="transform"):
                raise TypeError("Expected a Maya transform node")
        self._transform_node = node

    @property
    def space(self) -> Space:
        return self._space

    @space.setter
    def space(self, value: Space):
        if not isinstance(value, Space):
            raise TypeError("Expected Space")
        self._space = value

    @property
    def Flip(self) -> Flip:
        return self._flip

    @Flip.setter
    def Flip(self, value: Flip):
        if not isinstance(value, Flip):
            raise TypeError("Expected Flip")
        self._flip = value

    @property
    def forward(self) -> om.MVector:
        return self.get_axis_vector(self.get_matrix(), self._forward_axis)

    @property
    def up(self) -> om.MVector:
        return self.get_axis_vector(self.get_matrix(), self._up_axis)

    @property
    def right(self) -> om.MVector:
        return self.get_axis_vector(self.get_matrix(), self._right_axis)

    @staticmethod
    def get_world_pos(obj_name) -> om.MVector:
        values = cmds.xform(node_name(obj_name), query=True, matrix=True, worldSpace=True)
        return om.MVector(*values[12:15])

    @staticmethod
    def get_matrix_position(matrix: om.MMatrix) -> om.MVector:
        return om.MVector(
            matrix.getElement(3, 0),
            matrix.getElement(3, 1),
            matrix.getElement(3, 2),
        )

    @staticmethod
    def set_matrix_translation(matrix: om.MMatrix, position: om.MVector):
        position = _vector(position)
        matrix.setElement(3, 0, position.x)
        matrix.setElement(3, 1, position.y)
        matrix.setElement(3, 2, position.z)
        return matrix

    @staticmethod
    def get_axis_vector(matrix: om.MMatrix, axis: Axis) -> om.MVector:
        if Axis.X in axis:
            row = 0
        elif Axis.Y in axis:
            row = 1
        elif Axis.Z in axis:
            row = 2
        else:
            raise ValueError("Axis must contain X, Y, or Z")

        vector = om.MVector(*(matrix.getElement(row, column) for column in range(3)))
        return -vector if Axis.REVERSE in axis else vector

    @staticmethod
    def set_axis_vector(matrix: om.MMatrix, vector: om.MVector, axis: Axis):
        if Axis.X in axis:
            row = 0
        elif Axis.Y in axis:
            row = 1
        elif Axis.Z in axis:
            row = 2
        else:
            raise ValueError("Axis must contain X, Y, or Z")

        vector = _vector(vector)
        if Axis.REVERSE in axis:
            vector = -vector
        for column, value in enumerate((vector.x, vector.y, vector.z)):
            matrix.setElement(row, column, value)
        return matrix

    @staticmethod
    def ensure_right_handedness(forward, up, right, handedness_rule: Flip):
        if not (((right ^ up) * forward) > 0 and ((up ^ forward) * right) > 0):
            target = {
                Flip.RIGHT: right,
                Flip.UP: up,
                Flip.FORWARD: forward,
            }[handedness_rule]
            target.x = -target.x
            target.y = -target.y
            target.z = -target.z

    @staticmethod
    def set_matrix_vectors(matrix, x, y, z, position, flip: Flip, ignore_scale: bool):
        x, y, z = _vector(x), _vector(y), _vector(z)
        MatrixUtils.ensure_right_handedness(z, y, x, flip)
        if ignore_scale:
            x, y, z = _normal(x), _normal(y), _normal(z)
        MatrixUtils.set_axis_vector(matrix, x, Axis.X)
        MatrixUtils.set_axis_vector(matrix, y, Axis.Y)
        MatrixUtils.set_axis_vector(matrix, z, Axis.Z)
        MatrixUtils.set_matrix_translation(matrix, position)
        return matrix

    @staticmethod
    def get_three_point_matrix(p1, p2, p3, u_dir=None):
        p1, p2, p3 = _vector(p1), _vector(p2), _vector(p3)
        forward = _normal(p3 - p1)
        right = _normal(p2 - p1)
        if math.fabs(forward * right) > 0.999:
            om.MGlobal.displayError("Your three points are too in line with one another!")
            return None

        right, up = MatrixUtils.get_orthogonal_vectors(forward, right, v3_dir=u_dir)
        return MatrixUtils.set_matrix_vectors(
            om.MMatrix(), forward, up, right, p1, Flip.RIGHT, True
        )

    @staticmethod
    def get_world_matrix(obj_name) -> om.MMatrix:
        name = node_name(obj_name)
        values = cmds.xform(name, query=True, matrix=True, worldSpace=True)
        pivot = cmds.xform(name, query=True, worldSpace=True, rotatePivot=True)
        values[12:15] = pivot
        return om.MMatrix(values)

    @staticmethod
    def set_world_matrix(obj_name, matrix, no_scale=False):
        if no_scale:
            transform = om.MTransformationMatrix(matrix)
            transform.setScale((1.0, 1.0, 1.0), om.MSpace.kTransform)
            matrix = transform.asMatrix()
        cmds.xform(
            node_name(obj_name), matrix=_matrix_values(matrix), worldSpace=True
        )

    @staticmethod
    def get_third_axis(a1: Axis, a2: Axis):
        used = (a1 | a2) & ~Axis.REVERSE
        return Axis.ALL & ~used

    @staticmethod
    def get_orthogonal_vectors(v1, v2, v3_dir=None):
        v1, v2 = _vector(v1), _vector(v2)
        v3 = _normal(v1 ^ v2)
        if v3_dir is not None and v3 * _vector(v3_dir) < 0:
            v3 = -v3

        scale = v2.length()
        v2 = _normal(v3 ^ v1) * scale
        return v2, v3

    def set_forward_up_coordinates(self, forward: Axis, up: Axis):
        self._forward_axis = forward
        self._up_axis = up
        self._right_axis = self.get_third_axis(forward, up)

    def set_coordinates(self, foward: Axis, up: Axis, right: Axis):
        self._forward_axis = foward
        self._up_axis = up
        self._right_axis = right

    def get_matrix(self) -> om.MMatrix:
        if self.transform_node is None:
            raise ValueError("transform_node is not set")
        space_flag = (
            {"worldSpace": True} if self.space == Space.WORLD else {"objectSpace": True}
        )
        values = cmds.xform(
            node_name(self.transform_node),
            query=True,
            matrix=True,
            **space_flag
        )
        return om.MMatrix(values)

    def get_translation(self) -> om.MVector:
        if self.transform_node is None:
            raise ValueError("transform_node is not set")
        space_flag = (
            {"worldSpace": True} if self.space == Space.WORLD else {"objectSpace": True}
        )
        values = cmds.xform(
            node_name(self.transform_node),
            query=True,
            translation=True,
            **space_flag
        )
        return om.MVector(*values)

    def _set_forward_up_right(self, forward, up, right, flip: Flip, ignore_scale: bool):
        forward, up, right = _vector(forward), _vector(up), _vector(right)
        self.ensure_right_handedness(forward, up, right, flip)
        if ignore_scale:
            forward, up, right = _normal(forward), _normal(up), _normal(right)

        matrix = self.get_matrix()
        self.set_axis_vector(matrix, forward, self._forward_axis)
        self.set_axis_vector(matrix, up, self._up_axis)
        self.set_axis_vector(matrix, right, self._right_axis)
        space_flag = (
            {"worldSpace": True} if self.space == Space.WORLD else {"objectSpace": True}
        )
        cmds.xform(
            node_name(self.transform_node),
            matrix=_matrix_values(matrix),
            **space_flag
        )

    def set_forward_up(self, forward, up, priority=Direction.FORWARD, ignore_scale=True):
        if Direction.FORWARD in priority:
            up, right = self.get_orthogonal_vectors(forward, up)
        elif Direction.UP in priority:
            forward, right = self.get_orthogonal_vectors(up, forward)
        else:
            raise TypeError("Priority must contain FORWARD or UP")
        self._set_forward_up_right(forward, up, right, Flip.RIGHT, ignore_scale)

    def set_forward_right(self, forward, right, priority=Direction.FORWARD, ignore_scale=True):
        if Direction.FORWARD in priority:
            right, up = self.get_orthogonal_vectors(forward, right)
        elif Direction.RIGHT in priority:
            forward, up = self.get_orthogonal_vectors(right, forward)
        else:
            raise TypeError("Priority must contain FORWARD or RIGHT")
        self._set_forward_up_right(forward, up, right, Flip.UP, ignore_scale)

    def set_up_right(self, up, right, priority=Direction.UP, ignore_scale=True):
        if Direction.UP in priority:
            right, forward = self.get_orthogonal_vectors(up, right)
        elif Direction.RIGHT in priority:
            up, forward = self.get_orthogonal_vectors(right, up)
        else:
            raise TypeError("Priority must contain UP or RIGHT")
        self._set_forward_up_right(forward, up, right, Flip.FORWARD, ignore_scale)
