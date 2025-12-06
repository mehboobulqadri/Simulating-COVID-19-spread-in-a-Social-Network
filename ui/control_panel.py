import pygame

class ControlPanel:
    def __init__(self, screen_width, screen_height):
        self.width = 200
        self.height = 160 # Increased height for new buttons
        self.x = screen_width - self.width - 10
        self.y = 10
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        
        self.paused = False
        self.speed = 1.0
        
        # Callbacks (to be assigned by main)
        self.on_save = None
        self.on_load = None
        self.on_export = None
        
        # Buttons
        self.buttons = [
            {'label': 'Pause/Play', 'rect': pygame.Rect(self.x + 10, self.y + 40, 80, 30), 'action': self.toggle_pause},
            {'label': '1x', 'rect': pygame.Rect(self.x + 10, self.y + 80, 40, 30), 'action': lambda: self.set_speed(1.0)},
            {'label': '2x', 'rect': pygame.Rect(self.x + 60, self.y + 80, 40, 30), 'action': lambda: self.set_speed(2.0)},
            {'label': '5x', 'rect': pygame.Rect(self.x + 110, self.y + 80, 40, 30), 'action': lambda: self.set_speed(5.0)},
            {'label': 'Save', 'rect': pygame.Rect(self.x + 10, self.y + 120, 50, 30), 'action': self.trigger_save},
            {'label': 'Load', 'rect': pygame.Rect(self.x + 70, self.y + 120, 50, 30), 'action': self.trigger_load},
            {'label': 'CSV', 'rect': pygame.Rect(self.x + 130, self.y + 120, 50, 30), 'action': self.trigger_export}
        ]
        
        self.font = pygame.font.SysFont("Arial", 16)

    def toggle_pause(self):
        self.paused = not self.paused

    def set_speed(self, speed):
        self.speed = speed
        
    def trigger_save(self):
        if self.on_save: self.on_save()
        
    def trigger_load(self):
        if self.on_load: self.on_load()
        
    def trigger_export(self):
        if self.on_export: self.on_export()

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                for btn in self.buttons:
                    if btn['rect'].collidepoint(event.pos):
                        btn['action']()
                        return True # Consumed event
        return False

    def render(self, screen):
        # Background
        pygame.draw.rect(screen, (40, 40, 40, 200), self.rect)
        pygame.draw.rect(screen, (100, 100, 100), self.rect, 1)
        
        # Title
        title = self.font.render(f"Speed: {self.speed}x {'(PAUSED)' if self.paused else ''}", True, (255, 255, 255))
        screen.blit(title, (self.x + 10, self.y + 10))
        
        # Buttons
        for btn in self.buttons:
            color = (80, 80, 80)
            if btn['label'] == 'Pause/Play' and self.paused:
                color = (100, 50, 50)
            elif btn['label'] == f"{int(self.speed)}x" or (btn['label'] == '1x' and self.speed == 1.0):
                 # Highlight current speed (approximate check)
                 if btn['label'] != 'Pause/Play':
                     if float(btn['label'][:-1]) == self.speed:
                         color = (50, 100, 50)
            
            pygame.draw.rect(screen, color, btn['rect'])
            pygame.draw.rect(screen, (150, 150, 150), btn['rect'], 1)
            
            label = self.font.render(btn['label'], True, (200, 200, 200))
            text_rect = label.get_rect(center=btn['rect'].center)
            screen.blit(label, text_rect)
