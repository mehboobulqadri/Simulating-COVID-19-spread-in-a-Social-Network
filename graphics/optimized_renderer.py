import pygame
import pygame.gfxdraw
import numpy as np
from entities.person import State
from entities.building import BuildingType, Building

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

        # Stats (will be computed when cities are set)
        self.total_agents = 0
        self.total_commuters = 0


    def set_cities(self, cities):
        """Set cities and recompute commuter stats"""
        self.cities = cities
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
        # Create circle surfaces for people
        states = {
            State.SUSCEPTIBLE: (100, 200, 255),
            State.EXPOSED: (255, 255, 100),
            State.INFECTIOUS: (255, 50, 50),
            State.RECOVERED: (50, 200, 50),
            State.DECEASED: (50, 50, 50),
            State.VACCINATED: (200, 100, 255)
        }
        
        # Store state colors for legend rendering
        self.state_colors = states
        
        # Building type colors and symbols
        self.building_colors = {
            BuildingType.RESIDENTIAL: (100, 200, 100),
            BuildingType.WORKPLACE: (100, 100, 200),
            BuildingType.HOSPITAL: (255, 255, 255),
            BuildingType.COMMERCIAL: (240, 180, 60),
            BuildingType.SCHOOL: (220, 120, 120),
            BuildingType.PARK: (50, 160, 80)
        }
        
        self.building_symbols = {
            BuildingType.RESIDENTIAL: '□',
            BuildingType.WORKPLACE: '▲',
            BuildingType.HOSPITAL: '✚',
            BuildingType.COMMERCIAL: '$',
            BuildingType.SCHOOL: '◆',
            BuildingType.PARK: '♣'
        }
        
        # Trace highlight surface
        trace = pygame.Surface((14, 14), pygame.SRCALPHA)
        pygame.draw.circle(trace, (0, 240, 255), (7, 7), 6)
        pygame.draw.circle(trace, (0, 120, 150), (7, 7), 6, 2)
        self.trace_surf = trace
        
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
        
        # Create white surface for asymptomatic carriers
        asymptomatic = pygame.Surface((8, 8), pygame.SRCALPHA)
        pygame.draw.circle(asymptomatic, (255, 255, 255), (4, 4), 3)
        self.person_surfs['asymptomatic'] = asymptomatic

        # Variant outline overlays (drawn under infectious agents)
        self.variant_colors = {
            "base": (255, 140, 80),
            "high-transmission": (255, 90, 190),
            "high-mortality": (200, 70, 70),
        }
        self.variant_outline_surfs = {}
        for name, color in self.variant_colors.items():
            s = pygame.Surface((18, 18), pygame.SRCALPHA)
            pygame.draw.circle(s, (*color, 120), (9, 9), 8, 2)
            self.variant_outline_surfs[name] = s

    def set_world_data(self, cities):
        self.cities = cities

    def render(self, min_detail=False):
        # Clear screen
        self.screen.fill((20, 20, 25)) # Darker background
        
        zoom = self.camera.zoom
        
        # Draw Grid (skip when minimizing detail)
        if not min_detail:
            self._render_grid()
        
        # Draw Cities
        for city in self.cities:
            # Draw City Grid Roads
            if hasattr(city, 'roads'):
                for road in city.roads:
                    start = self.camera.apply(*road.start)
                    end = self.camera.apply(*road.end)
                    width = max(1, int(road.width * zoom))
                    pygame.draw.line(self.screen, (40, 40, 45), start, end, width)
            
            # Draw Inter-City Highways with dashed pattern
            if hasattr(city, 'highways'):
                for road in city.highways:
                    start = self.camera.apply(*road.start)
                    end = self.camera.apply(*road.end)
                    width = max(2, int(road.width * zoom))
                    self._draw_dashed_line(start, end, (120, 120, 70), width, dash_length=8)

            # Draw Districts
            for district in city.districts:
                # Convert district bounds to screen rect
                screen_rect = self._world_to_screen_rect(district.bounds)
                
                # Cull if off-screen
                if not self.screen.get_rect().colliderect(screen_rect):
                    continue
                
                # Draw District Floor
                pygame.draw.rect(self.screen, (30, 30, 35), screen_rect)
                
                # Quarantine glow for quarantined districts
                if hasattr(district, 'is_quarantined') and district.is_quarantined:
                    # Yellow glow overlay
                    glow_surf = pygame.Surface(screen_rect.size, pygame.SRCALPHA)
                    glow_surf.fill((255, 200, 0, 60))  # Yellow with transparency
                    self.screen.blit(glow_surf, screen_rect.topleft)
                    # Yellow border
                    pygame.draw.rect(self.screen, (255, 200, 0), screen_rect, 3)
                
                # Highlight if hovered
                if self.interaction and self.interaction.hovered_entity == district:
                    pygame.draw.rect(self.screen, (60, 60, 80), screen_rect, 2)
                else:
                    pygame.draw.rect(self.screen, (40, 40, 50), screen_rect, 1)
                
                # Draw Buildings
                if zoom > 0.5 and not min_detail:
                    for b in district.buildings:
                        b_rect = self._world_to_screen_rect(b.bounds)
                        color = b.color
                        pygame.draw.rect(self.screen, color, b_rect)
                        # Roof detail with darker shade
                        pygame.draw.rect(self.screen, (int(color[0]*0.7), int(color[1]*0.7), int(color[2]*0.7)), b_rect.inflate(-4, -4))
                        
                        # Quarantine glow for quarantined buildings
                        if hasattr(b, 'is_quarantined') and b.is_quarantined:
                            # Yellow border for quarantined building
                            pygame.draw.rect(self.screen, (255, 200, 0), b_rect, 2)
                        
                        # Draw building type symbol/label if building is large enough
                        if b_rect.width > 20 and b_rect.height > 20:
                            symbol = self.building_symbols.get(b.type, '□')
                            sym_font = pygame.font.SysFont("Arial", 10, bold=True)
                            sym_surf = sym_font.render(symbol, True, (255, 255, 255))
                            sym_rect = sym_surf.get_rect(center=(int(b_rect.centerx), int(b_rect.centery)))
                            self.screen.blit(sym_surf, sym_rect)
                
                # Draw People (visible at lower zoom levels now)
                if zoom > 0.3:  # Changed from 0.8 to 0.3 for better visibility when zoomed out
                    # Optimization: Batch blits
                    blits = []
                    
                    for p in district.people:
                        px, py = self.camera.apply(p.x, p.y)

                        # Variant outline (drawn under the agent) for infectious cases
                        if p.state == State.INFECTIOUS:
                            variant_name = getattr(p, 'variant', 'base')
                            outline = self.variant_outline_surfs.get(variant_name)
                            if outline:
                                blits.append((outline, (px - 9, py - 9)))
                        
                        if self.interaction and getattr(self.interaction, 'tracing_enabled', True) and getattr(self.interaction, 'selected_entity', None) is p:
                            blits.append((self.trace_surf, (px - 7, py - 7)))
                        
                        # Asymptomatic carriers appear as white (distinct from healthy)
                        if hasattr(p, 'is_asymptomatic') and p.is_asymptomatic and p.state == State.INFECTIOUS:
                            surf = self.person_surfs['asymptomatic']
                            offset = 4
                        # Check vaccination status first (takes priority over base state)
                        elif hasattr(p, 'is_vaccinated') and p.is_vaccinated:
                            surf = self.person_surfs[State.VACCINATED]
                            offset = 4
                        elif p.state == State.INFECTIOUS:
                            surf = self.person_surfs['glow']
                            offset = 8
                        else:
                            surf = self.person_surfs[p.state]
                            offset = 4
                            
                        blits.append((surf, (px - offset, py - offset)))
                    
                    self.screen.blits(blits)

        # Draw trace polyline for selected person
        if self.interaction and getattr(self.interaction, 'tracing_enabled', False):
            pts = getattr(self.interaction, 'trace_points', [])
            if pts and len(pts) > 1:
                screen_pts = [self.camera.apply(px, py) for px, py in pts]
                pygame.draw.lines(self.screen, (0, 240, 255), False, screen_pts, 2)

        # Render Visual Effects (skip at minimal detail)
        if self.visual_effects and not min_detail:
            self.visual_effects.render(self.screen, self.camera)
        
        # Render Legend (skip at minimal detail) - REMOVED (Moved to RightStatsPanel)
        # if not min_detail:
        #     self._render_legend()
        
        # Render HUD (always render; shows FPS) - REMOVED (Moved to RightStatsPanel)
        # self._render_hud()
            
        # Render Hover Info (skip at minimal detail)
        if self.interaction and not min_detail:
            self._render_hover_info()

        # Render selection box overlay if active
        if self.interaction and getattr(self.interaction, 'box_select_active', False):
            if self.interaction.box_start and self.interaction.box_end:
                x1, y1 = self.interaction.box_start
                x2, y2 = self.interaction.box_end
                rect = pygame.Rect(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
                overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                overlay.fill((0, 200, 255, 60))
                self.screen.blit(overlay, rect.topleft)
                pygame.draw.rect(self.screen, (0, 240, 255), rect, 2)

    def _draw_dashed_line(self, start, end, color, width, dash_length=8):
        """Draw a dashed line from start to end."""
        x1, y1 = start
        x2, y2 = end
        dx = x2 - x1
        dy = y2 - y1
        distance = (dx**2 + dy**2)**0.5
        
        if distance == 0:
            return
        
        # Normalize direction
        dx /= distance
        dy /= distance
        
        # Draw dashes
        current_pos = 0
        while current_pos < distance:
            dash_end = min(current_pos + dash_length, distance)
            line_start = (x1 + dx * current_pos, y1 + dy * current_pos)
            line_end = (x1 + dx * dash_end, y1 + dy * dash_end)
            pygame.draw.line(self.screen, color, line_start, line_end, width)
            current_pos += dash_length * 2  # Skip equal length gap

    def _render_legend(self):
        pass
        # """Draw state legend in top-left corner"""
        # legend_x = 15
        # legend_y = 15
        # box_w = 160
        # row_h = 24
        # padding = 10
        
        # legend_items = [
        #     (State.SUSCEPTIBLE, "Healthy"),
        #     (State.EXPOSED, "Exposed"),
        #     (State.INFECTIOUS, "Infected"),
        #     (State.RECOVERED, "Recovered"),
        #     (State.VACCINATED, "Vaccinated")
        # ]
        
        # box_h = len(legend_items) * row_h + padding * 2
        
        # # Background with semi-transparency
        # bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        # bg.fill((0, 0, 0, 180))
        # self.screen.blit(bg, (legend_x, legend_y))
        
        # # Border
        # pygame.draw.rect(self.screen, (100, 120, 140), (legend_x, legend_y, box_w, box_h), 2)
        
        # # Draw each state with its color
        # for i, (state, label) in enumerate(legend_items):
        #     y = legend_y + padding + i * row_h
        #     color = self.state_colors[state]
        #     
        #     # Color square
        #     pygame.draw.rect(self.screen, color, (legend_x + padding, y + 4, 12, 12))
        #     pygame.draw.rect(self.screen, (200, 200, 200), (legend_x + padding, y + 4, 12, 12), 1)
        #     
        #     # Label text
        #     text = self.font.render(label, True, (220, 220, 220))
        #     self.screen.blit(text, (legend_x + padding + 18, y + 3))

    def _render_hud(self):
        pass
        # """Draw HUD with FPS, agents, commuters, and infection counts"""
        # hud_x = self.screen.get_width() - 200
        # hud_y = 15
        # hud_w = 185
        # hud_h = 105
        
        # hud_bg = pygame.Surface((hud_w, hud_h), pygame.SRCALPHA)
        # hud_bg.fill((0, 0, 0, 180))
        # self.screen.blit(hud_bg, (hud_x, hud_y))
        # pygame.draw.rect(self.screen, (100, 180, 200), (hud_x, hud_y, hud_w, hud_h), 2)

        # self.fps = self.fps_clock.get_fps()
        # fps_color = (100, 200, 100) if self.fps > 45 else (255, 200, 100) if self.fps > 30 else (255, 100, 100)
        # fps_text = self.font_small.render(f"FPS: {self.fps:.1f}", True, fps_color)
        # self.screen.blit(fps_text, (hud_x + 15, hud_y + 10))

        # agents_text = self.font_small.render(f"Agents: {self.total_agents}", True, (200, 200, 200))
        # commuters_text = self.font_small.render(f"Commuters: {self.total_commuters}", True, (180, 200, 255))

        # exposed = 0
        # infectious = 0
        # for city in self.cities:
        #     for district in city.districts:
        #         for p in district.people:
        #             if p.state == State.EXPOSED:
        #                 exposed += 1
        #             elif p.state == State.INFECTIOUS:
        #                 infectious += 1

        # exposed_text = self.font_small.render(f"Exposed: {exposed}", True, (255, 200, 120))
        # infectious_text = self.font_small.render(f"Infectious: {infectious}", True, (255, 120, 120))

        # self.screen.blit(agents_text, (hud_x + 15, hud_y + 28))
        # self.screen.blit(commuters_text, (hud_x + 15, hud_y + 44))
        # self.screen.blit(exposed_text, (hud_x + 15, hud_y + 60))
        # self.screen.blit(infectious_text, (hud_x + 15, hud_y + 76))

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
