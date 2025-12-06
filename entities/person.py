from enum import Enum
import random
import math
from core.graph_hierarchy import Entity

class State(Enum):
    SUSCEPTIBLE = 0
    EXPOSED = 1
    INFECTIOUS = 2
    RECOVERED = 3
    DECEASED = 4
    VACCINATED = 5

class Person(Entity):
    def __init__(self, uid, x, y, district):
        super().__init__(x, y)
        self.uid = uid
        self.district = district
        self.state = State.SUSCEPTIBLE
        self.infection_timer = 0
        self.home_location = (x, y)
        self.work_location = None # Will be assigned by WorldGenerator
        self.target_location = None
        self.speed = 2.0
        
        # Risk factors
        self.age = random.randint(0, 90)
        self.immunity = 0.0
        self.is_hospitalized = False
        self.hospital_location = None
        
    def update(self, time_engine=None):
        if self.state == State.DECEASED:
            return

        # Hospital Logic
        if self.state == State.INFECTIOUS and not self.is_hospitalized:
            # Find hospital
            if self.district and self.district.parent and hasattr(self.district.parent, 'hospitals'):
                hospitals = self.district.parent.hospitals
                if hospitals:
                    # Pick random hospital in city (or nearest)
                    hospital = random.choice(hospitals)
                    self.hospital_location = (hospital.bounds.centerx, hospital.bounds.centery)
                    self.is_hospitalized = True
                    self.target_location = self.hospital_location
        
        if self.state == State.RECOVERED and self.is_hospitalized:
            self.is_hospitalized = False
            self.hospital_location = None
            self.target_location = self.home_location # Go home

        # Movement Logic
        if time_engine:
            hour = time_engine.hour
            
            if self.is_hospitalized:
                # Stay at hospital
                if self.hospital_location:
                    self.target_location = self.hospital_location
            else:
                # Morning Commute (8 AM - 9 AM)
                if 8 <= hour < 9 and self.work_location:
                    self.target_location = self.work_location
                # Evening Return (5 PM - 6 PM)
                elif 17 <= hour < 18:
                    self.target_location = self.home_location
                # Random movement if at destination
                elif self.target_location is None:
                    # Wander around current position
                    self.x += random.uniform(-0.5, 0.5)
                    self.y += random.uniform(-0.5, 0.5)
                    return

        # Move towards target
        if self.target_location:
            dx = self.target_location[0] - self.x
            dy = self.target_location[1] - self.y
            dist = math.sqrt(dx*dx + dy*dy)
            
            if dist < self.speed:
                self.x = self.target_location[0]
                self.y = self.target_location[1]
                self.target_location = None # Arrived
            else:
                self.x += (dx / dist) * self.speed
                self.y += (dy / dist) * self.speed

    def expose(self):
        if self.state == State.SUSCEPTIBLE:
            self.state = State.EXPOSED
            self.infection_timer = random.randint(100, 300) # Frames until infectious

    def tick_infection(self):
        if self.state == State.EXPOSED:
            self.infection_timer -= 1
            if self.infection_timer <= 0:
                self.state = State.INFECTIOUS
                self.infection_timer = random.randint(500, 1000) # Duration of infection
        elif self.state == State.INFECTIOUS:
            self.infection_timer -= 1
            if self.infection_timer <= 0:
                if random.random() < 0.02: # 2% death rate placeholder
                    self.state = State.DECEASED
                else:
                    self.state = State.RECOVERED
