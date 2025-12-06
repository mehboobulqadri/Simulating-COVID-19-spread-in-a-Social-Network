import pygame

class Interaction:
    def __init__(self, camera):
        self.camera = camera
        self.hovered_entity = None
        self.selected_entity = None
        
    def handle_input(self, cities):
        mouse_pos = pygame.mouse.get_pos()
        
        # Convert screen pos to world pos
        # Inverse of camera.apply:
        # screen_x = (x - self.x) * self.zoom + self.width / 2
        # x = (screen_x - self.width / 2) / self.zoom + self.x
        
        wx = (mouse_pos[0] - self.camera.width / 2) / self.camera.zoom + self.camera.x
        wy = (mouse_pos[1] - self.camera.height / 2) / self.camera.zoom + self.camera.y
        
        self.hovered_entity = self._find_entity_at(wx, wy, cities)
        
    def _find_entity_at(self, x, y, cities):
        # Check based on zoom level
        zoom = self.camera.zoom
        
        if zoom < 0.5:
            # Check Cities
            for city in cities:
                dist_sq = (city.location[0] - x)**2 + (city.location[1] - y)**2
                if dist_sq < 20**2: # 20 is radius
                    return city
        else:
            # Check Districts and People
            for city in cities:
                for district in city.districts:
                    if district.bounds.collidepoint(x, y):
                        if zoom > 2.0:
                            # Check People (QuadTree query would be better here)
                            # Simple linear check for now as optimization requires passing quadtree
                            # But we can use the district's quadtree if we had access to it easily
                            # Let's just iterate people in district for now (MVP)
                            for person in district.people:
                                dist_sq = (person.x - x)**2 + (person.y - y)**2
                                if dist_sq < 5**2: # 5 is radius
                                    return person
                        return district
        return None

    def get_hover_info(self):
        if not self.hovered_entity:
            return None
            
        info = []
        ent = self.hovered_entity
        
        # Determine type by checking attributes
        if hasattr(ent, 'districts'): # City
            info.append(f"City: {ent.name}")
            info.append(f"Districts: {len(ent.districts)}")
            pop = sum(len(d.people) for d in ent.districts)
            info.append(f"Population: {pop}")
            
        elif hasattr(ent, 'people'): # District
            info.append(f"District: {ent.name}")
            info.append(f"Population: {len(ent.people)}")
            infected = sum(1 for p in ent.people if p.state.name == 'INFECTIOUS')
            info.append(f"Infected: {infected}")
            
        elif hasattr(ent, 'state'): # Person
            info.append(f"Person: {ent.uid}")
            info.append(f"State: {ent.state.name}")
            info.append(f"Age: {ent.age}")
            if ent.work_location:
                info.append("Has Job")
            
        return info
