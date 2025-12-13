import pygame
import pygame_gui
from pygame_gui.elements import UIButton, UIPanel, UILabel, UIWindow, UIHorizontalSlider
from pygame_gui.windows import UIMessageWindow
from ui.ui_dashboard import UIDashboard

class UIManagerWrapper:
    def __init__(self, width, height, simulation_engine):
        self.width = width
        self.height = height
        self.engine = simulation_engine
        
        self.manager = pygame_gui.UIManager((width, height), theme_path=None) # Use default theme for now
        
        # Create Main Control Bar (Bottom)
        self.control_bar = UIPanel(
            relative_rect=pygame.Rect(0, height - 60, width, 60),
            manager=self.manager,
            anchors={'left': 'left', 'right': 'right', 'bottom': 'bottom'}
        )
        
        # Control Buttons
        self.btn_pause = UIButton(
            relative_rect=pygame.Rect(10, 10, 80, 40),
            text='Pause',
            manager=self.manager,
            container=self.control_bar
        )
        
        self.btn_god_mode = UIButton(
            relative_rect=pygame.Rect(100, 10, 100, 40),
            text='God Mode',
            manager=self.manager,
            container=self.control_bar
        )
        
        self.btn_stats = UIButton(
            relative_rect=pygame.Rect(210, 10, 80, 40),
            text='Stats',
            manager=self.manager,
            container=self.control_bar
        )
        
        self.speed_label = UILabel(
            relative_rect=pygame.Rect(300, 10, 120, 40),
            text='Speed: 1x',
            manager=self.manager,
            container=self.control_bar
        )
        
        self.slider_speed = UIHorizontalSlider(
            relative_rect=pygame.Rect(430, 15, 200, 30),
            start_value=1.0,
            value_range=(0.0, 10.0),
            manager=self.manager,
            container=self.control_bar
        )
        
        # Windows
        self.god_mode_window = None
        self.dashboard = UIDashboard(self.manager, width - 340, 20) # Top Right
        
        # State
        self.paused = False
        self.speed = 1.0

    def toggle_god_mode(self):
        if self.god_mode_window:
            self.god_mode_window.kill()
            self.god_mode_window = None
        else:
            self.god_mode_window = UIWindow(
                rect=pygame.Rect(50, 50, 300, 400),
                manager=self.manager,
                window_display_title='God Mode Settings'
            )
            
            # Add Sliders to God Mode Window
            y = 10
            self.sliders = {}
            
            params = [
                ('Infection Prob', 'infection_prob', 0.0, 1.0),
                ('Infection Radius', 'infection_radius', 1.0, 50.0),
                ('Vaccination Rate', 'vaccination_rate', 0.0, 0.1)
            ]
            
            for label, attr, min_v, max_v in params:
                UILabel(
                    relative_rect=pygame.Rect(10, y, 200, 20),
                    text=label,
                    manager=self.manager,
                    container=self.god_mode_window
                )
                
                current_val = getattr(self.engine, attr)
                
                slider = UIHorizontalSlider(
                    relative_rect=pygame.Rect(10, y + 25, 260, 20),
                    start_value=current_val,
                    value_range=(min_v, max_v),
                    manager=self.manager,
                    container=self.god_mode_window
                )
                
                self.sliders[slider] = attr
                y += 60

    def toggle_stats(self):
        if self.dashboard.window.visible:
            self.dashboard.window.hide()
        else:
            self.dashboard.window.show()

    def handle_event(self, event):
        self.manager.process_events(event)
        
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.btn_pause:
                self.paused = not self.paused
                self.btn_pause.set_text("Play" if self.paused else "Pause")
            elif event.ui_element == self.btn_god_mode:
                self.toggle_god_mode()
            elif event.ui_element == self.btn_stats:
                self.toggle_stats()
                
        elif event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
            if event.ui_element == self.slider_speed:
                self.speed = event.value
                self.speed_label.set_text(f"Speed: {self.speed:.1f}x")
            
            # Handle God Mode Sliders
            if self.god_mode_window and event.ui_element in self.sliders:
                attr = self.sliders[event.ui_element]
                setattr(self.engine, attr, event.value)

    def update(self, time_delta, stats_manager=None):
        self.manager.update(time_delta)
        if stats_manager:
            self.dashboard.update(stats_manager)

    def draw(self, screen):
        self.manager.draw_ui(screen)
