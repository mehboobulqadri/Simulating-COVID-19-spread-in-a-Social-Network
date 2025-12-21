import pygame
import random
import math
from entities.city import City
from entities.district import District
from entities.person import Person
from entities.building import Building, BuildingType
import networkx as nx

class Road:
    def __init__(self, start, end, width=10, kind="road"):
        self.start = start
        self.end = end
        self.width = width
        # Tag whether this is a city road or inter-city highway (for hover info)
        self.kind = kind

class WorldGenerator:
    @staticmethod
    def _nearest_building(origin, buildings):
        if not buildings:
            return None
        ox, oy = origin
        best = None
        best_d2 = float('inf')
        for b in buildings:
            cx, cy = b.bounds.centerx, b.bounds.centery
            d2 = (cx - ox) ** 2 + (cy - oy) ** 2
            if d2 < best_d2:
                best_d2 = d2
                best = b
        return best
    @staticmethod
    def generate_social_networks(cities):
        """Generate Watts-Strogatz small-world networks for each city"""
        print("Generating social networks...")
        
        for city in cities:
            # Get all people in this city
            city_people = []
            for district in city.districts:
                city_people.extend(district.people)
            
            n = len(city_people)
            if n < 4:
                # Too few people for meaningful network
                continue
                
            # Watts-Strogatz parameters
            k = min(8, n - 1)  # Average degree (neighbors per node)
            p = 0.1  # Rewiring probability (creates shortcuts)
            
            # Generate small-world graph
            G = nx.watts_strogatz_graph(n, k, p)
            
            # Store neighbor lists on each person
            for idx, person in enumerate(city_people):
                neighbor_indices = list(G.neighbors(idx))
                person.social_neighbors = [city_people[i] for i in neighbor_indices]
                person.neighbor_count = len(neighbor_indices)
            
            print(f"  {city.name}: {n} people, avg {k} neighbors")
        
        print("Social networks generated!")

    @staticmethod
    def _generate_city_positions(num_cities, map_width, map_height, min_distance=800):
        """
        Generate non-overlapping city positions with better spacing
        
        Args:
            num_cities: Number of cities to place
            map_width: Width of the map
            map_height: Height of the map  
            min_distance: Minimum distance between city centers
            
        Returns:
            List of (x, y) positions
        """
        positions = []
        max_attempts = 1000
        
        # Add margins to keep cities away from edges
        margin = 500
        valid_min_x = margin
        valid_max_x = map_width - margin
        valid_min_y = margin
        valid_max_y = map_height - margin
        
        # Calculate city footprint (grid size)
        # Each city is about 6x6 blocks * 120 = 720 units wide
        city_radius = 360  # Half of city size for collision detection
        effective_min_distance = max(min_distance, city_radius * 2 + 200)
        
        print(f"\nGenerating {num_cities} cities with minimum distance: {effective_min_distance}")
        
        # Place first city near center
        if num_cities > 0:
            center_x = map_width // 2 + random.randint(-200, 200)
            center_y = map_height // 2 + random.randint(-200, 200)
            positions.append((center_x, center_y))
            print(f"  ✓ City 1 placed at center ({center_x}, {center_y})")
        
        # Place remaining cities
        for i in range(1, num_cities):
            placed = False
            attempts = 0
            best_position = None
            best_min_dist = 0
            
            while attempts < max_attempts:
                # Generate random candidate position
                cx = random.randint(valid_min_x, valid_max_x)
                cy = random.randint(valid_min_y, valid_max_y)
                
                # Check distance to all existing cities
                min_dist = float('inf')
                valid = True
                
                for existing_x, existing_y in positions:
                    dist = math.hypot(cx - existing_x, cy - existing_y)
                    min_dist = min(min_dist, dist)
                    
                    if dist < effective_min_distance:
                        valid = False
                        break
                
                # If we found a valid position, use it
                if valid:
                    positions.append((cx, cy))
                    placed = True
                    print(f"  ✓ City {i+1} placed at ({cx}, {cy}) - min distance: {min_dist:.0f}")
                    break
                
                # Track the best position we've found
                if min_dist > best_min_dist:
                    best_min_dist = min_dist
                    best_position = (cx, cy)
                
                attempts += 1
            
            # If we couldn't place with ideal distance, use best position
            if not placed and best_position:
                positions.append(best_position)
                print(f"  ⚠ City {i+1} placed at best position ({best_position[0]}, {best_position[1]}) - distance: {best_min_dist:.0f}")
            elif not placed:
                # Last resort: place it somewhere
                cx = random.randint(valid_min_x, valid_max_x)
                cy = random.randint(valid_min_y, valid_max_y)
                positions.append((cx, cy))
                print(f"  ⚠ City {i+1} placed randomly after {max_attempts} attempts")
        
        return positions

    @staticmethod
    def generate_world(num_cities=3, map_width=3000, map_height=3000):
        cities = []
        
        # Grid settings
        block_size = 120
        road_width = 15
        
        # Generate non-overlapping city positions
        city_positions = WorldGenerator._generate_city_positions(
            num_cities, 
            map_width, 
            map_height,
            min_distance=1000  # Adjust this to change spacing
        )
        
        for i, (cx, cy) in enumerate(city_positions):
            city = City(f"c_{i}", f"City {i+1}", (cx, cy))
            city.roads = [] # Add roads list to city
            
            # Generate Grid Layout
            # Create a central grid of 6x6 blocks
            grid_w, grid_h = 6, 6
            
            start_x = cx - (grid_w * block_size) // 2
            start_y = cy - (grid_h * block_size) // 2
            
            # Create Roads (Horizontal)
            for r in range(grid_h + 1):
                y = start_y + r * block_size
                road = Road((start_x, y), (start_x + grid_w * block_size, y), road_width, kind="road")
                city.roads.append(road)
                
            # Create Roads (Vertical)
            for c_idx in range(grid_w + 1):
                x = start_x + c_idx * block_size
                road = Road((x, start_y), (x, start_y + grid_h * block_size), road_width, kind="road")
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
                    
                    # Ensure city registries exist
                    if not hasattr(city, 'workplaces'):
                        city.workplaces = []
                    if not hasattr(city, 'commercials'):
                        city.commercials = []
                    if not hasattr(city, 'schools'):
                        city.schools = []
                    if not hasattr(city, 'parks'):
                        city.parks = []

                    for r in range(rows):
                        for c in range(cols):
                            if random.random() < 0.7:  # 70% density
                                lx = bounds.x + c * lot_size + 5
                                ly = bounds.y + r * lot_size + 5
                                lw = lot_size - 10
                                lh = lot_size - 10

                                b_type = BuildingType.RESIDENTIAL
                                if is_center:
                                    roll = random.random()
                                    if roll < 0.2:
                                        b_type = BuildingType.HOSPITAL
                                    elif roll < 0.6:
                                        b_type = BuildingType.WORKPLACE
                                    else:
                                        b_type = BuildingType.COMMERCIAL
                                else:
                                    roll = random.random()
                                    if roll < 0.7:
                                        b_type = BuildingType.RESIDENTIAL
                                    elif roll < 0.8:
                                        b_type = BuildingType.SCHOOL
                                    elif roll < 0.9:
                                        b_type = BuildingType.PARK
                                    else:
                                        b_type = BuildingType.COMMERCIAL

                                building = Building(lx, ly, lw, lh, b_type)
                                district.add_building(building)
                                # Register special buildings
                                if b_type == BuildingType.HOSPITAL:
                                    city.hospitals.append(building)
                                elif b_type == BuildingType.WORKPLACE:
                                    city.workplaces.append(building)
                                elif b_type == BuildingType.COMMERCIAL:
                                    city.commercials.append(building)
                                elif b_type == BuildingType.SCHOOL:
                                    city.schools.append(building)
                                elif b_type == BuildingType.PARK:
                                    city.parks.append(building)
                    
                    # Add People
                    pop = random.randint(20, 50)
                    for k in range(pop):
                        px = random.randint(bounds.left, bounds.right)
                        py = random.randint(bounds.top, bounds.bottom)
                        person = Person(f"p_{i}_{district_idx}_{k}", px, py, district)
                        # Student assignment
                        person.is_student = 6 <= getattr(person, 'age', 0) <= 18
                        # School location (nearest available)
                        if person.is_student:
                            school_b = WorldGenerator._nearest_building(person.home_location, getattr(city, 'schools', []))
                            if not school_b:
                                # Fallback to workplace/hospital if no schools generated
                                school_b = WorldGenerator._nearest_building(person.home_location, getattr(city, 'workplaces', [])) or WorldGenerator._nearest_building(person.home_location, getattr(city, 'hospitals', []))
                            person.school_location = (school_b.bounds.centerx, school_b.bounds.centery) if school_b else person.home_location
                        else:
                            person.school_location = None

                        # Lunch spot (nearest commercial)
                        lunch_b = WorldGenerator._nearest_building(person.home_location, getattr(city, 'commercials', []))
                        person.lunch_location = (lunch_b.bounds.centerx, lunch_b.bounds.centery) if lunch_b else None

                        # Leisure spot (nearest park or commercial)
                        leisure_b = WorldGenerator._nearest_building(person.home_location, getattr(city, 'parks', []))
                        if not leisure_b:
                            leisure_b = WorldGenerator._nearest_building(person.home_location, getattr(city, 'commercials', []))
                        person.leisure_location = (leisure_b.bounds.centerx, leisure_b.bounds.centery) if leisure_b else None

                        district.add_person(person)
                        
                    city.add_district(district)
                    district_idx += 1
            
            cities.append(city)
        
        print(f"\n✓ Generated {len(cities)} cities with proper spacing")
            
        # Assign Work Locations (with cross-city commuters)
        city_workplaces = []
        for city in cities:
            wps = []
            for d in city.districts:
                for b in d.buildings:
                    if b.type == BuildingType.WORKPLACE or b.type == BuildingType.HOSPITAL:
                        wps.append(b)
            if not wps:
                wps = [b for d in city.districts for b in d.buildings]
            city_workplaces.append(wps)

        cross_city_prob = 0.12  # ~12% commuters

        for city_idx, city in enumerate(cities):
            local_wps = city_workplaces[city_idx]
            other_wps = [b for idx, wps in enumerate(city_workplaces) if idx != city_idx for b in wps]

            for d in city.districts:
                for p in d.people:
                    p.home_city_id = city_idx
                    p.work_city_id = city_idx
                    is_work_age = 16 <= getattr(p, 'age', 0) <= 65
                    if is_work_age and random.random() < 0.8:  # 80% of working-age population is employed
                        p.is_employed = True
                        if other_wps and random.random() < cross_city_prob:
                            target_b = random.choice(other_wps)
                            for idx, wps in enumerate(city_workplaces):
                                if target_b in wps:
                                    p.work_city_id = idx
                                    break
                        else:
                            target_b = random.choice(local_wps)

                        p.work_location = (target_b.bounds.centerx, target_b.bounds.centery)

        # Generate social networks
        WorldGenerator.generate_social_networks(cities)
        
        # Add inter-city roads
        WorldGenerator.generate_inter_city_roads(cities)
        
        return cities
    
    @staticmethod
    def generate_inter_city_roads(cities):
        """Generate roads connecting city centers"""
        if len(cities) < 2:
            return
        
        print("\nGenerating inter-city highways...")
            
        # Connect each city to its nearest neighbors
        for i, city_a in enumerate(cities):
            distances = []
            for j, city_b in enumerate(cities):
                if i != j:
                    dist = math.hypot(city_a.location[0] - city_b.location[0],
                                     city_a.location[1] - city_b.location[1])
                    distances.append((dist, j, city_b))
            
            # Connect to 2 nearest cities (or all if less than 2)
            distances.sort()
            num_connections = min(2, len(distances))
            
            for _, j, city_b in distances[:num_connections]:
                # Create highway between cities
                road = Road(city_a.location, city_b.location, width=20, kind="highway")
                # Store on both cities to avoid duplicates
                if not hasattr(city_a, 'highways'):
                    city_a.highways = []
                city_a.highways.append(road)
                print(f"  ✓ Highway: {city_a.name} → {city_b.name}")
        
        print("Inter-city highways generated!")
    
    @staticmethod
    def visualize_city_layout(cities, map_width=3000, map_height=3000):
        """
        Debug function to visualize city placement
        Prints a simple ASCII representation with distance validation
        """
        print("\n" + "="*70)
        print("CITY LAYOUT VISUALIZATION")
        print("="*70)
        
        # Calculate grid size for ASCII visualization
        grid_width = 70
        grid_height = 25
        grid = [[' ' for _ in range(grid_width)] for _ in range(grid_height)]
        
        # Plot cities on grid
        for i, city in enumerate(cities):
            x = int((city.location[0] / map_width) * (grid_width - 1))
            y = int((city.location[1] / map_height) * (grid_height - 1))
            x = max(0, min(grid_width - 1, x))
            y = max(0, min(grid_height - 1, y))
            
            # Use letter labels for up to 26 cities
            label = chr(65 + i) if i < 26 else str(i)
            grid[y][x] = label
        
        # Print grid
        print("┌" + "─" * grid_width + "┐")
        for row in grid:
            print("│" + "".join(row) + "│")
        print("└" + "─" * grid_width + "┘")
        
        # Print city details
        print("\nCITY DETAILS:")
        for i, city in enumerate(cities):
            label = chr(65 + i) if i < 26 else str(i)
            num_districts = len(city.districts)
            total_pop = sum(len(d.people) for d in city.districts)
            print(f"  [{label}] {city.name:20} @ ({city.location[0]:6.0f}, {city.location[1]:6.0f}) "
                  f"- {num_districts} districts, {total_pop} people")
        
        # Calculate and print all pairwise distances
        print(f"\nPAIRWISE DISTANCES:")
        min_found = float('inf')
        distances_list = []
        
        for i, city1 in enumerate(cities):
            for j, city2 in enumerate(cities):
                if i >= j:
                    continue
                dx = city2.location[0] - city1.location[0]
                dy = city2.location[1] - city1.location[1]
                dist = math.sqrt(dx*dx + dy*dy)
                min_found = min(min_found, dist)
                
                label1 = chr(65 + i) if i < 26 else str(i)
                label2 = chr(65 + j) if j < 26 else str(j)
                
                # Color code based on distance
                if dist >= 800:
                    status = "✓"  # Good spacing
                elif dist >= 600:
                    status = "○"  # Acceptable
                else:
                    status = "✗"  # Too close
                
                distances_list.append((dist, status, label1, label2, city1.name, city2.name))
        
        # Sort and print distances
        distances_list.sort()
        for dist, status, l1, l2, name1, name2 in distances_list:
            print(f"  {status} [{l1}] {name1:15} ↔ [{l2}] {name2:15}: {dist:6.0f} units")
        
        print(f"\n{'='*70}")
        print(f"Overall minimum distance: {min_found:.0f} units")
        print(f"Recommended minimum: 800 units")
        
        if min_found >= 800:
            print("✓ All cities have adequate spacing!")
        elif min_found >= 600:
            print("○ Cities are close but acceptable")
        else:
            print("✗ Warning: Some cities may overlap or be too close")
        
        print("="*70 + "\n")


# Testing/Debug function
if __name__ == "__main__":
    print("Testing WorldGenerator with enhanced city placement...")
    
    # Generate world
    cities = WorldGenerator.generate_world(
        num_cities=5,
        map_width=3000,
        map_height=3000
    )
    
    # Visualize the layout
    WorldGenerator.visualize_city_layout(cities, map_width=3000, map_height=3000)
    
    print(f"\n✓ Successfully generated {len(cities)} cities!")
    
    # Print additional statistics
    total_pop = sum(sum(len(d.people) for d in city.districts) for city in cities)
    total_districts = sum(len(city.districts) for city in cities)
    print(f"Total population: {total_pop}")
    print(f"Total districts: {total_districts}")
    print(f"Average population per city: {total_pop / len(cities):.0f}")