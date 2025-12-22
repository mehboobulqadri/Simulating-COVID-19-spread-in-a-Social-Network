import pygame

class QuadTree:
    def __init__(self, boundary, capacity=4):
        self.boundary = boundary  # pygame.Rect
        self.capacity = capacity
        self.points = []
        self.divided = False
        self.northeast = None
        self.northwest = None
        self.southeast = None
        self.southwest = None

    def insert(self, entity):
        # entity must have .x and .y attributes
        if not self.boundary.collidepoint(entity.x, entity.y):
            return False

        if len(self.points) < self.capacity:
            self.points.append(entity)
            return True
        else:
            if not self.divided:
                self.subdivide()
            
            if self.northeast.insert(entity): return True
            if self.northwest.insert(entity): return True
            if self.southeast.insert(entity): return True
            if self.southwest.insert(entity): return True
            
        return False

    def subdivide(self):
        x = self.boundary.x
        y = self.boundary.y
        w = self.boundary.width / 2
        h = self.boundary.height / 2

        self.northeast = QuadTree(pygame.Rect(x + w, y, w, h), self.capacity)
        self.northwest = QuadTree(pygame.Rect(x, y, w, h), self.capacity)
        self.southeast = QuadTree(pygame.Rect(x + w, y + h, w, h), self.capacity)
        self.southwest = QuadTree(pygame.Rect(x, y + h, w, h), self.capacity)
        self.divided = True

    def query(self, range_rect, found=None):
        if found is None:
            found = []

        if not self.boundary.colliderect(range_rect):
            return found

        for p in self.points:
            if range_rect.collidepoint(p.x, p.y):
                found.append(p)

        if self.divided:
            self.northeast.query(range_rect, found)
            self.northwest.query(range_rect, found)
            self.southeast.query(range_rect, found)
            self.southwest.query(range_rect, found)

        return found

    def clear(self):
        self.points = []
        self.divided = False
        self.northeast = None
        self.northwest = None
        self.southeast = None
        self.southwest = None
