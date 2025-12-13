import pygame
import networkx as nx
import random
import math
from entities.city import City
from entities.district import District
from entities.person import Person
from entities.building import Building, BuildingType

class Road:
    def __init__(self, start, end, width=10):
        self.start = start
        self.end = end
        self.width = width

class WorldGenerator:
    @staticmethod
    def generate_world(num_cities=3, map_width=3000, map_height=3000):
        cities = []
        
        # Grid settings
        block_size = 120
        road_width = 15
        
        for i in range(num_cities):
            # Place city center far from others
            valid = False
            cx, cy = 0, 0
            while not valid:
                cx = random.randint(500, map_width - 500)
                cy = random.randint(500, map_height - 500)
                valid = True
                for c in cities:
                    if math.hypot(c.location[0]-cx, c.location[1]-cy) < 800:
                        valid = False
                        break
            
            city = City(f"c_{i}", f"City {i+1}", (cx, cy))
            city.roads = [] # Add roads list to city
            
            # Generate Grid Layout
            # Create a central grid of 5x5 blocks
            grid_w, grid_h = 6, 6
            
            start_x = cx - (grid_w * block_size) // 2
            start_y = cy - (grid_h * block_size) // 2
            
            # Create Roads (Horizontal)
            for r in range(grid_h + 1):
                y = start_y + r * block_size
                road = Road((start_x, y), (start_x + grid_w * block_size, y), road_width)
                city.roads.append(road)
                
            # Create Roads (Vertical)
            for c_idx in range(grid_w + 1):
                x = start_x + c_idx * block_size
                road = Road((x, start_y), (x, start_y + grid_h * block_size), road_width)
                city.roads.append(road)
            
            # Create Districts (Blocks)
            # Group blocks into districts (e.g. 2x2 blocks = 1 district)
            
            district_idx = 0
            for by in range(0, grid_h, 2):
                for bx in range(0, grid_w, 2):
                    # Define district bounds (2x2 blocks)
                    d_x = start_x + bx * block_size
                    d_y = start_y + by * block_size
                    d_w = block_size * 2
                    d_h = block_size * 2
                    
                    # Add padding for roads
                    bounds = pygame.Rect(d_x + road_width, d_y + road_width, 
                                       d_w - road_width*2, d_h - road_width*2)
                    
                    district = District(f"d_{i}_{district_idx}", f"District {district_idx+1}", bounds)
                    
                    # Zoning: Center blocks are Commercial/Hospital, Outer are Residential
                    dist_to_center = math.hypot((bx+1) - grid_w/2, (by+1) - grid_h/2)
                    
                    is_center = dist_to_center < 1.5
                    
                    # Add Buildings
                    # Fill block with buildings
                    # Subdivide block into lots
                    lot_size = 40
                    cols = int(bounds.width / lot_size)
                    rows = int(bounds.height / lot_size)
                    
                    for r in range(rows):
                        for c in range(cols):
                            if random.random() < 0.7: # 70% density
                                lx = bounds.x + c * lot_size + 5
                                ly = bounds.y + r * lot_size + 5
                                lw = lot_size - 10
                                lh = lot_size - 10
                                
                                b_type = BuildingType.RESIDENTIAL
                                if is_center:
                                    if random.random() < 0.3:
                                        b_type = BuildingType.HOSPITAL
                                        city.hospitals.append(Building(lx, ly, lw, lh, b_type))
                                    else:
                                        b_type = BuildingType.WORKPLACE
                                
                                building = Building(lx, ly, lw, lh, b_type)
                                district.add_building(building)
                    
                    # Add People
                    pop = random.randint(20, 50)
                    for k in range(pop):
                        px = random.randint(bounds.left, bounds.right)
                        py = random.randint(bounds.top, bounds.bottom)
                        person = Person(f"p_{i}_{district_idx}_{k}", px, py, district)
                        district.add_person(person)
                        
                    city.add_district(district)
                    district_idx += 1
            
            cities.append(city)
            
        # Assign Work Locations (including cross-city commuters)
        # Build a list of workplaces per city for local assignment and cross-city selection
        city_workplaces = []
        for city in cities:
            wps = []
            for d in city.districts:
                for b in d.buildings:
                    if b.type == BuildingType.WORKPLACE or b.type == BuildingType.HOSPITAL:
                        wps.append(b)
            if not wps:
                # Fallback if no workplaces: consider any building
                wps = [b for d in city.districts for b in d.buildings]
            city_workplaces.append(wps)

        # Probability that a person works in another city (commuter)
        cross_city_prob = 0.12  # ~12% commuters

        for city_idx, city in enumerate(cities):
            local_wps = city_workplaces[city_idx]
            # Prepare a flat list of other cities' workplaces
            other_wps = [b for idx, wps in enumerate(city_workplaces) if idx != city_idx for b in wps]

            for d in city.districts:
                for p in d.people:
                    # Track home/work city ids for commuter logic and analytics
                    p.home_city_id = city_idx
                    p.work_city_id = city_idx

                    if random.random() < 0.8:  # 80% employed
                        # Decide if this person is a cross-city commuter
                        if other_wps and random.random() < cross_city_prob:
                            target_b = random.choice(other_wps)
                            # Update work city id based on which city the workplace belongs to
                            # Find city index for target_b by scanning membership
                            for idx, wps in enumerate(city_workplaces):
                                if target_b in wps:
                                    p.work_city_id = idx
                                    break
                        else:
                            target_b = random.choice(local_wps)

                        p.work_location = (target_b.bounds.centerx, target_b.bounds.centery)

        # Generate social networks per city (Watts-Strogatz small-world)
        for city in cities:
            # Collect people list for index mapping
            city_people = [p for d in city.districts for p in d.people]
            n = len(city_people)
            if n == 0:
                continue
            # Average degree ~8, rewiring probability 0.1
            k = max(4, min(12, 8))
            p = 0.1
            G = nx.watts_strogatz_graph(n, k, p)
            # Assign neighbors to each person
            for i, person in enumerate(city_people):
                neighbor_indices = list(G.neighbors(i))
                person.social_neighbors = [city_people[j] for j in neighbor_indices]
                person.neighbor_count = len(neighbor_indices)

        return cities
