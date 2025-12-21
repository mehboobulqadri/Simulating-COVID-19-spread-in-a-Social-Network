import pygame
import numpy as np

class Camera:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.x = 0
        self.y = 0
        self.zoom = 1.0
        self.target_zoom = 1.0
        self.target_x = 0
        self.target_y = 0
        self.pan_speed = 5
        self.zoom_speed = 0.1
        self.min_zoom = 0.08
        self.max_zoom = 6.0
        self.smoothing = 0.15  # Smoothing factor for pan/zoom (0-1, higher = snappier)
        
        # Drag state
        self.is_dragging = False
        self.last_mouse_pos = (0, 0)

    def get_projection_matrix(self):
        # Orthographic Projection: 0..width, height..0 (Top-left origin)
        L, R = 0, self.width
        B, T = self.height, 0 
        
        return np.array([
            [2/(R-L), 0, 0, 0],
            [0, 2/(T-B), 0, 0],
            [0, 0, -1, 0],
            [-(R+L)/(R-L), -(T+B)/(T-B), 0, 1]
        ], dtype='f4')

    def get_view_matrix(self):
        # Transform: Translate(-Cam) -> Scale(Zoom) -> Translate(ScreenCenter)
        
        # T_world
        t_world = np.identity(4, dtype='f4')
        t_world[3, 0] = -self.x
        t_world[3, 1] = -self.y
        
        # Scale
        scale = np.identity(4, dtype='f4')
        scale[0, 0] = self.zoom
        scale[1, 1] = self.zoom
        
        # T_screen
        t_screen = np.identity(4, dtype='f4')
        t_screen[3, 0] = self.width / 2
        t_screen[3, 1] = self.height / 2
        
        return t_world @ scale @ t_screen

    def handle_input(self):
        keys = pygame.key.get_pressed()
        pan_delta = self.pan_speed / self.zoom
        
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.target_x -= pan_delta
            self.x -= pan_delta
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.target_x += pan_delta
            self.x += pan_delta
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.target_y -= pan_delta
            self.y -= pan_delta
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.target_y += pan_delta
            self.y += pan_delta
            
    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            if event.y > 0:
                self.target_zoom *= 1.1
            elif event.y < 0:
                self.target_zoom /= 1.1
            # Clamp zoom
            if self.target_zoom < self.min_zoom:
                self.target_zoom = self.min_zoom
            elif self.target_zoom > self.max_zoom:
                self.target_zoom = self.max_zoom

        # Legacy wheel mapping on some systems (buttons 4/5)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 4:  # wheel up
                self.target_zoom *= 1.1
                if self.target_zoom > self.max_zoom:
                    self.target_zoom = self.max_zoom
            elif event.button == 5:  # wheel down
                self.target_zoom /= 1.1
                if self.target_zoom < self.min_zoom:
                    self.target_zoom = self.min_zoom
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Left click
                self.is_dragging = True
                self.last_mouse_pos = event.pos
                
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                self.is_dragging = False
                
        elif event.type == pygame.MOUSEMOTION:
            if self.is_dragging:
                dx = event.pos[0] - self.last_mouse_pos[0]
                dy = event.pos[1] - self.last_mouse_pos[1]
                
                # Adjust camera position immediately (inverse of mouse movement)
                # Update both current AND target to avoid smooth interpolation fighting the drag
                pan_x = dx / self.zoom
                pan_y = dy / self.zoom
                
                self.x -= pan_x
                self.y -= pan_y
                self.target_x -= pan_x
                self.target_y -= pan_y
                
                self.last_mouse_pos = event.pos
        
    def update(self):
        # Smooth zoom interpolation only
        zoom_diff = self.target_zoom - self.zoom
        if abs(zoom_diff) > 0.001:
            self.zoom += zoom_diff * self.smoothing
        else:
            self.zoom = self.target_zoom
        
        # NO pan interpolation - camera position is set directly by input
        # This prevents drift back to center
        
        # Keyboard zoom fallback (for users with trackpads/wheel issues)
        keys = pygame.key.get_pressed()
        # '[' to zoom out, ']' to zoom in
        if keys[pygame.K_LEFTBRACKET]:
            self.target_zoom /= (1.0 + self.zoom_speed)
        if keys[pygame.K_RIGHTBRACKET]:
            self.target_zoom *= (1.0 + self.zoom_speed)
        # Clamp zoom
        if self.target_zoom < self.min_zoom:
            self.target_zoom = self.min_zoom
        elif self.target_zoom > self.max_zoom:
            self.target_zoom = self.max_zoom
        
    def apply(self, x, y):
        # Convert world coordinates to screen coordinates
        screen_x = (x - self.x) * self.zoom + self.width / 2
        screen_y = (y - self.y) * self.zoom + self.height / 2
        return int(screen_x), int(screen_y)
    
    def screen_to_world(self, screen_x, screen_y):
        # Convert screen coordinates to world coordinates
        world_x = (screen_x - self.width / 2) / self.zoom + self.x
        world_y = (screen_y - self.height / 2) / self.zoom + self.y
        return world_x, world_y

    def frame_bounds(self, min_x, min_y, max_x, max_y, padding=200):
        """Center and zoom camera to fit given world bounds."""
        w = max_x - min_x
        h = max_y - min_y
        if w <= 0 or h <= 0:
            return
        w_p = w + 2 * padding
        h_p = h + 2 * padding
        self.target_zoom = min(self.width / w_p, self.height / h_p)
        self.target_x = (min_x + max_x) / 2
        self.target_y = (min_y + max_y) / 2
        # Snap to target immediately for initial framing
        self.x = self.target_x
        self.y = self.target_y
        self.zoom = self.target_zoom
