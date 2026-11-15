"""Integration tests intended to run with Autodesk Maya's mayapy."""

import unittest

import maya.standalone
from maya import cmds
from maya.api import OpenMaya as om

from cg3dguru import udata
from cg3dguru.maya import Attribute, Node
from cg3dguru.rigging.stretchy_spline import create_stretchy_spline
from cg3dguru.utils.math import MatrixUtils
from cg3dguru.utils.modeling import plot_percent_on_curve


class MayaV2IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        maya.standalone.initialize(name="python")

    @classmethod
    def tearDownClass(cls):
        maya.standalone.uninitialize()

    def tearDown(self):
        cmds.file(new=True, force=True)

    def test_udata_handles_and_attribute_types(self):
        class DemoData(udata.BaseData):
            @staticmethod
            def get_attributes():
                return [
                    udata.create_attr("label", "string"),
                    udata.create_attr("enabled", "bool"),
                    udata.create_attr("indices", "Int32Array"),
                    udata.create_attr("color", "float3"),
                    udata.create_attr("link", "message"),
                ]

            @classmethod
            def post_create(cls, data):
                data.label.set("hello")
                data.enabled.set(True)

        node, data = DemoData.create_node(name="v2Demo")
        source = Node(cmds.createNode("transform", name="v2Source"))

        self.assertIsInstance(node, Node)
        self.assertIsInstance(data, Attribute)
        self.assertEqual(data.label.get(), "hello")
        self.assertTrue(data.enabled.get())

        data.indices.set([2, 4, 8])
        data.color.set((0.25, 0.5, 0.75))
        source.message.connect(data.link)

        self.assertEqual(data.indices.get(), [2, 4, 8])
        self.assertEqual(data.color.get()[0], (0.25, 0.5, 0.75))
        self.assertEqual(data.link.inputs(), [source])
        self.assertEqual(data.attr("label"), data.label)
        self.assertEqual(data.attr("label").get(), "hello")
        self.assertEqual(DemoData.get_data(str(node)).label.get(), "hello")
        self.assertEqual(udata.Utils.get_nodes_with_data([str(node)], DemoData), [node])

        DemoData.delete_data(node)
        self.assertIsNone(DemoData.get_data(node))

    def test_udata_supports_more_than_ten_compound_children(self):
        class LargeData(udata.BaseData):
            @staticmethod
            def get_attributes():
                attributes = [
                    udata.create_attr("link{}".format(index), "message")
                    for index in range(4)
                ]
                attributes.extend(
                    udata.create_attr("enabled{}".format(index), "bool")
                    for index in range(2)
                )
                attributes.extend(
                    udata.create_attr(
                        "axis{}".format(index), "enum",
                        enumName="X:Y:Z", defaultValue=index % 3,
                    )
                    for index in range(8)
                )
                return attributes

        node, data = LargeData.create_node(name="largeData")

        children = cmds.attributeQuery(
            "LargeData", node=str(node), listChildren=True
        )
        self.assertEqual(len(children), 14)
        self.assertEqual(children[-1], "axis7")
        self.assertEqual(data.axis7.get(), 1)
        data.axis7.set(2)
        self.assertEqual(LargeData.get_data(node).axis7.get(), 2)

    def test_udata_schema_update_preserves_values_and_locks(self):
        class VersionedData(udata.BaseData):
            schema_version = (0, 0, 0)
            include_new_attribute = False

            @classmethod
            def get_class_version(cls):
                return cls.schema_version

            @classmethod
            def get_attributes(cls):
                result = [udata.create_attr("label", "string")]
                if cls.include_new_attribute:
                    result.append(
                        udata.create_attr("enabled", "bool", defaultValue=True)
                    )
                return result

            @classmethod
            def post_create(cls, data):
                data.label.set("preserved")
                data.label.lock()

        node, _ = VersionedData.create_node(name="versionedData")
        VersionedData.schema_version = (0, 1, 0)
        VersionedData.include_new_attribute = True
        VersionedData.attributes = []

        old_auto_update = udata.AUTO_UPDATE
        udata.AUTO_UPDATE = True
        try:
            data = VersionedData.get_data(node)
        finally:
            udata.AUTO_UPDATE = old_auto_update

        self.assertEqual(data.label.get(), "preserved")
        self.assertTrue(data.label.isLocked())
        self.assertTrue(data.enabled.get())
        self.assertEqual(VersionedData.get_record(node).version, (0, 1, 0))

    def test_node_handles_survive_duplicate_names_renames_and_reparenting(self):
        first_parent = cmds.createNode("transform", name="firstParent")
        second_parent = cmds.createNode("transform", name="secondParent")
        first = Node(
            cmds.createNode("transform", name="duplicate", parent=first_parent)
        )
        second = Node(
            cmds.createNode("transform", name="duplicate", parent=second_parent)
        )

        self.assertNotEqual(first, second)
        self.assertEqual(first.name(), "|firstParent|duplicate")
        self.assertEqual(second.name(), "|secondParent|duplicate")
        self.assertEqual(first.short_name(), "duplicate")
        self.assertEqual(second.short_name(), "duplicate")
        self.assertEqual(Node(first.name()), first)
        with self.assertRaises(ValueError):
            Node("duplicate")

        original_hash = hash(first)
        tracked = {first}
        cmds.rename(first.name(), "renamed")
        self.assertEqual(first.name(), "|firstParent|renamed")
        self.assertEqual(hash(first), original_hash)
        self.assertIn(first, tracked)

        cmds.parent(first.name(), second_parent)
        self.assertEqual(first.name(), "|secondParent|renamed")
        self.assertEqual(first.getParent(), Node("|secondParent"))

        # Reproduce the proxy-rig collision: the output container and a
        # cloned source joint can legitimately share a short name.
        proxy_root = Node(cmds.createNode("transform", name="proxyRoot"))
        skeleton_root = Node(
            cmds.createNode(
                "transform", name="skeletonRoot", parent=proxy_root.name()
            )
        )
        cloned_root = Node(
            cmds.createNode(
                "joint", name="proxyRoot", parent=skeleton_root.name()
            )
        )
        self.assertEqual(proxy_root.name(), "|proxyRoot")
        self.assertEqual(
            cloned_root.name(), "|proxyRoot|skeletonRoot|proxyRoot"
        )
        self.assertEqual(proxy_root.getParent(), None)
        self.assertEqual(skeleton_root.getParent(), proxy_root)

        data_node = Node(cmds.createNode("network", name="identityData"))
        cmds.addAttr(data_node.name(), longName="source", attributeType="message")
        proxy_root.message.connect(data_node.source)
        self.assertEqual(data_node.source.inputs(), [proxy_root])

        cmds.delete(first.name())
        self.assertFalse(first.exists())
        with self.assertRaises(RuntimeError):
            first.name()

    def test_matrix_and_curve_helpers(self):
        transform = cmds.createNode("transform", name="matrixTest")
        cmds.xform(transform, worldSpace=True, translation=(1, 2, 3))
        helper = MatrixUtils(transform)

        self.assertTrue(
            helper.get_translation().isEquivalent(om.MVector(1, 2, 3), 1e-6)
        )
        helper.set_forward_up(om.MVector(0, 0, 1), om.MVector(0, 1, 0))
        self.assertTrue(helper.forward.isEquivalent(om.MVector(0, 0, 1), 1e-6))

        curve = cmds.curve(
            degree=1, point=[(0, 0, 0), (10, 0, 0)], name="curveTest"
        )
        shape = cmds.listRelatives(curve, shapes=True, fullPath=True)[0]
        marker = cmds.spaceLocator(name="markerTest")[0]
        plot_percent_on_curve(shape, 0.5, marker)
        position = cmds.xform(marker, query=True, translation=True, worldSpace=True)
        self.assertAlmostEqual(position[0], 5.0)

    def test_stretchy_spline_network(self):
        cmds.select(clear=True)
        start = cmds.joint(position=(0, 0, 0), name="stretchA")
        cmds.joint(position=(5, 0, 0), name="stretchB")
        end = cmds.joint(position=(10, 0, 0), name="stretchC")
        curve = cmds.curve(
            degree=2,
            point=[(0, 0, 0), (5, 0, 0), (10, 0, 0)],
            name="stretchCurve",
        )
        handle = cmds.ikHandle(
            startJoint=start,
            endEffector=end,
            solver="ikSplineSolver",
            curve=curve,
            createCurve=False,
            parentCurve=False,
        )[0]
        cmds.select(handle, replace=True)

        create_stretchy_spline()

        self.assertTrue(cmds.ls(type="multiplyDivide"))
        self.assertTrue(
            cmds.listConnections(start + ".scaleX", source=True, destination=False)
        )


if __name__ == "__main__":
    unittest.main()
