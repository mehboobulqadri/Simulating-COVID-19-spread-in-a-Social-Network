from enum import Enum
import random
import math

class State(Enum):
    SUSCEPTIBLE = 0
    EXPOSED = 1
    INFECTIOUS = 2
    RECOVERED = 3
    DECEASED = 4
    VACCINATED = 5

class Person:
    def __init__(self, uid, x, y, district):
        self.x = x
        self.y = y
        self.uid = uid
        self.district = district
        self.state = State.SUSCEPTIBLE
        self.infection_timer = 0
        self.home_location = (x, y)
        self.work_location = None # Will be assigned by WorldGenerator
        self.target_location = None
        self.speed = 2.0
        self.is_employed = False
        
        # Risk factors
        self.age = random.randint(0, 90)
        self.immunity = 0.0
        self.is_hospitalized = False
        self.hospital_location = None
        
        # Vaccination tracking
        self.is_vaccinated = False
        self.vaccination_date = None  # Day when first dose given
        self.booster_count = 0  # Number of boosters received
        self.vaccination_efficacy = 0.0  # Current efficacy 0-100%
        self.days_since_vaccination = 0  # Tracks efficacy decay
        
        # Asymptomatic carrier status
        self.is_asymptomatic = False

        # Variant tag for infection lineage/visuals
        self.variant = "base"
        
    def vaccinate(self, current_day=0):
        """Administer vaccination dose to person"""
        if not self.is_vaccinated:
            self.is_vaccinated = True
            self.vaccination_date = current_day
            self.vaccination_efficacy = 95.0  # Initial efficacy 95%
            self.days_since_vaccination = 0
            self.booster_count = 0
        else:
            # Booster dose
            self.booster_count += 1
            self.vaccination_date = current_day
            self.vaccination_efficacy = 95.0  # Reset to 95% after booster
            self.days_since_vaccination = 0
    
    def update_vaccination_efficacy(self, days_elapsed=1):
        """Update vaccination efficacy based on time decay"""
        if self.is_vaccinated:
            self.days_since_vaccination += days_elapsed
            # Efficacy decay: 95% -> 90% after 60 days -> 80% after 120 days -> 60% after 180 days
            # Using piecewise linear model
            if self.days_since_vaccination < 60:
                # 95% -> 90% in first 60 days (0.083%/day)
                self.vaccination_efficacy = 95.0 - (5.0 * self.days_since_vaccination / 60.0)
            elif self.days_since_vaccination < 120:
                # 90% -> 80% from 60-120 days (0.167%/day)
                self.vaccination_efficacy = 90.0 - (10.0 * (self.days_since_vaccination - 60) / 60.0)
            elif self.days_since_vaccination < 180:
                # 80% -> 60% from 120-180 days (0.333%/day)
                self.vaccination_efficacy = 80.0 - (20.0 * (self.days_since_vaccination - 120) / 60.0)
            else:
                # Floor at 60% after 180 days
                self.vaccination_efficacy = 60.0
            
            # Clamp between 60-95%
            self.vaccination_efficacy = max(60.0, min(95.0, self.vaccination_efficacy))
    
    def get_infection_susceptibility(self):
        """Get susceptibility to infection (0.0 = fully protected, 1.0 = fully susceptible)"""
        if self.is_vaccinated:
            return 1.0 - (self.vaccination_efficacy / 100.0)
        return 1.0