from flask import Flask, render_template, request, redirect
from datetime import datetime
import os
import json
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
import time
import uuid

app = Flask(__name__)

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL', "postgresql://wandertogetherdb_user:94Wr3w5tONCj72N6D9oGnlUU87b2AiNs@dpg-d58fuimr433s73f8dndg-a.oregon-postgres.render.com/wandertogetherdb")

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

    # Food & Cuisine
    'Local Cuisine',
    'Food Tours',
    'Cooking Classes',
    'Wine & Brewery',
    'Street Food',
    'Fine Dining',

    # Activities & Entertainment
    'Nightlife',
    'Shopping',
    'Photography',
    'Adventure Sports',
    'Water Sports',
    'Wildlife & Animals',

    # Relaxation & Wellness
    'Spa & Wellness',
    'Beaches & Coast',
    'Parks & Gardens',
    'Meditation & Yoga',
    'Retreats',

    # Urban & City Life
    'City Exploration',
    'Local Markets',
    'Architecture',
    'Nightlife',
    'Shopping',

    # Travel Styles
    'Road Trips',
    'Volunteer Work',
    'Digital Nomad'
]


def load_survey_weights():
    """Load predefined weights for compatibility factors"""
    return {
        'budget': 0.15,
        'pace': 0.12,
        'interests': 0.18,
        'style': 0.10,
        'sleep': 0.08,
        'gender': 0.12,
        'age': 0.10
    }


# Load simulated profiles
_json_path = Path(__file__).with_suffix('.json')
if not _json_path.exists():
    _json_path = Path('simulated_profiles.json')

if _json_path.exists():
    with open(_json_path, 'r') as f:
        SIMULATED_PROFILES = json.load(f)
else:
    from simulated_profiles import SIMULATED_PROFILES

# Normalize profile fields
for p in SIMULATED_PROFILES:
    if isinstance(p.get('interests'), set):
        p['interests'] = list(p['interests'])
    if isinstance(p.get('sleep'), set):
        p['sleep'] = list(p['sleep'])

from hybrid_algorithm import compute_algorithms as compute_hybrid_algorithm


def get_db_connection():
    """Get database connection"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None


def init_database():
    """Initialize database with enhanced schema if needed"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        with conn.cursor() as cur:
            # Read and execute enhanced schema
            schema_path = Path(__file__).parent / 'enhanced_schema.sql'
            if schema_path.exists():
                with open(schema_path, 'r') as f:
                    schema_sql = f.read()
                cur.execute(schema_sql)
                conn.commit()
                print("Enhanced database schema initialized successfully")
                return True
    except Exception as e:
        print(f"Database initialization error: {e}")
        conn.rollback()
    finally:
        conn.close()
    return False


def log_form_submission(user, session_id):
    """Log form submission (Step 1 of user journey)"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT log_form_submission(
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                session_id,
                user.get('name', ''),
                user.get('age'),
                user.get('gender'),
                user.get('budget'),
                user.get('pace'),
                user.get('style'),
                user.get('interests', []),
                user.get('sleep', []),
                user.get('cleanliness'),
                user.get('dietary'),
                user.get('alcohol'),
                user.get('smoking'),
                user.get('fitness'),
                user.get('bio')
            ))
            
            journey_id = cur.fetchone()[0]
            conn.commit()
            print(f"Logged form submission {journey_id} for session {session_id}")
            return journey_id
            
    except Exception as e:
        print(f"Form logging error: {e}")
        conn.rollback()
    finally:
        conn.close()
    
    return None


def log_recommendations(session_id, recommendations, processing_time_ms):
    """Log algorithm recommendations (Step 2 of user journey)"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        # Prepare suggested profiles data
        suggested_profiles = []
        for profile, final_score, compatibility_score in recommendations:
            suggested_profiles.append({
                'id': profile['id'],
                'name': profile['name'],
                'age': profile['age'],
                'gender': profile['gender'],
                'trust': profile.get('trust', 0),
                'final_score': final_score,
                'compatibility_score': compatibility_score,
                'budget': profile.get('budget'),
                'pace': profile.get('pace'),
                'style': profile.get('style'),
                'interests': profile.get('interests', []),
                'sleep': profile.get('sleep', []),
                'cleanliness': profile.get('cleanliness'),
                'dietary': profile.get('dietary'),
                'alcohol': profile.get('alcohol'),
                'smoking': profile.get('smoking'),
                'fitness': profile.get('fitness'),
                'bio': profile.get('bio', '')
            })
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT log_recommendations(%s, %s, %s)
            """, (session_id, json.dumps(suggested_profiles), processing_time_ms))
            
            updated_count = cur.fetchone()[0]
            conn.commit()
            print(f"Logged recommendations for session {session_id}")
            return updated_count
            
    except Exception as e:
        print(f"Recommendations logging error: {e}")
        conn.rollback()
    finally:
        conn.close()
    
    return None


def log_selections(session_id, selected_profiles, user_satisfaction=None, feedback_text=None):
    """Log user selections (Step 3 of user journey)"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        # Prepare selected profiles data
        selected_profiles_data = []
        selected_profile_ids = []
        
        for profile, final_score, compatibility_score in selected_profiles:
            selected_profiles_data.append({
                'id': profile['id'],
                'name': profile['name'],
                'age': profile['age'],
                'gender': profile['gender'],
                'trust': profile.get('trust', 0),
                'final_score': final_score,
                'compatibility_score': compatibility_score,
                'budget': profile.get('budget'),
                'pace': profile.get('pace'),
                'style': profile.get('style'),
                'interests': profile.get('interests', []),
                'sleep': profile.get('sleep', []),
                'cleanliness': profile.get('cleanliness'),
                'dietary': profile.get('dietary'),
                'alcohol': profile.get('alcohol'),
                'smoking': profile.get('smoking'),
                'fitness': profile.get('fitness'),
                'bio': profile.get('bio', '')
            })
            selected_profile_ids.append(profile['id'])
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT log_selections(%s, %s, %s, %s, %s)
            """, (
                session_id, 
                selected_profile_ids, 
                json.dumps(selected_profiles_data),
                user_satisfaction,
                feedback_text
            ))
            
            updated_count = cur.fetchone()[0]
            conn.commit()
            print(f"Logged selections for session {session_id}: {len(selected_profiles)} profiles")
            return updated_count
            
    except Exception as e:
        print(f"Selections logging error: {e}")
        conn.rollback()
    finally:
        conn.close()
    
    return None


@app.route('/', methods=['GET'])
def index():
    weights = load_survey_weights()
    msg = request.args.get('msg')
    # Generate session ID for tracking
    session_id = request.args.get('session_id') or str(uuid.uuid4())
    return render_template('index.html', weights=weights, interest_choices=INTEREST_CHOICES, message=msg, session_id=session_id)


def parse_user_form(form):
    interests = set(form.getlist('interests'))
    pace_text = form.get('pace_text') or form.get('pace')
    
    if pace_text in ('relaxed_itinerary',):
        pace = 1  # Relaxed pace
    elif pace_text in ('spontaneous',):
        pace = 2  # Moderate pace (spontaneous)
    elif pace_text in ('packed_itinerary',):
        pace = 3  # Fast-paced
    else:
        try:
            pace = int(pace_text)
        except (ValueError, TypeError):
            pace = 2  # Default to moderate

    user = {
        'name': form.get('name', '').strip(),
        'age': int(form.get('age', 25)),
        'gender': form.get('gender', '').strip(),
        'budget': int(form.get('budget', 2)),
        'pace': pace,
        'style': form.get('style', '').strip(),
        'interests': list(interests),
        'sleep': form.getlist('sleep'),
        'bio': form.get('bio', '').strip(),
        'cleanliness': form.get('cleanliness', '').strip(),
        'dietary': form.get('dietary', '').strip(),
        'alcohol': form.get('alcohol', '').strip(),
        'smoking': form.get('smoking', '').strip(),
        'fitness': form.get('fitness', '').strip(),
    }
    return user


def compute_hybrid_recommendations(user, weights):
    """Compute top 6 recommendations using hybrid algorithm"""
    start_time = time.time()
    
    # Get hybrid algorithm results
    hybrid_results = compute_hybrid_algorithm(user, weights, SIMULATED_PROFILES)
    
    # Extract recommendations from hybrid results
    recommendations = hybrid_results.get('Safety-Enhanced Empirical', [])
    
    # Return top 6 recommendations
    return recommendations[:6]


@app.route('/recommend', methods=['POST'])
def recommend():
    weights = load_survey_weights()
    user = parse_user_form(request.form)
    session_id = request.form.get('session_id', str(uuid.uuid4()))
    
    # Step 1: Log form submission
    log_form_submission(user, session_id)
    
    # Step 2: Get recommendations
    start_time = time.time()
    recommendations = compute_hybrid_recommendations(user, weights)
    processing_time_ms = int((time.time() - start_time) * 1000)
    
    # Step 2: Log recommendations
    log_recommendations(session_id, recommendations, processing_time_ms)
    
    return render_template('results.html', recommendations=recommendations, weights=weights, user=user, session_id=session_id)


@app.route('/submit_matches', methods=['POST'])
def submit_matches():
    selections = request.form.getlist('selected')
    if not selections:
        return "No selections made", 400
    if len(selections) < 1 or len(selections) > 6:
        return "Select between 1 and 6 candidates", 400

    # reconstruct user from hidden fields
    user = parse_user_form(request.form)
    session_id = request.form.get('session_id', str(uuid.uuid4()))
    
    # Parse selected profiles
    selected_profiles = []
    for selection in selections:
        parts = selection.split('::')
        if len(parts) >= 4:
            profile_id = int(parts[0])
            final_score = float(parts[1])
            compatibility_score = float(parts[2])
            trust_score = float(parts[3])
            
            # Find the full profile data
            for profile in SIMULATED_PROFILES:
                if profile['id'] == profile_id:
                    selected_profiles.append((profile, final_score, compatibility_score))
                    break
    
    # Step 3: Log selections
    log_selections(session_id, selected_profiles)
    
    # Console logging
    print(f"User {user.get('name', 'Unknown')} submitted {len(selections)} matches")
    for profile, final_score, compatibility_score in selected_profiles:
        print(f"  - {profile['name']}: Score {final_score:.3f}, Compatibility {compatibility_score:.3f}")

    return redirect('/?msg=Matches+Submitted')


@app.route('/status', methods=['GET'])
def status():
    return {'status': 'ok', 'algorithm': 'hybrid_v1', 'database': 'connected' if get_db_connection() else 'disconnected'}


@app.route('/analytics', methods=['GET'])
def analytics():
    """Enhanced analytics endpoint"""
    conn = get_db_connection()
    if not conn:
        return {'error': 'Database not connected'}, 500
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Journey analytics
            cur.execute("SELECT * FROM journey_analytics ORDER BY journey_date DESC LIMIT 30")
            journey_summary = cur.fetchall()
            
            # Profile popularity
            cur.execute("SELECT * FROM profile_popularity LIMIT 20")
            popular_profiles = cur.fetchall()
            
            # Overall stats
            cur.execute("""
                SELECT 
                    COUNT(*) as total_journeys,
                    COUNT(CASE WHEN journey_status = 'selections_made' THEN 1 END) as completed_journeys,
                    AVG(processing_time_ms) as avg_processing_time,
                    AVG(avg_selected_trust) as avg_trust,
                    AVG(avg_selected_compatibility) as avg_compatibility
                FROM user_journey
            """)
            overall_stats = cur.fetchone()
            
            return {
                'overall_stats': dict(overall_stats),
                'journey_analytics': [dict(row) for row in journey_summary],
                'popular_profiles': [dict(row) for row in popular_profiles]
            }
    except Exception as e:
        return {'error': str(e)}, 500
    finally:
        conn.close()


if __name__ == '__main__':
    # Initialize database on startup
    init_database()
    
    port = int(os.getenv('PORT', 5001))
    debug = os.getenv('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', port=port, debug=debug)
