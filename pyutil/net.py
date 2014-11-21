from pyutil.string import StringUtil

class Node(object):
    class SMarkError(Exception):
        pass

    def __init__(self, name, ip):
        self.name = name
        self.ip = ip
        self.parent = None
        self.children = []

    def fullname(self):
        """The full name of this node."""
        result = [self.name]
        curr = self.parent
        while curr is not None:
            result.insert(0, curr.name)
            curr = curr.parent
        result = '/'.join(result)
        if not result.startswith('/'):
            result = '/' + result
        return result

    def add_child(self, node):
        self.children.append(node)
        node.parent = self

    def add_children(self, nodes):
        for node in nodes:
            self.add_child(node)

    def get_child(self, name):
        """Get the child by name."""
        for child in self.children:
            if child.name == name:
                return child
        return None

    def get_node(self, fullname):
        """Get node by full name."""
        fullname = Node.normalize_name(fullname)
        # find the node
        names = fullname.split('/')
        curr = self
        for name in names[1:]:
            child = curr.get_child(name)
            if child is None:
                return None
            curr = child
        return curr

    def level(self):
        """Current level of this node. The topmost level is 0."""
        count = -1
        curr = self
        while curr is not None:
            curr = curr.parent
            count += 1
        return count

    def __str__(self):
        return '(%s, %s)' % (self.fullname(), self.ip)

    @classmethod
    def normalize_name(self, string):
        if not string.startswith('/'):
            raise ValueError("Name must starts with /: %s" % string)
        string = string.rstrip('/')
        result = []
        for i, ch in enumerate(string):
            if i == 0:
                result.append(ch)
            elif (ch == '/') and (result[-1] == '/'):
                continue
            else:
                result.append(ch)
        return ''.join(result)

    @classmethod
    def serialize(cls, node, writer, smark='(', emark=')', sep=','):
        if node is None:
            raise ValueError('Node is None.')
        cls.ensure_valid_ser(node, smark + emark + sep)
        writer.write('%s%s%s%s%s'
                     % (smark, node.name, sep, node.ip, emark))

    @classmethod
    def deserialize(self, reader, smark='(', emark=')', sep=','):
        ch = reader.read()
        if ch != smark:
            raise Node.SMarkError(ch)
        chars = []
        while ch != emark:
            ch = reader.read()
            if ch == '':
                raise EOFError('Unexpected EOF.')
            if ch != emark:
                chars.append(ch)
        name, ip = ''.join(chars).split(sep)
        ip = None if ip == 'None' else ip
        return Node(name, ip)

    @classmethod
    def ensure_valid_ser(cls, node, chars):
        if StringUtil.has_chars(node.name, chars):
            raise ValueError('Conflict node name and special chars: %s, %s'
                             % (node.name, chars))
        if (node.ip is not None) and StringUtil.has_chars(node.ip, chars):
            raise ValueError('Conflict node name and special chars: %s, %s'
                             % (node.ip, chars))


class Topology(object):
    class SMarkError(Exception):
        pass

    class EMarkError(Exception):
        pass

    def __init__(self):
        self.root = Node('', None)

    def add_node(self, fullname, ip):
        """Add a node."""
        fullname = Node.normalize_name(fullname)
        names = fullname.split('/')
        curr = self.root
        for i in range(1, len(names)):
            name = names[i]
            node = curr.get_child(name)
            nodeip = None if i != len(names) - 1 else ip
            if node is None:
                node = Node(name, nodeip)
                curr.add_child(node)
            curr = node
        return curr

    def add_nodes(self, nameips):
        """Add a list of nodes"""
        for name, ip in nameips:
            self.add_node(name, ip)

    def get_leaves(self, scope=None):
        """Get all leaf node under scope."""
        if scope is None:
            node = self.root
        else:
            node = self.root.get_node(scope)
        leaves = []
        queue = [node]
        while len(queue) != 0:
            curr = queue.pop(0)
            for child in curr.children:
                if len(child.children) == 0:
                    leaves.append(child)
                else:
                    queue.append(child)
        return sorted(leaves, key=str)

    def get_racks(self, scope=None):
        """Get all racks under scope."""
        racks = set([])
        for leaf in self.get_leaves(scope):
            racks.add(leaf.parent)
        return sorted(racks, key=str)

    def get_node(self, fullname):
        """Get the node by full name."""
        return self.root.get_node(fullname)

    def find_by_name(self, name):
        """Search the node by its name."""
        # bfs search
        queue = [self.root]
        while len(queue) > 0:
            node = queue.pop(0)
            if node.name == name:
                return node
            for child in node.children:
                queue.append(child)
        return None

    def find_by_ip(self, ip):
        """Search the node by its ip."""
        # bfs search
        queue = [self.root]
        while len(queue) > 0:
            node = queue.pop(0)
            if node.ip == ip:
                return node
            for child in node.children:
                queue.append(child)
        return None

    def get_nhops(self, node1, node2):
        if node1 is node2:
            return 0
        dis = 0
        while (node1 is not None) and (node1.level() > node2.level()):
            node1 = node1.parent
            dis += 1
        while (node2 is not None) and (node2.level() > node1.level()):
            node2 = node2.parent
            dis += 1
        while ((node1 is not None) and (node2 is not None) and
                (node1 is not node2)):
            node1 = node1.parent
            node2 = node2.parent
            dis += 2
        return dis

    @classmethod
    def serialize(cls, topology, writer, scope=None,
                  smark='{', emark='}', sep='$'):
        if topology is None:
            raise ValueError('Topology is None.')
        if scope is None:
            node = topology.root
        else:
            node = topology.get_node(scope)
        pstack = []
        curr = node
        cvisited = False
        writer.write(smark)
        while (len(pstack) > 0) or (not cvisited):
            if not cvisited:
                if len(curr.children) > 0:
                    pstack.append([curr, 0])
                    Node.ensure_valid_ser(node, smark + emark + sep)
                    Node.serialize(curr, writer)
                    curr = curr.children[0]
                else:
                    cvisited = True
                    Node.ensure_valid_ser(node, smark + emark + sep)
                    Node.serialize(curr, writer)
                    writer.write(sep)
            else:
                parent, idx = pstack[-1]
                if idx != len(parent.children) - 1:
                    idx += 1
                    pstack[-1][1] = idx
                    curr = parent.children[idx]
                    cvisited = False
                else:
                    pstack.pop()
                    curr = parent
                    writer.write(sep)
        writer.write(emark)

    @classmethod
    def deserialize(cls, reader, smark='{', emark='}', sep='$',
                    nsmark='(', nemark=')', nsep=','):
        ch = reader.read()
        if ch != smark:
            raise Topology.SMarkError(ch)
        topology = Topology()
        root = Node.deserialize(reader, nsmark, nemark, nsep)
        if root.name is not '' and root.ip is not None:
            raise ValueError('Incorrect root serialization.')
        curr = topology.root
        stack = [curr]
        while True:
            try:
                child = Node.deserialize(reader, nsmark, nemark, nsep)
                if curr is None:
                    root = child
                else:
                    curr.add_child(child)
                    stack.append(child)
                curr = child
            except Node.SMarkError as e:
                ch = e.args[0]
                if ch == sep:
                    if len(stack) == 0:
                        raise SyntaxError('Unmatching separators and nodes.')
                    stack.pop()
                    if len(stack) == 0:
                        break
                    curr = stack[-1]
                else:
                    raise Node.SMarkError(ch)
        ch = reader.read()
        if ch != emark:
            raise Topology.EMarkError(ch)
        return topology
