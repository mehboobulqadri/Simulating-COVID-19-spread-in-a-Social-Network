import pygame
from ui.theme import UITheme

class ControlPanel:
    def __init__(self, screen_width, screen_height):
        self.width = 220
        self.height = 240
        self.x = screen_width - self.width - 20
        self.y = 20
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        
        self.paused = False
        self.speed = 1.0
        self.hovered_btn = None
        
        # Callbacks (to be assigned by main)
        self.on_save = None
        self.on_load = None
        self.on_export = None
        self.on_god_mode = None
        
        # Buttons
        # Layout:
        # [ Pause/Play ]
        # [ 1x ] [ 2x ] [ 5x ]
        # [ Save ] [ Load ]
        # [ Export CSV ]
        # [ GOD MODE ]
        
        self.buttons = [
            {'label': 'Pause/Play', 'rect': pygame.Rect(self.x + 20, self.y + 50, 180, 30), 'action': self.toggle_pause},
            {'label': '1x', 'rect': pygame.Rect(self.x + 20, self.y + 90, 50, 30), 'action': lambda: self.set_speed(1.0)},
            {'label': '2x', 'rect': pygame.Rect(self.x + 85, self.y + 90, 50, 30), 'action': lambda: self.set_speed(2.0)},
            {'label': '5x', 'rect': pygame.Rect(self.x + 150, self.y + 90, 50, 30), 'action': lambda: self.set_speed(5.0)},
            {'label': 'Save', 'rect': pygame.Rect(self.x + 20, self.y + 130, 85, 30), 'action': self.trigger_save},
            {'label': 'Load', 'rect': pygame.Rect(self.x + 115, self.y + 130, 85, 30), 'action': self.trigger_load},
            {'label': 'Export CSV', 'rect': pygame.Rect(self.x + 20, self.y + 170, 180, 30), 'action': self.trigger_export},
            {'label': 'GOD MODE', 'rect': pygame.Rect(self.x + 20, self.y + 210, 180, 30), 'action': self.trigger_god_mode}
        ]
        
        # Adjust height to fit buttons
        self.height = 260
        self.rect.height = self.height

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
        
    def trigger_god_mode(self):
        if self.on_god_mode: self.on_god_mode()

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered_btn = None
            for i, btn in enumerate(self.buttons):
                if btn['rect'].collidepoint(event.pos):
                    self.hovered_btn = i
                    break
                    
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                for btn in self.buttons:
                    if btn['rect'].collidepoint(event.pos):
                        btn['action']()
                        return True # Consumed event
        return False

    def render(self, screen):
        # Background
        UITheme.draw_panel_bg(screen, self.rect)
        
        # Title
        title_font = UITheme.get_font(18, bold=True)
        status_text = "PAUSED" if self.paused else f"SPEED: {self.speed}x"
        title = title_font.render(status_text, True, UITheme.TEXT_COLOR)
        screen.blit(title, (self.x + 20, self.y + 15))
        
        # Buttons
        for i, btn in enumerate(self.buttons):
            active = False
            if btn['label'] == 'Pause/Play' and self.paused:
                active = True
            elif btn['label'] == f"{int(self.speed)}x" or (btn['label'] == '1x' and self.speed == 1.0):
                 if btn['label'] != 'Pause/Play':
                     if float(btn['label'][:-1]) == self.speed:
                         active = True
            elif btn['label'] == 'GOD MODE':
                # Maybe highlight if god mode is active? 
                # We don't track god mode state here easily, but that's fine.
                pass
            
            hover = (self.hovered_btn == i)
            UITheme.draw_button(screen, btn['rect'], btn['label'], active, hover)

