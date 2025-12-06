import pygame
from enum import Enum

class BuildingType(Enum):
    RESIDENTIAL = 0
    WORKPLACE = 1
    HOSPITAL = 2

class Building:
    def __init__(self, x, y, width, height, b_type):
        self.bounds = pygame.Rect(x, y, width, height)
        self.type = b_type
        self.color = (100, 100, 100)
        
        if self.type == BuildingType.HOSPITAL:
            self.color = (255, 255, 255) # White with Red Cross (handled in renderer)
        elif self.type == BuildingType.WORKPLACE:
            self.color = (100, 100, 200)
        elif self.type == BuildingType.RESIDENTIAL:
            self.color = (100, 200, 100)
