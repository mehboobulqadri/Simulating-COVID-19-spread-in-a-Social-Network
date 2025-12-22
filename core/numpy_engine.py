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
        
        # City tracking for infection spread monitoring
        self.city_id = np.zeros(self.num_people, dtype=np.int8)  # Which city person lives in
        
        # Vaccination tracking
        self.is_vaccinated = np.zeros(self.num_people, dtype=np.bool_)
        self.vaccination_efficacy = np.zeros(self.num_people, dtype=np.float32)
        self.days_since_vaccination = np.zeros(self.num_people, dtype=np.float32)
        
        # Asymptomatic carriers (appear healthy but can spread)
        self.is_asymptomatic = np.zeros(self.num_people, dtype=np.bool_)

        # Variant tracking (0 = base). Values index into self.variant_profiles
        self.variant_id = np.zeros(self.num_people, dtype=np.int8)
        
        # NEW REALISM FEATURES
        # Superspreader designation (10-20% have higher transmission)
        self.is_superspreader = np.random.random(self.num_people) < 0.15
        self.superspreader_mult = 2.5
        
        # Individual susceptibility variation (genetic/health factors)
        self.susceptibility = np.random.uniform(0.5, 2.0, self.num_people).astype(np.float32)
        
        # Viral load tracking (days since infection for gradual infectiousness)
        self.days_infected = np.zeros(self.num_people, dtype=np.int32)
        
        # Immunity decay for reinfection
        self.immunity_timer = np.zeros(self.num_people, dtype=np.int32)
        self.immunity_duration = 360  # 360 ticks (~6 months)
        
        # Household clusters (assigned during init)
        self.household_id = np.zeros(self.num_people, dtype=np.int32)
        
        # Location tracking for transmission multipliers
        self.current_location_type = np.zeros(self.num_people, dtype=np.int8)  # 0=home, 1=work, 2=leisure, 3=other
        
        # NPIs (Non-Pharmaceutical Interventions)
        self.mask_wearing_active = False
        self.mask_compliance = 0.70
        self.mask_effectiveness = 0.60
        self.is_wearing_mask = np.zeros(self.num_people, dtype=np.bool_)
        
        # Flags: 0=None, 1=HasTarget, 2=Hospitalized
        self.flags = np.zeros(self.num_people, dtype=np.int8)
        
        # Initialize Data
        idx = 0
        self.person_map = []
        self.person_to_index = {}
        household_counter = 0
        
        for city_idx, city in enumerate(cities):
            for district in city.districts:
                # Group people into households (2-6 people per household)
                district_people = district.people
                household_sizes = []
                remaining = len(district_people)
                
                while remaining > 0:
                    if remaining == 1:
                        household_sizes.append(1)
                        remaining = 0
                    else:
                        size = min(random.randint(2, 6), remaining)
                        household_sizes.append(size)
                        remaining -= size
                
                person_idx_in_district = 0
                for household_size in household_sizes:
                    household_counter += 1
                    household_members = district_people[person_idx_in_district:person_idx_in_district + household_size]
                    
                    # Assign same household ID and home location to all members
                    if household_members:
                        shared_home = household_members[0].home_location
                        
                        for p in household_members:
                            self.pos[idx] = [p.x, p.y]
                            self.home[idx] = shared_home
                            if p.work_location:
                                self.work[idx] = p.work_location
                            else:
                                self.work[idx] = p.home_location
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
                            self.household_id[idx] = household_counter
                            self.city_id[idx] = city_idx
                            self.person_map.append(p)
                            self.person_to_index[p] = idx
                            idx += 1
                    
                    person_idx_in_district += household_size
        
        print(f"Created {household_counter} households (avg {self.num_people/max(1, household_counter):.1f} people/household)")
        
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
                    
        # Constants - reduced for more realistic spread
        self.infection_radius = 10.0
        self.infection_prob = 0.015  # Reduced from 0.05 for slower spread
        self.recovery_rate = 0.02  # Base death rate (will be modified by age)
        # Factor to scale spatial spillover probability relative to base infection_prob
        self.spatial_spillover_factor = 0.2  # Reduced from 0.3
        self.infection_radius_sq = self.infection_radius ** 2
        self.asymptomatic_rate = 0.40  # Default asymptomatic rate (used by base variant)

        # Variant profiles (kept compact for now)
        self.variant_profiles = [
            {
                "name": "base",
                "transmission_mult": 1.0,
                "mortality_mult": 1.0,
                "incubation_range": (200, 400),  # Longer incubation
                "infectious_range": (600, 1200),  # Longer infectious period
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
        self.vaccination_rate = 0.001  # 0.1% of unvaccinated per tick (VERY gradual)
        self.hospital_cure_rate = 0.01
        self.vaccination_active = False
        self.vaccination_target_rate = 0.0  # Target population % (0-1)
        
        # Auto-vaccination trigger settings
        self.auto_vaccination_enabled = True
        self.auto_vaccination_triggered = False
        self.auto_vacc_death_threshold = 20  # Trigger when 20+ deaths
        self.auto_vacc_city_threshold = 2  # Trigger when infection in 2+ cities
        
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
        
        # Hospital capacity system
        self.hospital_capacity = max(50, int(self.num_people * 0.02))  # 2% of population
        self.hospitalized = np.zeros(self.num_people, dtype=np.bool_)
        self.hospital_mortality_multiplier = 2.5  # Mortality increases when hospitals full
        
        # Location-based transmission multipliers
        self.location_transmission_mults = {
            0: 3.0,   # Home/Family (prolonged close contact)
            1: 1.5,   # Work/School (indoor, many hours)
            2: 0.5,   # Leisure/Outdoor (better ventilation)
            3: 1.0    # Other/Transit
        }
        
        # Household transmission rate (for god mode control)
        self.household_transmission_rate = 0.80
        
        # Behavioral fear response
        self.fear_active = True
        self.fear_threshold = 0.01  # 1% death rate triggers fear
        self.fear_movement_reduction = 0.40  # 40% reduction in movement
        self.total_deaths = 0
        
        # Seasonal/Environmental effects
        self.seasonal_effects_active = True
        self.current_season_mult = 1.0  # Will vary by day
        
        # Contact intensity by distance
        self.contact_distance_close = 5.0
        self.contact_distance_moderate = 10.0
        self.contact_intensity_close = 1.0
        self.contact_intensity_moderate = 0.3
        self.contact_intensity_brief = 0.05

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
    
    def toggle_masks(self):
        """Toggle mask wearing on/off"""
        self.mask_wearing_active = not self.mask_wearing_active
        
        if self.mask_wearing_active:
            compliance_random = np.random.random(self.num_people)
            self.is_wearing_mask = compliance_random < self.mask_compliance
            compliant_count = np.sum(self.is_wearing_mask)
            print(f"😷 MASKS ACTIVE: {compliant_count}/{self.num_people} agents wearing masks ({self.mask_compliance*100:.0f}% compliance)")
            print(f"   Transmission reduced by {self.mask_effectiveness*100:.0f}%")
        else:
            self.is_wearing_mask[:] = False
            print(f"😷 MASKS DEACTIVATED")
        
        return self.mask_wearing_active
    
    def get_seasonal_multiplier(self, day):
        """Calculate seasonal transmission multiplier based on day"""
        if not self.seasonal_effects_active:
            return 1.0
        
        year_cycle = 365.0
        day_in_year = day % year_cycle
        
        # Winter (days 0-90, 275-365): 1.5x transmission
        # Summer (days 120-240): 0.7x transmission
        # Spring/Fall: 1.0x transmission
        
        if day_in_year < 90 or day_in_year > 275:
            return 1.5
        elif 120 <= day_in_year <= 240:
            return 0.7
        else:
            return 1.0

    def set_quarantine_for_people(self, people, active=True, location=None):
        """Quarantine or release a list of people immediately.

        This is used by district/building click selection so quarantine takes
        effect right away instead of waiting for new infections.
        """
        if not people:
            return 0

        mask = self._build_scope_mask(people)
        count = int(np.count_nonzero(mask))
        if count == 0:
            return 0

        if active:
            self.in_quarantine[mask] = True
            # Default quarantine location is home unless a target location is provided
            if location is not None:
                self.quarantine_location[mask] = location
            else:
                self.quarantine_location[mask] = self.home[mask]
            self.quarantine_active = True
        else:
            self.in_quarantine[mask] = False
            # If nobody remains quarantined, turn the global flag off so movement resumes
            if not np.any(self.in_quarantine):
                self.quarantine_active = False

        return count

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
    
    def get_infected_cities_count(self):
        """Count how many cities have at least one infection (exposed or infectious)"""
        infected_mask = (self.state == State.EXPOSED.value) | (self.state == State.INFECTIOUS.value)
        if not np.any(infected_mask):
            return 0
        
        # Get unique city IDs where there are infections
        infected_city_ids = np.unique(self.city_id[infected_mask])
        return len(infected_city_ids)

    def update(self, time_engine, dt):
        # 0. Update seasonal effects
        self.current_season_mult = self.get_seasonal_multiplier(time_engine.current_day)
        
        # Auto-vaccination trigger logic
        if self.auto_vaccination_enabled and not self.auto_vaccination_triggered and not self.vaccination_active:
            infected_cities = self.get_infected_cities_count()
            
            # Trigger if deaths exceed threshold OR infection in 2+ cities
            if self.total_deaths >= self.auto_vacc_death_threshold or infected_cities >= self.auto_vacc_city_threshold:
                self.auto_vaccination_triggered = True
                self.vaccination_active = True
                self.vaccination_target_rate = 0.20  # Start with LOW 20% target
                self.vaccination_scope_mask = np.ones(self.num_people, dtype=np.bool_)
                
                if self.total_deaths >= self.auto_vacc_death_threshold:
                    print(f"🚨 AUTO-VACCINATION TRIGGERED: {self.total_deaths} deaths exceeded threshold ({self.auto_vacc_death_threshold})")
                else:
                    print(f"🚨 AUTO-VACCINATION TRIGGERED: Infection spread to {infected_cities} cities (threshold: {self.auto_vacc_city_threshold})")
                print(f"💉 Starting gradual rollout - initial target: 20% (will increase to 50% over time)")
        
        # Gradually increase vaccination target over time if auto-triggered
        if self.auto_vaccination_triggered and self.vaccination_active:
            # Increase target by 0.1% per tick until reaching 50%
            if self.vaccination_target_rate < 0.50:
                self.vaccination_target_rate = min(0.50, self.vaccination_target_rate + 0.001)
        
        # Update immunity timers for recovered people (reinfection possibility)
        recovered_mask = (self.state == State.RECOVERED.value)
        self.immunity_timer[recovered_mask] += 1
        
        # Recovered people lose immunity after duration
        immunity_lost = recovered_mask & (self.immunity_timer >= self.immunity_duration)
        if np.any(immunity_lost):
            self.state[immunity_lost] = State.SUSCEPTIBLE.value
            self.immunity_timer[immunity_lost] = 0
            reinfectable_count = int(np.sum(immunity_lost))
            if reinfectable_count > 0:
                print(f"⏰ {reinfectable_count} people lost immunity and are now susceptible again")
        
        # 1. Update Logic (State Transitions)
        # Vectorized state timers
        
        # Update viral load for infected people
        infected_or_exposed = (self.state == State.EXPOSED.value) | (self.state == State.INFECTIOUS.value)
        self.days_infected[infected_or_exposed] += 1
        
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
                
                # Hospitalize symptomatic patients (if capacity available)
                symptomatic_mask = ~asym_flags
                symptomatic_indices = v_indices[symptomatic_mask]
                
                # Prioritize by age (elderly first, then adults, then children)
                ages = self.age[symptomatic_indices]
                hospitalization_priority = np.where(ages >= 65, 3.0,
                                          np.where(ages >= 18, 2.0, 1.0))
                sorted_priority_indices = symptomatic_indices[np.argsort(-hospitalization_priority)]
                
                # Assign hospital beds based on capacity
                current_hospitalized = int(np.sum(self.hospitalized))
                available_beds = max(0, self.hospital_capacity - current_hospitalized)
                can_hospitalize = min(len(sorted_priority_indices), available_beds)
                
                if can_hospitalize > 0:
                    self.hospitalized[sorted_priority_indices[:can_hospitalize]] = True
                
                # Quarantine symptomatic if quarantine active
                if self.quarantine_active:
                    self.in_quarantine[symptomatic_indices] = True
        
        # Infectious -> Recovered/Deceased
        infectious_mask = (self.state == State.INFECTIOUS.value)
        self.timer[infectious_mask] -= 1
        finished_infection = infectious_mask & (self.timer <= 0)
        
        count_finished = np.count_nonzero(finished_infection)
        if count_finished > 0:
            # Age-based and vaccination-based mortality rates
            finished_indices = np.where(finished_infection)[0]
            ages = self.age[finished_indices]
            vaccinated = self.is_vaccinated[finished_indices]
            asymptomatic = self.is_asymptomatic[finished_indices]
            v_ids = self.variant_id[finished_indices]
            
            # UNVACCINATED: High mortality rates (most should die)
            # Children (0-17): 60%, Adults (18-64): 75%, Elderly (65+): 85%
            unvaccinated_death_rates = np.where(ages < 18, 0.60,
                                       np.where(ages < 65, 0.75, 0.85))
            
            # VACCINATED: Low mortality rates (most should survive)
            # Base rates: Children: 5%, Adults: 10%, Elderly: 15%
            # Modified by vaccine efficacy (higher efficacy = lower death rate)
            vaccinated_base_rates = np.where(ages < 18, 0.05,
                                    np.where(ages < 65, 0.10, 0.15))
            
            # Apply vaccine efficacy (higher efficacy reduces death rate further)
            # efficacy of 95% -> death rate * 0.05, efficacy of 60% -> death rate * 0.40
            efficacy = self.vaccination_efficacy[finished_indices]
            vaccinated_death_rates = vaccinated_base_rates * (1.0 - efficacy / 100.0)
            
            # Choose death rate based on vaccination status
            death_rates = np.where(vaccinated, vaccinated_death_rates, unvaccinated_death_rates)
            
            # Asymptomatic cases have 30% lower mortality
            death_rates = np.where(asymptomatic, death_rates * 0.70, death_rates)
            
            # Hospital capacity penalty: If not hospitalized, mortality increases
            is_hospitalized = self.hospitalized[finished_indices]
            death_rates = np.where(~is_hospitalized & ~asymptomatic, 
                                  death_rates * self.hospital_mortality_multiplier, 
                                  death_rates)
            
            # Scale by variant-specific mortality factor
            death_rates = death_rates * self.variant_mortality[v_ids]
            
            # Clamp death rates to [0, 1]
            death_rates = np.clip(death_rates, 0.0, 1.0)
            
            # Roll for death vs recovery
            outcomes = np.random.random(count_finished)
            deaths = outcomes < death_rates
            recoveries = ~deaths
            
            self.state[finished_indices[deaths]] = State.DECEASED.value
            self.state[finished_indices[recoveries]] = State.RECOVERED.value
            
            # Track total deaths for fear response
            self.total_deaths += int(np.sum(deaths))
            
            # Reset viral load for finished infections
            self.days_infected[finished_indices] = 0
            
            # Start immunity timer for recovered people
            self.immunity_timer[finished_indices[recoveries]] = 0
            
            # Release hospital beds
            self.hospitalized[finished_indices] = False
            
            # Clear asymptomatic flag when infection ends
            self.is_asymptomatic[finished_indices] = False
            
            # Release from quarantine when infection ends
            self.in_quarantine[finished_indices] = False

        # 2. Movement Logic
        hour = time_engine.hour
        
        # Calculate fear response based on death rate
        death_rate = self.total_deaths / max(1, self.num_people)
        fear_mask = np.zeros(self.num_people, dtype=np.bool_)
        if self.fear_active and death_rate > self.fear_threshold:
            # Random portion of population stays home due to fear
            fear_random = np.random.random(self.num_people)
            fear_mask = fear_random < self.fear_movement_reduction
        
        # Quarantine mode: quarantined agents stay in quarantine location
        if self.quarantine_active:
            quarantined = self.in_quarantine & (self.state != State.DECEASED.value)
            # Hard-stop movement: zero speed and force target to quarantine location
            self.target[quarantined] = self.quarantine_location[quarantined]
            self.flags[quarantined] |= 1
            # Override speeds to 0 while quarantined so they cannot drift
            self.speed[quarantined] = 0.0
        
        # In lockdown mode, compliant agents stay home and don't follow schedules
        if self.lockdown_active:
            # Send lockdown-compliant agents home
            lockdown_compliant = self.lockdown_mask & (self.state != State.DECEASED.value)
            self.target[lockdown_compliant] = self.home[lockdown_compliant]
            self.flags[lockdown_compliant] |= 1
        
        # Fear response: scared agents stay home
        if np.any(fear_mask):
            fear_agents = fear_mask & (self.state != State.DECEASED.value)
            self.target[fear_agents] = self.home[fear_agents]
            self.flags[fear_agents] |= 1
            self.current_location_type[fear_agents] = 0  # Home
        
        # Non-lockdown agents (or non-compliant during lockdown) follow normal schedules
        # Apply movement only to agents NOT in lockdown compliance or fear
        active_movement_mask = ~(self.lockdown_mask | fear_mask) if (self.lockdown_active or np.any(fear_mask)) else np.ones(self.num_people, dtype=np.bool_)
        
        # Set Targets based on time and track location types
        # Student Morning (7-8)
        if 7 <= hour < 8:
            student_mask = (self.state != State.DECEASED.value) & self.student & active_movement_mask
            self.target[student_mask] = self.school[student_mask]
            self.flags[student_mask] |= 1
            self.current_location_type[student_mask] = 1  # School/Work

        # Morning Commute (8-9)
        if 8 <= hour < 9:
            active = (self.state != State.DECEASED.value) & self.employed & active_movement_mask
            self.target[active] = self.work[active]
            self.flags[active] |= 1
            self.current_location_type[active] = 1  # Work
            
        # Lunch Break (12-13) for employed
        if 12 <= hour < 13:
            lunch_mask = (self.state != State.DECEASED.value) & self.employed & active_movement_mask
            self.target[lunch_mask] = self.lunch[lunch_mask]
            self.flags[lunch_mask] |= 1
            self.current_location_type[lunch_mask] = 2  # Leisure/Outdoor

        # Return to Work after Lunch (13-14)
        if 13 <= hour < 14:
            back_to_work = (self.state != State.DECEASED.value) & self.employed & active_movement_mask
            self.target[back_to_work] = self.work[back_to_work]
            self.flags[back_to_work] |= 1
            self.current_location_type[back_to_work] = 1  # Work

        # Student Afternoon (15-16) go home
        if 15 <= hour < 16:
            student_home = (self.state != State.DECEASED.value) & self.student & active_movement_mask
            self.target[student_home] = self.home[student_home]
            self.flags[student_home] |= 1
            self.current_location_type[student_home] = 0  # Home

        # Evening Return (17-18) employed
        if 17 <= hour < 18:
            active = (self.state != State.DECEASED.value) & self.employed & active_movement_mask
            self.target[active] = self.home[active]
            self.flags[active] |= 1
            self.current_location_type[active] = 0  # Home

        # Evening leisure (18-20) for all living agents
        if 18 <= hour < 20:
            leisure_mask = (self.state != State.DECEASED.value) & active_movement_mask
            self.target[leisure_mask] = self.leisure[leisure_mask]
            self.flags[leisure_mask] |= 1
            self.current_location_type[leisure_mask] = 2  # Leisure

        # Return home (20-22) for everyone
        if 20 <= hour < 22:
            back_home = (self.state != State.DECEASED.value) & active_movement_mask
            self.target[back_home] = self.home[back_home]
            self.flags[back_home] |= 1
            self.current_location_type[back_home] = 0  # Home
            
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
        # Infectious people + presymptomatic (exposed in late incubation)
        infectious_indices = np.where(self.state == State.INFECTIOUS.value)[0]
        
        # Presymptomatic transmission: Exposed people in last 2-3 days of incubation
        exposed_indices = np.where((self.state == State.EXPOSED.value) & (self.timer < 100))[0]
        
        # Combine both groups (presymptomatic transmit at 40% rate)
        all_transmitters = np.concatenate([infectious_indices, exposed_indices]) if len(exposed_indices) > 0 else infectious_indices
        
        if len(all_transmitters) > 0:
            self._process_infections(all_transmitters, infectious_indices)
            
        # Sync back to objects for Renderer (Temporary, until Renderer uses Arrays)
        # This is slow, but necessary for the current Renderer
        # for i, p in enumerate(self.person_map):
        #     p.x, p.y = self.pos[i]
        #     p.state = State(self.state[i])
        #     p.is_asymptomatic = bool(self.is_asymptomatic[i])
        #     p.variant = self.variant_names[int(self.variant_id[i])]

    def _process_infections(self, all_transmitters, fully_infectious_indices):
        """Enhanced infection with all realism features"""
        # Rebuild spatial grid for this frame
        self._update_spatial_grid()
        
        # Run vaccination campaign if active
        if self.vaccination_active:
            self.run_vaccination_campaign(target_rate=self.vaccination_target_rate)
        
        # Batch all potential exposures
        exposures_to_apply = []
        
        # Household transmission (VERY HIGH RATE - 80% within household)
        # Process households with at least one infectious member
        for inf_idx in fully_infectious_indices:
            household = self.household_id[inf_idx]
            if household == 0:
                continue
            
            # Find all household members
            household_members = np.where(self.household_id == household)[0]
            susceptible_members = household_members[self.state[household_members] == State.SUSCEPTIBLE.value]
            
            if len(susceptible_members) == 0:
                continue
            
            variant_idx = int(self.variant_id[inf_idx])
            
            # Configurable base transmission rate within household
            household_transmission_prob = self.household_transmission_rate * float(self.variant_transmission[variant_idx])
            
            for member_idx in susceptible_members:
                # Apply individual susceptibility
                final_prob = household_transmission_prob * self.susceptibility[member_idx]
                
                # Vaccination protection
                if self.is_vaccinated[member_idx]:
                    final_prob *= (1.0 - self.vaccination_efficacy[member_idx] / 100.0)
                
                # Mask protection (both wear masks)
                if self.mask_wearing_active:
                    if self.is_wearing_mask[inf_idx] and self.is_wearing_mask[member_idx]:
                        final_prob *= (1.0 - self.mask_effectiveness)
                
                if np.random.random() < final_prob:
                    exposures_to_apply.append((int(member_idx), variant_idx))
        
        # Primary transmission: Through social network (optimized batch processing)
        for inf_idx in all_transmitters:
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
            
            # Calculate viral load multiplier based on days infected
            days = self.days_infected[inf_idx]
            if days < 2:
                viral_load_mult = 0.3  # Early infection
            elif days <= 5:
                viral_load_mult = 1.0  # Peak infectiousness
            elif days <= 10:
                viral_load_mult = 0.5  # Declining
            else:
                viral_load_mult = 0.2  # Late infection
            
            # Presymptomatic transmission (if exposed)
            if self.state[inf_idx] == State.EXPOSED.value:
                viral_load_mult *= 0.4  # 40% transmission rate for presymptomatic
            
            # Base transmission with all modifiers
            base_transmission_prob = self.infection_prob * 2.0 * float(self.variant_transmission[variant_idx])
            base_transmission_prob *= viral_load_mult
            base_transmission_prob *= self.current_season_mult  # Seasonal effect
            
            # Superspreader multiplier
            if self.is_superspreader[inf_idx]:
                base_transmission_prob *= self.superspreader_mult
            
            # Location-based multiplier (use transmitter's location)
            location_type = int(self.current_location_type[inf_idx])
            location_mult = self.location_transmission_mults.get(location_type, 1.0)
            base_transmission_prob *= location_mult
            
            transmission_probs = np.full(len(susceptible_neighbors), base_transmission_prob, dtype=np.float32)
            
            # Individual susceptibility (vectorized)
            transmission_probs *= self.susceptibility[susceptible_neighbors]
            
            # Vaccination protection (vectorized)
            vaccinated_mask = self.is_vaccinated[susceptible_neighbors]
            if np.any(vaccinated_mask):
                efficacy_reduction = (1.0 - self.vaccination_efficacy[susceptible_neighbors[vaccinated_mask]] / 100.0)
                transmission_probs[vaccinated_mask] *= efficacy_reduction
            
            # Mask effectiveness (if both wearing masks)
            if self.mask_wearing_active:
                if self.is_wearing_mask[inf_idx]:
                    both_masked = self.is_wearing_mask[susceptible_neighbors]
                    transmission_probs[both_masked] *= (1.0 - self.mask_effectiveness)
            
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
        for inf_idx in all_transmitters:
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
            nearby_distances = np.sqrt(dist_sq[within_radius])
            
            # Calculate viral load multiplier
            days = self.days_infected[inf_idx]
            if days < 2:
                viral_load_mult = 0.3
            elif days <= 5:
                viral_load_mult = 1.0
            elif days <= 10:
                viral_load_mult = 0.5
            else:
                viral_load_mult = 0.2
            
            # Presymptomatic
            if self.state[inf_idx] == State.EXPOSED.value:
                viral_load_mult *= 0.4
            
            # Base probability with modifiers
            base_prob = spatial_spillover_prob * float(self.variant_transmission[variant_idx])
            base_prob *= viral_load_mult
            base_prob *= self.current_season_mult
            
            # Superspreader
            if self.is_superspreader[inf_idx]:
                base_prob *= self.superspreader_mult
            
            # Location multiplier
            location_type = int(self.current_location_type[inf_idx])
            location_mult = self.location_transmission_mults.get(location_type, 1.0)
            base_prob *= location_mult
            
            transmission_probs = np.full(len(nearby_susceptible), base_prob, dtype=np.float32)
            
            # Contact intensity based on distance
            close_mask = nearby_distances < self.contact_distance_close
            moderate_mask = (nearby_distances >= self.contact_distance_close) & (nearby_distances < self.contact_distance_moderate)
            brief_mask = nearby_distances >= self.contact_distance_moderate
            
            transmission_probs[close_mask] *= self.contact_intensity_close
            transmission_probs[moderate_mask] *= self.contact_intensity_moderate
            transmission_probs[brief_mask] *= self.contact_intensity_brief
            
            # Individual susceptibility
            transmission_probs *= self.susceptibility[nearby_susceptible]
            
            # Vaccination protection
            vaccinated_mask = self.is_vaccinated[nearby_susceptible]
            if np.any(vaccinated_mask):
                efficacy_reduction = (1.0 - self.vaccination_efficacy[nearby_susceptible[vaccinated_mask]] / 100.0)
                transmission_probs[vaccinated_mask] *= efficacy_reduction
            
            # Mask effectiveness
            if self.mask_wearing_active:
                if self.is_wearing_mask[inf_idx]:
                    both_masked = self.is_wearing_mask[nearby_susceptible]
                    transmission_probs[both_masked] *= (1.0 - self.mask_effectiveness)
            
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
