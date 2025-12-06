import pygame
import random
from entities.city import City
from entities.district import District
from entities.person import Person

class WorldGenerator:
    @staticmethod
    def generate_world(num_cities=3, map_width=2000, map_height=2000):
        cities = []
        all_districts = []
        
        # Helper to check overlap
        def check_overlap(new_rect, existing_districts):
            for d in existing_districts:
                # Add padding to ensure gap
                if new_rect.colliderect(d.bounds.inflate(20, 20)):
                    return True
            return False

        for i in range(num_cities):
            # Random city location
            # Ensure cities are far apart
            valid_city_loc = False
            attempts = 0
            while not valid_city_loc and attempts < 50:
                cx = random.randint(200, map_width - 200)
                cy = random.randint(200, map_height - 200)
                valid_city_loc = True
                for c in cities:
                    dist = ((c.location[0] - cx)**2 + (c.location[1] - cy)**2)**0.5
                    if dist < 400: # Minimum distance between cities
                        valid_city_loc = False
                        break
                attempts += 1
            
            if not valid_city_loc:
                continue # Skip if can't place city

            city = City(f"c_{i}", f"City {i+1}", (cx, cy))
            
            # Create districts around city center
            num_districts = random.randint(3, 6)
            city_districts = []
            
            for j in range(num_districts):
                # Try to place district without overlap
                placed = False
                d_attempts = 0
                while not placed and d_attempts < 50:
                    # Place relative to city center
                    angle = random.uniform(0, 6.28)
                    dist = random.uniform(50, 200)
                    dx = int(cx + dist * 0.5 * random.choice([-1, 1])) # Spread out
                    dy = int(cy + dist * 0.5 * random.choice([-1, 1]))
                    
                    w = random.randint(100, 180)
                    h = random.randint(100, 180)
                    bounds = pygame.Rect(dx, dy, w, h)
                    
                    if not check_overlap(bounds, all_districts):
                        placed = True
                        district = District(f"d_{i}_{j}", f"District {j+1}", bounds)
                        
                        # Populate district
                        population = random.randint(50, 150)
                        for k in range(population):
                            px = random.randint(bounds.left + 5, bounds.right - 5)
                            py = random.randint(bounds.top + 5, bounds.bottom - 5)
                            person = Person(f"p_{i}_{j}_{k}", px, py, district)
                            district.add_person(person)
                            
                        city.add_district(district)
                        city_districts.append(district)
                        all_districts.append(district)
                    
                    d_attempts += 1
            
            # Connect districts (Roads)
            # Simple MST or just connect to nearest neighbors
            # For now, just store neighbors in the district object
            for d1 in city_districts:
                # Connect to 2 nearest districts
                others = sorted(city_districts, key=lambda d2: ((d1.bounds.centerx - d2.bounds.centerx)**2 + (d1.bounds.centery - d2.bounds.centery)**2))
                for d2 in others[1:3]: # Skip self (index 0)
                    if d2 not in [n[0] for n in d1.neighbors]:
                        d1.add_neighbor(d2)
                        d2.add_neighbor(d1)

            cities.append(city)
            
        # Assign Work Locations
        # 80% work locally (same city), 20% commute to other cities
        for city in cities:
            for district in city.districts:
                for person in district.people:
                    if random.random() < 0.8: # 80% workforce
                        if random.random() < 0.2 and len(cities) > 1:
                            # Inter-city commuter
                            other_city = random.choice([c for c in cities if c != city])
                            if other_city.districts:
                                work_district = random.choice(other_city.districts)
                            else:
                                work_district = district # Fallback
                        else:
                            # Local commuter
                            work_district = random.choice(city.districts)
                            
                        wx = random.randint(work_district.bounds.left + 5, work_district.bounds.right - 5)
                        wy = random.randint(work_district.bounds.top + 5, work_district.bounds.bottom - 5)
                        person.work_location = (wx, wy)
            
        return cities
