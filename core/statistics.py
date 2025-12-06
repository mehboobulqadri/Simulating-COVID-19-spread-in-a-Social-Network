from entities.person import State

class StatisticsManager:
    def __init__(self):
        self.history = {
            State.SUSCEPTIBLE: [],
            State.EXPOSED: [],
            State.INFECTIOUS: [],
            State.RECOVERED: [],
            State.DECEASED: [],
            State.VACCINATED: []
        }
        self.time_points = []
        self.max_history = 200 # Keep last N points for graph
        
    def update(self, cities, current_time):
        # Aggregate counts
        counts = {s: 0 for s in State}
        
        for city in cities:
            for district in city.districts:
                for person in district.people:
                    counts[person.state] += 1
                    
        # Record history
        self.time_points.append(current_time)
        for s in State:
            self.history[s].append(counts[s])
            
        # Trim if too long
        if len(self.time_points) > self.max_history:
            self.time_points.pop(0)
            for s in State:
                self.history[s].pop(0)
                
    def get_latest_counts(self):
        if not self.time_points:
            return {s: 0 for s in State}
        return {s: self.history[s][-1] for s in State}
