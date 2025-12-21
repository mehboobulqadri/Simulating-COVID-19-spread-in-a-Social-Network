import pygame
from ui.theme import UITheme

class ControlPanel:
    def __init__(self, screen_width, screen_height):
        self.width = 280
        self.height = screen_height
        # Animation states - start hidden off-screen
        self.offset_x = -self.width
        self.target_x = -self.width
        self.speed_anim = 0.45  # Softer easing for smoother slide
        self.velocity = 0.0     # For damped spring motion
        
        self.x = self.offset_x
        self.y = 0
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        
        # Hover detection zone (thin strip on left edge)
        self.hover_zone_width = 18
        self.pinned = False
        self.pin_rect = pygame.Rect(self.width - 34, 20, 16, 16)
        
        self.paused = False
        self.speed = 1.0
        self.hovered_btn = None
        
        # Callbacks
        self.on_save = None
        self.on_load = None
        self.on_export = None
        self.on_god_mode = None
        
        # Button configuration with original x positions
        self.buttons = []
        self._setup_buttons()

    def _setup_buttons(self):
        y_offset = 80
        button_width = 240
        button_x = 20
        spacing = 10
        
        # Simulation Controls Section
        self.buttons.append({
            'label': 'Pause' if not self.paused else 'Play',
            'rect': pygame.Rect(button_x, y_offset, button_width, 45),
            'action': self.toggle_pause,
            'original_x': button_x,
            'type': 'main'
        })
        y_offset += 55
        
        # Speed Controls
        speed_btn_width = (button_width - 20) // 3
        for i, (label, speed_val) in enumerate([('1x', 1.0), ('2x', 2.0), ('5x', 5.0)]):
            self.buttons.append({
                'label': label,
                'rect': pygame.Rect(button_x + i * (speed_btn_width + 10), y_offset, speed_btn_width, 40),
                'action': lambda s=speed_val: self.set_speed(s),
                'original_x': button_x + i * (speed_btn_width + 10),
                'type': 'speed'
            })
        y_offset += 60
        
        # Section separator
        y_offset += 10
        
        # File Operations Section
        file_ops = [
            ('Save Simulation', self.trigger_save),
            ('Load Simulation', self.trigger_load),
            ('Export CSV', self.trigger_export)
        ]
        
        for label, action in file_ops:
            self.buttons.append({
                'label': label,
                'rect': pygame.Rect(button_x, y_offset, button_width, 40),
                'action': action,
                'original_x': button_x,
                'type': 'file'
            })
            y_offset += 50
        
        # Section separator
        y_offset += 20
        

        # self.buttons.append({
        #     'label': 'GOD MODE',
        #     'rect': pygame.Rect(button_x, y_offset, button_width, 55),
        #     'action': self.trigger_god_mode,
        #     'original_x': button_x,
        #     'type': 'god'
        # })

    def update(self, mouse_pos):
        # Hover detection - show panel when mouse near left edge OR over the panel, or pinned
        if self.pinned:
            self.target_x = 0
        elif mouse_pos[0] <= self.hover_zone_width or (self.offset_x > -self.width and mouse_pos[0] < self.width):
            self.target_x = 0
        else:
            self.target_x = -self.width
        
        # Damped spring animation for a softer overshoot
        delta = self.target_x - self.offset_x
        self.velocity = self.velocity * 0.7 + delta * self.speed_anim
        self.offset_x += self.velocity
        if abs(delta) < 0.5 and abs(self.velocity) < 0.4:
            self.offset_x = self.target_x
            self.velocity = 0.0
        
        # Clamp offset_x to ensure it doesn't go beyond bounds
        if self.offset_x > 0:
            self.offset_x = 0
        if self.offset_x < -self.width:
            self.offset_x = -self.width
            
        self.rect.x = self.offset_x
        self.pin_rect.x = self.offset_x + self.width - 34
        
        # Update button positions relative to panel movement
        for btn in self.buttons:
            btn['rect'].x = self.offset_x + btn['original_x']

    def toggle_pause(self): 
        self.paused = not self.paused
        # Update button label
        for btn in self.buttons:
            if btn['type'] == 'main':
                btn['label'] = 'Play' if self.paused else 'Pause'
    
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
        
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.pin_rect.collidepoint(event.pos):
                self.pinned = not self.pinned
                return True
            for btn in self.buttons:
                if btn['rect'].collidepoint(event.pos):
                    btn['action']()
                    return True
        return False

    def render(self, screen):
        # Panel background with subtle transparency
        UITheme.draw_panel_bg(screen, self.rect)
        
        # Header
        header_font = UITheme.get_font(24, bold=True)
        header = header_font.render("CONTROL PANEL", True, UITheme.ACCENT_COLOR)
        screen.blit(header, (self.offset_x + 20, 25))
        
        # Status indicator
        status_font = UITheme.get_font(13)
        status_color = (255, 100, 100) if self.paused else (100, 255, 100)
        status_text = "● PAUSED" if self.paused else f"● RUNNING {self.speed}x"
        status_surf = status_font.render(status_text, True, status_color)
        screen.blit(status_surf, (self.offset_x + 20, 55))
        
        # Section labels
        section_font = UITheme.get_font(12, bold=True)
        section_color = (150, 150, 160)
        
        # Simulation section (above speed buttons)
        sim_label = section_font.render("SIMULATION", True, section_color)
        screen.blit(sim_label, (self.offset_x + 20, 135))
        
        
        
        # Advanced section
        
        
        # Render buttons
        for i, btn in enumerate(self.buttons):
            btn_type = btn.get('type', 'normal')
            
            # Determine if button is active
            active = False
            if btn_type == 'main' and self.paused:
                active = True
            elif btn_type == 'speed' and btn['label'] == f"{int(self.speed)}x":
                active = True
            
            hover = (self.hovered_btn == i)
            
            # Special styling for god mode button
            if btn_type == 'god':
                self._draw_god_button(screen, btn['rect'], btn['label'], hover)
            else:
                UITheme.draw_button(screen, btn['rect'], btn['label'], active, hover)
        
        # Edge indicator (shows when panel is hidden)
        if self.offset_x < -self.width + 5:
            indicator_rect = pygame.Rect(0, self.height // 2 - 30, 3, 60)
            pygame.draw.rect(screen, UITheme.ACCENT_COLOR, indicator_rect, border_radius=2)

        # Pin toggle
        pin_hover = self.pin_rect.collidepoint(pygame.mouse.get_pos())
        pin_bg = pygame.Color(40, 40, 50, 220)
        pygame.draw.rect(screen, pin_bg, self.pin_rect, border_radius=4)
        pygame.draw.rect(screen, UITheme.ACCENT_COLOR if (self.pinned or pin_hover) else (120, 120, 130), self.pin_rect, 2, border_radius=4)
        # Draw a small pin glyph
        cx = self.pin_rect.centerx
        cy = self.pin_rect.centery
        pygame.draw.line(screen, (220, 220, 230), (cx, cy - 4), (cx, cy + 4), 2)
        pygame.draw.line(screen, (220, 220, 230), (cx - 4, cy), (cx + 4, cy), 2)
        if self.pinned:
            pygame.draw.circle(screen, UITheme.ACCENT_COLOR, (cx, cy), 3)

    def _draw_god_button(self, screen, rect, text, hover):
        # Special gold/red styling for god mode
        color = (180, 140, 0) if not hover else (220, 180, 20)
        pygame.draw.rect(screen, color, rect, border_radius=8)
        pygame.draw.rect(screen, (255, 215, 0), rect, 2, border_radius=8)
        
        font = UITheme.get_font(16, bold=True)
        text_surf = font.render(text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=rect.center)
        screen.blit(text_surf, text_rect)