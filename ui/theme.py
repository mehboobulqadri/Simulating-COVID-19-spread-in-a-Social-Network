import pygame

class UITheme:
    # Colors
    BG_COLOR = (30, 30, 40, 230) # Dark Blue-Grey, Transparent
    BORDER_COLOR = (100, 100, 120)
    TEXT_COLOR = (220, 220, 220)
    ACCENT_COLOR = (0, 150, 200) # Cyan/Blue
    HIGHLIGHT_COLOR = (50, 180, 230)
    WARNING_COLOR = (200, 50, 50)
    SUCCESS_COLOR = (50, 200, 50)
    
    # Fonts
    _font_cache = {}
    
    @staticmethod
    def get_font(size=16, bold=False):
        key = (size, bold)
        if key not in UITheme._font_cache:
            UITheme._font_cache[key] = pygame.font.SysFont("Segoe UI", size, bold=bold)
        return UITheme._font_cache[key]
        
    @staticmethod
    def draw_panel_bg(screen, rect):
        # Glassmorphism effect (simple)
        s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        s.fill(UITheme.BG_COLOR)
        screen.blit(s, (rect.x, rect.y))
        pygame.draw.rect(screen, UITheme.BORDER_COLOR, rect, 1, border_radius=10)
        
    @staticmethod
    def draw_button(screen, rect, text, active=False, hover=False):
        color = UITheme.ACCENT_COLOR if active else (60, 60, 70)
        if hover and not active:
            color = (80, 80, 90)
            
        pygame.draw.rect(screen, color, rect, border_radius=5)
        pygame.draw.rect(screen, UITheme.BORDER_COLOR, rect, 1, border_radius=5)
        
        font = UITheme.get_font(14, bold=True)
        text_surf = font.render(text, True, UITheme.TEXT_COLOR)
        text_rect = text_surf.get_rect(center=rect.center)
        screen.blit(text_surf, text_rect)
