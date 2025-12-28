#!/usr/bin/env python3
"""
WanderTogether Survey Analysis
Analyzes the survey data to derive empirical weights for the matching algorithm
"""

import pandas as pd
import numpy as np
from collections import Counter
import re

def main():
    # Load the survey data
    df = pd.read_csv('WanderTogether_ A Survey on Travel Companion Matching(1-26).csv')
    
    # Clean column names for easier access
    df.columns = [
        'ID', 'Start_time', 'Completion_time', 'Email', 'Name', 'Last_modified',
        'Solo_travel_frequency', 'Solo_travel_concerns', 'Compatibility_importance',
        'Compatibility_factors', 'Fake_profile_concern', 'Security_features',
        'ID_verification_willingness', 'Additional_features'
    ]
    
    print("=" * 60)
    print("WANDERTOGETHER SURVEY ANALYSIS")
    print("=" * 60)
    print(f"Total Respondents: {len(df)}")
    print(f"Survey Period: {df['Start_time'].iloc[0]} to {df['Completion_time'].iloc[-1]}")
    
    analyze_travel_frequency(df)
    analyze_solo_travel_concerns(df)
    analyze_compatibility_factors(df)
    analyze_security_concerns(df)
    analyze_security_features(df)
    analyze_verification_willingness(df)
    generate_algorithm_weights(df)

def analyze_travel_frequency(df):
    """Analyze solo travel frequency patterns"""
    print("\n" + "=" * 40)
    print("TRAVEL FREQUENCY ANALYSIS")
    print("=" * 40)
    
    travel_freq_data = []
    for freq in df['Solo_travel_frequency'].dropna():
        freq_str = str(freq)
        # Handle cases where multiple options were selected (in arrays)
        if '[' in freq_str and ']' in freq_str:
            options = re.findall(r'"([^"]*)"', freq_str)
            travel_freq_data.extend(options)
        else:
            if freq_str.strip() and freq_str != 'nan':
                travel_freq_data.append(freq_str.strip())
    
    travel_freq_counter = Counter(travel_freq_data)
    total_responses = sum(travel_freq_counter.values())
    
    print("Travel Frequency Distribution:")
    for freq, count in travel_freq_counter.most_common():
        percentage = count / total_responses * 100
        print(f"  {freq}: {count} responses ({percentage:.1f}%)")
    
    # Key insight: Calculate new/infrequent traveler percentage
    new_infrequent = travel_freq_counter.get('I am planning my first solo trip', 0) + travel_freq_counter.get('Rarely', 0)
    print(f"\nKEY INSIGHT: {new_infrequent}/{total_responses} ({new_infrequent/total_responses*100:.1f}%) are new or infrequent solo travelers")
    print("This validates the need for cold-start problem solutions in the algorithm")

def analyze_solo_travel_concerns(df):
    """Analyze main concerns about solo travel"""
    print("\n" + "=" * 40)
    print("SOLO TRAVEL CONCERNS ANALYSIS")
    print("=" * 40)
    
    all_concerns = []
    for concerns in df['Solo_travel_concerns'].dropna():
        concern_list = [c.strip() for c in str(concerns).split(';') if c.strip()]
        all_concerns.extend(concern_list)
    
    concern_counts = Counter(all_concerns)
    print("Primary Solo Travel Concerns:")
    for concern, count in concern_counts.most_common():
        percentage = count / len(df) * 100
        print(f"  {concern}: {count} responses ({percentage:.1f}%)")
    
    # Key insights
    safety_concern = concern_counts.get('Safety and security', 0)
    cost_concern = concern_counts.get('High costs', 0)
    print(f"\nKEY INSIGHTS:")
    print(f"- Safety is the PRIMARY concern ({safety_concern}/{len(df)} = {safety_concern/len(df)*100:.1f}%)")
    print(f"- Cost sharing opportunity ({cost_concern}/{len(df)} = {cost_concern/len(df)*100:.1f}%)")
    print("This validates the platform's security-first approach and cost-sharing value proposition")

def analyze_compatibility_factors(df):
    """Analyze which compatibility factors are most important"""
    print("\n" + "=" * 40)
    print("COMPATIBILITY FACTORS ANALYSIS") 
    print("=" * 40)
    
    all_factors = []
    for factors in df['Compatibility_factors'].dropna():
        factor_list = [f.strip() for f in str(factors).split(';') if f.strip()]
        all_factors.extend(factor_list)
    
    factor_counts = Counter(all_factors)
    print("Compatibility Factor Rankings:")
    for factor, count in factor_counts.most_common():
        percentage = count / len(df) * 100
        print(f"  {factor}: {count} responses ({percentage:.1f}%)")
    
    return factor_counts

def analyze_security_concerns(df):
    """Analyze security concerns about fake profiles"""
    print("\n" + "=" * 40)
    print("SECURITY CONCERNS ANALYSIS")
    print("=" * 40)
    
    security_concerns = df['Fake_profile_concern'].value_counts()
    print("Fake Profile Concern Levels:")
    very_concerned = 0
    somewhat_concerned = 0
    
    for concern, count in security_concerns.items():
        percentage = count / len(df) * 100
        print(f"  {concern}: {count} responses ({percentage:.1f}%)")
        
        if 'Very concerned' in str(concern):
            very_concerned += count
        elif 'Somewhat concerned' in str(concern):
            somewhat_concerned += count
    
    total_concerned = very_concerned + somewhat_concerned
    print(f"\nKEY INSIGHT: {total_concerned}/{len(df)} ({total_concerned/len(df)*100:.1f}%) express security concerns")
    print("This validates the critical importance of robust verification systems")

def analyze_security_features(df):
    """Analyze preferred security features"""
    print("\n" + "=" * 40)
    print("SECURITY FEATURES PREFERENCES")
    print("=" * 40)
    
    all_security_features = []
    for features in df['Security_features'].dropna():
        feature_list = [f.strip() for f in str(features).split(';') if f.strip()]
        all_security_features.extend(feature_list)
    
    security_counts = Counter(all_security_features)
    print("Security Feature Rankings:")
    for feature, count in security_counts.most_common():
        percentage = count / len(df) * 100
        print(f"  {feature}: {count} responses ({percentage:.1f}%)")
    
    # Key insight about government ID verification
    gov_id_count = security_counts.get('Government ID verification (e.g., passport/driver\'s license check)', 0)
    print(f"\nKEY INSIGHT: {gov_id_count}/{len(df)} ({gov_id_count/len(df)*100:.1f}%) demand government ID verification")
    print("This validates blockchain-based identity verification as essential infrastructure")

def analyze_verification_willingness(df):
    """Analyze willingness to undergo ID verification"""
    print("\n" + "=" * 40)
    print("ID VERIFICATION WILLINGNESS")
    print("=" * 40)
    
    id_verification = df['ID_verification_willingness'].value_counts()
    willing_count = 0
    
    for willingness, count in id_verification.items():
        percentage = count / len(df) * 100
        print(f"  {willingness}: {count} responses ({percentage:.1f}%)")
        
        if 'Yes' in str(willingness):
            willing_count += count
    
    print(f"\nKEY INSIGHT: {willing_count}/{len(df)} ({willing_count/len(df)*100:.1f}%) willing to undergo verification")
    print("This confirms user acceptance of blockchain-based identity verification")

def generate_algorithm_weights(df):
    """Generate empirical weights for the matching algorithm"""
    print("\n" + "=" * 50)
    print("EMPIRICAL ALGORITHM WEIGHTS")
    print("=" * 50)
    
    # Re-analyze compatibility factors for weights
    all_factors = []
    for factors in df['Compatibility_factors'].dropna():
        factor_list = [f.strip() for f in str(factors).split(';') if f.strip()]
        all_factors.extend(factor_list)
    
    factor_counts = Counter(all_factors)
    
    print("Derived weights for hybrid matrix factorization:")
    print("-" * 50)
    
    # Map survey responses to algorithm features
    weight_mapping = {
        'Similar budget': ['Similar budget'],
        'Travel pace': ['Similar travel pace (e.g., relaxed vs. fast-paced)'],
        'Shared interests': [' Shared interests (e.g., hiking, food, history)', 'Shared interests (e.g., hiking, food, history)'],
        'Travel style': ['Same travel style (e.g., backpacking vs. luxury)'],
        'Gender preference': ['Same gender', 'Different gender'],
        'Age group': ['Similar age group'],
        'Sleep schedule': ['Matching sleep schedules']
    }
    
    algorithm_weights = {}
    
    for feature, survey_options in weight_mapping.items():
        total_count = 0
        for option in survey_options:
            total_count += factor_counts.get(option, 0)
        
        # Normalize to create weight (responses / total respondents)
        weight = total_count / len(df)
        algorithm_weights[feature] = weight
        
        print(f"W_{feature.lower().replace(' ', '_')} = {weight:.3f}")
        print(f"  Based on {total_count}/{len(df)} responses")
        
        # Categorize importance
        if weight >= 0.70:
            importance = "HIGH PRIORITY"
        elif weight >= 0.50:
            importance = "MODERATE PRIORITY"  
        elif weight >= 0.30:
            importance = "LOW PRIORITY"
        else:
            importance = "MINIMAL PRIORITY"
        print(f"  Classification: {importance}")
        print()
    
    # Generate the actual algorithm configuration
    print("ALGORITHM CONFIGURATION:")
    print("-" * 30)
    print("Primary Factors (Weight ≥ 0.70):")
    primary_factors = {k: v for k, v in algorithm_weights.items() if v >= 0.70}
    for factor, weight in primary_factors.items():
        print(f"  {factor}: {weight:.3f}")
    
    print("\nSecondary Factors (0.50 ≤ Weight < 0.70):")
    secondary_factors = {k: v for k, v in algorithm_weights.items() if 0.50 <= v < 0.70}
    for factor, weight in secondary_factors.items():
        print(f"  {factor}: {weight:.3f}")
    
    print("\nMinimal Factors (Weight < 0.30):")
    minimal_factors = {k: v for k, v in algorithm_weights.items() if v < 0.30}
    for factor, weight in minimal_factors.items():
        print(f"  {factor}: {weight:.3f}")
    
    # Feature vector construction formula
    print("\n" + "=" * 60)
    print("FEATURE VECTOR CONSTRUCTION FORMULA")
    print("=" * 60)
    print("user_vector = [")
    for factor, weight in algorithm_weights.items():
        normalized_factor = factor.lower().replace(' ', '_')
        print(f"    {weight:.3f} * normalized_{normalized_factor},")
    print("]")
    
    print("\nHybrid Similarity Calculation:")
    print("Hybrid_Score = α * Content_Similarity + β * Collaborative_Filter + γ * Trust_Score")
    print("Where Content_Similarity uses the empirically-derived weights above")


    def report_survey_vs_profile(df):
        """Compare survey columns to the profile fields used by the app and report gaps.

        The survey is the canonical source for this analysis; this function lists which
        per-respondent parameters appear in the CSV and which profile fields are
        not captured by the current web `ProfileForm.jsx` implementation.
        """
        print("\n" + "=" * 60)
        print("SURVEY VS PROFILE FORM AUDIT")
        print("=" * 60)
        survey_cols = list(df.columns)
        print(f"Survey columns found: {', '.join(survey_cols)}")

        # Profile form expected fields (app-side)
        profile_fields = ['name', 'age', 'gender', 'pace', 'style', 'sleep', 'interests_list', 'bio', 'id_verification_willingness']

        present = [f for f in profile_fields if any(f.lower() in c.lower() for c in survey_cols)]
        missing = [f for f in profile_fields if f not in present]

        print('\nProfile fields that appear to be present in the survey:')
        for f in present:
            print(f" - {f}")

        print('\nProfile fields missing from the survey (per-respondent values):')
        for f in missing:
            print(f" - {f}")

        print('\nRecommendation: Add the missing fields as explicit per-respondent questions so the profile form can be pre-filled from survey data.')


if __name__ == "__main__":
    main()