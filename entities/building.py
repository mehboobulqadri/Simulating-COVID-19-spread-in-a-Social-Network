import pygame
from enum import Enum

class BuildingType(Enum):
    RESIDENTIAL = 0
    WORKPLACE = 1
    HOSPITAL = 2
    COMMERCIAL = 3
    SCHOOL = 4
    PARK = 5

class Building:
    def __init__(self, x, y, width, height, b_type):
        self.bounds = pygame.Rect(x, y, width, height)
        self.type = b_type
        self.color = (100, 100, 100)
        self.is_quarantined = False  # Track if building is quarantined

        # Distinct color palette by building type
        if self.type == BuildingType.HOSPITAL:
            self.color = (255, 255, 255)  # White
        elif self.type == BuildingType.WORKPLACE:
            self.color = (100, 100, 200)  # Blue-ish
        elif self.type == BuildingType.RESIDENTIAL:
            self.color = (100, 200, 100)  # Green
        elif self.type == BuildingType.COMMERCIAL:
            self.color = (240, 180, 60)   # Amber
        elif self.type == BuildingType.SCHOOL:
            self.color = (220, 120, 120) # Soft red
        elif self.type == BuildingType.PARK:
            self.color = (50, 160, 80)   # Deep green
