import pygame
from ui.theme import UITheme
from entities.person import State

class Minimap:
    def __init__(self, screen_width, screen_height, world_width=2000, world_height=2000):
        self.size = 200
        self.x = screen_width - self.size - 10
        self.y = screen_height - self.size - 10
        self.rect = pygame.Rect(self.x, self.y, self.size, self.size)
        
        self.world_width = world_width
        self.world_height = world_height
        self.world_origin = (0, 0)
        self._update_scale()
        
        self.dragging = False

    def set_world_bounds(self, min_x, min_y, max_x, max_y):
        self.world_origin = (min_x, min_y)
        self.world_width = max(1, max_x - min_x)
        self.world_height = max(1, max_y - min_y)
        self._update_scale()

    def _update_scale(self):
        self.scale_x = self.size / self.world_width
        self.scale_y = self.size / self.world_height

    def handle_event(self, event, camera):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.dragging = True
                self._move_camera_to_click(event.pos, camera)
                return True
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self._move_camera_to_click(event.pos, camera)
                return True
        return False

    def _move_camera_to_click(self, pos, camera):
        # Convert screen pos to minimap local
        mx = pos[0] - self.x
        my = pos[1] - self.y
        
        # Clamp
        mx = max(0, min(self.size, mx))
        my = max(0, min(self.size, my))
        
        # Convert to world coordinates
        wx = mx / self.scale_x
        wy = my / self.scale_y
        ox, oy = self.world_origin
        wx += ox
        wy += oy
        
        # Set camera center
        camera.x = wx
        camera.y = wy

    def render(self, screen, cities, camera, trace_points=None, simulation_engine=None):
        # Background
        UITheme.draw_panel_bg(screen, self.rect)
        
        # Title
        font = UITheme.get_font(12, bold=True)
        title = font.render("Minimap", True, (200, 200, 200))
        screen.blit(title, (self.x + 5, self.y - 20))
        
        # Draw Cities/Districts
        ox, oy = self.world_origin
        for city in cities:
            # City Dot
            cx = self.x + (city.location[0] - ox) * self.scale_x
            cy = self.y + (city.location[1] - oy) * self.scale_y
            pygame.draw.circle(screen, (200, 200, 200), (cx, cy), 4)
            pygame.draw.circle(screen, (100, 100, 100), (cx, cy), 4, 1)
            
            for district in city.districts:
                r = district.bounds
                dx = self.x + (r.x - ox) * self.scale_x
                dy = self.y + (r.y - oy) * self.scale_y
                dw = r.width * self.scale_x
                dh = r.height * self.scale_y
                
                # Count all infection states from simulation engine (actual current state)
                total_pop = len(district.people)
                exposed = 0
                infectious = 0
                
                if simulation_engine:
                    # Use actual simulation state
                    for p in district.people:
                        idx = simulation_engine.person_to_index.get(p)
                        if idx is not None:
                            state_val = simulation_engine.state[idx]
                            if state_val == 1:  # EXPOSED
                                exposed += 1
                            elif state_val == 2:  # INFECTIOUS
                                infectious += 1
                else:
                    # Fallback to person objects (might be stale)
                    exposed = sum(1 for p in district.people if p.state.name == 'EXPOSED')
                    infectious = sum(1 for p in district.people if p.state.name == 'INFECTIOUS')
                
                # Calculate infection ratio
                infection_ratio = (exposed + infectious) / total_pop if total_pop > 0 else 0
                
                # Direct color mapping based on infection severity
                if infection_ratio < 0.05:
                    # Clean (< 5%): dark grey
                    color = (60, 65, 70)
                elif infection_ratio < 0.15:
                    # Light spread (5-15%): grey-yellow
                    t = (infection_ratio - 0.05) / 0.10
                    color = (int(60 + 140 * t), int(65 + 150 * t), int(70 - 20 * t))
                elif infection_ratio < 0.35:
                    # Medium spread (15-35%): yellow-orange
                    t = (infection_ratio - 0.15) / 0.20
                    color = (int(200 + 40 * t), int(215 - 100 * t), int(50 - 30 * t))
                elif infection_ratio < 0.60:
                    # High spread (35-60%): orange-red
                    t = (infection_ratio - 0.35) / 0.25
                    color = (int(240 + 15 * t), int(115 - 85 * t), int(20 - 10 * t))
                else:
                    # Critical (>60%): deep red
                    color = (255, 30, 10)
                
                pygame.draw.rect(screen, color, (dx, dy, dw, dh))
                
                # Draw border based on infection level
                if infection_ratio > 0.35:
                    border_color = (255, 20, 20)  # Red for high
                    pygame.draw.rect(screen, border_color, (dx, dy, dw, dh), 2)
                elif infection_ratio > 0.15:
                    border_color = (255, 140, 30)  # Orange for medium
                    pygame.draw.rect(screen, border_color, (dx, dy, dw, dh), 1)
                elif infection_ratio > 0.05:
                    border_color = (255, 220, 80)  # Yellow for low
                    pygame.draw.rect(screen, border_color, (dx, dy, dw, dh), 1)
        if trace_points and len(trace_points) > 1:
            pts = []
            for pair in trace_points:
                try:
                    wx, wy = pair
                    # Validate coordinates are numbers
                    if wx is None or wy is None:
                        continue
                    wx, wy = float(wx), float(wy)
                    mx = self.x + (wx - ox) * self.scale_x
                    my = self.y + (wy - oy) * self.scale_y
                    # Ensure mx, my are floats/ints, not numpy scalars
                    mx, my = float(mx), float(my)
                    pts.append((mx, my))
                except (TypeError, ValueError, AttributeError):
                    continue
            # Only draw if we have valid points
            if len(pts) > 1:
                try:
                    pygame.draw.lines(screen, (0, 240, 255), False, pts, 2)
                except (TypeError, ValueError):
                    # Silently skip on any remaining issues
                    pass
                
        # Draw Camera Viewport
        # Camera x,y is center.
        # Top-left of viewport in world coords:
        # vx_world = camera.x - (screen_w / 2) / zoom
        
        screen_w = camera.width
        screen_h = camera.height
        zoom = camera.zoom
        
        vx_world = camera.x - (screen_w / 2) / zoom
        vy_world = camera.y - (screen_h / 2) / zoom
        vw_world = screen_w / zoom
        vh_world = screen_h / zoom
        
        vx = (vx_world - ox) * self.scale_x
        vy = (vy_world - oy) * self.scale_y
        vw = vw_world * self.scale_x
        vh = vh_world * self.scale_y
        
        view_rect = pygame.Rect(self.x + vx, self.y + vy, vw, vh)
        
        # Draw viewport rect with clipping
        clip_rect = self.rect.clip(view_rect)
        if clip_rect.width > 0 and clip_rect.height > 0:
             pygame.draw.rect(screen, (255, 255, 255), clip_rect, 1)
        
        # Building legend below minimap
        self._render_legend(screen, cities)
    
    def _render_legend(self, screen, cities):
        """Render building type legend below minimap."""
        from entities.building import BuildingType
        
        # Count buildings by type
        building_counts = {bt: 0 for bt in BuildingType}
        for city in cities:
            for district in city.districts:
                for b in district.buildings:
                    building_counts[b.type] += 1
        
        # Building type colors and symbols
        building_info = [
            (BuildingType.RESIDENTIAL, "Res", (100, 200, 100)),
            (BuildingType.WORKPLACE, "Work", (100, 100, 200)),
            (BuildingType.HOSPITAL, "Hosp", (255, 255, 255)),
            (BuildingType.COMMERCIAL, "Comm", (240, 180, 60)),
            (BuildingType.SCHOOL, "School", (220, 120, 120)),
            (BuildingType.PARK, "Park", (50, 160, 80))
        ]
        
        font_small = UITheme.get_font(10)
        legend_y = self.y + self.size + 15
        legend_x = self.x
        
        for i, (btype, label, color) in enumerate(building_info):
            count = building_counts[btype]
            # Color square
            pygame.draw.rect(screen, color, (legend_x, legend_y + i * 16, 12, 12))
            # Label and count
            text = font_small.render(f"{label}: {count}", True, (200, 200, 200))
            screen.blit(text, (legend_x + 18, legend_y + i * 16))
