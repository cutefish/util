class Node(object):
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
        names = fullname.split('/')
        if names[0] != '':
            raise ValueError("Name must starts with /: %s" % fullname)
        curr = self
        for name in names[1:]:
            child = curr.get_child(name)
            if child is None:
                return None
            curr = child
        return curr

    def level(self):
        """Current level of this node. The topmost level is 0."""
        count = 0
        curr = self
        while curr is not None:
            curr = curr.parent
            count += 1
        return count

    def __str__(self):
        return '%s:%s' % (self.fullname(), self.ip)


class Topology(object):
    def __init__(self):
        self.root = Node('', None)

    def add_node(self, fullname, ip):
        """Add a node."""
        names = fullname.split('/')
        if names[0] != "":
            raise ValueError("Name must starts with /: %s" % fullname)
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
        for leaf in self.getleaves(scope):
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
                queue.append(node)
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
                queue.append(node)
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

    def get_string(self, scope=None, endmark='#'):
        if scope is None:
            node = self.root
        else:
            node = self.get_node(scope)
        result = []
        pstack = []
        curr = node
        cvisited = False
        while (len(pstack) > 0) or (not cvisited):
            if not cvisited:
                if len(curr.children) > 0:
                    pstack.append((curr, 0))
                    result.append('(%s,%s)' % (curr.name, curr.ip))
                else:
                    cvisited = True
                    result.append('(%s,%s)%s' % (curr.name, curr.ip, endmark))
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
                    result.append(endmark)
        return ''.join(result)
