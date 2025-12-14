import pygame
from ui.theme import UITheme

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

    def render(self, screen, cities, camera, trace_points=None):
        # Background
        UITheme.draw_panel_bg(screen, self.rect)
        
        # Draw Cities/Districts
        ox, oy = self.world_origin
        for city in cities:
            # City Dot
            cx = self.x + (city.location[0] - ox) * self.scale_x
            cy = self.y + (city.location[1] - oy) * self.scale_y
            pygame.draw.circle(screen, (200, 200, 200), (cx, cy), 3)
            
            for district in city.districts:
                r = district.bounds
                dx = self.x + (r.x - ox) * self.scale_x
                dy = self.y + (r.y - oy) * self.scale_y
                dw = r.width * self.scale_x
                dh = r.height * self.scale_y
                
                color = (100, 100, 120)
                # Maybe color by infection?
                # Check infection rate
                infected = len([p for p in district.people if p.state.name == 'INFECTIOUS'])
                if infected > 0:
                    ratio = infected / len(district.people)
                    color = (100 + int(155 * ratio), 100 - int(100 * ratio), 100 - int(100 * ratio))
                
                pygame.draw.rect(screen, color, (dx, dy, dw, dh))

        # Draw trace polyline (cyan) if provided
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
