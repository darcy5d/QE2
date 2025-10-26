#!/usr/bin/env python3
"""
Master Diagnostic Runner
Runs all diagnostic tools and generates comprehensive report
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime
import json


class DiagnosticRunner:
    """Run all diagnostic tools"""
    
    def __init__(self, race_type: str = 'Flat'):
        """
        Initialize diagnostic runner
        
        Args:
            race_type: Race type ('Flat', 'Hurdle', 'Chase')
        """
        self.race_type = race_type
        self.script_dir = Path(__file__).parent
        self.results = {}
        
    def run_script(self, script_name: str, description: str) -> bool:
        """
        Run a diagnostic script
        
        Args:
            script_name: Name of script to run
            description: Human-readable description
        
        Returns:
            True if successful, False otherwise
        """
        print("\n" + "="*80)
        print(f"RUNNING: {description}")
        print("="*80)
        
        script_path = self.script_dir / script_name
        
        if not script_path.exists():
            print(f"❌ Script not found: {script_name}")
            return False
        
        try:
            # Run script
            result = subprocess.run(
                [sys.executable, str(script_path), '--race-type', self.race_type],
                capture_output=False,
                text=True,
                cwd=str(self.script_dir)
            )
            
            if result.returncode == 0:
                print(f"\n✓ {description} completed successfully")
                return True
            else:
                print(f"\n❌ {description} failed with code {result.returncode}")
                return False
                
        except Exception as e:
            print(f"\n❌ {description} failed: {e}")
            return False
    
    def run_feature_analysis(self) -> bool:
        """Run feature importance analysis"""
        return self.run_script(
            'analyze_features.py',
            'Feature Importance Analysis & Data Leakage Detection'
        )
    
    def run_data_validation(self) -> bool:
        """Run training data validation"""
        return self.run_script(
            'validate_training_data.py',
            'Training Data Validation'
        )
    
    def run_calibration_diagnostics(self) -> bool:
        """Run calibration diagnostics"""
        return self.run_script(
            'calibration_diagnostics.py',
            'Calibration Diagnostics'
        )
    
    def run_calibration_training(self) -> bool:
        """Run calibration training"""
        return self.run_script(
            'train_calibration.py',
            'Calibration Training (Temperature Scaling)'
        )
    
    def generate_summary_report(self):
        """Generate HTML summary report"""
        print("\n" + "="*80)
        print("GENERATING COMPREHENSIVE REPORT")
        print("="*80)
        
        race_type_lower = self.race_type.lower()
        
        # Collect outputs
        model_dir = self.script_dir / 'models'
        
        # Feature analysis
        feature_analysis_csv = model_dir / 'feature_analysis_report.csv'
        feature_importance_png = model_dir / 'feature_importance_analysis.png'
        
        # Calibration
        calibration_report = model_dir / 'calibration_report.txt'
        calibration_curve = model_dir / 'calibration_curve.png'
        reliability_diagram = model_dir / 'reliability_diagram.png'
        calibration_params = model_dir / f'calibration_params_{race_type_lower}.json'
        
        # Generate HTML report
        html_output = model_dir / 'diagnostic_report.html'
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Model Diagnostics Report - {self.race_type} Racing</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 40px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-left: 4px solid #3498db;
            padding-left: 10px;
        }}
        .section {{
            background: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .status-good {{
            color: #27ae60;
            font-weight: bold;
        }}
        .status-warning {{
            color: #f39c12;
            font-weight: bold;
        }}
        .status-bad {{
            color: #e74c3c;
            font-weight: bold;
        }}
        img {{
            max-width: 100%;
            height: auto;
            margin: 20px 0;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        .metric {{
            display: inline-block;
            background: #ecf0f1;
            padding: 10px 20px;
            margin: 10px 10px 10px 0;
            border-radius: 5px;
        }}
        .metric-label {{
            font-weight: bold;
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        .metric-value {{
            font-size: 1.5em;
            color: #2c3e50;
        }}
        pre {{
            background: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }}
        .timestamp {{
            color: #7f8c8d;
            font-size: 0.9em;
            text-align: right;
        }}
    </style>
</head>
<body>
    <h1>🔍 Model Diagnostics Report</h1>
    <div class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
    
    <div class="section">
        <h2>📊 Model Information</h2>
        <div class="metric">
            <div class="metric-label">Race Type</div>
            <div class="metric-value">{self.race_type}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Model File</div>
            <div class="metric-value">xgboost_{race_type_lower}.json</div>
        </div>
    </div>
    
    <div class="section">
        <h2>🎯 Feature Importance Analysis</h2>
        <p>Identifies most important features and detects potential data leakage.</p>
"""
        
        if feature_importance_png.exists():
            html_content += f"""
        <img src="feature_importance_analysis.png" alt="Feature Importance">
        <p><a href="feature_analysis_report.csv">📄 Download detailed feature analysis (CSV)</a></p>
"""
        else:
            html_content += """
        <p class="status-warning">⚠️ Feature importance visualization not generated</p>
"""
        
        html_content += """
    </div>
    
    <div class="section">
        <h2>📈 Calibration Analysis</h2>
        <p>Evaluates how well predicted probabilities match actual outcomes.</p>
"""
        
        if calibration_report.exists():
            with open(calibration_report, 'r') as f:
                calibration_text = f.read()
            html_content += f"""
        <pre>{calibration_text}</pre>
"""
        
        if calibration_curve.exists():
            html_content += """
        <h3>Calibration Curve</h3>
        <img src="calibration_curve.png" alt="Calibration Curve">
"""
        
        if reliability_diagram.exists():
            html_content += """
        <h3>Reliability by Rank</h3>
        <img src="reliability_diagram.png" alt="Reliability Diagram">
"""
        
        if not (calibration_curve.exists() or reliability_diagram.exists()):
            html_content += """
        <p class="status-warning">⚠️ Calibration visualizations not generated</p>
"""
        
        html_content += """
    </div>
    
    <div class="section">
        <h2>🎛️ Calibration Parameters</h2>
"""
        
        if calibration_params.exists():
            with open(calibration_params, 'r') as f:
                params = json.load(f)
            
            temperature = params.get('temperature', 1.0)
            
            if temperature > 1.5:
                status_class = "status-warning"
                interpretation = "Model is OVERCONFIDENT - reducing prediction confidence"
            elif temperature < 0.7:
                status_class = "status-warning"
                interpretation = "Model is UNDERCONFIDENT - increasing prediction confidence"
            else:
                status_class = "status-good"
                interpretation = "Model calibration is reasonable"
            
            html_content += f"""
        <div class="metric">
            <div class="metric-label">Temperature</div>
            <div class="metric-value {status_class}">{temperature:.4f}</div>
        </div>
        <p><strong>Interpretation:</strong> {interpretation}</p>
        <p class="status-good">✓ Calibration parameters will be automatically applied to future predictions</p>
"""
        else:
            html_content += """
        <p class="status-warning">⚠️ No calibration parameters trained yet</p>
        <p>Run: <code>python train_calibration.py --race-type {race_type}</code></p>
"""
        
        html_content += """
    </div>
    
    <div class="section">
        <h2>📋 Recommendations</h2>
        <ul>
"""
        
        # Add recommendations based on results
        if calibration_params.exists():
            with open(calibration_params, 'r') as f:
                params = json.load(f)
            temperature = params.get('temperature', 1.0)
            
            if temperature > 1.5:
                html_content += """
            <li><strong>High temperature detected:</strong> Model is overconfident. Calibration will reduce stake sizes on marginal bets.</li>
"""
            elif temperature < 0.7:
                html_content += """
            <li><strong>Low temperature detected:</strong> Model is underconfident. Calibration will increase confidence in top picks.</li>
"""
        
        html_content += """
            <li><strong>Monitor performance:</strong> Track ROI and win rates on real bets to validate calibration effectiveness.</li>
            <li><strong>Retrain periodically:</strong> Re-run diagnostics after adding significant new training data.</li>
            <li><strong>Check feature importance:</strong> Ensure no suspicious features (odds-based) dominate the model.</li>
        </ul>
    </div>
    
    <div class="section">
        <h2>🔄 Next Steps</h2>
        <ol>
            <li>Review feature importance to ensure no data leakage</li>
            <li>Verify training data size and quality is sufficient</li>
            <li>Check calibration curves for systematic bias</li>
            <li>Test calibrated predictions on upcoming races</li>
            <li>Monitor real-world betting performance</li>
        </ol>
    </div>
    
    <div class="timestamp">
        <p>All diagnostic outputs are saved in: <code>Datafetch/ml/models/</code></p>
    </div>
</body>
</html>
"""
        
        # Write HTML report
        with open(html_output, 'w') as f:
            f.write(html_content)
        
        print(f"\n✓ Comprehensive report saved to: {html_output}")
        print(f"\n📊 Open in browser: file://{html_output}")
    
    def run_all_diagnostics(self):
        """Run complete diagnostic pipeline"""
        print("="*80)
        print("MODEL DIAGNOSTICS & CALIBRATION PIPELINE")
        print(f"Race Type: {self.race_type}")
        print("="*80)
        
        # Track results
        success_count = 0
        total_steps = 4
        
        # Step 1: Feature Analysis
        if self.run_feature_analysis():
            success_count += 1
            self.results['feature_analysis'] = 'success'
        else:
            self.results['feature_analysis'] = 'failed'
        
        # Step 2: Data Validation
        if self.run_data_validation():
            success_count += 1
            self.results['data_validation'] = 'success'
        else:
            self.results['data_validation'] = 'failed'
        
        # Step 3: Calibration Diagnostics
        if self.run_calibration_diagnostics():
            success_count += 1
            self.results['calibration_diagnostics'] = 'success'
        else:
            self.results['calibration_diagnostics'] = 'failed'
        
        # Step 4: Calibration Training
        if self.run_calibration_training():
            success_count += 1
            self.results['calibration_training'] = 'success'
        else:
            self.results['calibration_training'] = 'failed'
        
        # Generate summary report
        self.generate_summary_report()
        
        # Final summary
        print("\n" + "="*80)
        print("DIAGNOSTIC PIPELINE COMPLETE")
        print("="*80)
        print(f"\nCompleted: {success_count}/{total_steps} steps")
        
        if success_count == total_steps:
            print("\n✓✓ All diagnostics completed successfully!")
            print("\nYour model is now calibrated and ready for betting.")
            print("Calibration will be automatically applied to all future predictions.")
            return 0
        else:
            print(f"\n⚠️  Some diagnostics failed ({total_steps - success_count} failures)")
            print("Review the output above for details.")
            return 1


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run all model diagnostics')
    parser.add_argument('--race-type', type=str, default='Flat',
                       choices=['Flat', 'Hurdle', 'Chase'],
                       help='Race type to analyze')
    
    args = parser.parse_args()
    
    # Run diagnostics
    runner = DiagnosticRunner(race_type=args.race_type)
    return runner.run_all_diagnostics()


if __name__ == "__main__":
    sys.exit(main())

