import pygame
from core.graph_hierarchy import GraphNode
from core.spatial_index import QuadTree

class District(GraphNode):
    def __init__(self, uid, name, bounds, capacity=10):
        super().__init__(uid)
        self.name = name
        self.bounds = bounds # pygame.Rect
        self.quadtree = QuadTree(bounds, capacity)
        self.people = []
        self.buildings = []
        self.is_quarantined = False  # Track if district is quarantined
        
    def add_building(self, building):
        self.buildings.append(building)
        
    def add_person(self, person):
        self.people.append(person)
        self.quadtree.insert(person)
        
    def update(self, time_engine=None):
        # Rebuild quadtree every frame for moving entities
        # Optimization: Only rebuild if movement threshold exceeded
        self.quadtree.clear()
        for person in self.people:
            person.update(time_engine)
            
            # NOTE: We removed the strict clamping to bounds here to allow inter-district travel.
            # People can now move outside their home district to go to work.
            # However, for QuadTree efficiency, we might want to migrate them to the new district's list
            # if they stay there long term, but for now, keeping them in their home district list
            # while they physically move elsewhere is simpler, though it breaks spatial indexing efficiency.
            
            # Ideally: If person leaves district bounds, move them to the new district's people list.
            # But that requires a global lookup or reference to neighbors.
            
            # For Phase 2 MVP, we will just let them move freely but still be managed by home district.
            # The QuadTree insert will fail if they are outside bounds, so we need to handle that.
            
            if self.bounds.collidepoint(person.x, person.y):
                self.quadtree.insert(person)
            
            person.tick_infection()
