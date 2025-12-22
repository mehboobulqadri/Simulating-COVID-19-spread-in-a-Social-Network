class GraphNode:
    def __init__(self, uid, parent=None):
        self.uid = uid
        self.parent = parent
        self.children = []
        self.neighbors = []  # Adjacency list

    def add_child(self, child):
        self.children.append(child)
        child.parent = self

    def add_neighbor(self, neighbor, weight=1.0):
        self.neighbors.append((neighbor, weight))
