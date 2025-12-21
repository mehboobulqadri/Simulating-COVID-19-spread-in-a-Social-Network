import pickle
import os
from entities.person import State

class PersistenceManager:
    @staticmethod
    def save_state(filepath, cities, time_engine, stats_manager):
        # We need to serialize the entire state
        # Pickle is easiest for Python objects, but we need to be careful with Pygame surfaces
        # Fortunately, our entities don't store surfaces directly (except maybe cached ones?)
        # TextureManager handles textures, so we should be fine if we don't pickle that.
        
        # Create a data dict
        data = {
            'cities': cities,
            'time': {
                'ticks': time_engine.ticks,
                'current_day': time_engine.current_day
            },
            'stats': {
                'history': stats_manager.history,
                'time_points': stats_manager.time_points
            }
        }
        
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(data, f)
            return True
        except Exception as e:
            print(f"Save failed: {e}")
            return False

    @staticmethod
    def load_state(filepath):
        try:
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
            return data
        except Exception as e:
            print(f"Load failed: {e}")
            return None
