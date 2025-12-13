import numpy as np
import random
from entities.person import State

class NumpySimulationEngine:
    def __init__(self, cities):
        self.cities = cities
        self.num_people = 0
        
        # Count total people
        for city in cities:
            for district in city.districts:
                self.num_people += len(district.people)
                
        print(f"Initializing Numpy Engine for {self.num_people} agents...")
        
        # Allocate Arrays
        self.pos = np.zeros((self.num_people, 2), dtype=np.float32)
        self.target = np.zeros((self.num_people, 2), dtype=np.float32)
        self.home = np.zeros((self.num_people, 2), dtype=np.float32)
        self.work = np.zeros((self.num_people, 2), dtype=np.float32)
        
        self.state = np.zeros(self.num_people, dtype=np.int8)
        self.timer = np.zeros(self.num_people, dtype=np.int32)
        self.speed = np.zeros(self.num_people, dtype=np.float32)
        
        # Flags: 0=None, 1=HasTarget, 2=Hospitalized
        self.flags = np.zeros(self.num_people, dtype=np.int8)
        
        # Initialize Data
        idx = 0
        self.person_map = [] # Map index back to object (for compatibility/debugging)
        
        for city in cities:
            for district in city.districts:
                for p in district.people:
                    self.pos[idx] = [p.x, p.y]
                    self.home[idx] = p.home_location
                    if p.work_location:
                        self.work[idx] = p.work_location
                    else:
                        self.work[idx] = p.home_location # No work, stay home
                        
                    self.state[idx] = p.state.value
                    self.speed[idx] = p.speed
                    self.person_map.append(p)
                    idx += 1
                    
        # Constants
        self.infection_radius = 10.0
        self.infection_prob = 0.05
        self.infection_radius_sq = self.infection_radius ** 2
        
        # God Mode / Settings
        self.vaccination_threshold = 0.3
        self.vaccination_rate = 0.005
        self.hospital_cure_rate = 0.01
        self.vaccination_active = False

    def update(self, time_engine):
        # 1. Update Logic (State Transitions)
        # Vectorized state timers
        
        # Exposed -> Infectious
        exposed_mask = (self.state == State.EXPOSED.value)
        self.timer[exposed_mask] -= 1
        # Find those who finished incubation
        new_infectious = exposed_mask & (self.timer <= 0)
        self.state[new_infectious] = State.INFECTIOUS.value
        self.timer[new_infectious] = np.random.randint(500, 1000, size=np.count_nonzero(new_infectious))
        
        # Infectious -> Recovered/Deceased
        infectious_mask = (self.state == State.INFECTIOUS.value)
        self.timer[infectious_mask] -= 1
        finished_infection = infectious_mask & (self.timer <= 0)
        
        count_finished = np.count_nonzero(finished_infection)
        if count_finished > 0:
            # 2% death rate
            outcomes = np.random.random(count_finished)
            deaths = outcomes < 0.02
            recoveries = ~deaths
            
            # Map back to full array indices
            finished_indices = np.where(finished_infection)[0]
            
            self.state[finished_indices[deaths]] = State.DECEASED.value
            self.state[finished_indices[recoveries]] = State.RECOVERED.value

        # 2. Movement Logic
        hour = time_engine.hour
        
        # Set Targets based on time
        # Morning Commute (8-9)
        if 8 <= hour < 9:
            # Everyone goes to work (if not hospitalized/dead)
            active = (self.state != State.DECEASED.value)
            self.target[active] = self.work[active]
            self.flags[active] |= 1 # Has Target
            
        # Evening Return (17-18)
        elif 17 <= hour < 18:
            active = (self.state != State.DECEASED.value)
            self.target[active] = self.home[active]
            self.flags[active] |= 1
            
        # Move towards target
        has_target = (self.flags & 1) == 1
        if np.any(has_target):
            # Calculate vectors
            diff = self.target[has_target] - self.pos[has_target]
            dist_sq = np.sum(diff**2, axis=1)
            dist = np.sqrt(dist_sq)
            
            # Avoid division by zero
            valid_dist = dist > 0.1
            
            # Move
            # If dist < speed, snap to target
            # If dist >= speed, move by speed
            
            speeds = self.speed[has_target]
            
            # Indices within the 'has_target' subset
            reached = dist <= speeds
            not_reached = ~reached
            
            # Update positions for those who haven't reached
            # We need to be careful with indexing here.
            # It's easier to do it in full array if memory allows, or use indices.
            
            indices = np.where(has_target)[0]
            
            # Snap reached
            reached_indices = indices[reached]
            self.pos[reached_indices] = self.target[reached_indices]
            self.flags[reached_indices] &= ~1 # Clear target flag
            
            # Move not reached
            moving_indices = indices[not_reached]
            # Normalize diff
            norm_diff = diff[not_reached] / dist[not_reached, np.newaxis]
            self.pos[moving_indices] += norm_diff * speeds[not_reached, np.newaxis]

        # 3. Infection Logic (Spatial Hash)
        # Only run if there are infectious people
        infectious_indices = np.where(self.state == State.INFECTIOUS.value)[0]
        if len(infectious_indices) > 0:
            self._process_infections(infectious_indices)
            
        # Sync back to objects for Renderer (Temporary, until Renderer uses Arrays)
        # This is slow, but necessary for the current Renderer
        for i, p in enumerate(self.person_map):
            p.x, p.y = self.pos[i]
            p.state = State(self.state[i])

    def _process_infections(self, infectious_indices):
        """Graph-based infection with optional spatial spillover"""
        # Primary transmission: Through social network
        for inf_idx in infectious_indices:
            infected_person = self.person_map[inf_idx]
            
            # Check if person has social neighbors
            if not hasattr(infected_person, 'social_neighbors'):
                continue
                
            # Infect social contacts
            for neighbor in infected_person.social_neighbors:
                # Find neighbor's index in person_map
                try:
                    neighbor_idx = self.person_map.index(neighbor)
                except ValueError:
                    continue
                    
                # Only infect if susceptible
                if self.state[neighbor_idx] == State.SUSCEPTIBLE.value:
                    # Social contact infection probability (higher than spatial)
                    if np.random.random() < self.infection_prob * 2.0:  # 2x more likely via social contact
                        self.state[neighbor_idx] = State.EXPOSED.value
                        self.timer[neighbor_idx] = np.random.randint(100, 300)
        
        # Secondary transmission: Spatial spillover (incidental contacts)
        # Keep a reduced version for realism (e.g., touching same surface)
        spatial_spillover_prob = self.infection_prob * 0.3  # 30% of base rate
        spatial_radius_sq = self.infection_radius_sq  # Use full spatial radius again
        
        for inf_idx in infectious_indices:
            inf_pos = self.pos[inf_idx]
            
            # Check nearby people (simple brute force for now, can optimize later)
            diff = self.pos - inf_pos
            d2 = np.sum(diff**2, axis=1)
            
            # Find close susceptible people
            close_mask = (d2 < spatial_radius_sq) & (self.state == State.SUSCEPTIBLE.value)
            close_indices = np.where(close_mask)[0]
            
            for close_idx in close_indices:
                if close_idx != inf_idx:  # Don't infect self
                    if np.random.random() < spatial_spillover_prob:
                        self.state[close_idx] = State.EXPOSED.value
                        self.timer[close_idx] = np.random.randint(100, 300)

    def infect_random_person(self):
        # Find a susceptible person
        susceptible = np.where(self.state == State.SUSCEPTIBLE.value)[0]
        if len(susceptible) > 0:
            target = np.random.choice(susceptible)
            self.state[target] = State.INFECTIOUS.value
            self.timer[target] = 1000
            
            # Return position for visual effect
            return self.pos[target]
        return None
