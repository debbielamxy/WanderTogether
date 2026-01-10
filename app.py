from flask import Flask, render_template, request, redirect
import csv
from datetime import datetime
import pandas as pd
from collections import Counter
import os
import psycopg2
from psycopg2.extras import execute_values

app = Flask(__name__)


# Canonical interest choices shown on the form
INTEREST_CHOICES = [
    # Culture & Exploration
    'Historical Sites',
    'Museums & Art',
    'Local Culture',
    'Architecture',
    'Religious Sites',
    'Festivals & Events',

    # Nature & Adventure
    'Hiking & Nature',
    'Beaches & Coast',
    'Wildlife & Animals',
    'National Parks',
    'Mountains & Scenery',
    'Camping & Outdoors',

    # Food & Culinary
    'Street Food',
    'Fine Dining',
    'Cooking Experiences',
    'Wine & Drinks',
    'Coffee Culture',

    # Activities & Sports
    'Water Sports',
    'Adventure Sports',
    'Winter Sports',
    'Photography',
    'Wellness & Spa',

    # Urban & Social
    'Shopping',
    'Nightlife & Bars',
    'Live Music & Concerts',
    'City Exploration',
    'Local Markets',

    # Travel Styles
    'Road Trips',
    'Volunteer Work',
    'Digital Nomad'
]


def load_survey_weights(csv_path='WanderTogether_ A Survey on Travel Companion Matching(1-26).csv'):
    df = pd.read_csv(csv_path)
    all_factors = []
    if 'Which compatibility factors are important to you in a travel companion? (Select up to 3)' in df.columns:
        col = 'Which compatibility factors are important to you in a travel companion? (Select up to 3)'
    else:
        col = 'Compatibility_factors'
    for factors in df[col].dropna():
        factor_list = [f.strip() for f in str(factors).split(';') if f.strip()]
        all_factors.extend(factor_list)
    counts = Counter(all_factors)
    total = len(df)
    feature_map = {
        'budget': ['Similar budget'],
        'pace': ['Similar travel pace (e.g., relaxed vs. fast-paced)'],
        'interests': ['Shared interests (e.g., hiking, food, history)', ' Shared interests (e.g., hiking, food, history)'],
        'style': ['Same travel style (e.g., economical vs. luxury)'],
        'gender': ['Same gender'],  # Only count same-gender preferences
        'age': ['Similar age group'],
        'sleep': ['Matching sleep schedules']
    }
    weights = {}
    for k, opts in feature_map.items():
        c = sum(counts.get(o, 0) for o in opts)
        weights[k] = c / total if total > 0 else 0.0
    return weights


from pathlib import Path
import json

# Prefer loading the fixed JSON snapshot so simulated profiles are deterministic
_json_path = Path(__file__).with_suffix('.json')
if not _json_path.exists():
    _json_path = Path('simulated_profiles.json')

if _json_path.exists():
    with open(_json_path, 'r') as f:
        SIMULATED_PROFILES = json.load(f)
else:
    # fallback to module import
    from simulated_profiles import SIMULATED_PROFILES

# Normalize profile fields (convert sets to lists for Jinja and comparisons)
for p in SIMULATED_PROFILES:
    if isinstance(p.get('interests'), set):
        p['interests'] = list(p['interests'])
    if isinstance(p.get('sleep'), set):
        p['sleep'] = list(p['sleep'])



from hybrid_algorithm import compute_algorithms as compute_hybrid_algorithm


@app.route('/', methods=['GET'])
def index():
    weights = load_survey_weights()
    # optional message from redirects (e.g., after submit)
    msg = request.args.get('msg')
    return render_template('index.html', weights=weights, interest_choices=INTEREST_CHOICES, message=msg)


def parse_user_form(form):
    interests = set(form.getlist('interests'))
    # Map textual pace choices to numeric scale (1 relaxed -> 3 fast)
    pace_text = form.get('pace_text') or form.get('pace')
    # Map textual pace choices to numeric scale (1 relaxed -> 3 fast)
    if pace_text in ('relaxed_itinerary',):
        pace = 1  # Relaxed pace
    elif pace_text in ('spontaneous',):
        pace = 2  # Moderate pace (spontaneous)
    elif pace_text in ('packed_itinerary',):
        pace = 3  # Fast-paced
    else:
        try:
            pace = int(form.get('pace', 2))
        except Exception:
            pace = 2

    sleep_vals = set(form.getlist('sleep'))

    # Infer travel budget from style if budget not provided in UI
    style = form.get('style', 'backpacking')
    # mapping: economical=1, average=2, luxury=3
    if style in ('economical',):
        travel_budget = 1
    elif style in ('average',):
        travel_budget = 2
    elif style in ('luxury',):
        travel_budget = 3
    else:
        travel_budget = 2

    user = {
        'name': form.get('name', ''),
        'age': int(form.get('age', 30)) if form.get('age') else None,
        'gender': form.get('gender', 'prefer_not'),
        'budget': travel_budget,
        'travel_budget': travel_budget,
        'pace': pace,
        'pace_text': pace_text,
        'style': form.get('style', 'backpacking'),
        'cleanliness': form.get('cleanliness', ''),
        'dietary': form.get('dietary', ''),
        'alcohol': form.get('alcohol', ''),
        'smoking': form.get('smoking', ''),
        'fitness': form.get('fitness', ''),
        'interests': interests,
        'sleep': sleep_vals,
        'bio': form.get('bio', '')
    }
    return user


def compute_hybrid_recommendations(user, weights):
    """
    Compute top 8 recommendations using hybrid algorithm
    Returns list of (profile, final_score, compatibility_score) tuples
    """
    # Get hybrid algorithm results
    hybrid_results = compute_hybrid_algorithm(user, weights, SIMULATED_PROFILES)
    
    # Extract recommendations from hybrid results (key is 'Safety-Enhanced Empirical')
    recommendations = hybrid_results.get('Safety-Enhanced Empirical', [])
    
    # Return top 8 recommendations
    return recommendations[:8]


@app.route('/recommend', methods=['POST'])
def recommend():
    weights = load_survey_weights()
    user = parse_user_form(request.form)
    
    # Get top 8 hybrid recommendations
    recommendations = compute_hybrid_recommendations(user, weights)
    
    return render_template('results.html', recommendations=recommendations, weights=weights, user=user)


LOG_PATH = 'hybrid_algorithm_log.csv'

# Header for hybrid algorithm logging
LOG_HEADER = [
    'timestamp',
    'user_name',
    'profile_id',
    'final_score',
    'compatibility_score',
    'trust_score',
    'user_age',
    'user_gender',
    'user_budget',
    'user_pace',
    'user_style',
    'user_interests',
    'user_bio'
]


def ensure_log_header():
    import os
    from pathlib import Path
    # If file exists and non-empty, verify header; otherwise write it
    if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > 0:
        with open(LOG_PATH, 'r', newline='') as f:
            first_line = f.readline().strip()
        expected = ','.join(LOG_HEADER)
        if first_line != expected:
            # Backup old file and start a new one with updated header
            backup = f"{LOG_PATH}.bak.{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
            Path(LOG_PATH).rename(backup)
            with open(LOG_PATH, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(LOG_HEADER)
        with open(LOG_PATH, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(LOG_HEADER)


@app.route('/record', methods=['POST'])
def record():
    ensure_log_header()
    algorithm = request.form.get('algorithm')
    decision = request.form.get('decision')  # 'match' or 'skip'
    profile_id = int(request.form.get('profile_id'))
    profile_name = request.form.get('profile_name')
    score = float(request.form.get('score'))

    # user fields (hidden inputs)
    user = parse_user_form(request.form)
    interests_str = ','.join(sorted(user['interests']))
    sleeps_str = ','.join(sorted(user.get('sleep', [])))

    with open(LOG_PATH, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.utcnow().isoformat(), algorithm, decision, profile_id, profile_name, f"{score:.4f}",
            user.get('name',''), user.get('age',''), user.get('gender',''), user['budget'], user.get('travel_budget',''), user['pace'], user.get('pace_text',''), user['style'],
            user.get('cleanliness',''), user.get('dietary',''), user.get('alcohol',''), user.get('smoking',''), user.get('fitness',''),
            interests_str, sleeps_str, user['bio']
        ])

    # Recompute and re-render results for continued interactions
    weights = load_survey_weights()
    recommendations = compute_hybrid_recommendations(user, weights)
    return render_template('results.html', recommendations=recommendations, weights=weights, user=user, message=f"Recorded {decision} for {profile_name} in {algorithm}")


@app.route('/submit_matches', methods=['POST'])
def submit_matches():
    # 'selected' checkboxes have values like 'profile_id::score::compatibility::trust'
    selections = request.form.getlist('selected')
    if not selections:
        return "No selections made", 400
    if len(selections) < 1 or len(selections) > 8:
        return "Select between 1 and 8 candidates", 400

    # reconstruct user from hidden fields
    user = parse_user_form(request.form)
    
    # Log selections for analysis
    ensure_log_header()
    
    with open(LOG_PATH, 'a', newline='') as f:
        writer = csv.writer(f)
        for selection in selections:
            parts = selection.split('::')
            if len(parts) >= 4:
                profile_id = parts[0]
                final_score = parts[1]
                compatibility_score = parts[2]
                trust_score = parts[3]
                
                writer.writerow([
                    datetime.utcnow().isoformat(),
                    user.get('name',''),
                    profile_id,
                    final_score,
                    compatibility_score,
                    trust_score,
                    user.get('age',''),
                    user.get('gender',''),
                    user['budget'],
                    user['pace'],
                    user.get('style',''),
                    ','.join(sorted(user['interests'])) if user.get('interests') else '',
                    user.get('bio','')
                ])

    return redirect('/?msg=Matches+Submitted')


@app.route('/status', methods=['GET'])
def status():
    return {'status': 'ok'}

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    debug = os.getenv('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', port=port, debug=debug)
