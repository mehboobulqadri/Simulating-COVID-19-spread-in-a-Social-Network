import pygame
import pygame_gui
from pygame_gui.elements import UIButton, UIPanel, UILabel, UIWindow, UIHorizontalSlider, UITextBox, UIScrollingContainer
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
            relative_rect=pygame.Rect(100, 10, 120, 40),
            text='Control Panel',
            manager=self.manager,
            container=self.control_bar
        )
        
        self.btn_stats = UIButton(
            relative_rect=pygame.Rect(210, 10, 80, 40),
            text='Stats',
            manager=self.manager,
            container=self.control_bar
        )

        self.btn_minimap = UIButton(
            relative_rect=pygame.Rect(300, 10, 130, 40),
            text='Minimap: Always',
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
            value_range=(0.5, 20.0),
            manager=self.manager,
            container=self.control_bar
        )
        
        # Windows
        self.god_mode_window = None
        self.dashboard = UIDashboard(self.manager, width - 340, 20) # Top Right
        
        # State
        self.paused = False
        self.speed = 1.0
        # Default to always showing the minimap
        self.show_minimap_always = True

    def toggle_god_mode(self):
        if self.god_mode_window:
            self.god_mode_window.kill()
            self.god_mode_window = None
        else:
            # Place Control Panel window at bottom-left, above control bar
            win_w, win_h = 300, 400
            margin = 20
            control_bar_h = 60
            win_x = margin
            win_y = self.height - win_h - control_bar_h - margin
            if win_y < margin:
                win_y = margin

            self.god_mode_window = UIWindow(
                rect=pygame.Rect(win_x, win_y, win_w, win_h),
                manager=self.manager,
                window_display_title='Control Panel'
            )
            # Add a scrolling container inside the window to allow all controls to be accessible
            self.god_mode_scroller = UIScrollingContainer(
                relative_rect=pygame.Rect(10, 10, win_w - 20, win_h - 20),
                manager=self.manager,
                container=self.god_mode_window,
                allow_scroll_x=False,
                allow_scroll_y=True
            )
            # Create a larger content panel inside the scroller; children go here
            self.god_mode_content = UIPanel(
                relative_rect=pygame.Rect(0, 0, win_w - 20, win_h),
                manager=self.manager,
                container=self.god_mode_scroller
            )
            
            # Add Sliders to Control Panel Window (inside scroller)
            y = 10
            self.sliders = {}
            
            params = [
                ('Infection Prob', 'infection_prob', 0.0, 1.0),
                ('Infection Radius', 'infection_radius', 1.0, 50.0),
                ('Recovery Rate', 'recovery_rate', 0.0, 0.5),
                ('Vaccination Rate', 'vaccination_rate', 0.0, 0.1),
                ('Spatial Spillover', 'spatial_spillover_factor', 0.0, 1.0)
            ]
            
            for label, attr, min_v, max_v in params:
                UILabel(
                    relative_rect=pygame.Rect(10, y, 200, 20),
                    text=label,
                    manager=self.manager,
                    container=self.god_mode_content
                )
                
                current_val = getattr(self.engine, attr)
                
                slider = UIHorizontalSlider(
                    relative_rect=pygame.Rect(10, y + 25, 260, 20),
                    start_value=current_val,
                    value_range=(min_v, max_v),
                    manager=self.manager,
                    container=self.god_mode_content
                )
                
                self.sliders[slider] = attr
                y += 60
            
            # Add Road Snapping Toggle Button
            self.btn_road_snap = UIButton(
                relative_rect=pygame.Rect(10, y, 260, 30),
                text=f"Road Snapping: {'ON' if self.engine.use_road_snapping else 'OFF'}",
                manager=self.manager,
                container=self.god_mode_content
            )
            y += 40

            # Add Speed control inside Control Panel
            UILabel(
                relative_rect=pygame.Rect(10, y, 200, 20),
                text='Sim Speed',
                manager=self.manager,
                container=self.god_mode_content
            )
            self.god_mode_speed_slider = UIHorizontalSlider(
                relative_rect=pygame.Rect(10, y + 25, 260, 20),
                start_value=self.speed,
                value_range=(0.5, 20.0),
                manager=self.manager,
                container=self.god_mode_content
            )
            # Set content height and inform scroller so the scrollbar appears
            content_height = y + 120
            self.god_mode_content.set_dimensions((win_w - 20, content_height))
            self.god_mode_scroller.set_scrollable_area_dimensions((win_w - 20, content_height))

    def toggle_pause(self):
        """Toggle pause state via keyboard shortcut"""
        self.paused = not self.paused
        self.btn_pause.set_text("Play" if self.paused else "Pause")

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
            elif event.ui_element == self.btn_minimap:
                # Toggle remains, but default is Always; if set to Auto, it will still render in main
                self.show_minimap_always = not self.show_minimap_always
                self.btn_minimap.set_text(f"Minimap: {'Always' if self.show_minimap_always else 'Auto'}")
            elif self.god_mode_window and hasattr(self, 'btn_road_snap') and event.ui_element == self.btn_road_snap:
                self.engine.use_road_snapping = not self.engine.use_road_snapping
                self.btn_road_snap.set_text(f"Road Snapping: {'ON' if self.engine.use_road_snapping else 'OFF'}")
                
        elif event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
            if event.ui_element == self.slider_speed:
                self.speed = event.value
                self.speed_label.set_text(f"Speed: {self.speed:.1f}x")
                # Propagate to engine movement speed
                if hasattr(self.engine, 'set_speed_multiplier'):
                    self.engine.set_speed_multiplier(self.speed)
            
            # Handle God Mode Sliders
            if self.god_mode_window:
                # Engine-bound sliders
                if event.ui_element in self.sliders:
                    attr = self.sliders[event.ui_element]
                    setattr(self.engine, attr, event.value)
                # God Mode speed slider
                if hasattr(self, 'god_mode_speed_slider') and event.ui_element == self.god_mode_speed_slider:
                    self.speed = event.value
                    self.speed_label.set_text(f"Speed: {self.speed:.1f}x")
                    if hasattr(self.engine, 'set_speed_multiplier'):
                        self.engine.set_speed_multiplier(self.speed)

    def update(self, time_delta, stats_manager=None):
        self.manager.update(time_delta)
        if stats_manager:
            self.dashboard.update(stats_manager)

    def draw(self, screen):
        self.manager.draw_ui(screen)
