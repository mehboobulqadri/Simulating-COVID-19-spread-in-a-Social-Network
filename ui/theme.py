import pygame

class UITheme:
    """Modern, professional theme for COVID-19 simulation UI"""
    
    # Color palette - Dark modern theme
    BG_COLOR = (22, 25, 32, 245)  # Dark blue-grey with high opacity
    BG_GRADIENT_TOP = (28, 32, 40, 245)
    BG_GRADIENT_BOTTOM = (18, 20, 26, 245)
    
    BORDER_COLOR = (80, 90, 110)
    BORDER_GLOW = (120, 140, 170, 80)
    
    TEXT_COLOR = (230, 235, 245)
    TEXT_SECONDARY = (160, 170, 190)
    TEXT_MUTED = (120, 130, 150)
    
    ACCENT_COLOR = (0, 170, 230)  # Bright cyan
    ACCENT_GLOW = (0, 200, 255, 120)
    
    HIGHLIGHT_COLOR = (40, 200, 255)
    WARNING_COLOR = (255, 90, 90)
    SUCCESS_COLOR = (50, 220, 120)
    INFO_COLOR = (100, 180, 255)
    
    # Button states
    BUTTON_NORMAL = (45, 50, 60)
    BUTTON_HOVER = (60, 70, 85)
    BUTTON_ACTIVE = (0, 150, 200)
    BUTTON_DISABLED = (30, 33, 40)
    
    # Fonts cache
    _font_cache = {}
    
    @staticmethod
    def get_font(size=16, bold=False, italic=False):
        """Get cached font with specified properties"""
        key = (size, bold, italic)
        if key not in UITheme._font_cache:
            try:
                # Try to use a modern sans-serif font
                font_name = "Segoe UI"  # Windows
                if not pygame.font.match_font(font_name):
                    font_name = "Arial"  # Fallback
                
                UITheme._font_cache[key] = pygame.font.SysFont(
                    font_name, size, bold=bold, italic=italic
                )
            except:
                UITheme._font_cache[key] = pygame.font.Font(None, size)
        
        return UITheme._font_cache[key]
    
    @staticmethod
    def draw_panel_bg(screen, rect, gradient=True):
        """Draw modern panel background with optional gradient"""
        s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        
        if gradient:
            # Vertical gradient effect
            for i in range(rect.height):
                t = i / rect.height
                # Interpolate between top and bottom colors
                r = int(UITheme.BG_GRADIENT_TOP[0] * (1-t) + UITheme.BG_GRADIENT_BOTTOM[0] * t)
                g = int(UITheme.BG_GRADIENT_TOP[1] * (1-t) + UITheme.BG_GRADIENT_BOTTOM[1] * t)
                b = int(UITheme.BG_GRADIENT_TOP[2] * (1-t) + UITheme.BG_GRADIENT_BOTTOM[2] * t)
                a = int(UITheme.BG_GRADIENT_TOP[3] * (1-t) + UITheme.BG_GRADIENT_BOTTOM[3] * t)
                pygame.draw.line(s, (r, g, b, a), (0, i), (rect.width, i))
        else:
            s.fill(UITheme.BG_COLOR)
        
        screen.blit(s, (rect.x, rect.y))
        
        # Outer glow
        glow_rect = rect.inflate(6, 6)
        pygame.draw.rect(screen, UITheme.BORDER_GLOW, glow_rect, 3, border_radius=14)
        
        # Main border
        pygame.draw.rect(screen, UITheme.BORDER_COLOR, rect, 2, border_radius=12)
    
    @staticmethod
    def draw_button(screen, rect, text, active=False, hover=False, disabled=False, button_type='normal'):
        """
        Draw a modern button with state-based styling
        
        button_type: 'normal', 'primary', 'success', 'warning', 'danger'
        """
        # Determine button color based on state and type
        if disabled:
            color = UITheme.BUTTON_DISABLED
            text_color = UITheme.TEXT_MUTED
        elif active:
            if button_type == 'success':
                color = UITheme.SUCCESS_COLOR
            elif button_type == 'warning':
                color = (220, 180, 30)
            elif button_type == 'danger':
                color = UITheme.WARNING_COLOR
            else:
                color = UITheme.BUTTON_ACTIVE
            text_color = (255, 255, 255)
        elif hover:
            color = UITheme.BUTTON_HOVER
            text_color = UITheme.TEXT_COLOR
        else:
            color = UITheme.BUTTON_NORMAL
            text_color = UITheme.TEXT_COLOR
        
        # Button shadow (subtle depth)
        shadow_rect = rect.move(0, 2)
        shadow_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        shadow_surf.fill((0, 0, 0, 60))
        screen.blit(shadow_surf, (shadow_rect.x, shadow_rect.y))
        
        # Button background
        pygame.draw.rect(screen, color, rect, border_radius=6)
        
        # Button border
        border_color = UITheme.HIGHLIGHT_COLOR if hover else UITheme.BORDER_COLOR
        if active:
            border_color = UITheme.ACCENT_GLOW[:3]
        pygame.draw.rect(screen, border_color, rect, 2, border_radius=6)
        
        # Highlight effect on hover
        if hover and not active:
            highlight_rect = pygame.Rect(rect.x, rect.y, rect.width, rect.height // 3)
            highlight_surf = pygame.Surface((rect.width, rect.height // 3), pygame.SRCALPHA)
            highlight_surf.fill((255, 255, 255, 20))
            screen.blit(highlight_surf, (highlight_rect.x, highlight_rect.y))
        
        # Button text
        font = UITheme.get_font(14, bold=True)
        text_surf = font.render(text, True, text_color)
        text_rect = text_surf.get_rect(center=rect.center)
        screen.blit(text_surf, text_rect)
    
    @staticmethod
    def draw_status_indicator(screen, pos, active, label="", size=8):
        """Draw a status indicator dot with optional label"""
        color = UITheme.SUCCESS_COLOR if active else UITheme.WARNING_COLOR
        glow_color = (*color[:3], 100)
        
        # Glow
        pygame.draw.circle(screen, glow_color, pos, size + 3)
        # Main dot
        pygame.draw.circle(screen, color, pos, size)
        # Highlight
        highlight_pos = (pos[0] - size // 3, pos[1] - size // 3)
        pygame.draw.circle(screen, (255, 255, 255, 150), highlight_pos, size // 2)
        
        # Label
        if label:
            font = UITheme.get_font(13, bold=True)
            text_color = color if active else UITheme.TEXT_SECONDARY
            text_surf = font.render(label, True, text_color)
            screen.blit(text_surf, (pos[0] + size + 8, pos[1] - 8))
    
    @staticmethod
    def draw_section_header(screen, rect, text):
        """Draw a section header with underline"""
        font = UITheme.get_font(12, bold=True)
        text_surf = font.render(text, True, UITheme.TEXT_SECONDARY)
        screen.blit(text_surf, (rect.x, rect.y))
        
        # Underline
        line_y = rect.y + text_surf.get_height() + 3
        pygame.draw.line(screen, UITheme.BORDER_COLOR, 
                        (rect.x, line_y), 
                        (rect.x + rect.width, line_y), 2)
    
    @staticmethod
    def draw_stat_box(screen, rect, label, value, color=None):
        """Draw a colored stat display box"""
        if color is None:
            color = UITheme.ACCENT_COLOR
        
        # Background with transparency
        bg_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        bg_surf.fill((40, 45, 55, 200))
        screen.blit(bg_surf, (rect.x, rect.y))
        
        # Colored left border
        border_rect = pygame.Rect(rect.x, rect.y, 4, rect.height)
        pygame.draw.rect(screen, color, border_rect, border_radius=2)
        
        # Main border
        pygame.draw.rect(screen, (*color, 150), rect, 1, border_radius=4)
        
        # Label
        label_font = UITheme.get_font(11)
        label_surf = label_font.render(label, True, UITheme.TEXT_SECONDARY)
        screen.blit(label_surf, (rect.x + 10, rect.y + 4))
        
        # Value
        value_font = UITheme.get_font(16, bold=True)
        value_surf = value_font.render(str(value), True, color)
        value_rect = value_surf.get_rect(right=rect.right - 10, centery=rect.centery)
        screen.blit(value_surf, value_rect)
    
    @staticmethod
    def draw_progress_bar(screen, rect, progress, color=None, show_percentage=True):
        """
        Draw a progress bar
        progress: float between 0.0 and 1.0
        """
        if color is None:
            color = UITheme.ACCENT_COLOR
        
        progress = max(0.0, min(1.0, progress))
        
        # Background
        pygame.draw.rect(screen, (40, 45, 55), rect, border_radius=3)
        pygame.draw.rect(screen, UITheme.BORDER_COLOR, rect, 1, border_radius=3)
        
        # Fill
        if progress > 0:
            fill_width = int(rect.width * progress)
            fill_rect = pygame.Rect(rect.x, rect.y, fill_width, rect.height)
            pygame.draw.rect(screen, color, fill_rect, border_radius=3)
            
            # Highlight on filled portion
            highlight_rect = pygame.Rect(rect.x, rect.y, fill_width, rect.height // 2)
            highlight_surf = pygame.Surface((fill_width, rect.height // 2), pygame.SRCALPHA)
            highlight_surf.fill((255, 255, 255, 30))
            screen.blit(highlight_surf, (highlight_rect.x, highlight_rect.y))
        
        # Percentage text
        if show_percentage:
            font = UITheme.get_font(11, bold=True)
            text = f"{int(progress * 100)}%"
            text_surf = font.render(text, True, UITheme.TEXT_COLOR)
            text_rect = text_surf.get_rect(center=rect.center)
            screen.blit(text_surf, text_rect)
    
    @staticmethod
    def draw_tooltip(screen, pos, text_lines, max_width=300):
        """Draw a tooltip at the specified position"""
        font = UITheme.get_font(12)
        padding = 10
        line_height = 18
        
        # Calculate size
        width = max_width
        height = len(text_lines) * line_height + padding * 2
        
        # Position tooltip above cursor
        x = pos[0] - width // 2
        y = pos[1] - height - 10
        
        # Keep on screen
        screen_rect = screen.get_rect()
        if x < 5:
            x = 5
        if x + width > screen_rect.width - 5:
            x = screen_rect.width - width - 5
        if y < 5:
            y = pos[1] + 20
        
        tooltip_rect = pygame.Rect(x, y, width, height)
        
        # Background with shadow
        shadow_rect = tooltip_rect.move(2, 2)
        shadow_surf = pygame.Surface((width, height), pygame.SRCALPHA)
        shadow_surf.fill((0, 0, 0, 100))
        screen.blit(shadow_surf, (shadow_rect.x, shadow_rect.y))
        
        # Main background
        bg_surf = pygame.Surface((width, height), pygame.SRCALPHA)
        bg_surf.fill((30, 35, 45, 250))
        screen.blit(bg_surf, (x, y))
        
        # Border
        pygame.draw.rect(screen, UITheme.BORDER_COLOR, tooltip_rect, 2, border_radius=5)
        
        # Text
        text_y = y + padding
        for line in text_lines:
            text_surf = font.render(line, True, UITheme.TEXT_COLOR)
            screen.blit(text_surf, (x + padding, text_y))
            text_y += line_height