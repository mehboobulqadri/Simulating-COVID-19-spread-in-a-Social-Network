import pygame
from entities.person import State
from entities.building import BuildingType
from graphics.textures import TextureManager

class Renderer:
    def __init__(self, screen, camera):
        self.screen = screen
        self.camera = camera
        self.cities = []
        self.texture_manager = TextureManager()
        self.visual_effects = None # Will be set by main
        self.interaction = None # Will be set by main
        self.time_engine = None # Will be set by main
        
        # Colors
        self.colors = {
            State.SUSCEPTIBLE: (100, 200, 255), # Light Blue
            State.EXPOSED: (255, 255, 100),     # Yellow
            State.INFECTIOUS: (255, 50, 50),    # Red
            State.RECOVERED: (50, 200, 50),     # Green
            State.DECEASED: (50, 50, 50),       # Dark Grey
            State.VACCINATED: (200, 100, 255)   # Purple
        }
        
        self.font = pygame.font.SysFont("Arial", 14)

    def set_world_data(self, cities):
        self.cities = cities

    def render(self):
        # Draw Grid (Optional, maybe toggleable later)
        self._render_grid()
        
        # Render Entities based on Zoom Level
        zoom = self.camera.zoom
        
        for city in self.cities:
            if zoom < 0.5:
                self._render_city_macro(city)
            else:
                # Draw connections (roads) first so they are under districts
                self._render_connections(city, zoom)
                
                for district in city.districts:
                    self._render_district(district, zoom)
                    
        # Render Visual Effects
        if self.visual_effects:
            self.visual_effects.render(self.screen, self.camera)
            
        # Render Lighting Overlay
        if self.time_engine:
            self._render_lighting()
            
        # Render Hover Info
        if self.interaction:
            self._render_hover_info()

    def _render_lighting(self):
        hour = self.time_engine.hour
        alpha = 0
        
        # Night cycle: 20:00 (8 PM) to 06:00 (6 AM)
        if hour >= 20 or hour < 6:
            if hour >= 20:
                # Fade in 20:00 - 22:00
                if hour < 22:
                    alpha = int(150 * ((hour - 20) / 2))
                else:
                    alpha = 150 # Max darkness
            else:
                # Fade out 04:00 - 06:00
                if hour < 4:
                    alpha = 150
                else:
                    alpha = int(150 * (1 - (hour - 4) / 2))
        
        if alpha > 0:
            s = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
            s.fill((0, 0, 20, alpha)) # Dark blue tint
            self.screen.blit(s, (0, 0))

    def _render_grid(self):
        grid_size = 500
        cols = 10
        rows = 10
        for i in range(cols + 1):
            start = self.camera.apply(i * grid_size, 0)
            end = self.camera.apply(i * grid_size, rows * grid_size)
            pygame.draw.line(self.screen, (40, 40, 40), start, end)
        for i in range(rows + 1):
            start = self.camera.apply(0, i * grid_size)
            end = self.camera.apply(cols * grid_size, i * grid_size)
            pygame.draw.line(self.screen, (40, 40, 40), start, end)

    def _render_connections(self, city, zoom):
        # Draw lines between connected districts
        for district in city.districts:
            start = self.camera.apply(district.bounds.centerx, district.bounds.centery)
            for neighbor, weight in district.neighbors:
                end = self.camera.apply(neighbor.bounds.centerx, neighbor.bounds.centery)
                pygame.draw.line(self.screen, (80, 80, 80), start, end, max(1, int(2 * zoom)))

    def _render_city_macro(self, city):
        cx, cy = self.camera.apply(*city.location)
        
        # Use Texture
        tex = self.texture_manager.get_texture('city_icon')
        if tex:
            # Scale texture based on zoom
            size = int(60 * self.camera.zoom)
            if size > 5:
                scaled_tex = pygame.transform.scale(tex, (size, size))
                self.screen.blit(scaled_tex, (cx - size//2, cy - size//2))
            else:
                pygame.draw.circle(self.screen, (150, 150, 150), (cx, cy), 20 * self.camera.zoom)
        else:
            pygame.draw.circle(self.screen, (150, 150, 150), (cx, cy), 20 * self.camera.zoom)
            
        # Label
        if self.camera.zoom > 0.2:
            text = self.font.render(city.name, True, (200, 200, 200))
            self.screen.blit(text, (cx + 10, cy + 10))

    def _render_district(self, district, zoom):
        # Draw district bounds
        rect = district.bounds
        screen_rect = pygame.Rect(*self.camera.apply(rect.x, rect.y), rect.width * zoom, rect.height * zoom)
        
        # Render Ground Texture (Tiled)
        tex = self.texture_manager.get_texture('ground_grass')
        if tex and zoom > 0.5:
            # Create a surface for the district
            d_surf = pygame.Surface((screen_rect.width, screen_rect.height))
            
            # Scale texture based on zoom (optional, but keeps detail consistent)
            # Actually, let's keep texture scale constant relative to world, so it zooms with camera
            tex_size = int(100 * zoom)
            if tex_size > 0:
                scaled_tex = pygame.transform.scale(tex, (tex_size, tex_size))
                
                for y in range(0, screen_rect.height, tex_size):
                    for x in range(0, screen_rect.width, tex_size):
                        d_surf.blit(scaled_tex, (x, y))
                
                self.screen.blit(d_surf, (screen_rect.x, screen_rect.y))
        else:
            # Fallback fill
            fill_color = (60, 60, 80, 100)
            s = pygame.Surface((screen_rect.width, screen_rect.height), pygame.SRCALPHA)
            s.fill(fill_color)
            self.screen.blit(s, (screen_rect.x, screen_rect.y))

        # Highlight if hovered
        border_color = (80, 80, 100)
        width = 1
        if self.interaction and self.interaction.hovered_entity == district:
            border_color = (200, 200, 200)
            width = 2
            
        pygame.draw.rect(self.screen, border_color, screen_rect, width)
        
        # Draw District Name if zoomed enough
        if zoom > 0.8:
            text = self.font.render(district.name, True, (200, 200, 200))
            # Add shadow
            shadow = self.font.render(district.name, True, (0, 0, 0))
            self.screen.blit(shadow, (screen_rect.x + 6, screen_rect.y + 6))
            self.screen.blit(text, (screen_rect.x + 5, screen_rect.y + 5))
        
        if zoom > 1.5:
            # Render Buildings
            for building in district.buildings:
                self._render_building(building, zoom)

            # Render People
            for person in district.people:
                px, py = self.camera.apply(person.x, person.y)
                
                # Use Glow Texture
                glow = self.texture_manager.get_texture('person_glow')
                if glow:
                    # Tint the glow based on state
                    color = self.colors.get(person.state, (255, 255, 255))
                    tinted_glow = glow.copy()
                    tinted_glow.fill(color, special_flags=pygame.BLEND_RGBA_MULT)
                    
                    # Scale
                    size = int(20 * zoom)
                    if size > 0:
                        scaled_glow = pygame.transform.scale(tinted_glow, (size, size))
                        self.screen.blit(scaled_glow, (px - size//2, py - size//2))
                else:
                    color = self.colors.get(person.state, (255, 255, 255))
                    pygame.draw.circle(self.screen, color, (px, py), 2 * zoom)

    def _render_building(self, building, zoom):
        rect = building.bounds
        screen_rect = pygame.Rect(*self.camera.apply(rect.x, rect.y), rect.width * zoom, rect.height * zoom)
        
        tex_name = 'building_residential'
        if building.type == BuildingType.WORKPLACE:
            tex_name = 'building_workplace'
        elif building.type == BuildingType.HOSPITAL:
            tex_name = 'building_hospital'
            
        tex = self.texture_manager.get_texture(tex_name)
        if tex:
            scaled_tex = pygame.transform.scale(tex, (screen_rect.width, screen_rect.height))
            self.screen.blit(scaled_tex, screen_rect)
        else:
            color = building.color
            pygame.draw.rect(self.screen, color, screen_rect)
            pygame.draw.rect(self.screen, (50, 50, 50), screen_rect, 1)

    def _render_hover_info(self):
        info = self.interaction.get_hover_info()
        if info:
            mx, my = pygame.mouse.get_pos()
            
            # Background box
            box_w = 150
            box_h = len(info) * 20 + 10
            
            # Ensure box stays on screen
            if mx + box_w > self.screen.get_width():
                mx -= box_w
            if my + box_h > self.screen.get_height():
                my -= box_h
                
            pygame.draw.rect(self.screen, (20, 20, 20, 230), (mx + 10, my + 10, box_w, box_h))
            pygame.draw.rect(self.screen, (100, 100, 100), (mx + 10, my + 10, box_w, box_h), 1)
            
            for i, line in enumerate(info):
                text = self.font.render(line, True, (255, 255, 255))
                self.screen.blit(text, (mx + 15, my + 15 + i * 20))
