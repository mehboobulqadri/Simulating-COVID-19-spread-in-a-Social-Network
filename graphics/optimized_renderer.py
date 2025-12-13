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
        self.font_large = pygame.font.SysFont("Arial", 18, bold=True)
        self.font_small = pygame.font.SysFont("Arial", 12)
        
        # FPS tracking
        self.fps_clock = pygame.time.Clock()
        self.fps = 0.0

        # Compute commuter stats (agents whose work city != home city)
        self.total_agents = 0
        self.total_commuters = 0
        for city in self.cities:
            for district in city.districts:
                for p in district.people:
                    self.total_agents += 1
                    home_id = getattr(p, 'home_city_id', None)
                    work_id = getattr(p, 'work_city_id', None)
                    if home_id is not None and work_id is not None and work_id != home_id:
                        self.total_commuters += 1

    def _create_assets(self):
        # Create circle surfaces for people and define state colors
        states = {
            State.SUSCEPTIBLE: (100, 200, 255),
            State.EXPOSED: (255, 200, 100),
            State.INFECTIOUS: (255, 80, 80),
            State.RECOVERED: (120, 200, 120),
            State.DECEASED: (50, 50, 50),
            State.VACCINATED: (200, 100, 255)
        }

        # Store state colors for legend rendering
        self.state_colors = states

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
        
        # Render Legend
        self._render_legend()
        
        # Render HUD (Time, FPS, Agent Count, Infection Rate)
        self._render_hud()
            
        # Render Hover Info
        if self.interaction:
            self._render_hover_info()

    def _render_legend(self):
        """Draw state legend in top-left corner"""
        legend_x = 15
        legend_y = 15
        box_w = 160
        row_h = 24
        padding = 10
        
        legend_items = [
            (State.SUSCEPTIBLE, "Healthy"),
            (State.EXPOSED, "Exposed"),
            (State.INFECTIOUS, "Infected"),
            (State.RECOVERED, "Recovered"),
            (State.VACCINATED, "Vaccinated")
        ]
        
        box_h = len(legend_items) * row_h + padding * 2
        
        # Background with semi-transparency
        bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 180))
        self.screen.blit(bg, (legend_x, legend_y))
        
        # Border
        pygame.draw.rect(self.screen, (100, 120, 140), (legend_x, legend_y, box_w, box_h), 2)
        
        # Draw each state with its color
        for i, (state, label) in enumerate(legend_items):
            y = legend_y + padding + i * row_h
            color = self.state_colors[state]
            
            # Color square
            pygame.draw.rect(self.screen, color, (legend_x + padding, y + 4, 12, 12))
            pygame.draw.rect(self.screen, (200, 200, 200), (legend_x + padding, y + 4, 12, 12), 1)
            
            # Label text
            text = self.font.render(label, True, (220, 220, 220))
            self.screen.blit(text, (legend_x + padding + 18, y + 3))

    def _render_hud(self):
        """Draw HUD with FPS and agent count only"""
        # Calculate total agents
        total_agents = 0
        for city in self.cities:
            for district in city.districts:
                total_agents += len(district.people)
        
        # Top-right HUD panel (compact)
        hud_x = self.screen.get_width() - 200
        hud_y = 15
        hud_w = 185
        hud_h = 70
        
        # Background
        hud_bg = pygame.Surface((hud_w, hud_h), pygame.SRCALPHA)
        hud_bg.fill((0, 0, 0, 180))
        self.screen.blit(hud_bg, (hud_x, hud_y))
        
        # Border
        pygame.draw.rect(self.screen, (100, 180, 200), (hud_x, hud_y, hud_w, hud_h), 2)
        
        # FPS
        self.fps = self.fps_clock.get_fps()
        fps_color = (100, 200, 100) if self.fps > 45 else (255, 200, 100) if self.fps > 30 else (255, 100, 100)
        fps_text = self.font_small.render(f"FPS: {self.fps:.1f}", True, fps_color)
        self.screen.blit(fps_text, (hud_x + 15, hud_y + 10))
        
        # Total Agents
        agents_text = self.font_small.render(f"Agents: {total_agents}", True, (200, 200, 200))
        self.screen.blit(agents_text, (hud_x + 15, hud_y + 28))

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
