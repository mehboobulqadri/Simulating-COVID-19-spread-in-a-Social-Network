import numpy as np
import random
from entities.person import State
from core.pathfinding import SimplePathfinder

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
        self.person_to_index = {} # Fast lookup from person object to array index
        
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
                    self.person_to_index[p] = idx
                    idx += 1
                    
        # Constants
        self.infection_radius = 10.0
        self.infection_prob = 0.05
        self.recovery_rate = 0.02  # Death rate from illness
        # Factor to scale spatial spillover probability relative to base infection_prob
        self.spatial_spillover_factor = 0.3
        self.infection_radius_sq = self.infection_radius ** 2
        
        # Settings
        self.vaccination_threshold = 0.3
        self.vaccination_rate = 0.005
        self.hospital_cure_rate = 0.01
        self.vaccination_active = False
        
        # Pathfinding
        self.use_road_snapping = True  # Toggle for road-following behavior
        # Global speed multiplier (controlled via UI)
        self.speed_multiplier = 1.0
        
        # Spatial grid for infection optimization
        # Divide world into cells to avoid O(N) proximity checks
        self.grid_cell_size = max(20.0, self.infection_radius * 2.0)  # Cell size ~ 2x infection radius
        self.spatial_grid = {}  # Maps (grid_x, grid_y) -> list of person indices

    def set_speed_multiplier(self, multiplier: float):
        # Clamp to reasonable range to avoid instability and maintain smoothness
        self.speed_multiplier = float(max(0.5, min(multiplier, 6.0)))
    
    def _update_spatial_grid(self):
        """Rebuild spatial grid for this frame (O(N) but only ~constant cells per agent)"""
        self.spatial_grid.clear()
        for idx in range(self.num_people):
            x, y = self.pos[idx]
            gx = int(x / self.grid_cell_size)
            gy = int(y / self.grid_cell_size)
            grid_key = (gx, gy)
            if grid_key not in self.spatial_grid:
                self.spatial_grid[grid_key] = []
            self.spatial_grid[grid_key].append(idx)
    
    def _get_nearby_agents(self, pos_x, pos_y, radius_sq):
        """Get all agents within radius using spatial grid (O(1) avg case)"""
        nearby = []
        grid_radius = int(np.ceil(np.sqrt(radius_sq) / self.grid_cell_size)) + 1
        gx = int(pos_x / self.grid_cell_size)
        gy = int(pos_y / self.grid_cell_size)
        
        # Check surrounding cells
        for dx in range(-grid_radius, grid_radius + 1):
            for dy in range(-grid_radius, grid_radius + 1):
                cell_key = (gx + dx, gy + dy)
                if cell_key in self.spatial_grid:
                    nearby.extend(self.spatial_grid[cell_key])
        return nearby

    def update(self, time_engine, dt):
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
            # Use configurable recovery_rate for death probability
            outcomes = np.random.random(count_finished)
            deaths = outcomes < self.recovery_rate
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
            
            # Scale by dt*60 to approximate previous per-frame speeds at 60 FPS
            speeds = self.speed[has_target] * self.speed_multiplier * (dt * 60.0)
            
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
            
            # Apply road snapping for realistic movement
            if self.use_road_snapping:
                for idx in moving_indices:
                    # Calculate next position
                    next_pos = self.pos[idx] + norm_diff[np.where(moving_indices == idx)[0][0]] * (self.speed[idx] * self.speed_multiplier * (dt * 60.0))
                    
                    # Snap to road
                    snapped_x, snapped_y, is_on_road = SimplePathfinder.snap_to_road(
                        next_pos, self.cities, road_snap_distance=25
                    )
                    
                    if is_on_road:
                        self.pos[idx] = [snapped_x, snapped_y]
                    else:
                        self.pos[idx] = next_pos
            else:
                # Original direct movement
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
        """Graph-based infection with optional spatial spillover (grid-optimized)"""
        # Rebuild spatial grid for this frame
        self._update_spatial_grid()
        
        # Primary transmission: Through social network
        for inf_idx in infectious_indices:
            infected_person = self.person_map[inf_idx]
            
            # Check if person has social neighbors
            if not hasattr(infected_person, 'social_neighbors'):
                continue
                
            # Infect social contacts
            for neighbor in infected_person.social_neighbors:
                # Fast index lookup
                neighbor_idx = self.person_to_index.get(neighbor)
                if neighbor_idx is None:
                    continue
                    
                # Only infect if susceptible
                if self.state[neighbor_idx] == State.SUSCEPTIBLE.value:
                    # Social contact infection probability (higher than spatial)
                    if np.random.random() < self.infection_prob * 2.0:  # 2x more likely via social contact
                        self.state[neighbor_idx] = State.EXPOSED.value
                        self.timer[neighbor_idx] = np.random.randint(100, 300)
        
        # Secondary transmission: Spatial spillover using grid optimization
        spatial_spillover_prob = self.infection_prob * float(getattr(self, 'spatial_spillover_factor', 0.3))
        spatial_radius_sq = self.infection_radius_sq * 2.0  # Slightly expanded radius
        
        for inf_idx in infectious_indices:
            inf_pos = self.pos[inf_idx]
            
            # Use spatial grid to get nearby candidates (much faster than full N check)
            close_candidates = self._get_nearby_agents(inf_pos[0], inf_pos[1], spatial_radius_sq)
            
            for close_idx in close_candidates:
                if close_idx == inf_idx:
                    continue
                    
                # Only infect if susceptible
                if self.state[close_idx] != State.SUSCEPTIBLE.value:
                    continue
                
                # Check actual distance
                diff = self.pos[close_idx] - inf_pos
                d2 = np.dot(diff, diff)
                
                if d2 < spatial_radius_sq:
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
