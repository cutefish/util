import unittest

from pyutil.net import Node, Topology

class TestTopology(unittest.TestCase):
    def testNode(self):
        top = Node('dc', None)
        rack1 = Node('rack1', None)
        node1 = Node('N1', None)
        rack2 = Node('rack2', None)
        node2 = Node('N2', None)
        top.add_children([rack1, rack2])
        rack1.add_child(node1)
        rack2.add_child(node2)
        self.assertEqual(node1.fullname(), '/dc/rack1/node1')
        self.assertEqual(node2.fullname(), '/dc/rack2/node2')
        self.assertEqual(node1.level(), 2)
        self.assertEqual(node2.level(), 2)
        self.assertEqual(top.get_node('/dc/rack1'), rack1)
        self.assertEqual(top.get_node('/dc/rack2'), rack2)

    def testTopology(self):
        topology = Topology()
        topology.addNodes(
                ['/dc/rack1/N%s' % (i) for i in range(1, 7)] +
                ['/dc/rack2/N%s' % (i) for i in range(7, 13)] +
                ['/dc/rack3/N%s' % (i) for i in range(13, 19)] +
                ['/dc/rack4/N%s' % (i) for i in range(19, 25)],
                ['192.168.0.1%02d' % (i) for i in range(1, 25)]
                )
        topology.printToStdout()
        self.assertEqual(len(topology.getLeaves("")), 24)
        self.assertEqual(len(topology.getRacks("")), 4)
        rack = topology.root.findByName('/dc/rack1')
        self.assertEqual('/dc/rack1', rack.getFullName())
        node = rack.findByName('/N5')
        self.assertEqual('/dc/rack1/N5', node.getFullName())
        self.assertEqual(node.ip, '192.168.0.105')
        n1 = topology.findNode('192.168.0.107')
        n2 = topology.findNode('192.168.0.108')
        n3 = topology.findNode('192.168.0.124')
        r1 = topology.findNode('/dc/rack1')
        self.assertEqual(topology.getDistance(n1, n2), 2)
        self.assertEqual(topology.getDistance(n2, n3), 4)
        self.assertEqual(topology.getDistance(n1, r1), 3)
        self.assertEqual(topology.getDistance(r1, n3), 3)

if __name__ == '__main__':
    suite = unittest.TestSuite([
        unittest.TestLoader().loadTestsFromTestCase(TestTopology),
    ])
    unittest.TextTestRunner().run(suite)
