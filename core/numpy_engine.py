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
        self.school = np.zeros((self.num_people, 2), dtype=np.float32)
        self.lunch = np.zeros((self.num_people, 2), dtype=np.float32)
        self.leisure = np.zeros((self.num_people, 2), dtype=np.float32)
        
        self.state = np.zeros(self.num_people, dtype=np.int8)
        self.timer = np.zeros(self.num_people, dtype=np.int32)
        self.speed = np.zeros(self.num_people, dtype=np.float32)
        self.employed = np.zeros(self.num_people, dtype=np.bool_)
        self.student = np.zeros(self.num_people, dtype=np.bool_)
        
        # Age demographics
        self.age = np.zeros(self.num_people, dtype=np.int8)  # Age in years
        
        # Vaccination tracking
        self.is_vaccinated = np.zeros(self.num_people, dtype=np.bool_)
        self.vaccination_efficacy = np.zeros(self.num_people, dtype=np.float32)
        self.days_since_vaccination = np.zeros(self.num_people, dtype=np.float32)
        
        # Asymptomatic carriers (appear healthy but can spread)
        self.is_asymptomatic = np.zeros(self.num_people, dtype=np.bool_)

        # Variant tracking (0 = base). Values index into self.variant_profiles
        self.variant_id = np.zeros(self.num_people, dtype=np.int8)
        
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
                    if getattr(p, 'school_location', None):
                        self.school[idx] = p.school_location
                    else:
                        self.school[idx] = p.home_location
                    if getattr(p, 'lunch_location', None):
                        self.lunch[idx] = p.lunch_location
                    else:
                        self.lunch[idx] = p.work_location if p.work_location else p.home_location
                    if getattr(p, 'leisure_location', None):
                        self.leisure[idx] = p.leisure_location
                    else:
                        self.leisure[idx] = p.home_location
                        
                    self.state[idx] = p.state.value
                    self.speed[idx] = p.speed
                    self.employed[idx] = getattr(p, 'is_employed', False)
                    self.student[idx] = getattr(p, 'is_student', False)
                    self.is_vaccinated[idx] = p.is_vaccinated
                    self.vaccination_efficacy[idx] = p.vaccination_efficacy
                    self.days_since_vaccination[idx] = p.days_since_vaccination
                    self.person_map.append(p)
                    self.person_to_index[p] = idx
                    idx += 1
        
        # Initialize quarantine locations to home (will stay home when quarantined)
        self.quarantine_location = self.home.copy()
        
        # Assign realistic age distribution
        # ~20% children (0-17), ~65% adults (18-64), ~15% elderly (65+)
        age_groups = np.random.choice(['child', 'adult', 'elderly'], 
                                      size=self.num_people, 
                                      p=[0.20, 0.65, 0.15])
        
        for i in range(self.num_people):
            if age_groups[i] == 'child':
                self.age[i] = np.random.randint(0, 18)
            elif age_groups[i] == 'adult':
                self.age[i] = np.random.randint(18, 65)
            else:  # elderly
                self.age[i] = np.random.randint(65, 90)
        
        # Print age demographics
        children = np.sum(self.age < 18)
        adults = np.sum((self.age >= 18) & (self.age < 65))
        elderly = np.sum(self.age >= 65)
        print(f"\nAge Demographics:")
        print(f"  Children (0-17): {children} ({children/self.num_people*100:.1f}%) - Mortality: 0.5%")
        print(f"  Adults (18-64): {adults} ({adults/self.num_people*100:.1f}%) - Mortality: 2.0%")
        print(f"  Elderly (65+): {elderly} ({elderly/self.num_people*100:.1f}%) - Mortality: 8.0%")
                    
        # Constants
        self.infection_radius = 10.0
        self.infection_prob = 0.05
        self.recovery_rate = 0.02  # Base death rate (will be modified by age)
        # Factor to scale spatial spillover probability relative to base infection_prob
        self.spatial_spillover_factor = 0.3
        self.infection_radius_sq = self.infection_radius ** 2
        self.asymptomatic_rate = 0.40  # Default asymptomatic rate (used by base variant)

        # Variant profiles (kept compact for now)
        self.variant_profiles = [
            {
                "name": "base",
                "transmission_mult": 1.0,
                "mortality_mult": 1.0,
                "incubation_range": (100, 300),
                "infectious_range": (500, 1000),
                "asymptomatic_rate": 0.40,
                "color": (255, 140, 80),
            },
            {
                "name": "high-transmission",
                "transmission_mult": 1.6,
                "mortality_mult": 1.1,
                "incubation_range": (80, 220),
                "infectious_range": (550, 1100),
                "asymptomatic_rate": 0.35,
                "color": (255, 90, 190),
            },
            {
                "name": "high-mortality",
                "transmission_mult": 1.0,
                "mortality_mult": 1.7,
                "incubation_range": (100, 320),
                "infectious_range": (480, 900),
                "asymptomatic_rate": 0.30,
                "color": (200, 70, 70),
            },
        ]
        self.variant_names = [p["name"] for p in self.variant_profiles]
        self.variant_transmission = np.array([p["transmission_mult"] for p in self.variant_profiles], dtype=np.float32)
        self.variant_mortality = np.array([p["mortality_mult"] for p in self.variant_profiles], dtype=np.float32)
        self.variant_incub_min = np.array([p["incubation_range"][0] for p in self.variant_profiles], dtype=np.int32)
        self.variant_incub_max = np.array([p["incubation_range"][1] for p in self.variant_profiles], dtype=np.int32)
        self.variant_infectious_min = np.array([p["infectious_range"][0] for p in self.variant_profiles], dtype=np.int32)
        self.variant_infectious_max = np.array([p["infectious_range"][1] for p in self.variant_profiles], dtype=np.int32)
        self.variant_asym_rate = np.array([p["asymptomatic_rate"] for p in self.variant_profiles], dtype=np.float32)
        self.active_variant = 0  # index into variant_profiles
        
        # Settings
        self.vaccination_threshold = 0.3
        self.vaccination_rate = 0.005  # % of unvaccinated per tick (gradual spread)
        self.hospital_cure_rate = 0.01
        self.vaccination_active = False
        self.vaccination_target_rate = 0.0  # Target population % (0-1)
        
        # Pathfinding
        self.use_road_snapping = False  # Disabled for performance (enables 50+ FPS vs 9 FPS)
        # Global speed multiplier (controlled via UI)
        self.speed_multiplier = 1.0
        
        # Lockdown mode
        self.lockdown_active = False
        self.lockdown_compliance = 0.80  # 80% of people stay home
        self.lockdown_mask = np.zeros(self.num_people, dtype=np.bool_)  # Who is in lockdown
        
        # Quarantine zones (isolate symptomatic infected)
        self.quarantine_active = False
        self.in_quarantine = np.zeros(self.num_people, dtype=np.bool_)  # Who is quarantined
        self.quarantine_location = np.zeros((self.num_people, 2), dtype=np.float32)  # Where they quarantine
        
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
    
    def toggle_lockdown(self):
        """Toggle lockdown mode on/off"""
        self.lockdown_active = not self.lockdown_active
        
        if self.lockdown_active:
            # Randomly select agents who will comply with lockdown
            compliance_random = np.random.random(self.num_people)
            self.lockdown_mask = compliance_random < self.lockdown_compliance
            compliant_count = np.sum(self.lockdown_mask)
            print(f"🔒 LOCKDOWN ACTIVE: {compliant_count}/{self.num_people} agents staying home ({self.lockdown_compliance*100:.0f}% compliance)")
        else:
            self.lockdown_mask = np.zeros(self.num_people, dtype=np.bool_)
            print(f"🔓 LOCKDOWN LIFTED: Movement restored to normal")
        
        return self.lockdown_active
    
    def toggle_quarantine(self):
        """Toggle quarantine mode on/off"""
        self.quarantine_active = not self.quarantine_active
        
        if self.quarantine_active:
            print(f"🏥 QUARANTINE ACTIVATED")
            print(f"   Symptomatic infectious agents will be isolated")
        else:
            # Release everyone from quarantine
            self.in_quarantine[:] = False
            print(f"🏥 QUARANTINE DEACTIVATED")
            print(f"   All quarantined agents released")
        
        return self.quarantine_active

    def set_active_variant(self, name_or_index):
        """Set the currently active variant used for new infections."""
        if isinstance(name_or_index, str):
            try:
                idx = self.variant_names.index(name_or_index)
            except ValueError:
                print(f"⚠ Unknown variant '{name_or_index}'. Available: {', '.join(self.variant_names)}")
                return self.active_variant
        else:
            idx = int(name_or_index)
        idx = int(np.clip(idx, 0, len(self.variant_profiles) - 1))
        self.active_variant = idx
        print(f"🧬 Active variant set to: {self.variant_names[self.active_variant]}")
        return self.active_variant

    def cycle_variant(self):
        """Cycle through known variants (for quick keyboard toggle)."""
        self.active_variant = (self.active_variant + 1) % len(self.variant_profiles)
        print(f"🧬 Active variant set to: {self.variant_names[self.active_variant]}")
        return self.active_variant

    def _apply_exposure(self, target_idx: int, source_variant: int):
        """Assign exposed state, incubation timer, and variant for a target."""
        self.state[target_idx] = State.EXPOSED.value
        self.variant_id[target_idx] = source_variant
        low = int(self.variant_incub_min[source_variant])
        high = int(self.variant_incub_max[source_variant])
        self.timer[target_idx] = np.random.randint(low, high)
        # Reset asymptomatic flag until infectious stage sets it
        self.is_asymptomatic[target_idx] = False
    
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
        """Rebuild spatial grid for this frame (fully vectorized)"""
        self.spatial_grid.clear()
        
        # Vectorized grid calculation
        gx = (self.pos[:, 0] / self.grid_cell_size).astype(int)
        gy = (self.pos[:, 1] / self.grid_cell_size).astype(int)
        
        # Use numpy argsort to group by grid cells (much faster than Python loop)
        # Create composite key: (gx * MAX_Y + gy) for unique cell identification
        max_gy = gy.max() + 1 if len(gy) > 0 else 1
        cell_ids = gx * max_gy + gy
        
        # Sort indices by cell_id
        sorted_indices = np.argsort(cell_ids)
        sorted_cells = cell_ids[sorted_indices]
        
        # Find boundaries where cell changes
        unique_cells, cell_starts = np.unique(sorted_cells, return_index=True)
        cell_ends = np.append(cell_starts[1:], len(sorted_cells))
        
        # Populate grid dictionary
        for i, cell_id in enumerate(unique_cells):
            gx_val = cell_id // max_gy
            gy_val = cell_id % max_gy
            grid_key = (int(gx_val), int(gy_val))
            self.spatial_grid[grid_key] = sorted_indices[cell_starts[i]:cell_ends[i]].tolist()
    
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

        # Assign infectious duration and asymptomatic probability per variant
        if np.any(new_infectious):
            new_indices = np.where(new_infectious)[0]
            for vid in range(len(self.variant_profiles)):
                vmask = new_infectious & (self.variant_id == vid)
                if not np.any(vmask):
                    continue
                count = int(np.count_nonzero(vmask))
                low = int(self.variant_infectious_min[vid])
                high = int(self.variant_infectious_max[vid])
                self.timer[vmask] = np.random.randint(low, high, size=count)
                # Asymptomatic assignment per variant
                asym_rate = float(self.variant_asym_rate[vid])
                asym_roll = np.random.random(count)
                asym_flags = asym_roll < asym_rate
                v_indices = np.where(vmask)[0]
                self.is_asymptomatic[v_indices] = asym_flags
                if self.quarantine_active:
                    symptomatic_mask = ~asym_flags
                    symptomatic_indices = v_indices[symptomatic_mask]
                    self.in_quarantine[symptomatic_indices] = True
        
        # Infectious -> Recovered/Deceased
        infectious_mask = (self.state == State.INFECTIOUS.value)
        self.timer[infectious_mask] -= 1
        finished_infection = infectious_mask & (self.timer <= 0)
        
        count_finished = np.count_nonzero(finished_infection)
        if count_finished > 0:
            # Age-based mortality rates
            finished_indices = np.where(finished_infection)[0]
            ages = self.age[finished_indices]
            
            # Calculate death probability based on age
            # Children (0-17): 0.5%, Adults (18-64): 2%, Elderly (65+): 8%
            death_rates = np.where(ages < 18, 0.005,
                          np.where(ages < 65, 0.02, 0.08))
            # Scale by variant-specific mortality factor
            v_ids = self.variant_id[finished_indices]
            death_rates = death_rates * self.variant_mortality[v_ids]
            
            # Roll for death vs recovery
            outcomes = np.random.random(count_finished)
            deaths = outcomes < death_rates
            recoveries = ~deaths
            
            self.state[finished_indices[deaths]] = State.DECEASED.value
            self.state[finished_indices[recoveries]] = State.RECOVERED.value
            
            # Clear asymptomatic flag when infection ends
            self.is_asymptomatic[finished_indices] = False
            
            # Release from quarantine when infection ends
            self.in_quarantine[finished_indices] = False
            
            # Release from quarantine when infection ends
            self.in_quarantine[finished_indices] = False

        # 2. Movement Logic
        hour = time_engine.hour
        
        # Quarantine mode: quarantined agents stay in quarantine location
        if self.quarantine_active:
            quarantined = self.in_quarantine & (self.state != State.DECEASED.value)
            self.target[quarantined] = self.quarantine_location[quarantined]
            self.flags[quarantined] |= 1
        
        # In lockdown mode, compliant agents stay home and don't follow schedules
        if self.lockdown_active:
            # Send lockdown-compliant agents home
            lockdown_compliant = self.lockdown_mask & (self.state != State.DECEASED.value)
            self.target[lockdown_compliant] = self.home[lockdown_compliant]
            self.flags[lockdown_compliant] |= 1
        
        # Non-lockdown agents (or non-compliant during lockdown) follow normal schedules
        # Apply movement only to agents NOT in lockdown compliance
        active_movement_mask = ~self.lockdown_mask if self.lockdown_active else np.ones(self.num_people, dtype=np.bool_)
        
        # Set Targets based on time
        # Student Morning (7-8)
        if 7 <= hour < 8:
            student_mask = (self.state != State.DECEASED.value) & self.student & active_movement_mask
            self.target[student_mask] = self.school[student_mask]
            self.flags[student_mask] |= 1

        # Morning Commute (8-9)
        if 8 <= hour < 9:
            active = (self.state != State.DECEASED.value) & self.employed & active_movement_mask
            self.target[active] = self.work[active]
            self.flags[active] |= 1 # Has Target
            
        # Lunch Break (12-13) for employed
        if 12 <= hour < 13:
            lunch_mask = (self.state != State.DECEASED.value) & self.employed & active_movement_mask
            self.target[lunch_mask] = self.lunch[lunch_mask]
            self.flags[lunch_mask] |= 1

        # Return to Work after Lunch (13-14)
        if 13 <= hour < 14:
            back_to_work = (self.state != State.DECEASED.value) & self.employed & active_movement_mask
            self.target[back_to_work] = self.work[back_to_work]
            self.flags[back_to_work] |= 1

        # Student Afternoon (15-16) go home
        if 15 <= hour < 16:
            student_home = (self.state != State.DECEASED.value) & self.student & active_movement_mask
            self.target[student_home] = self.home[student_home]
            self.flags[student_home] |= 1

        # Evening Return (17-18) employed
        if 17 <= hour < 18:
            active = (self.state != State.DECEASED.value) & self.employed & active_movement_mask
            self.target[active] = self.home[active]
            self.flags[active] |= 1

        # Evening leisure (18-20) for all living agents
        if 18 <= hour < 20:
            leisure_mask = (self.state != State.DECEASED.value) & active_movement_mask
            self.target[leisure_mask] = self.leisure[leisure_mask]
            self.flags[leisure_mask] |= 1

        # Return home (20-22) for everyone
        if 20 <= hour < 22:
            back_home = (self.state != State.DECEASED.value) & active_movement_mask
            self.target[back_home] = self.home[back_home]
            self.flags[back_home] |= 1
            
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

        # Gentle wandering for agents without a target (daytime only)
        no_target_mask = (self.flags & 1) == 0
        active_mask = (self.state != State.DECEASED.value) & no_target_mask
        if np.any(active_mask) and getattr(time_engine, 'is_daytime', True):
            # Random small movement scaled by circadian factor
            scale = 0.3 * (dt * 60.0) * float(getattr(time_engine, 'circadian_factor', 1.0))
            jitter = (np.random.rand(np.count_nonzero(active_mask), 2) - 0.5) * scale
            self.pos[np.where(active_mask)[0]] += jitter

        # 3. Infection Logic (Spatial Hash)
        # Only run if there are infectious people
        infectious_indices = np.where(self.state == State.INFECTIOUS.value)[0]
        if len(infectious_indices) > 0:
            self._process_infections(infectious_indices)
            
        # Sync back to objects for Renderer (Temporary, until Renderer uses Arrays)
        # This is slow, but necessary for the current Renderer
        # for i, p in enumerate(self.person_map):
        #     p.x, p.y = self.pos[i]
        #     p.state = State(self.state[i])
        #     p.is_asymptomatic = bool(self.is_asymptomatic[i])
        #     p.variant = self.variant_names[int(self.variant_id[i])]

    def _process_infections(self, infectious_indices):
        """Graph-based infection with optional spatial spillover (vectorized) + vaccination"""
        # Rebuild spatial grid for this frame
        self._update_spatial_grid()
        
        # Run vaccination campaign if active (gradual spread like infection)
        if self.vaccination_active:
            self.run_vaccination_campaign(target_rate=self.vaccination_target_rate)
        
        # Batch all potential exposures, then apply at once to avoid redundant checks
        exposures_to_apply = []  # List of (neighbor_idx, variant_idx) tuples
        
        # Primary transmission: Through social network (optimized batch processing)
        for inf_idx in infectious_indices:
            infected_person = self.person_map[inf_idx]
            variant_idx = int(self.variant_id[inf_idx])
            
            # Check if person has social neighbors
            if not hasattr(infected_person, 'social_neighbors') or len(infected_person.social_neighbors) == 0:
                continue
            
            # Batch lookup all neighbor indices
            neighbor_indices = []
            for neighbor in infected_person.social_neighbors:
                neighbor_idx = self.person_to_index.get(neighbor)
                if neighbor_idx is not None:
                    neighbor_indices.append(neighbor_idx)
            
            if len(neighbor_indices) == 0:
                continue
            
            # Vectorized susceptibility check
            neighbor_indices = np.array(neighbor_indices)
            susceptible_mask = self.state[neighbor_indices] == State.SUSCEPTIBLE.value
            susceptible_neighbors = neighbor_indices[susceptible_mask]
            
            if len(susceptible_neighbors) == 0:
                continue
            
            # Vectorized transmission probability calculation
            base_transmission_prob = self.infection_prob * 2.0 * float(self.variant_transmission[variant_idx])
            transmission_probs = np.full(len(susceptible_neighbors), base_transmission_prob, dtype=np.float32)
            
            # Apply vaccination protection (vectorized)
            vaccinated_mask = self.is_vaccinated[susceptible_neighbors]
            if np.any(vaccinated_mask):
                efficacy_reduction = (1.0 - self.vaccination_efficacy[susceptible_neighbors[vaccinated_mask]] / 100.0)
                transmission_probs[vaccinated_mask] *= efficacy_reduction
            
            # Vectorized random roll for transmission
            infection_rolls = np.random.random(len(susceptible_neighbors))
            infected_mask = infection_rolls < transmission_probs
            newly_infected = susceptible_neighbors[infected_mask]
            
            # Queue exposures
            for neighbor_idx in newly_infected:
                exposures_to_apply.append((int(neighbor_idx), variant_idx))
        
        # Secondary transmission: Spatial spillover (optimized batch processing)
        spatial_spillover_prob = self.infection_prob * float(getattr(self, 'spatial_spillover_factor', 0.3))
        spatial_radius_sq = self.infection_radius_sq * 2.0
        
        # Process in batches to reduce overhead
        for inf_idx in infectious_indices:
            inf_pos = self.pos[inf_idx]
            variant_idx = int(self.variant_id[inf_idx])
            
            # Use spatial grid to get nearby candidates
            close_candidates = self._get_nearby_agents(inf_pos[0], inf_pos[1], spatial_radius_sq)
            
            if len(close_candidates) == 0:
                continue
            
            # Convert to numpy array for vectorized operations
            close_candidates = np.array([c for c in close_candidates if c != inf_idx])
            
            if len(close_candidates) == 0:
                continue
            
            # Vectorized susceptibility check
            susceptible_mask = self.state[close_candidates] == State.SUSCEPTIBLE.value
            susceptible_candidates = close_candidates[susceptible_mask]
            
            if len(susceptible_candidates) == 0:
                continue
            
            # Vectorized distance calculation
            diff = self.pos[susceptible_candidates] - inf_pos
            dist_sq = np.sum(diff**2, axis=1)
            within_radius = dist_sq < spatial_radius_sq
            
            if not np.any(within_radius):
                continue
            
            nearby_susceptible = susceptible_candidates[within_radius]
            
            # Vectorized transmission probability
            base_prob = spatial_spillover_prob * float(self.variant_transmission[variant_idx])
            transmission_probs = np.full(len(nearby_susceptible), base_prob, dtype=np.float32)
            
            # Apply vaccination protection
            vaccinated_mask = self.is_vaccinated[nearby_susceptible]
            if np.any(vaccinated_mask):
                efficacy_reduction = (1.0 - self.vaccination_efficacy[nearby_susceptible[vaccinated_mask]] / 100.0)
                transmission_probs[vaccinated_mask] *= efficacy_reduction
            
            # Vectorized infection roll
            infection_rolls = np.random.random(len(nearby_susceptible))
            infected_mask = infection_rolls < transmission_probs
            newly_infected = nearby_susceptible[infected_mask]
            
            # Queue exposures
            for neighbor_idx in newly_infected:
                exposures_to_apply.append((int(neighbor_idx), variant_idx))
        
        # Apply all exposures at once (deduplicate to avoid double-infection)
        if exposures_to_apply:
            # Deduplicate by neighbor_idx (keep first exposure)
            seen = set()
            for neighbor_idx, variant_idx in exposures_to_apply:
                if neighbor_idx not in seen:
                    seen.add(neighbor_idx)
                    # Final check: still susceptible? (might have been exposed by earlier in batch)
                    if self.state[neighbor_idx] == State.SUSCEPTIBLE.value:
                        self._apply_exposure(neighbor_idx, variant_idx)

    def infect_random_person(self):
        # Find a susceptible person
        susceptible = np.where(self.state == State.SUSCEPTIBLE.value)[0]
        if len(susceptible) > 0:
            target = np.random.choice(susceptible)
            variant_idx = int(self.active_variant)
            self.variant_id[target] = variant_idx
            # Skip exposure delay and go straight to infectious for manual seeding
            self.state[target] = State.INFECTIOUS.value
            low = int(self.variant_infectious_min[variant_idx])
            high = int(self.variant_infectious_max[variant_idx])
            self.timer[target] = np.random.randint(low, high)
            
            # Return position for visual effect
            return self.pos[target]
        return None
