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
    'Food Markets',
    'Cooking Experiences',
    'Wine & Drinks',
    'Coffee Culture',

    # Activities & Sports
    'Water Sports',
    'Adventure Sports',
    'Winter Sports',
    'Cycling',
    'Photography',
    'Wellness & Spa',

    # Urban & Social
    'Shopping',
    'Nightlife & Bars',
    'Live Music & Concerts',
    'Art Galleries',
    'City Exploration',
    'Local Markets',

    # Travel Styles
    'Road Trips',
    'Backpacking',
    'Luxury Travel',
    'Volunteer Work',
    'Digital Nomad',
    'Slow Travel'
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
        'style': ['Same travel style (e.g., backpacking vs. luxury)'],
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



from recommendation_algorithms import compute_algorithms as compute_algorithms_module


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
    if pace_text in ('relaxed_itinerary', 'spontaneous'):
        pace = 1
    elif pace_text in ('flexible', 'mixed'):
        pace = 2
    elif pace_text in ('packed_itinerary', 'itinerary'):
        pace = 3
    else:
        try:
            pace = int(form.get('pace', 2))
        except Exception:
            pace = 2

    sleep_vals = set(form.getlist('sleep'))

    # Infer travel budget from style if budget not provided in UI
    style = form.get('style', 'backpacking')
    # mapping: backpacking=1, economical=1, midrange/average=2, comfort=2, luxury=3
    if style in ('backpacking', 'economical'):
        travel_budget = 1
    elif style in ('midrange', 'average', 'comfort', 'occasional_splurging', 'occasional_splurge'):
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


def compute_algorithms(user, weights):
    algorithms = {}

    # delegate to the recommendation_algorithms module
    return compute_algorithms_module(user, weights, SIMULATED_PROFILES)


@app.route('/recommend', methods=['POST'])
def recommend():
    weights = load_survey_weights()
    user = parse_user_form(request.form)
    algorithms = compute_algorithms(user, weights)
    return render_template('results.html', algorithms=algorithms, weights=weights, user=user)


LOG_PATH = 'algorithm_evaluation_log.csv'

# New compact header focused on algorithm evaluation
LOG_HEADER = [
    'user_name',
    'algorithm1_recommendation_name','algorithm1_recommendation_id','algorithm1_compatibility','algorithm1_trust','algorithm1_matched_successfully',
    'algorithm2_recommendation_name','algorithm2_recommendation_id','algorithm2_compatibility','algorithm2_trust','algorithm2_matched_successfully',
    'algorithm3_recommendation_name','algorithm3_recommendation_id','algorithm3_compatibility','algorithm3_trust','algorithm3_matched_successfully',
    'algorithm4_recommendation_name','algorithm4_recommendation_id','algorithm4_compatibility','algorithm4_trust','algorithm4_matched_successfully'
]


def _get_db_conn():
    dsn = os.getenv('DATABASE_URL')
    if not dsn:
        return None
    try:
        conn = psycopg2.connect(dsn)
        conn.autocommit = True
        return conn
    except Exception:
        return None


def _ensure_db():
    conn = _get_db_conn()
    if not conn:
        return
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                id SERIAL PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                user_name TEXT,
                algorithm1_recommendation_name TEXT,
                algorithm1_recommendation_id TEXT,
                algorithm1_compatibility TEXT,
                algorithm1_trust TEXT,
                algorithm1_matched_successfully TEXT,
                algorithm2_recommendation_name TEXT,
                algorithm2_recommendation_id TEXT,
                algorithm2_compatibility TEXT,
                algorithm2_trust TEXT,
                algorithm2_matched_successfully TEXT,
                algorithm3_recommendation_name TEXT,
                algorithm3_recommendation_id TEXT,
                algorithm3_compatibility TEXT,
                algorithm3_trust TEXT,
                algorithm3_matched_successfully TEXT,
                algorithm4_recommendation_name TEXT,
                algorithm4_recommendation_id TEXT,
                algorithm4_compatibility TEXT,
                algorithm4_trust TEXT,
                algorithm4_matched_successfully TEXT
            )
            """
        )
    conn.close()


def _insert_submission_row(header, row):
    conn = _get_db_conn()
    if not conn:
        return
    cols = ','.join(header)
    placeholders = ','.join(['%s'] * len(row))
    sql = f"INSERT INTO submissions ({cols}) VALUES ({placeholders})"
    try:
        with conn.cursor() as cur:
            cur.execute(sql, row)
    finally:
        conn.close()


def ensure_log_header():
    import os
    from pathlib import Path
    # If file exists and non-empty, verify header; otherwise write it
    if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > 0:
        with open(LOG_PATH, 'r', newline='') as f:
            first_line = f.readline().strip()
        expected = ','.join(LOG_HEADER)
        if first_line != expected:
            # Backup old file and start a new one with the updated header
            backup = f"{LOG_PATH}.bak.{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
            Path(LOG_PATH).rename(backup)
            with open(LOG_PATH, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(LOG_HEADER)
    else:
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
    algorithms = compute_algorithms(user, weights)
    return render_template('results.html', algorithms=algorithms, weights=weights, user=user, message=f"Recorded {decision} for {profile_name} in {algorithm}")


@app.route('/submit_matches', methods=['POST'])
def submit_matches():
    ensure_log_header()
    # 'selected' checkboxes have values like 'Algorithm::profile_id::score'
    selections = request.form.getlist('selected')
    if not selections:
        return "No selections made", 400
    if len(selections) < 1 or len(selections) > 4:
        return "Select between 1 and 4 candidates", 400

    # reconstruct user from hidden fields
    user = parse_user_form(request.form)

    # Algorithm keys in canonical order as rendered
    alg_order = ['Empirical','Logistics+Trust','Safety+Social','SemanticBio']

    # Determine matched flags per algorithm
    def matched_for_alg(alg_key: str) -> bool:
        prefix = alg_key + '::'
        return any(sel.startswith(prefix) for sel in selections)

    # Collect recommended name and id from hidden inputs (one per algorithm)
    rec1_name = request.form.get('algorithm1_recommendation_name', '')
    rec1_id = request.form.get('algorithm1_recommendation_id', '')
    rec1_compat = request.form.get('algorithm1_recommendation_compatibility', '')
    rec1_trust = request.form.get('algorithm1_recommendation_trust', '')
    rec2_name = request.form.get('algorithm2_recommendation_name', '')
    rec2_id = request.form.get('algorithm2_recommendation_id', '')
    rec2_compat = request.form.get('algorithm2_recommendation_compatibility', '')
    rec2_trust = request.form.get('algorithm2_recommendation_trust', '')
    rec3_name = request.form.get('algorithm3_recommendation_name', '')
    rec3_id = request.form.get('algorithm3_recommendation_id', '')
    rec3_compat = request.form.get('algorithm3_recommendation_compatibility', '')
    rec3_trust = request.form.get('algorithm3_recommendation_trust', '')
    rec4_name = request.form.get('algorithm4_recommendation_name', '')
    rec4_id = request.form.get('algorithm4_recommendation_id', '')
    rec4_compat = request.form.get('algorithm4_recommendation_compatibility', '')
    rec4_trust = request.form.get('algorithm4_recommendation_trust', '')

    row = [
        user.get('name',''),
        rec1_name, rec1_id, rec1_compat, rec1_trust, 'true' if matched_for_alg(alg_order[0]) else 'false',
        rec2_name, rec2_id, rec2_compat, rec2_trust, 'true' if matched_for_alg(alg_order[1]) else 'false',
        rec3_name, rec3_id, rec3_compat, rec3_trust, 'true' if matched_for_alg(alg_order[2]) else 'false',
        rec4_name, rec4_id, rec4_compat, rec4_trust, 'true' if matched_for_alg(alg_order[3]) else 'false'
    ]

    with open(LOG_PATH, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(row)

    # redirect back to input with a success message
    _ensure_db()
    _insert_submission_row(LOG_HEADER, row)
    return redirect('/?msg=Match+Submitted')


@app.route('/status', methods=['GET'])
def status():
    return {'status': 'ok'}

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    debug = os.getenv('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', port=port, debug=debug)
