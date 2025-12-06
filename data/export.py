import csv
from entities.person import State

class DataExporter:
    @staticmethod
    def export_csv(filepath, stats_manager):
        try:
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                
                # Header
                header = ['Time'] + [s.name for s in State]
                writer.writerow(header)
                
                # Rows
                # Assuming all history lists are same length
                length = len(stats_manager.time_points)
                for i in range(length):
                    row = [stats_manager.time_points[i]]
                    for s in State:
                        row.append(stats_manager.history[s][i])
                    writer.writerow(row)
            return True
        except Exception as e:
            print(f"Export failed: {e}")
            return False
