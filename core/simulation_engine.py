import pygame
import random
from entities.person import State

class SimulationEngine:
    def __init__(self, cities):
        self.cities = cities
        self.infection_radius = 10.0
        self.infection_probability = 0.05 # Per frame contact probability
        
        # God Mode / Settings
        self.vaccination_threshold = 0.3 # 30% infected triggers vaccination
        self.vaccination_active = False
        self.vaccination_rate = 0.005 # Chance per frame to be vaccinated if susceptible
        self.hospital_cure_rate = 0.01 # Chance per frame to be cured in hospital
        
    def update(self):
        total_people = 0
        total_infected = 0
        
        for city in self.cities:
            for district in city.districts:
                total_people += len(district.people)
                total_infected += len([p for p in district.people if p.state == State.INFECTIOUS])
                self._process_district_infections(district)
                
        # Check Threshold
        if total_people > 0:
            infection_rate = total_infected / total_people
            if infection_rate >= self.vaccination_threshold:
                self.vaccination_active = True
                
        # Apply Vaccination / Cure
        if self.vaccination_active:
            self._apply_vaccination_logic()

    def _apply_vaccination_logic(self):
        for city in self.cities:
            for district in city.districts:
                for person in district.people:
                    # Global Vaccination Campaign (Susceptible -> Vaccinated)
                    if person.state == State.SUSCEPTIBLE:
                        if random.random() < self.vaccination_rate:
                            person.state = State.VACCINATED
                            
                    # Hospital Cure (Infected -> Vaccinated/Recovered)
                    if person.state == State.INFECTIOUS and person.is_hospitalized:
                        if random.random() < self.hospital_cure_rate:
                            person.state = State.VACCINATED
                            person.is_hospitalized = False # Discharge
                            person.target_location = person.home_location

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
