import unittest
from StringIO import StringIO

from pyutil.net import Node, Topology

class TestTopology(unittest.TestCase):
    def testNode(self):
        top = Node('dc', None)
        rack1 = Node('R1', None)
        node1 = Node('N1', None)
        rack2 = Node('R2', None)
        node2 = Node('N2', None)
        top.addchildren([rack1, rack2])
        rack1.addchild(node1)
        rack2.addchild(node2)
        self.assertEqual(node1.fullname(), '/dc/R1/N1')
        self.assertEqual(node2.fullname(), '/dc/R2/N2')
        self.assertEqual(node1.level(), 2)
        self.assertEqual(node2.level(), 2)
        self.assertEqual(top.getnode('/R1'), rack1)
        self.assertEqual(top.getnode('//R2///N2/'), node2)
        writer = StringIO()
        Node.serialize(top, writer)
        self.assertEqual(writer.getvalue(), '(dc,None)')
        reader = StringIO(writer.getvalue())
        node = Node.deserialize(reader)
        self.assertEqual(node.name, 'dc')
        self.assertEqual(node.ip, None)


    def testTopology(self):
        topology = Topology()
        topology.addnodes(
            [('/dc/R%s/N%s' % ((i - 1) / 6 + 1, i), '1%02d' % (i))
             for i in range(1, 25)])
        self.assertEqual(len(topology.getleaves()), 24)
        self.assertEqual(len(topology.getracks()), 4)
        self.assertEqual(len(topology.getleaves('/dc/R1/')), 6)
        node = topology.find_by_name('R1')
        self.assertEqual('/dc/R1', node.fullname())
        node = topology.find_by_name('N7')
        self.assertEqual('/dc/R2/N7', node.fullname())
        node = topology.find_by_ip('124')
        self.assertEqual('/dc/R4/N24', node.fullname())
        n1 = topology.find_by_ip('107')
        n2 = topology.find_by_ip('108')
        n3 = topology.find_by_ip('124')
        r1 = topology.find_by_name('R1')
        self.assertEqual(topology.getnhops(n1, n2), 2)
        self.assertEqual(topology.getnhops(n2, n3), 4)
        self.assertEqual(topology.getnhops(n1, r1), 3)
        self.assertEqual(topology.getnhops(r1, n3), 3)
        string = '{(,None)(dc,0)(r0,10)(n1,100)$(n2,101)$$(r1,11)(n3,110)$$$$}'
        reader = StringIO(string)
        topology = Topology.deserialize(reader)
        writer = StringIO()
        Topology.serialize(topology, writer)
        self.assertEqual(string, writer.getvalue())

if __name__ == '__main__':
    suite = unittest.TestSuite([
        unittest.TestLoader().loadTestsFromTestCase(TestTopology),
    ])
    unittest.TextTestRunner().run(suite)
