import pygame
from core.graph_hierarchy import GraphNode

class City(GraphNode):
    def __init__(self, uid, name, location):
        super().__init__(uid)
        self.name = name
        self.location = location # (x, y) center
        self.districts = []
        
    def add_district(self, district):
        self.districts.append(district)
        self.add_child(district)
        
    def update(self, time_engine=None):
        for district in self.districts:
            district.update(time_engine)
