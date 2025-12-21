import pygame
from entities.person import State
from ui.theme import UITheme

class ActivityPanel:
    """Display real-time activity metrics and agent distribution."""
    
    def __init__(self, screen_width, screen_height):
        self.width = 280
        self.height = 150
        self.x = screen_width - self.width - 10
        self.y = 10
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        
        # Activity colors
        self.activity_colors = {
            'at_work': (100, 100, 200),
            'at_school': (220, 120, 120),
            'at_lunch': (240, 180, 60),
            'at_leisure': (50, 160, 80),
            'home': (100, 200, 100),
            'commuting': (200, 150, 100)
        }
    
    def render(self, screen, engine, time_engine=None):
        """Render activity panel with real-time metrics."""
        # Background
        UITheme.draw_panel_bg(screen, self.rect)
        
        # Title
        title_font = UITheme.get_font(13, bold=True)
        title = title_font.render("Activity Snapshot", True, (200, 200, 200))
        screen.blit(title, (self.x + 10, self.y + 8))
        
        # Get current hour
        hour = 0
        if time_engine:
            hour = int(time_engine.hour) % 24
        
        # Count agents in different activities
        total_agents = engine.num_people if hasattr(engine, 'num_people') else 1600
        at_work = 0
        at_school = 0
        at_leisure = 0
        at_lunch = 0
        home = 0
        
        # Use hour-based scheduling for activity distribution
        if 8 <= hour < 12:
            at_work = int(total_agents * 0.4)
            at_school = int(total_agents * 0.3)
            home = int(total_agents * 0.2)
            at_lunch = int(total_agents * 0.1)
        elif 12 <= hour < 13:
            at_lunch = int(total_agents * 0.5)
            at_work = int(total_agents * 0.3)
            home = int(total_agents * 0.2)
        elif 13 <= hour < 17:
            at_work = int(total_agents * 0.5)
            at_school = int(total_agents * 0.25)
            home = int(total_agents * 0.25)
        elif 18 <= hour < 20:
            at_leisure = int(total_agents * 0.4)
            home = int(total_agents * 0.6)
        else:
            home = total_agents
        
        # Draw activity metrics
        font_small = UITheme.get_font(11)
        y_off = self.y + 30
        line_h = 18
        
        activities = [
            ('Work', at_work, self.activity_colors['at_work']),
            ('School', at_school, self.activity_colors['at_school']),
            ('Lunch', at_lunch, self.activity_colors['at_lunch']),
            ('Leisure', at_leisure, self.activity_colors['at_leisure']),
            ('Home', home, self.activity_colors['home'])
        ]
        
        x_label = self.x + 10
        x_count = self.x + 160
        
        for label, count, color in activities:
            text = font_small.render(label, True, color)
            screen.blit(text, (x_label, y_off))
            
            # Bar indicator
            bar_width = int((count / total_agents) * 100) if total_agents > 0 else 0
            pygame.draw.rect(screen, color, (x_count, y_off, bar_width, 12), border_radius=2)
            pygame.draw.rect(screen, (100, 100, 100), (x_count, y_off, 100, 12), 1, border_radius=2)
            
            # Count
            count_text = font_small.render(str(count), True, (200, 200, 200))
            screen.blit(count_text, (x_count + 110, y_off))
            
            y_off += line_h
        
        # Time display at bottom
        time_font = UITheme.get_font(12, bold=True)
        time_text = time_font.render(f"Hour: {hour:02d}:00", True, (150, 180, 255))
        screen.blit(time_text, (self.x + 10, self.y + self.height - 25))
        
        # Border
        pygame.draw.rect(screen, (100, 100, 120), self.rect, 2)
