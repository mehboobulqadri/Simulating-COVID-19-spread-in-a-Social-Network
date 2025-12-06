import pygame
from entities.person import State

class Dashboard:
    def __init__(self, screen_width, screen_height):
        self.width = 300
        self.height = 150
        self.x = 10
        self.y = screen_height - self.height - 10
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        
        self.font = pygame.font.SysFont("Arial", 12)
        
        # Colors for graph lines
        self.colors = {
            State.SUSCEPTIBLE: (100, 200, 255),
            State.EXPOSED: (255, 255, 100),
            State.INFECTIOUS: (255, 50, 50),
            State.RECOVERED: (50, 200, 50),
            State.DECEASED: (100, 100, 100),
            State.VACCINATED: (200, 100, 255)
        }

    def render(self, screen, stats_manager):
        # Background
        pygame.draw.rect(screen, (30, 30, 30, 200), self.rect)
        pygame.draw.rect(screen, (100, 100, 100), self.rect, 1)
        
        if not stats_manager.time_points:
            return

        # Draw Graph
        # Normalize values to fit height
        max_val = 0
        for s in State:
            if stats_manager.history[s]:
                max_val = max(max_val, max(stats_manager.history[s]))
        
        if max_val == 0:
            max_val = 1
            
        graph_h = self.height - 20
        graph_w = self.width - 20
        x_start = self.x + 10
        y_bottom = self.y + self.height - 10
        
        # Draw lines
        points_count = len(stats_manager.time_points)
        if points_count < 2:
            return
            
        x_step = graph_w / (stats_manager.max_history - 1)
        
        for s in State:
            points = []
            history = stats_manager.history[s]
            for i, val in enumerate(history):
                px = x_start + i * x_step
                py = y_bottom - (val / max_val) * graph_h
                points.append((px, py))
            
            if len(points) > 1:
                pygame.draw.lines(screen, self.colors[s], False, points, 2)
                
        # Legend / Current Stats
        latest = stats_manager.get_latest_counts()
        y_off = self.y - 20
        x_off = self.x
        
        # Draw mini legend above graph
        legend_items = [
            (State.INFECTIOUS, "Inf"),
            (State.RECOVERED, "Rec"),
            (State.DECEASED, "Dec")
        ]
        
        for i, (state, label) in enumerate(legend_items):
            color = self.colors[state]
            text = f"{label}: {latest[state]}"
            surf = self.font.render(text, True, color)
            screen.blit(surf, (x_off + i * 80, y_off))
