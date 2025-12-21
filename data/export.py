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
                    'susceptible': [int(x) for x in stats_manager.history[State.SUSCEPTIBLE]],
                    'exposed': [int(x) for x in stats_manager.history[State.EXPOSED]],
                    'infectious': [int(x) for x in stats_manager.history[State.INFECTIOUS]],
                    'recovered': [int(x) for x in stats_manager.history[State.RECOVERED]],
                    'deceased': [int(x) for x in stats_manager.history[State.DECEASED]],
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
            return False

    @staticmethod
    def generate_comprehensive_report(output_dir, stats_manager):
        """Generate reports in DOCX, PDF, MD, and LaTeX formats"""
        try:
            import os
            from docx import Document
            from docx.shared import Inches
            from matplotlib.backends.backend_pdf import PdfPages
            
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            # Fixed filename to keep only the latest report
            base_filename = "latest_simulation_report"
            
            # --- Generate Charts ---
            print("Generating charts...")
            chart_paths = DataExporter._generate_charts(output_dir, stats_manager)
            
            # --- Generate DOCX ---
            print("Generating DOCX report...")
            DataExporter._generate_docx(output_dir, base_filename, stats_manager, chart_paths)
            
            # --- Generate PDF ---
            print("Generating PDF report...")
            DataExporter._generate_pdf(output_dir, base_filename, stats_manager)
            
            # --- Generate Markdown ---
            print("Generating Markdown report...")
            DataExporter._generate_markdown(output_dir, base_filename, stats_manager, chart_paths)
            
            # --- Generate LaTeX ---
            print("Generating LaTeX report...")
            DataExporter._generate_latex(output_dir, base_filename, stats_manager, chart_paths)
            
            return True
        except Exception as e:
            print(f"Report generation failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def _generate_charts(output_dir, stats_manager):
        """Generate Matplotlib charts and return their paths"""
        paths = {}
        if not HAS_MATPLOTLIB: return paths
        import os
        
        times = stats_manager.time_points
        
        # 1. SEIR Curve
        plt.figure(figsize=(10, 6))
        plt.plot(times, stats_manager.history[State.SUSCEPTIBLE], label='Susceptible', color='blue')
        plt.plot(times, stats_manager.history[State.EXPOSED], label='Exposed', color='orange')
        plt.plot(times, stats_manager.history[State.INFECTIOUS], label='Infectious', color='red')
        plt.plot(times, stats_manager.history[State.RECOVERED], label='Recovered', color='green')
        plt.plot(times, stats_manager.history[State.DECEASED], label='Deceased', color='black')
        plt.title('Epidemic Curve (SEIRD)')
        plt.xlabel('Days')
        plt.ylabel('Population')
        plt.legend()
        plt.grid(True, alpha=0.3)
        seir_path = os.path.join(output_dir, 'seir_curve.png')
        plt.savefig(seir_path, dpi=300)
        plt.close()
        paths['seir'] = seir_path
        
        # 2. R-Value
        plt.figure(figsize=(10, 6))
        plt.plot(times, stats_manager.r_values, label='R-Value', color='purple')
        plt.axhline(y=1.0, color='r', linestyle='--', label='Threshold (R=1)')
        plt.title('Effective Reproduction Number (Rt)')
        plt.xlabel('Days')
        plt.ylabel('R-Value')
        plt.legend()
        plt.grid(True, alpha=0.3)
        r_path = os.path.join(output_dir, 'r_value.png')
        plt.savefig(r_path, dpi=300)
        plt.close()
        paths['r_value'] = r_path
        
        # 3. Vaccination vs Deceased
        fig, ax1 = plt.figure(figsize=(10, 6)), plt.gca()
        ax1.set_xlabel('Days')
        ax1.set_ylabel('Vaccination %', color='blue')
        ax1.plot(times, stats_manager.vaccination_rates, color='blue', label='Vaccination %')
        ax1.tick_params(axis='y', labelcolor='blue')
        
        ax2 = ax1.twinx()
        ax2.set_ylabel('Cumulative Deaths', color='black')
        ax2.plot(times, stats_manager.history[State.DECEASED], color='black', label='Deaths')
        ax2.tick_params(axis='y', labelcolor='black')
        
        plt.title('Vaccination Impact on Mortality')
        fig.tight_layout()
        vax_path = os.path.join(output_dir, 'vaccination_impact.png')
        plt.savefig(vax_path, dpi=300)
        plt.close()
        paths['vaccination'] = vax_path
        
        return paths

    @staticmethod
    def _generate_docx(output_dir, base_name, stats_manager, chart_paths):
        import os
        from docx import Document
        from docx.shared import Inches
        
        doc = Document()
        doc.add_heading('COVID-19 Simulation Report', 0)
        
        doc.add_paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Simulation Summary
        doc.add_heading('Executive Summary', level=1)
        final_counts = stats_manager.get_latest_counts()
        adv_metrics = stats_manager.get_advanced_metrics()
        
        table = doc.add_table(rows=1, cols=2)
        table.style = 'Light Shading Accent 1'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Metric'
        hdr_cells[1].text = 'Value'
        
        metrics = [
            ('Total Infections', f"{adv_metrics['total_infections']:,}"),
            ('Total Deaths', f"{final_counts[State.DECEASED]:,}"),
            ('Survivors', f"{final_counts[State.RECOVERED]:,}"),
            ('Peak R-Value', f"{max(stats_manager.r_values) if stats_manager.r_values else 0:.2f}"),
            ('Final Vaccination Rate', f"{adv_metrics['vaccination_rate']:.1f}%")
        ]
        
        for metric, value in metrics:
            row_cells = table.add_row().cells
            row_cells[0].text = metric
            row_cells[1].text = value
            
        # Charts
        doc.add_heading('Epidemic Progression', level=1)
        if 'seir' in chart_paths:
            doc.add_picture(chart_paths['seir'], width=Inches(6))
            
        doc.add_heading('Transmission Dynamics', level=1)
        if 'r_value' in chart_paths:
            doc.add_picture(chart_paths['r_value'], width=Inches(6))
            
        doc.add_heading('Intervention Impact', level=1)
        if 'vaccination' in chart_paths:
            doc.add_picture(chart_paths['vaccination'], width=Inches(6))
            
            
        # --- Educational Context ---
        doc.add_heading('Understanding the Metrics', level=1)
        
        doc.add_heading('SEIR Model', level=2)
        doc.add_paragraph(
            "The SEIR model tracks the flow of people between four states: "
            "Susceptible (S), Exposed (E), Infectious (I), and Recovered (R). "
            "Exposed individuals have contracted the virus but are not yet infectious (incubation period)."
        )
        
        doc.add_heading('Effective Reproduction Number (Rt)', level=2)
        doc.add_paragraph(
            "Rt represents the average number of people infected by a single infectious person "
            "at a specific point in time. An Rt > 1.0 means the epidemic is growing, "
            "while Rt < 1.0 means it is shrinking."
        )
        
        doc.add_heading('Herd Immunity', level=2)
        doc.add_paragraph(
            "Vaccinaton reduces the pool of susceptible individuals. When a sufficient proportion "
            "of the population is immune, transmission slows down significantly, protecting even "
            "those who are not vaccinated."
        )
            
        doc.save(os.path.join(output_dir, f"{base_name}.docx"))

    @staticmethod
    def _generate_pdf(output_dir, base_name, stats_manager):
        import os
        from matplotlib.backends.backend_pdf import PdfPages
        
        if not HAS_MATPLOTLIB: return
        
        pdf_path = os.path.join(output_dir, f"{base_name}.pdf")
        with PdfPages(pdf_path) as pdf:
            # Page 1: Summary Text
            plt.figure(figsize=(11, 8.5))
            plt.axis('off')
            plt.text(0.5, 0.9, "COVID-19 Simulation Report", ha='center', fontsize=24)
            plt.text(0.5, 0.85, f"Generated: {datetime.now().strftime('%Y-%m-%d')}", ha='center')
            
            final_counts = stats_manager.get_latest_counts()
            info_text = (
                f"Total Infections: {final_counts[State.INFECTIOUS] + final_counts[State.RECOVERED] + final_counts[State.DECEASED]:,}\n"
                f"Total Deaths: {final_counts[State.DECEASED]:,}\n"
                f"Recovered: {final_counts[State.RECOVERED]:,}\n"
                f"Peak R0: {max(stats_manager.r_values) if stats_manager.r_values else 0:.2f}\n"
            )
            plt.text(0.1, 0.6, info_text, fontsize=14, family='monospace')
            pdf.savefig()
            plt.close()
            
            # Page 2: Graphs
            # We explicitly replot here to save into PDF context
            times = stats_manager.time_points
            
            plt.figure(figsize=(10, 6))
            plt.plot(times, stats_manager.history[State.SUSCEPTIBLE], label='S')
            plt.plot(times, stats_manager.history[State.EXPOSED], label='E')
            plt.plot(times, stats_manager.history[State.INFECTIOUS], label='I')
            plt.plot(times, stats_manager.history[State.RECOVERED], label='R')
            plt.plot(times, stats_manager.history[State.DECEASED], label='D')
            plt.legend()
            plt.title('SEIRD Model')
            pdf.savefig()
            plt.close()
            
            plt.figure(figsize=(10, 6))
            plt.plot(times, stats_manager.r_values, label='Rt', color='purple')
            plt.axhline(1, color='red', linestyle='--')
            plt.title('Reproduction Number')
            pdf.savefig()
            plt.close()
            
            # Page 3: Educational Context
            plt.figure(figsize=(11, 8.5))
            plt.axis('off')
            plt.text(0.5, 0.9, "Understanding Your Report", ha='center', fontsize=20, weight='bold')
            
            explanation_text = (
                "SEIR Model:\n"
                "- Susceptible: Healthy individuals who can catch the virus.\n"
                "- Exposed: Infected but not yet contagious (incubation).\n"
                "- Infectious: Actively spreading the virus to neighbors.\n"
                "- Recovered: Generated immunity after infection.\n\n"
                "R-Value (Rt):\n"
                "- Rt > 1.0: Outbreak is growing exponentially.\n"
                "- Rt < 1.0: Outbreak is under control/decaying.\n"
                "- Target: Keep Rt below 1.0 via lockdown or vaccination."
            )
            plt.text(0.1, 0.5, explanation_text, fontsize=12, family='sans-serif', va='center')
            pdf.savefig()
            plt.close()

    @staticmethod
    def _generate_markdown(output_dir, base_name, stats_manager, chart_paths):
        import os
        md_path = os.path.join(output_dir, f"{base_name}.md")
        final_counts = stats_manager.get_latest_counts()
        
        with open(md_path, 'w') as f:
            f.write(f"# COVID-19 Simulation Report\n\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Executive Summary\n\n")
            f.write(f"- **Total Deaths**: {final_counts[State.DECEASED]:,}\n")
            f.write(f"- **Active Cases**: {final_counts[State.INFECTIOUS]:,}\n")
            f.write(f"- **Recovered**: {final_counts[State.RECOVERED]:,}\n\n")
            
            f.write("## Visualizations\n\n")
            if 'seir' in chart_paths:
                f.write(f"![SEIR Curve]({os.path.basename(chart_paths['seir'])})\n\n")
            if 'r_value' in chart_paths:
                f.write(f"![R-Value]({os.path.basename(chart_paths['r_value'])})\n\n")
            if 'vaccination' in chart_paths:
                f.write(f"![Vaccination]({os.path.basename(chart_paths['vaccination'])})\n\n")
            
            f.write("## Understanding the Metrics\n\n")
            f.write("### SEIR Model\n")
            f.write("- **Susceptible**: Healthy individuals who can catch the virus.\n")
            f.write("- **Exposed**: Infected but not yet contagious (incubation).\n")
            f.write("- **Infectious**: Actively spreading the virus to neighbors.\n")
            f.write("- **Recovered**: Generated immunity after infection.\n\n")
            
            f.write("### R-Value (Rt)\n")
            f.write("- **Rt > 1.0**: Outbreak is growing exponentially.\n")
            f.write("- **Rt < 1.0**: Outbreak is under control/decaying.\n")

    @staticmethod
    def _generate_latex(output_dir, base_name, stats_manager, chart_paths):
        import os
        tex_path = os.path.join(output_dir, f"{base_name}.tex")
        final_counts = stats_manager.get_latest_counts()
        
        with open(tex_path, 'w') as f:
            f.write(r"""\documentclass{article}
\usepackage{graphicx}
\usepackage{hyperref}
\title{COVID-19 Simulation Report}
\author{Antigravity Simulator}
\date{\today}
\begin{document}
\maketitle
\section{Summary}
""")
            f.write(f"Total Deaths: {final_counts[State.DECEASED]} \\\\\n")
            f.write(f"Active Cases: {final_counts[State.INFECTIOUS]} \\\\\n")
            
            f.write(r"\section{Visualizations}" + "\n")
            
            if 'seir' in chart_paths:
                f.write(r"\begin{figure}[h]" + "\n")
                f.write(r"\centering" + "\n")
                f.write(f"\\includegraphics[width=0.8\\textwidth]{{{os.path.basename(chart_paths['seir'])}}}\n")
                f.write(r"\caption{Epidemic SEIR Curve}" + "\n")
                f.write(r"\end{figure}" + "\n")
                
            f.write(r"\end{document}")
