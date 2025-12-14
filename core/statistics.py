from entities.person import State
import numpy as np

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
        
        # Advanced metrics history
        self.r_values = []  # R-value (avg infections per infected)
        self.doubling_times = []  # Days for active cases to double
        self.mortality_rates = []  # Deaths per day
        self.vaccination_rates = []  # % vaccinated
        self.infection_counts = []  # Total infections per day
        
    def update(self, cities, current_time, engine=None):
        # Aggregate counts
        counts = {s: 0 for s in State}
        vaccinated_count = 0
        
        for city in cities:
            for district in city.districts:
                for person in district.people:
                    counts[person.state] += 1
                    if person.is_vaccinated:
                        vaccinated_count += 1
                    
        # Record history
        self.time_points.append(current_time)
        for s in State:
            self.history[s].append(counts[s])
            
        # Calculate advanced metrics
        total_population = sum(counts.values())
        
        # Vaccination rate
        if total_population > 0:
            vax_rate = vaccinated_count / total_population
            self.vaccination_rates.append(vax_rate * 100)
        else:
            self.vaccination_rates.append(0)
        
        # Daily infections (exposed + infectious)
        daily_infections = counts[State.EXPOSED] + counts[State.INFECTIOUS]
        self.infection_counts.append(daily_infections)
        
        # Mortality (new deaths this update)
        if len(self.history[State.DECEASED]) > 1:
            daily_deaths = self.history[State.DECEASED][-1] - self.history[State.DECEASED][-2]
        else:
            daily_deaths = self.history[State.DECEASED][-1] if self.history[State.DECEASED] else 0
        self.mortality_rates.append(max(0, daily_deaths))
        
        # Calculate R-value: avg infections caused by currently infectious people
        # Simplified: R = (new_exposed_today * recovery_period) / infectious_count
        r_value = self._calculate_r_value()
        self.r_values.append(r_value)
        
        # Calculate doubling time
        doubling_time = self._calculate_doubling_time()
        self.doubling_times.append(doubling_time)
            
        # Trim if too long
        if len(self.time_points) > self.max_history:
            self.time_points.pop(0)
            for s in State:
                self.history[s].pop(0)
            self.r_values.pop(0)
            self.doubling_times.pop(0)
            self.mortality_rates.pop(0)
            self.vaccination_rates.pop(0)
            self.infection_counts.pop(0)
    
    def _calculate_r_value(self):
        """Calculate current R-value (avg infections per infectious person)"""
        if len(self.history[State.INFECTIOUS]) < 5:
            return 0.0
        
        # Look at last 5 days of data
        recent_infectious = self.history[State.INFECTIOUS][-5:]
        recent_exposed = self.history[State.EXPOSED][-5:]
        
        avg_infectious = np.mean(recent_infectious)
        avg_new_infected = np.mean(recent_exposed[-3:]) if len(recent_exposed) >= 3 else 0
        
        if avg_infectious > 0:
            # Rough estimate: R ~ new_exposed / infectious (simplified)
            return float(avg_new_infected / avg_infectious) if avg_infectious > 0 else 0.0
        return 0.0
    
    def _calculate_doubling_time(self):
        """Calculate doubling time in days for active infections"""
        if len(self.infection_counts) < 2:
            return float('inf')
        
        # Find when cases doubled
        recent_counts = self.infection_counts[-10:]
        if len(recent_counts) < 2:
            return float('inf')
        
        earliest = recent_counts[0]
        latest = recent_counts[-1]
        
        if earliest <= 0 or latest <= earliest:
            return float('inf')
        
        # Doubling time ~ ln(2) / growth_rate
        growth_factor = latest / earliest
        if growth_factor <= 1:
            return float('inf')
        
        days_elapsed = len(recent_counts) - 1
        doubling_time = days_elapsed * np.log(2) / np.log(growth_factor)
        
        return max(0.1, float(doubling_time))  # Clamp to reasonable value
    
    def get_latest_counts(self):
        if not self.time_points:
            return {s: 0 for s in State}
        return {s: self.history[s][-1] for s in State}
    
    def get_advanced_metrics(self):
        """Return dict of advanced statistics"""
        return {
            'r_value': self.r_values[-1] if self.r_values else 0.0,
            'doubling_time': self.doubling_times[-1] if self.doubling_times else float('inf'),
            'daily_deaths': self.mortality_rates[-1] if self.mortality_rates else 0,
            'vaccination_rate': self.vaccination_rates[-1] if self.vaccination_rates else 0.0,
            'total_infections': self.infection_counts[-1] if self.infection_counts else 0
        }
