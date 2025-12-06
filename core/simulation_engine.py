import pygame
import random
from entities.person import State

class SimulationEngine:
    def __init__(self, cities):
        self.cities = cities
        self.infection_radius = 10.0
        self.infection_probability = 0.05 # Per frame contact probability
        
    def update(self):
        for city in self.cities:
            for district in city.districts:
                self._process_district_infections(district)
                
    def _process_district_infections(self, district):
        # Get all infectious people
        infectious_people = [p for p in district.people if p.state == State.INFECTIOUS]
        
        if not infectious_people:
            return
            
        # For each infectious person, query quadtree for neighbors
        for carrier in infectious_people:
            # Define query range around carrier
            range_rect = pygame.Rect(
                carrier.x - self.infection_radius,
                carrier.y - self.infection_radius,
                self.infection_radius * 2,
                self.infection_radius * 2
            )
            
            neighbors = district.quadtree.query(range_rect)
            
            for neighbor in neighbors:
                if neighbor.state == State.SUSCEPTIBLE:
                    # Distance check (circle vs square approximation)
                    dist_sq = (carrier.x - neighbor.x)**2 + (carrier.y - neighbor.y)**2
                    if dist_sq <= self.infection_radius**2:
                        if random.random() < self.infection_probability:
                            neighbor.expose()
