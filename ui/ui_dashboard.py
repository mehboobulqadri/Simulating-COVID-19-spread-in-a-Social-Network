import pygame
import pygame_gui
from pygame_gui.elements import UIWindow, UIImage, UILabel
from entities.person import State

class UIDashboard:
    def __init__(self, manager, x, y):
        self.manager = manager
        self.width = 320
        self.height = 240
        
        self.window = UIWindow(
            rect=pygame.Rect(x, y, self.width, self.height),
            manager=self.manager,
            window_display_title='Live Statistics',
            object_id='#stats_window'
        )
        
        # Surface for the graph
        self.graph_width = self.width - 30
        self.graph_height = self.height - 80
        self.graph_surface = pygame.Surface((self.graph_width, self.graph_height))
        
        self.graph_image = UIImage(
            relative_rect=pygame.Rect(10, 40, self.graph_width, self.graph_height),
            image_surface=self.graph_surface,
            manager=self.manager,
            container=self.window
        )
        
        # Legend Labels
        self.labels = {}
        states = [State.INFECTIOUS, State.RECOVERED, State.DECEASED]
        colors = {
            State.INFECTIOUS: (255, 50, 50),
            State.RECOVERED: (50, 200, 50),
            State.DECEASED: (150, 150, 150)
        }
        
        x_off = 10
        for s in states:
            lbl = UILabel(
                relative_rect=pygame.Rect(x_off, 5, 90, 20),
                text=f"{s.name[:3]}: 0",
                manager=self.manager,
                container=self.window
            )
            self.labels[s] = lbl
            x_off += 95
            
        self.colors = {
            State.SUSCEPTIBLE: (100, 200, 255),
            State.EXPOSED: (255, 255, 100),
            State.INFECTIOUS: (255, 50, 50),
            State.RECOVERED: (50, 200, 50),
            State.DECEASED: (150, 150, 150),
            State.VACCINATED: (200, 100, 255)
        }

    def update(self, stats_manager):
        if not self.window.visible:
            return

        # Update Labels
        latest = stats_manager.get_latest_counts()
        for s, lbl in self.labels.items():
            lbl.set_text(f"{s.name[:3]}: {latest.get(s, 0)}")
            
        # Redraw Graph
        self.graph_surface.fill((30, 30, 30))
        pygame.draw.rect(self.graph_surface, (60, 60, 60), self.graph_surface.get_rect(), 1)
        
        if not stats_manager.time_points or len(stats_manager.time_points) < 2:
            self.graph_image.set_image(self.graph_surface)
            return

        # Normalize
        max_val = 0
        for s in State:
            if stats_manager.history[s]:
                max_val = max(max_val, max(stats_manager.history[s]))
        
        if max_val == 0: max_val = 1
        
        w = self.graph_width
        h = self.graph_height
        
        x_step = w / (stats_manager.max_history - 1)
        
        for s in State:
            points = []
            history = stats_manager.history[s]
            # Only draw last N points that fit
            # Actually stats_manager limits history size, so we draw all
            
            for i, val in enumerate(history):
                px = i * x_step
                py = h - (val / max_val) * h
                points.append((px, py))
            
            if len(points) > 1:
                pygame.draw.lines(self.graph_surface, self.colors[s], False, points, 2)
                
        self.graph_image.set_image(self.graph_surface)
