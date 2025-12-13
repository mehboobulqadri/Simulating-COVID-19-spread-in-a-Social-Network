import pygame
import pygame.gfxdraw
import numpy as np
from entities.person import State
from entities.building import BuildingType

class OptimizedRenderer:
    def __init__(self, screen, camera):
        self.screen = screen
        self.camera = camera
        self.cities = []
        
        # Pre-render assets
        self.assets = {}
        self._create_assets()
        
        # Compatibility
        self.visual_effects = None
        self.interaction = None
        self.time_engine = None
        
        self.font = pygame.font.SysFont("Arial", 14)

    def _create_assets(self):
        # Create circle surfaces for people
        states = {
            State.SUSCEPTIBLE: (100, 200, 255),
            State.EXPOSED: (255, 255, 100),
            State.INFECTIOUS: (255, 50, 50),
            State.RECOVERED: (50, 200, 50),
            State.DECEASED: (50, 50, 50),
            State.VACCINATED: (200, 100, 255)
        }
        
        self.person_surfs = {}
        for state, color in states.items():
            # Create a small circle surface
            s = pygame.Surface((8, 8), pygame.SRCALPHA)
            pygame.draw.circle(s, color, (4, 4), 3)
            self.person_surfs[state] = s
            
            # Create a glow surface for infectious
            if state == State.INFECTIOUS:
                g = pygame.Surface((16, 16), pygame.SRCALPHA)
                # Outer glow
                pygame.draw.circle(g, (255, 50, 50, 100), (8, 8), 8)
                # Inner core
                pygame.draw.circle(g, (255, 200, 200), (8, 8), 3)
                self.person_surfs['glow'] = g

    def set_world_data(self, cities):
        self.cities = cities

    def render(self):
        # Clear screen
        self.screen.fill((20, 20, 25)) # Darker background
        
        zoom = self.camera.zoom
        
        # Draw Grid
        self._render_grid()
        
        # Draw Cities
        for city in self.cities:
            # Draw Roads
            if hasattr(city, 'roads'):
                for road in city.roads:
                    start = self.camera.apply(*road.start)
                    end = self.camera.apply(*road.end)
                    width = max(1, int(road.width * zoom))
                    pygame.draw.line(self.screen, (40, 40, 45), start, end, width)

            # Draw Districts
            for district in city.districts:
                # Convert district bounds to screen rect
                screen_rect = self._world_to_screen_rect(district.bounds)
                
                # Cull if off-screen
                if not self.screen.get_rect().colliderect(screen_rect):
                    continue
                
                # Draw District Floor
                pygame.draw.rect(self.screen, (30, 30, 35), screen_rect)
                
                # Highlight if hovered
                if self.interaction and self.interaction.hovered_entity == district:
                    pygame.draw.rect(self.screen, (60, 60, 80), screen_rect, 2)
                else:
                    pygame.draw.rect(self.screen, (40, 40, 50), screen_rect, 1)
                
                # Draw Buildings
                if zoom > 0.5:
                    for b in district.buildings:
                        b_rect = self._world_to_screen_rect(b.bounds)
                        color = b.color
                        pygame.draw.rect(self.screen, color, b_rect)
                        # Roof detail
                        pygame.draw.rect(self.screen, (color[0]*0.8, color[1]*0.8, color[2]*0.8), b_rect.inflate(-4, -4))
                
                # Draw People
                if zoom > 0.8:
                    # Optimization: Batch blits
                    blits = []
                    
                    for p in district.people:
                        px, py = self.camera.apply(p.x, p.y)
                        
                        if p.state == State.INFECTIOUS:
                            surf = self.person_surfs['glow']
                            offset = 8
                        else:
                            surf = self.person_surfs[p.state]
                            offset = 4
                            
                        blits.append((surf, (px - offset, py - offset)))
                    
                    self.screen.blits(blits)

        # Render Visual Effects
        if self.visual_effects:
            self.visual_effects.render(self.screen, self.camera)
            
        # Render Hover Info
        if self.interaction:
            self._render_hover_info()

    def _render_hover_info(self):
        info = self.interaction.get_hover_info()
        if info:
            mx, my = pygame.mouse.get_pos()
            
            # Background box
            box_w = 200
            box_h = len(info) * 20 + 15
            
            # Ensure box stays on screen
            if mx + box_w > self.screen.get_width():
                mx -= box_w
            if my + box_h > self.screen.get_height():
                my -= box_h
                
            # Draw shadow
            s = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
            s.fill((0, 0, 0, 180))
            self.screen.blit(s, (mx + 15, my + 15))
            
            # Draw border
            pygame.draw.rect(self.screen, (100, 100, 120), (mx + 15, my + 15, box_w, box_h), 1)
            
            for i, line in enumerate(info):
                text = self.font.render(line, True, (220, 220, 220))
                self.screen.blit(text, (mx + 25, my + 20 + i * 20))

    def render_overlay(self, surface):
        # Just blit the UI surface on top
        self.screen.blit(surface, (0, 0))

    def _render_grid(self):
        # Simple grid
        w, h = self.screen.get_size()
        grid_sz = int(100 * self.camera.zoom)
        if grid_sz < 20: return # Too dense
        
        offset_x = int(self.camera.x * self.camera.zoom) % grid_sz
        offset_y = int(self.camera.y * self.camera.zoom) % grid_sz
        
        for x in range(-offset_x, w, grid_sz):
            pygame.draw.line(self.screen, (50, 50, 60), (x, 0), (x, h))
        for y in range(-offset_y, h, grid_sz):
            pygame.draw.line(self.screen, (50, 50, 60), (0, y), (w, y))

    def _world_to_screen_rect(self, rect):
        x, y = self.camera.apply(rect.x, rect.y)
        w = int(rect.width * self.camera.zoom)
        h = int(rect.height * self.camera.zoom)
        return pygame.Rect(x, y, w, h)
