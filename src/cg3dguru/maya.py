"""Small, explicit Maya node and attribute handles built on :mod:`maya.cmds`.

The wrappers in this module intentionally cover only the conveniences used by
cg3dguru.  They are not a replacement for PyMEL's complete object model.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from maya import cmds


def node_name(node: str | "Node") -> str:
    """Return a Maya node name from either a string or :class:`Node`."""
    if isinstance(node, Node):
        return node.name()
    if isinstance(node, str):
        return node
    raise TypeError("Expected a Maya node name or Node, got {!r}".format(node))


def plug_name(plug: str | "Attribute") -> str:
    """Return a full plug name from either a string or :class:`Attribute`."""
    if isinstance(plug, Attribute):
        return plug.name()
    if isinstance(plug, str):
        return plug
    raise TypeError("Expected a Maya plug name or Attribute, got {!r}".format(plug))


class Node:
    """A lightweight handle around a Maya node name."""

    __slots__ = ("_name",)

    def __init__(self, name: str | "Node"):
        self._name = node_name(name) if isinstance(name, Node) else str(name)

    def __str__(self) -> str:
        return self._name

    def __repr__(self) -> str:
        return "Node({!r})".format(self._name)

    def __hash__(self) -> int:
        return hash(self._name)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Node):
            return self._name == other._name
        if isinstance(other, str):
            return self._name == other
        return NotImplemented

    def __lt__(self, other: object) -> bool:
        if isinstance(other, (Node, str)):
            return self._name < node_name(other)
        return NotImplemented

    def name(self) -> str:
        return self._name

    def exists(self) -> bool:
        return bool(cmds.objExists(self._name))

    def type(self) -> str:
        return cmds.nodeType(self._name)

    def attr(self, name: str) -> "Attribute":
        return Attribute(self, name)

    def getShapes(self, **kwargs: Any) -> list["Node"]:
        kwargs.setdefault("shapes", True)
        return [Node(name) for name in (cmds.listRelatives(self._name, **kwargs) or [])]

    def getParent(self) -> "Node | None":
        parents = cmds.listRelatives(self._name, parent=True, fullPath=True) or []
        return Node(parents[0]) if parents else None

    def __getattr__(self, name: str) -> "Attribute":
        if name.startswith("_"):
            raise AttributeError(name)
        return self.attr(name)


class Attribute:
    """A lightweight handle around a Maya plug.

    Attribute access on a compound handle resolves sibling child plugs, so a
    data block returned by ``BaseData.get_data`` supports concise expressions
    such as ``data.enabled.set(True)``.
    """

    __slots__ = ("_node", "_attribute")

    def __init__(self, node: str | Node, attribute: str | None = None):
        if attribute is None:
            path = str(node)
            if "." not in path:
                raise ValueError("A plug path must contain a node and attribute")
            node, attribute = path.split(".", 1)
        self._node = as_node(node)
        self._attribute = str(attribute)

    def __str__(self) -> str:
        return self.name()

    def __repr__(self) -> str:
        return "Attribute({!r})".format(self.name())

    def __hash__(self) -> int:
        return hash(self.name())

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Attribute):
            return self.name() == other.name()
        if isinstance(other, str):
            return self.name() == other
        return NotImplemented

    def name(self) -> str:
        return "{}.{}".format(self._node.name(), self._attribute)

    def node(self) -> Node:
        return self._node

    def exists(self) -> bool:
        return bool(cmds.objExists(self.name()))

    def get(self, **kwargs: Any) -> Any:
        return cmds.getAttr(self.name(), **kwargs)

    def set(self, *values: Any, **kwargs: Any) -> Any:
        if "type" not in kwargs and len(values) == 1:
            value = values[0]
            attribute_type = cmds.getAttr(self.name(), type=True)
            if attribute_type == "string" and isinstance(value, str):
                kwargs["type"] = "string"
            elif attribute_type == "stringArray":
                sequence = list(value)
                return cmds.setAttr(
                    self.name(), len(sequence), *sequence, type=attribute_type, **kwargs
                )
            elif attribute_type in {"Int32Array", "doubleArray"}:
                return cmds.setAttr(
                    self.name(), list(value), type=attribute_type, **kwargs
                )
            elif attribute_type in {
                "float2", "float3", "double2", "double3",
                "long2", "long3", "short2", "short3",
            }:
                values = tuple(value)
                kwargs["type"] = attribute_type
            elif attribute_type in {"vectorArray", "pointArray"}:
                sequence = list(value)
                return cmds.setAttr(
                    self.name(), len(sequence), *sequence, type=attribute_type, **kwargs
                )
            elif attribute_type == "matrix" and not isinstance(value, str):
                values = tuple(value)
                kwargs["type"] = "matrix"
        return cmds.setAttr(self.name(), *values, **kwargs)

    def isLocked(self) -> bool:
        return bool(cmds.getAttr(self.name(), lock=True))

    def lock(self) -> None:
        cmds.setAttr(self.name(), lock=True)

    def unlock(self) -> None:
        cmds.setAttr(self.name(), lock=False)

    def getArrayIndices(self) -> list[int]:
        return cmds.getAttr(self.name(), multiIndices=True) or []

    def inputs(self, **kwargs: Any) -> list[Node]:
        kwargs.setdefault("source", True)
        kwargs.setdefault("destination", False)
        return _connected_nodes(self.name(), kwargs)

    def outputs(self, **kwargs: Any) -> list[Node]:
        kwargs.setdefault("source", False)
        kwargs.setdefault("destination", True)
        return _connected_nodes(self.name(), kwargs)

    def connect(self, destination: str | "Attribute", force: bool = False) -> None:
        cmds.connectAttr(self.name(), plug_name(destination), force=force)

    def disconnect(self, destination: str | "Attribute") -> None:
        cmds.disconnectAttr(self.name(), plug_name(destination))

    def __getitem__(self, index: int) -> "Attribute":
        return Attribute(self._node, "{}[{}]".format(self._attribute, index))

    def __getattr__(self, name: str) -> "Attribute":
        if name.startswith("_"):
            raise AttributeError(name)
        parent_name = self._attribute.split("[", 1)[0]
        children = cmds.attributeQuery(
            parent_name, node=self._node.name(), listChildren=True
        ) or []
        if name in children:
            return self._node.attr(name)
        matches = [child for child in children if child.endswith("_" + name)]
        if len(matches) == 1:
            return self._node.attr(matches[0])
        return self._node.attr(name)


def _connected_nodes(path: str, kwargs: dict[str, Any]) -> list[Node]:
    kwargs.setdefault("plugs", False)
    connections = cmds.listConnections(path, **kwargs) or []
    if kwargs.get("plugs") or kwargs.get("p"):
        return connections
    return [Node(name) for name in connections]


def as_node(node: str | Node) -> Node:
    return node if isinstance(node, Node) else Node(node)


def as_attribute(attribute: str | Attribute) -> Attribute:
    return attribute if isinstance(attribute, Attribute) else Attribute(attribute)


def nodes(values: Iterable[str | Node] | None) -> list[Node]:
    return [as_node(value) for value in (values or [])]


def ls(*args: Any, **kwargs: Any) -> list[Node]:
    """Call ``cmds.ls`` and return lightweight node handles."""
    return nodes(cmds.ls(*args, **kwargs))


def has_attr(node: str | Node, attribute: str) -> bool:
    return bool(cmds.attributeQuery(attribute, node=node_name(node), exists=True))


def create_node(node_type: str, **kwargs: Any) -> Node:
    return Node(cmds.createNode(node_type, **kwargs))
