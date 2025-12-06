import pygame

class Camera:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.x = 0
        self.y = 0
        self.zoom = 1.0
        self.target_zoom = 1.0
        self.pan_speed = 5
        self.zoom_speed = 0.1
        
        # Drag state
        self.is_dragging = False
        self.last_mouse_pos = (0, 0)

    def handle_input(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.x -= self.pan_speed / self.zoom
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.x += self.pan_speed / self.zoom
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.y -= self.pan_speed / self.zoom
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.y += self.pan_speed / self.zoom
            
    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            if event.y > 0:
                self.zoom *= 1.1
            elif event.y < 0:
                self.zoom /= 1.1
        
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
                
                # Adjust camera position (inverse of mouse movement)
                self.x -= dx / self.zoom
                self.y -= dy / self.zoom
                
                self.last_mouse_pos = event.pos
        
    def update(self):
        # Smooth zoom interpolation could go here
        pass
        
    def apply(self, x, y):
        # Convert world coordinates to screen coordinates
        screen_x = (x - self.x) * self.zoom + self.width / 2
        screen_y = (y - self.y) * self.zoom + self.height / 2
        return int(screen_x), int(screen_y)
