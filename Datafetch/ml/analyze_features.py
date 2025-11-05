#!/usr/bin/env python3
"""
Feature Importance Analysis
Analyzes trained model to identify most important features and detect potential data leakage
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple

# Suspicious features that could indicate data leakage
LEAKAGE_SUSPECTS = [
    'odds_decimal',
    'odds_implied_prob',
    'market_prob',
    'favorite_rank',
    'odds_rank',
    'sp_',  # Starting price features
    'morning_odds',
    'forecast_odds'
]


class FeatureAnalyzer:
    """Analyze feature importance and detect potential data leakage"""
    
    def __init__(self, model_path: str, feature_cols_path: str):
        """
        Initialize analyzer
        
        Args:
            model_path: Path to trained XGBoost model (.json)
            feature_cols_path: Path to feature columns list (.json)
        """
        self.model_path = Path(model_path)
        self.feature_cols_path = Path(feature_cols_path)
        self.model = None
        self.feature_columns = None
        self.importance_df = None
        
    def load_model(self):
        """Load trained XGBoost model"""
        try:
            import xgboost as xgb
            
            if not self.model_path.exists():
                raise FileNotFoundError(f"Model not found: {self.model_path}")
            
            self.model = xgb.Booster()
            self.model.load_model(str(self.model_path))
            print(f"✓ Loaded model from {self.model_path.name}")
            
        except Exception as e:
            raise RuntimeError(f"Failed to load model: {e}")
    
    def load_feature_columns(self):
        """Load feature column names"""
        if not self.feature_cols_path.exists():
            raise FileNotFoundError(f"Feature columns file not found: {self.feature_cols_path}")
        
        with open(self.feature_cols_path, 'r') as f:
            self.feature_columns = json.load(f)
        
        print(f"✓ Loaded {len(self.feature_columns)} feature columns")
    
    def extract_importance(self, importance_type: str = 'gain') -> pd.DataFrame:
        """
        Extract feature importance from model
        
        Args:
            importance_type: Type of importance ('gain', 'weight', 'cover')
        
        Returns:
            DataFrame with features and importance scores
        """
        print(f"\nExtracting feature importance (type: {importance_type})...")
        
        importance_dict = self.model.get_score(importance_type=importance_type)
        
        if not importance_dict:
            print("⚠️  No feature importance scores available")
            return pd.DataFrame()
        
        # Create DataFrame
        importance_df = pd.DataFrame({
            'feature': list(importance_dict.keys()),
            'importance': list(importance_dict.values())
        }).sort_values('importance', ascending=False).reset_index(drop=True)
        
        # Add rank
        importance_df['rank'] = range(1, len(importance_df) + 1)
        
        # Calculate percentage
        total_importance = importance_df['importance'].sum()
        importance_df['percentage'] = (importance_df['importance'] / total_importance * 100)
        importance_df['cumulative_pct'] = importance_df['percentage'].cumsum()
        
        self.importance_df = importance_df
        
        print(f"✓ Extracted importance for {len(importance_df)} features")
        print(f"  Top 10 features account for {importance_df.head(10)['percentage'].sum():.1f}% of total importance")
        
        return importance_df
    
    def detect_leakage(self) -> Dict[str, List[str]]:
        """
        Detect potential data leakage by identifying suspicious features
        
        Returns:
            Dict with leakage categories and affected features
        """
        print("\n" + "="*80)
        print("DATA LEAKAGE DETECTION")
        print("="*80)
        
        leakage_found = {
            'high_risk': [],
            'medium_risk': [],
            'low_risk': []
        }
        
        if self.importance_df is None or len(self.importance_df) == 0:
            print("⚠️  No importance data to analyze")
            return leakage_found
        
        # Check top 20 features for suspicious patterns
        top_features = self.importance_df.head(20)
        
        for _, row in top_features.iterrows():
            feature = row['feature']
            rank = row['rank']
            pct = row['percentage']
            
            # Check if feature matches leakage patterns
            is_suspicious = any(suspect.lower() in feature.lower() for suspect in LEAKAGE_SUSPECTS)
            
            if is_suspicious:
                if rank <= 5:
                    leakage_found['high_risk'].append(feature)
                    print(f"🚨 HIGH RISK (Rank {rank}, {pct:.1f}%): {feature}")
                elif rank <= 10:
                    leakage_found['medium_risk'].append(feature)
                    print(f"⚠️  MEDIUM RISK (Rank {rank}, {pct:.1f}%): {feature}")
                else:
                    leakage_found['low_risk'].append(feature)
                    print(f"⚡ LOW RISK (Rank {rank}, {pct:.1f}%): {feature}")
        
        # Summary
        total_suspicious = sum(len(v) for v in leakage_found.values())
        
        print("\n" + "="*80)
        print("LEAKAGE SUMMARY")
        print("="*80)
        
        if total_suspicious == 0:
            print("✅ No obvious data leakage detected in top 20 features")
        else:
            print(f"⚠️  Found {total_suspicious} suspicious features in top 20:")
            print(f"   - High risk: {len(leakage_found['high_risk'])} features")
            print(f"   - Medium risk: {len(leakage_found['medium_risk'])} features")
            print(f"   - Low risk: {len(leakage_found['low_risk'])} features")
            
            if len(leakage_found['high_risk']) > 0:
                print("\n⚠️  WARNING: High-risk features in top 5 suggest possible data leakage!")
                print("   These features may contain information not available before the race.")
        
        return leakage_found
    
    def visualize_importance(self, top_n: int = 30, output_path: str = None):
        """
        Create visualization of feature importance
        
        Args:
            top_n: Number of top features to display
            output_path: Path to save plot (optional)
        """
        if self.importance_df is None or len(self.importance_df) == 0:
            print("⚠️  No importance data to visualize")
            return
        
        print(f"\nGenerating feature importance visualization (top {top_n})...")
        
        # Get top N features
        top_features = self.importance_df.head(top_n).copy()
        
        # Identify suspicious features
        top_features['is_suspicious'] = top_features['feature'].apply(
            lambda x: any(suspect.lower() in x.lower() for suspect in LEAKAGE_SUSPECTS)
        )
        
        # Create figure
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 10))
        
        # Plot 1: Horizontal bar chart
        colors = ['#ff6b6b' if suspicious else '#4ecdc4' 
                  for suspicious in top_features['is_suspicious']]
        
        ax1.barh(range(len(top_features)), top_features['importance'], color=colors)
        ax1.set_yticks(range(len(top_features)))
        ax1.set_yticklabels(top_features['feature'], fontsize=9)
        ax1.set_xlabel('Importance Score (Gain)', fontsize=11, fontweight='bold')
        ax1.set_title(f'Top {top_n} Most Important Features', fontsize=13, fontweight='bold')
        ax1.invert_yaxis()
        ax1.grid(axis='x', alpha=0.3)
        
        # Add legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#4ecdc4', label='Normal Feature'),
            Patch(facecolor='#ff6b6b', label='Suspicious Feature (Possible Leakage)')
        ]
        ax1.legend(handles=legend_elements, loc='lower right')
        
        # Plot 2: Cumulative importance
        ax2.plot(range(1, len(self.importance_df) + 1), 
                self.importance_df['cumulative_pct'], 
                linewidth=2, color='#4ecdc4')
        ax2.axhline(y=80, color='r', linestyle='--', alpha=0.5, label='80% threshold')
        ax2.axhline(y=90, color='orange', linestyle='--', alpha=0.5, label='90% threshold')
        ax2.set_xlabel('Number of Features', fontsize=11, fontweight='bold')
        ax2.set_ylabel('Cumulative Importance (%)', fontsize=11, fontweight='bold')
        ax2.set_title('Cumulative Feature Importance', fontsize=13, fontweight='bold')
        ax2.grid(alpha=0.3)
        ax2.legend()
        
        # Add text annotations for key percentages
        features_80 = self.importance_df[self.importance_df['cumulative_pct'] <= 80].shape[0]
        features_90 = self.importance_df[self.importance_df['cumulative_pct'] <= 90].shape[0]
        ax2.text(features_80, 82, f'{features_80} features', ha='center', fontsize=9, color='red')
        ax2.text(features_90, 92, f'{features_90} features', ha='center', fontsize=9, color='orange')
        
        plt.tight_layout()
        
        # Save plot
        if output_path:
            output_path = Path(output_path)
        else:
            output_path = self.model_path.parent / 'feature_importance_analysis.png'
        
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"✓ Saved visualization to {output_path}")
        
        plt.close()
    
    def print_top_features(self, n: int = 30):
        """Print top N features with details"""
        if self.importance_df is None or len(self.importance_df) == 0:
            print("⚠️  No importance data available")
            return
        
        print("\n" + "="*80)
        print(f"TOP {n} MOST IMPORTANT FEATURES")
        print("="*80)
        print(f"{'Rank':<6} {'Feature':<40} {'Importance':>12} {'%':>8} {'Cumulative %':>12}")
        print("-"*80)
        
        for _, row in self.importance_df.head(n).iterrows():
            feature = row['feature']
            is_suspicious = any(suspect.lower() in feature.lower() for suspect in LEAKAGE_SUSPECTS)
            flag = " 🚨" if is_suspicious else ""
            
            print(f"{int(row['rank']):<6} {feature:<40} {row['importance']:>12.2f} {row['percentage']:>7.2f}% {row['cumulative_pct']:>11.2f}%{flag}")
    
    def save_report(self, output_path: str = None):
        """Save detailed analysis report"""
        if output_path:
            output_path = Path(output_path)
        else:
            output_path = self.model_path.parent / 'feature_analysis_report.csv'
        
        if self.importance_df is not None and len(self.importance_df) > 0:
            # Add leakage flag column
            self.importance_df['potential_leakage'] = self.importance_df['feature'].apply(
                lambda x: any(suspect.lower() in x.lower() for suspect in LEAKAGE_SUSPECTS)
            )
            
            self.importance_df.to_csv(output_path, index=False)
            print(f"\n✓ Saved detailed report to {output_path}")
    
    def run_full_analysis(self, top_n: int = 30):
        """Run complete feature analysis pipeline"""
        print("="*80)
        print("FEATURE IMPORTANCE ANALYSIS")
        print("="*80)
        
        # Load model and features
        self.load_model()
        self.load_feature_columns()
        
        # Extract importance
        self.extract_importance(importance_type='gain')
        
        # Print top features
        self.print_top_features(n=top_n)
        
        # Detect leakage
        leakage_results = self.detect_leakage()
        
        # Visualize
        self.visualize_importance(top_n=top_n)
        
        # Save report
        self.save_report()
        
        print("\n" + "="*80)
        print("✓ FEATURE ANALYSIS COMPLETE")
        print("="*80)
        
        return {
            'importance_df': self.importance_df,
            'leakage_results': leakage_results
        }


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze feature importance and detect data leakage')
    parser.add_argument('--model', type=str, default='models/xgboost_flat.json',
                       help='Path to trained model')
    parser.add_argument('--features', type=str, default='models/feature_columns_flat.json',
                       help='Path to feature columns JSON')
    parser.add_argument('--top-n', type=int, default=30,
                       help='Number of top features to display')
    
    args = parser.parse_args()
    
    # Resolve paths relative to script location
    script_dir = Path(__file__).parent
    model_path = script_dir / args.model
    features_path = script_dir / args.features
    
    if not model_path.exists():
        print(f"❌ Model not found: {model_path}")
        print(f"   Train a model first using: python train_baseline.py")
        return 1
    
    if not features_path.exists():
        print(f"❌ Feature columns not found: {features_path}")
        return 1
    
    # Run analysis
    analyzer = FeatureAnalyzer(str(model_path), str(features_path))
    
    try:
        analyzer.run_full_analysis(top_n=args.top_n)
        return 0
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

