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
        self.employed = np.zeros(self.num_people, dtype=np.bool_)
        
        # Vaccination tracking
        self.is_vaccinated = np.zeros(self.num_people, dtype=np.bool_)
        self.vaccination_efficacy = np.zeros(self.num_people, dtype=np.float32)
        self.days_since_vaccination = np.zeros(self.num_people, dtype=np.float32)
        
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
                    self.employed[idx] = getattr(p, 'is_employed', False)
                    self.is_vaccinated[idx] = p.is_vaccinated
                    self.vaccination_efficacy[idx] = p.vaccination_efficacy
                    self.days_since_vaccination[idx] = p.days_since_vaccination
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
        self.vaccination_rate = 0.005  # % of unvaccinated per tick (gradual spread)
        self.hospital_cure_rate = 0.01
        self.vaccination_active = False
        self.vaccination_target_rate = 0.0  # Target population % (0-1)
        
        # Pathfinding
        self.use_road_snapping = True  # Toggle for road-following behavior
        # Global speed multiplier (controlled via UI)
        self.speed_multiplier = 1.0
        
        # Spatial grid for infection optimization
        # Divide world into cells to avoid O(N) proximity checks
        self.grid_cell_size = max(20.0, self.infection_radius * 2.0)  # Cell size ~ 2x infection radius
        self.spatial_grid = {}  # Maps (grid_x, grid_y) -> list of person indices
        
        # Vaccination statistics
        self.vaccination_day = 0  # Track vaccination campaign day
        self.vaccination_scope_mask = np.ones(self.num_people, dtype=np.bool_)

    def set_speed_multiplier(self, multiplier: float):
        # Clamp to reasonable range to avoid instability and maintain smoothness
        self.speed_multiplier = float(max(0.5, min(multiplier, 6.0)))
    
    def vaccinate_agent(self, idx):
        """Vaccinate a single agent"""
        if not self.is_vaccinated[idx]:
            self.is_vaccinated[idx] = True
            self.vaccination_efficacy[idx] = 95.0
            self.days_since_vaccination[idx] = 0
            self.state[idx] = State.VACCINATED.value
            # Update the person object for consistency and rendering
            person = self.person_map[idx]
            person.vaccinate(self.vaccination_day)
            person.vaccination_efficacy = 95.0  # Explicitly set
            person.is_vaccinated = True  # Explicitly set for rendering
            person.state = State.VACCINATED
    
    def update_vaccination_efficacy(self, days=1):
        """Update vaccination efficacy decay for all vaccinated agents"""
        vaccinated_mask = self.is_vaccinated
        
        # Update days since vaccination
        self.days_since_vaccination[vaccinated_mask] += days
        
        # Recalculate efficacy using piecewise linear decay model
        days_since = self.days_since_vaccination[vaccinated_mask]
        
        # Initial: 95%
        efficacy = np.full_like(days_since, 95.0, dtype=np.float32)
        
        # Days 0-60: 95% -> 90%
        mask1 = (days_since >= 0) & (days_since < 60)
        efficacy[mask1] = 95.0 - (5.0 * days_since[mask1] / 60.0)
        
        # Days 60-120: 90% -> 80%
        mask2 = (days_since >= 60) & (days_since < 120)
        efficacy[mask2] = 90.0 - (10.0 * (days_since[mask2] - 60) / 60.0)
        
        # Days 120-180: 80% -> 60%
        mask3 = (days_since >= 120) & (days_since < 180)
        efficacy[mask3] = 80.0 - (20.0 * (days_since[mask3] - 120) / 60.0)
        
        # Days 180+: floor at 60%
        mask4 = days_since >= 180
        efficacy[mask4] = 60.0
        
        self.vaccination_efficacy[vaccinated_mask] = efficacy
    
    def get_vaccination_rate(self):
        """Get percentage of vaccinated population (0.0 to 1.0)"""
        if self.num_people == 0:
            return 0.0
        vaccinated_count = int(np.sum(self.is_vaccinated))
        rate = float(vaccinated_count) / float(self.num_people)
        return max(0.0, min(1.0, rate))  # Clamp to [0, 1]

    def _build_scope_mask(self, people):
        """Build a boolean mask for the provided people list"""
        mask = np.zeros(self.num_people, dtype=np.bool_)
        for p in people:
            idx = self.person_to_index.get(p)
            if idx is not None:
                mask[idx] = True
        return mask

    def _get_vaccination_rate_within(self, mask):
        """Vaccination rate limited to a mask (0.0 to 1.0)"""
        total = int(np.count_nonzero(mask))
        if total == 0:
            return 0.0
        vaccinated = int(np.count_nonzero(self.is_vaccinated & mask))
        return max(0.0, min(1.0, vaccinated / float(total)))
    
    def vaccinate_area(self, area_type='all', target_rate=1.0):
        """Initiate gradual vaccination in an area (spreads gradually each tick)"""
        if self.num_people == 0:
            return 0

        # Default to whole population unless narrowed
        scope_mask = np.ones(self.num_people, dtype=np.bool_)

        if area_type == 'all':
            pass  # keep scope_mask as all True
        elif area_type == 'city' and self.cities:
            first_city = self.cities[0]
            people = [p for d in first_city.districts for p in d.people]
            scope_mask = self._build_scope_mask(people)
        elif area_type == 'district' and self.cities:
            all_districts = [d for city in self.cities for d in city.districts]
            if all_districts:
                chosen = random.choice(all_districts)
                people = list(chosen.people)
                scope_mask = self._build_scope_mask(people)
                print(f"✓ Starting district vaccination campaign - {chosen.name} (target: {target_rate*100:.0f}%)")

        if not np.any(scope_mask):
            print("⚠ No eligible agents found for vaccination scope; skipping campaign")
            return 0

        self.vaccination_scope_mask = scope_mask
        self.vaccination_target_rate = target_rate
        self.vaccination_active = True

        if area_type == 'all':
            print(f"✓ Starting nationwide vaccination campaign (target: {target_rate*100:.0f}%)")
        elif area_type == 'city':
            print(f"✓ Starting city-wide vaccination campaign (target: {target_rate*100:.0f}%)")
        return 0
    
    def run_vaccination_campaign(self, target_rate=0.10):
        """Gradually vaccinate agents up to target coverage (for automatic campaigns)"""
        self.vaccination_target_rate = target_rate
        scope_mask = self.vaccination_scope_mask if self.vaccination_scope_mask is not None else np.ones(self.num_people, dtype=np.bool_)
        current_rate = self._get_vaccination_rate_within(scope_mask)

        if current_rate >= target_rate:
            self.vaccination_active = False
            return

        eligible_mask = scope_mask & ~self.is_vaccinated & (self.state != State.DECEASED.value)
        eligible_indices = np.where(eligible_mask)[0]
        if len(eligible_indices) == 0:
            self.vaccination_active = False
            return

        to_vaccinate = max(1, int(len(eligible_indices) * self.vaccination_rate))
        chosen = np.random.choice(eligible_indices, size=min(to_vaccinate, len(eligible_indices)), replace=False)
        for idx in chosen:
            self.vaccinate_agent(idx)
    
    
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
    
    def _sync_vaccination_to_persons(self):
        """Sync vaccination state from numpy arrays to person objects for rendering"""
        for idx in range(self.num_people):
            person = self.person_map[idx]
            if self.is_vaccinated[idx]:
                if not person.is_vaccinated:
                    person.is_vaccinated = True
                person.vaccination_efficacy = max(60.0, float(self.vaccination_efficacy[idx]))
                person.days_since_vaccination = int(self.days_since_vaccination[idx])
                person.state = State.VACCINATED
                # Keep array state aligned if external code toggled person
                self.state[idx] = State.VACCINATED.value
    
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
        # Sync vaccination state to person objects for rendering
        self._sync_vaccination_to_persons()
        
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
            # Employed agents go to work
            active = (self.state != State.DECEASED.value) & self.employed
            self.target[active] = self.work[active]
            self.flags[active] |= 1 # Has Target
            
        # Evening Return (17-18)
        if 17 <= hour < 18:
            # Employed agents return home from work
            active = (self.state != State.DECEASED.value) & self.employed
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
        """Graph-based infection with optional spatial spillover (grid-optimized) + vaccination"""
        # Rebuild spatial grid for this frame
        self._update_spatial_grid()
        
        # Run vaccination campaign if active (gradual spread like infection)
        if self.vaccination_active:
            self.run_vaccination_campaign(target_rate=self.vaccination_target_rate)
        
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
                    transmission_prob = self.infection_prob * 2.0  # 2x more likely via social contact
                    
                    # Apply vaccination protection
                    if self.is_vaccinated[neighbor_idx]:
                        transmission_prob *= (1.0 - self.vaccination_efficacy[neighbor_idx] / 100.0)
                    
                    if np.random.random() < transmission_prob:
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
                    transmission_prob = spatial_spillover_prob
                    
                    # Apply vaccination protection
                    if self.is_vaccinated[close_idx]:
                        transmission_prob *= (1.0 - self.vaccination_efficacy[close_idx] / 100.0)
                    
                    if np.random.random() < transmission_prob:
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
