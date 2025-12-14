import csv
from entities.person import State
import json
from datetime import datetime
try:
    import matplotlib
    matplotlib.use('Agg')  # Non-GUI backend
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

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
    
    @staticmethod
    def export_html(filepath, stats_manager, cities=None):
        """Export simulation data as interactive HTML report"""
        try:
            # Calculate demographics
            total_population = 0
            vaccinated_count = 0
            if cities:
                for city in cities:
                    for district in city.districts:
                        for person in district.people:
                            total_population += 1
                            if person.is_vaccinated:
                                vaccinated_count += 1
            
            # Get final counts
            final_counts = stats_manager.get_latest_counts()
            advanced_metrics = stats_manager.get_advanced_metrics()
            
            # Generate inline chart data (as JSON)
            chart_data = {
                'times': stats_manager.time_points,
                'susceptible': stats_manager.history[State.SUSCEPTIBLE],
                'exposed': stats_manager.history[State.EXPOSED],
                'infectious': stats_manager.history[State.INFECTIOUS],
                'recovered': stats_manager.history[State.RECOVERED],
                'deceased': stats_manager.history[State.DECEASED],
                'r_values': stats_manager.r_values,
                'vaccination_rates': stats_manager.vaccination_rates
            }
            
            html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>COVID-19 Epidemic Simulation Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background-color: #2c3e50;
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #2c3e50;
        }}
        .metric-label {{
            color: #7f8c8d;
            font-size: 0.9em;
            margin-top: 5px;
        }}
        .chart-container {{
            position: relative;
            height: 400px;
            margin-bottom: 30px;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .demographics {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .demographics h3 {{
            margin-top: 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        td, th {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #2c3e50;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>COVID-19 Epidemic Simulation Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-value">{final_counts[State.SUSCEPTIBLE]:,}</div>
            <div class="metric-label">Susceptible</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{final_counts[State.INFECTIOUS]:,}</div>
            <div class="metric-label">Currently Infected</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{final_counts[State.RECOVERED]:,}</div>
            <div class="metric-label">Recovered</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{final_counts[State.DECEASED]:,}</div>
            <div class="metric-label">Deaths</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{advanced_metrics['r_value']:.2f}</div>
            <div class="metric-label">R-Value (Reproduction)</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{advanced_metrics['vaccination_rate']:.1f}%</div>
            <div class="metric-label">Vaccination Rate</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{advanced_metrics['doubling_time']:.1f}</div>
            <div class="metric-label">Doubling Time (days)</div>
        </div>
    </div>
    
    <div class="chart-container">
        <canvas id="epidemicChart"></canvas>
    </div>
    
    <div class="chart-container">
        <canvas id="vaccinationChart"></canvas>
    </div>
    
    <div class="demographics">
        <h3>Simulation Summary</h3>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
            <tr>
                <td>Total Population</td>
                <td>{total_population:,}</td>
            </tr>
            <tr>
                <td>Vaccinated</td>
                <td>{vaccinated_count:,} ({100*vaccinated_count/max(1, total_population):.1f}%)</td>
            </tr>
            <tr>
                <td>Total Deaths</td>
                <td>{final_counts[State.DECEASED]:,}</td>
            </tr>
            <tr>
                <td>Mortality Rate</td>
                <td>{100*final_counts[State.DECEASED]/max(1, total_population):.2f}%</td>
            </tr>
            <tr>
                <td>Attack Rate</td>
                <td>{100*(final_counts[State.RECOVERED] + final_counts[State.DECEASED])/max(1, total_population):.2f}%</td>
            </tr>
            <tr>
                <td>Simulation Days</td>
                <td>{len(stats_manager.time_points)}</td>
            </tr>
        </table>
    </div>
    
    <script>
        const chartData = {json.dumps(chart_data)};
        
        // Epidemic Chart
        const epidemicCtx = document.getElementById('epidemicChart').getContext('2d');
        new Chart(epidemicCtx, {{
            type: 'line',
            data: {{
                labels: chartData.times.map((t, i) => i % 10 === 0 ? t.toFixed(1) : ''),
                datasets: [
                    {{
                        label: 'Susceptible',
                        data: chartData.susceptible,
                        borderColor: 'rgb(0, 0, 255)',
                        tension: 0.1,
                        fill: false
                    }},
                    {{
                        label: 'Exposed',
                        data: chartData.exposed,
                        borderColor: 'rgb(255, 200, 0)',
                        tension: 0.1,
                        fill: false
                    }},
                    {{
                        label: 'Infectious',
                        data: chartData.infectious,
                        borderColor: 'rgb(255, 0, 0)',
                        tension: 0.1,
                        fill: false
                    }},
                    {{
                        label: 'Recovered',
                        data: chartData.recovered,
                        borderColor: 'rgb(0, 128, 0)',
                        tension: 0.1,
                        fill: false
                    }},
                    {{
                        label: 'Deceased',
                        data: chartData.deceased,
                        borderColor: 'rgb(0, 0, 0)',
                        tension: 0.1,
                        fill: false
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    title: {{ display: true, text: 'Epidemic Progression' }}
                }},
                scales: {{
                    y: {{ beginAtZero: true }}
                }}
            }}
        }});
        
        // Vaccination Chart
        const vaccinationCtx = document.getElementById('vaccinationChart').getContext('2d');
        new Chart(vaccinationCtx, {{
            type: 'line',
            data: {{
                labels: chartData.times.map((t, i) => i % 10 === 0 ? t.toFixed(1) : ''),
                datasets: [
                    {{
                        label: 'Vaccination Rate (%)',
                        data: chartData.vaccination_rates,
                        borderColor: 'rgb(50, 150, 200)',
                        backgroundColor: 'rgba(50, 150, 200, 0.1)',
                        tension: 0.1,
                        fill: true
                    }},
                    {{
                        label: 'R-Value',
                        data: chartData.r_values,
                        borderColor: 'rgb(200, 100, 50)',
                        tension: 0.1,
                        fill: false,
                        yAxisID: 'y1'
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                interaction: {{ mode: 'index', intersect: false }},
                plugins: {{
                    title: {{ display: true, text: 'Vaccination & R-Value Trends' }}
                }},
                scales: {{
                    y: {{ beginAtZero: true, max: 100 }},
                    y1: {{ type: 'linear', position: 'right', beginAtZero: true }}
                }}
            }}
        }});
    </script>
</body>
</html>
            """
            
            with open(filepath, 'w') as f:
                f.write(html_content)
            
            print(f"✓ HTML report exported to {filepath}")
            return True
        except Exception as e:
            print(f"HTML export failed: {e}")
            return False
    
    @staticmethod
    def export_json(filepath, stats_manager, cities=None):
        """Export simulation data as JSON"""
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'time_points': stats_manager.time_points,
                'statistics': {
                    'susceptible': stats_manager.history[State.SUSCEPTIBLE],
                    'exposed': stats_manager.history[State.EXPOSED],
                    'infectious': stats_manager.history[State.INFECTIOUS],
                    'recovered': stats_manager.history[State.RECOVERED],
                    'deceased': stats_manager.history[State.DECEASED],
                },
                'advanced_metrics': {
                    'r_values': stats_manager.r_values,
                    'doubling_times': stats_manager.doubling_times,
                    'mortality_rates': stats_manager.mortality_rates,
                    'vaccination_rates': stats_manager.vaccination_rates
                },
                'final_metrics': stats_manager.get_advanced_metrics()
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"✓ JSON report exported to {filepath}")
            return True
        except Exception as e:
            print(f"JSON export failed: {e}")
