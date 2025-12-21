import pygame
import numpy as np
from ui.theme import UITheme

class GodModePanel:
    def __init__(self, screen_width, screen_height, simulation_engine):
        self.width = 700
        self.height = 650
        self.x = (screen_width - self.width) // 2
        self.y = (screen_height - self.height) // 2
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.visible = False
        self.engine = simulation_engine
        
        # Scrolling
        self.scroll_offset = 0
        self.max_scroll = 0
        
        # Close button
        self.close_btn_rect = pygame.Rect(self.x + self.width - 30, self.y + 10, 20, 20)
        
        # Sliders configuration - EXPANDED
        self.sliders = [
            # Basic Transmission
            {'label': 'Infection Prob', 'attr': 'infection_prob', 'min': 0.0, 'max': 0.1, 'category': 'Transmission'},
            {'label': 'Infection Radius', 'attr': 'infection_radius', 'min': 1.0, 'max': 50.0, 'category': 'Transmission'},
            {'label': 'Spatial Spillover', 'attr': 'spatial_spillover_factor', 'min': 0.0, 'max': 1.0, 'category': 'Transmission'},
            
            # Vaccination
            {'label': 'Vaccination Rate', 'attr': 'vaccination_rate', 'min': 0.0, 'max': 0.05, 'category': 'Vaccination'},
            {'label': 'Vaccination Target %', 'attr': 'vaccination_target_rate', 'min': 0.0, 'max': 1.0, 'category': 'Vaccination'},
            
            # Hospital
            {'label': 'Hospital Capacity %', 'attr': 'hospital_capacity_pct', 'min': 0.0, 'max': 0.10, 'category': 'Hospital'},
            {'label': 'Hospital Mortality ×', 'attr': 'hospital_mortality_multiplier', 'min': 1.0, 'max': 5.0, 'category': 'Hospital'},
            
            # Realism Features
            {'label': 'Superspreader ×', 'attr': 'superspreader_mult', 'min': 1.0, 'max': 5.0, 'category': 'Realism'},
            {'label': 'Home Transmission ×', 'attr': 'home_transmission_mult', 'min': 0.5, 'max': 5.0, 'category': 'Realism'},
            {'label': 'Work Transmission ×', 'attr': 'work_transmission_mult', 'min': 0.5, 'max': 3.0, 'category': 'Realism'},
            {'label': 'Leisure Transmission ×', 'attr': 'leisure_transmission_mult', 'min': 0.1, 'max': 2.0, 'category': 'Realism'},
            {'label': 'Household Attack Rate', 'attr': 'household_transmission_rate', 'min': 0.0, 'max': 1.0, 'category': 'Realism'},
            {'label': 'Immunity Duration (days)', 'attr': 'immunity_duration', 'min': 30, 'max': 720, 'category': 'Realism'},
            
            # Fear Response
            {'label': 'Fear Threshold %', 'attr': 'fear_threshold', 'min': 0.0, 'max': 0.10, 'category': 'Behavior'},
            {'label': 'Fear Movement Reduction', 'attr': 'fear_movement_reduction', 'min': 0.0, 'max': 1.0, 'category': 'Behavior'},
            
            # NPIs
            {'label': 'Mask Effectiveness', 'attr': 'mask_effectiveness', 'min': 0.0, 'max': 1.0, 'category': 'NPIs'},
            {'label': 'Mask Compliance', 'attr': 'mask_compliance', 'min': 0.0, 'max': 1.0, 'category': 'NPIs'},
            {'label': 'Lockdown Compliance', 'attr': 'lockdown_compliance', 'min': 0.0, 'max': 1.0, 'category': 'NPIs'},
        ]
        
        # Action buttons
        self.buttons = [
            {'label': 'Start Vaccination', 'action': 'start_vaccination', 'category': 'Actions'},
            {'label': 'Stop Vaccination', 'action': 'stop_vaccination', 'category': 'Actions'},
            {'label': 'Toggle Seasonal Effects', 'action': 'toggle_seasonal', 'category': 'Actions'},
            {'label': 'Toggle Fear Response', 'action': 'toggle_fear', 'category': 'Actions'},
            {'label': 'Reset Deaths Counter', 'action': 'reset_deaths', 'category': 'Actions'},
        ]
        
        self.dragging_slider = None
        self.hovered_slider = None
        self.hovered_button = None

    def center_on_screen(self, screen_width, screen_height):
        self.x = (screen_width - self.width) // 2
        self.y = (screen_height - self.height) // 2
        self.rect.x = self.x
        self.rect.y = self.y
        self.close_btn_rect.x = self.x + self.width - 30
        self.close_btn_rect.y = self.y + 10

    def toggle(self):
        self.visible = not self.visible

    def _perform_action(self, action):
        """Execute button actions"""
        if action == 'start_vaccination':
            self.engine.vaccination_active = True
            self.engine.vaccination_target_rate = 0.50  # Default to 50%
            self.engine.vaccination_scope_mask = np.ones(self.engine.num_people, dtype=np.bool_)
            print(f"💉 MANUAL VACCINATION CAMPAIGN STARTED (target: 50%)")
        elif action == 'stop_vaccination':
            self.engine.vaccination_active = False
            print(f"💉 VACCINATION CAMPAIGN STOPPED")
        elif action == 'toggle_seasonal':
            self.engine.seasonal_effects_active = not self.engine.seasonal_effects_active
            status = "ON" if self.engine.seasonal_effects_active else "OFF"
            print(f"🌡️ SEASONAL EFFECTS: {status}")
        elif action == 'toggle_fear':
            self.engine.fear_active = not self.engine.fear_active
            status = "ON" if self.engine.fear_active else "OFF"
            print(f"😨 FEAR RESPONSE: {status}")
        elif action == 'reset_deaths':
            self.engine.total_deaths = 0
            print(f"💀 DEATH COUNTER RESET")

    def handle_event(self, event):
        if not self.visible:
            return False
        
        if event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                self.scroll_offset -= event.y * 30
                self.scroll_offset = max(0, min(self.scroll_offset, self.max_scroll))
                return True
            
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Check close button
            if self.close_btn_rect.collidepoint(event.pos):
                self.visible = False
                return True
            
            # Check if click is inside panel
            if self.rect.collidepoint(event.pos):
                mx, my = event.pos
                button_start_y = self.y + 60
                
                # Check buttons first
                for i, button in enumerate(self.buttons):
                    btn_rect = pygame.Rect(self.x + 20, button_start_y + i * 35 - self.scroll_offset, 200, 30)
                    if btn_rect.collidepoint(mx, my) and btn_rect.bottom < self.rect.bottom:
                        self._perform_action(button['action'])
                        return True
                
                # Then check sliders
                slider_start_y = button_start_y + len(self.buttons) * 35 + 40
                for i, slider in enumerate(self.sliders):
                    slider_y = slider_start_y + i * 55 - self.scroll_offset
                    bar_rect = pygame.Rect(self.x + 20, slider_y + 25, self.width - 40, 10)
                    
                    # Click anywhere on bar to set value + start dragging
                    if bar_rect.inflate(0, 20).collidepoint(mx, my) and bar_rect.bottom < self.rect.bottom:
                        self.dragging_slider = i
                        self._update_slider_value(i, mx, bar_rect)
                        return True
                
                return True  # Consume click inside panel
            else:
                # Click outside panel - close it
                self.visible = False
                return True

        if event.type == pygame.MOUSEMOTION:
            self.hovered_slider = None
            self.hovered_button = None
            mx, my = event.pos
            
            if self.rect.collidepoint(mx, my):
                # Check button hovers
                button_start_y = self.y + 60
                for i, button in enumerate(self.buttons):
                    btn_rect = pygame.Rect(self.x + 20, button_start_y + i * 35 - self.scroll_offset, 200, 30)
                    if btn_rect.collidepoint(mx, my) and btn_rect.bottom < self.rect.bottom:
                        self.hovered_button = i
                        break
                
                # Check slider hovers
                slider_start_y = self.y + 60 + len(self.buttons) * 35 + 40
                for i, slider in enumerate(self.sliders):
                    slider_y = slider_start_y + i * 55 - self.scroll_offset
                    bar_rect = pygame.Rect(self.x + 20, slider_y + 25, self.width - 40, 10)
                    if bar_rect.inflate(0, 20).collidepoint(mx, my) and bar_rect.bottom < self.rect.bottom:
                        self.hovered_slider = i
                        break
            
            # Update slider while dragging
            if self.dragging_slider is not None:
                slider_start_y = self.y + 60 + len(self.buttons) * 35 + 40
                slider_y = slider_start_y + self.dragging_slider * 55 - self.scroll_offset
                bar_rect = pygame.Rect(self.x + 20, slider_y + 25, self.width - 40, 10)
                self._update_slider_value(self.dragging_slider, event.pos[0], bar_rect)
                return True
                
        if event.type == pygame.MOUSEBUTTONUP:
            self.dragging_slider = None
                
        return False

    def _get_value(self, slider):
        """Get value with special handling for dict-based attributes"""
        attr = slider['attr']
        
        # Special cases for attributes stored in dicts
        if attr == 'home_transmission_mult':
            return self.engine.location_transmission_mults.get(0, 3.0)
        elif attr == 'work_transmission_mult':
            return self.engine.location_transmission_mults.get(1, 1.5)
        elif attr == 'leisure_transmission_mult':
            return self.engine.location_transmission_mults.get(2, 0.5)
        elif attr == 'household_transmission_rate':
            return getattr(self.engine, 'household_transmission_rate', 0.80)
        elif attr == 'hospital_capacity_pct':
            return self.engine.hospital_capacity / max(1, self.engine.num_people)
        else:
            return getattr(self.engine, attr, 0)
    
    def _set_value(self, slider, value):
        """Set value with special handling for dict-based attributes"""
        attr = slider['attr']
        
        # Special cases
        if attr == 'home_transmission_mult':
            self.engine.location_transmission_mults[0] = value
        elif attr == 'work_transmission_mult':
            self.engine.location_transmission_mults[1] = value
        elif attr == 'leisure_transmission_mult':
            self.engine.location_transmission_mults[2] = value
        elif attr == 'household_transmission_rate':
            self.engine.household_transmission_rate = value
        elif attr == 'hospital_capacity_pct':
            self.engine.hospital_capacity = int(value * self.engine.num_people)
        else:
            setattr(self.engine, attr, value)
    
    def _get_knob_rect(self, slider, bar_rect):
        val = self._get_value(slider)
        pct = (val - slider['min']) / (slider['max'] - slider['min'])
        knob_x = bar_rect.x + pct * bar_rect.width
        return pygame.Rect(knob_x - 8, bar_rect.y - 5, 16, 20)

    def _update_slider_value(self, index, mouse_x, bar_rect):
        slider = self.sliders[index]
        pct = (mouse_x - bar_rect.x) / bar_rect.width
        pct = max(0.0, min(1.0, pct))
        new_val = slider['min'] + pct * (slider['max'] - slider['min'])
        self._set_value(slider, new_val)

    def render(self, screen):
        if not self.visible:
            return
        
        # Create clipping rect for scrolling
        pygame.draw.rect(screen, (0, 0, 0, 0), self.rect)
        clip_rect = screen.get_clip()
        screen.set_clip(self.rect)
            
        # Background
        UITheme.draw_panel_bg(screen, self.rect)
        
        # Title
        title_font = UITheme.get_font(20, bold=True)
        title = title_font.render("GOD MODE SETTINGS", True, (255, 215, 0))
        screen.blit(title, (self.x + 20, self.y + 15))
        
        # Close Button (X)
        pygame.draw.rect(screen, (200, 50, 50), self.close_btn_rect, border_radius=4)
        close_font = UITheme.get_font(16, bold=True)
        close_txt = close_font.render("X", True, (255, 255, 255))
        close_rect = close_txt.get_rect(center=self.close_btn_rect.center)
        screen.blit(close_txt, close_rect)
        
        # Fonts
        label_font = UITheme.get_font(14)
        button_font = UITheme.get_font(13, bold=True)
        category_font = UITheme.get_font(15, bold=True)
        
        current_y = self.y + 60 - self.scroll_offset
        
        # --- ACTION BUTTONS ---
        cat_surf = category_font.render("ACTIONS", True, (100, 200, 255))
        if current_y > self.y + 50 and current_y < self.rect.bottom:
            screen.blit(cat_surf, (self.x + 20, current_y))
        current_y += 30
        
        for i, button in enumerate(self.buttons):
            btn_rect = pygame.Rect(self.x + 20, current_y, 200, 30)
            
            if btn_rect.bottom > self.y + 50 and btn_rect.top < self.rect.bottom:
                # Button background
                btn_color = (50, 120, 180) if self.hovered_button != i else (70, 150, 220)
                pygame.draw.rect(screen, btn_color, btn_rect, border_radius=5)
                
                # Button text
                btn_text = button_font.render(button['label'], True, (255, 255, 255))
                text_rect = btn_text.get_rect(center=btn_rect.center)
                screen.blit(btn_text, text_rect)
            
            current_y += 35
        
        current_y += 10
        
        # --- SLIDERS BY CATEGORY ---
        current_category = None
        for i, slider in enumerate(self.sliders):
            # Category header
            if slider.get('category') != current_category:
                current_category = slider['category']
                cat_surf = category_font.render(current_category.upper(), True, (100, 200, 255))
                if current_y > self.y + 50 and current_y < self.rect.bottom:
                    screen.blit(cat_surf, (self.x + 20, current_y))
                current_y += 30
            
            slider_y = current_y
            bar_rect = pygame.Rect(self.x + 20, slider_y + 25, self.width - 40, 6)
            
            # Only render if visible in viewport
            if bar_rect.bottom > self.y + 50 and bar_rect.top < self.rect.bottom:
                # Label and Value
                val = self._get_value(slider)
                if val < 1:
                    label_txt = f"{slider['label']}: {val:.3f}"
                elif val < 10:
                    label_txt = f"{slider['label']}: {val:.2f}"
                else:
                    label_txt = f"{slider['label']}: {val:.0f}"
                
                label_surf = label_font.render(label_txt, True, UITheme.TEXT_COLOR)
                screen.blit(label_surf, (self.x + 20, slider_y))
                
                # Bar
                pygame.draw.rect(screen, (60, 60, 70), bar_rect, border_radius=3)
                
                # Filled part
                pct = (val - slider['min']) / max(0.001, (slider['max'] - slider['min']))
                fill_rect = pygame.Rect(bar_rect.x, bar_rect.y, bar_rect.width * pct, bar_rect.height)
                pygame.draw.rect(screen, UITheme.ACCENT_COLOR, fill_rect, border_radius=3)
                
                # Knob
                knob_rect = self._get_knob_rect(slider, bar_rect)
                knob_color = (255, 255, 255)
                if self.hovered_slider == i or self.dragging_slider == i:
                    knob_color = UITheme.HIGHLIGHT_COLOR
                    
                pygame.draw.circle(screen, knob_color, knob_rect.center, 8)
            
            current_y += 55
        
        # Update max scroll
        self.max_scroll = max(0, current_y - self.rect.bottom + 20)
        
        # Restore clip
        screen.set_clip(clip_rect)
