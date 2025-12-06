import math

class TimeEngine:
    def __init__(self):
        self.ticks = 0
        self.day_length = 2400 # 100 ticks per hour
        self.current_day = 0
        self.hour = 0
        self.is_daytime = True
        self.circadian_factor = 1.0 # Multiplier for activity/infection
        
    def update(self):
        self.ticks += 1
        if self.ticks >= self.day_length:
            self.ticks = 0
            self.current_day += 1
            
        self.hour = (self.ticks / self.day_length) * 24
        
        # Circadian Rhythm Logic
        # 6 AM to 10 PM is "Active" time
        if 6 <= self.hour < 22:
            self.is_daytime = True
            # Peak activity at noon (12:00)
            # Simple sine wave approximation for activity
            self.circadian_factor = 0.5 + 0.5 * math.sin((self.hour - 6) * math.pi / 16)
        else:
            self.is_daytime = False
            self.circadian_factor = 0.1 # Low activity at night
            
    def get_time_string(self):
        minute = int((self.hour % 1) * 60)
        return f"Day {self.current_day} - {int(self.hour):02d}:{minute:02d}"
