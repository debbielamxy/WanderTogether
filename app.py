from flask import Flask, render_template, request, redirect
from datetime import datetime
import os
import json
from pathlib import Path

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


def load_survey_weights():
    """Load predefined weights for compatibility factors"""
    # Simplified weights based on typical travel companion preferences
    return {
        'budget': 0.15,
        'pace': 0.12,
        'interests': 0.18,
        'style': 0.10,
        'sleep': 0.08,
        'gender': 0.12,
        'age': 0.10
    }


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
    Compute top 6 recommendations using hybrid algorithm
    Returns list of (profile, final_score, compatibility_score) tuples
    """
    # Get hybrid algorithm results
    hybrid_results = compute_hybrid_algorithm(user, weights, SIMULATED_PROFILES)
    
    # Extract recommendations from hybrid results (key is 'Safety-Enhanced Empirical')
    recommendations = hybrid_results.get('Safety-Enhanced Empirical', [])
    
    # Return top 6 recommendations
    return recommendations[:6]


@app.route('/recommend', methods=['POST'])
def recommend():
    weights = load_survey_weights()
    user = parse_user_form(request.form)
    
    # Get top 6 hybrid recommendations
    recommendations = compute_hybrid_recommendations(user, weights)
    
    return render_template('results.html', recommendations=recommendations, weights=weights, user=user)



@app.route('/submit_matches', methods=['POST'])
def submit_matches():
    # 'selected' checkboxes have values like 'profile_id::score::compatibility::trust'
    selections = request.form.getlist('selected')
    if not selections:
        return "No selections made", 400
    if len(selections) < 1 or len(selections) > 6:
        return "Select between 1 and 6 candidates", 400

    # reconstruct user from hidden fields
    user = parse_user_form(request.form)
    
    # Log selections for analysis (simplified logging)
    log_data = []
    for selection in selections:
        parts = selection.split('::')
        if len(parts) >= 4:
            profile_id = parts[0]
            final_score = parts[1]
            compatibility_score = parts[2]
            trust_score = parts[3]
            
            log_data.append([
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
    
    # Simple logging to console (can be enhanced later)
    print(f"User {user.get('name', 'Unknown')} submitted {len(selections)} matches")
    for log_entry in log_data:
        print(f"  - Profile {log_entry[2]}: Score {log_entry[3]}, Compatibility {log_entry[4]}, Trust {log_entry[5]}")

    return redirect('/?msg=Matches+Submitted')


@app.route('/status', methods=['GET'])
def status():
    return {'status': 'ok'}

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    debug = os.getenv('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', port=port, debug=debug)
