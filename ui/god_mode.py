import pygame
from ui.theme import UITheme

class GodModePanel:
    def __init__(self, screen_width, screen_height, simulation_engine):
        self.width = 300
        self.height = 400
        self.x = 20
        self.y = 100
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.visible = False
        self.engine = simulation_engine
        
        # Sliders configuration
        # (label, attribute_name, min_val, max_val)
        self.sliders = [
            {'label': 'Infection Prob', 'attr': 'infection_probability', 'min': 0.0, 'max': 1.0},
            {'label': 'Infection Radius', 'attr': 'infection_radius', 'min': 1.0, 'max': 50.0},
            {'label': 'Vaccination Threshold', 'attr': 'vaccination_threshold', 'min': 0.0, 'max': 1.0},
            {'label': 'Vaccination Rate', 'attr': 'vaccination_rate', 'min': 0.0, 'max': 0.1},
            {'label': 'Hospital Cure Rate', 'attr': 'hospital_cure_rate', 'min': 0.0, 'max': 0.1}
        ]
        
        self.dragging_slider = None
        self.hovered_slider = None

    def toggle(self):
        self.visible = not self.visible

    def handle_event(self, event):
        if not self.visible:
            return False
            
        if event.type == pygame.MOUSEMOTION:
            self.hovered_slider = None
            mx, my = event.pos
            if self.rect.collidepoint(mx, my):
                for i, slider in enumerate(self.sliders):
                    slider_y = self.y + 60 + i * 60
                    bar_rect = pygame.Rect(self.x + 20, slider_y + 25, self.width - 40, 10)
                    if bar_rect.inflate(0, 20).collidepoint(mx, my):
                        self.hovered_slider = i
                        break
            
            if self.dragging_slider is not None:
                slider = self.sliders[self.dragging_slider]
                slider_y = self.y + 60 + self.dragging_slider * 60
                bar_rect = pygame.Rect(self.x + 20, slider_y + 25, self.width - 40, 10)
                self._update_slider_value(self.dragging_slider, event.pos[0], bar_rect)
                return True
            
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                mx, my = event.pos
                for i, slider in enumerate(self.sliders):
                    slider_y = self.y + 60 + i * 60
                    bar_rect = pygame.Rect(self.x + 20, slider_y + 25, self.width - 40, 10)
                    
                    if bar_rect.inflate(0, 20).collidepoint(mx, my):
                        self.dragging_slider = i
                        self._update_slider_value(i, mx, bar_rect)
                        return True
                return True # Consume click on panel
                
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging_slider = None
                
        return False

    def _get_knob_rect(self, slider, bar_rect):
        val = getattr(self.engine, slider['attr'])
        pct = (val - slider['min']) / (slider['max'] - slider['min'])
        knob_x = bar_rect.x + pct * bar_rect.width
        return pygame.Rect(knob_x - 8, bar_rect.y - 5, 16, 20)

    def _update_slider_value(self, index, mouse_x, bar_rect):
        slider = self.sliders[index]
        pct = (mouse_x - bar_rect.x) / bar_rect.width
        pct = max(0.0, min(1.0, pct))
        new_val = slider['min'] + pct * (slider['max'] - slider['min'])
        setattr(self.engine, slider['attr'], new_val)

    def render(self, screen):
        if not self.visible:
            return
            
        # Background
        UITheme.draw_panel_bg(screen, self.rect)
        
        # Title
        title_font = UITheme.get_font(20, bold=True)
        title = title_font.render("GOD MODE SETTINGS", True, (255, 215, 0))
        screen.blit(title, (self.x + 20, self.y + 15))
        
        # Sliders
        label_font = UITheme.get_font(14)
        
        for i, slider in enumerate(self.sliders):
            slider_y = self.y + 60 + i * 60
            
            # Label and Value
            val = getattr(self.engine, slider['attr'])
            label_txt = f"{slider['label']}: {val:.3f}"
            label_surf = label_font.render(label_txt, True, UITheme.TEXT_COLOR)
            screen.blit(label_surf, (self.x + 20, slider_y))
            
            # Bar
            bar_rect = pygame.Rect(self.x + 20, slider_y + 25, self.width - 40, 6)
            pygame.draw.rect(screen, (60, 60, 70), bar_rect, border_radius=3)
            
            # Filled part
            pct = (val - slider['min']) / (slider['max'] - slider['min'])
            fill_rect = pygame.Rect(bar_rect.x, bar_rect.y, bar_rect.width * pct, bar_rect.height)
            pygame.draw.rect(screen, UITheme.ACCENT_COLOR, fill_rect, border_radius=3)
            
            # Knob
            knob_rect = self._get_knob_rect(slider, bar_rect)
            knob_color = (255, 255, 255)
            if self.hovered_slider == i or self.dragging_slider == i:
                knob_color = UITheme.HIGHLIGHT_COLOR
                
            pygame.draw.circle(screen, knob_color, knob_rect.center, 8)

