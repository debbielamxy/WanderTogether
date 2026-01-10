from datetime import datetime
import re

def replace_punct(s):
    return re.sub(r"[^a-z0-9\s]", "", s)

SAFETY_KEYWORDS = {
    'female-only','verified','low-key','cautious','quiet','calm','safe','safety','trust','id-verified','blockchain','respectful'
}

OUTDOOR_KEYWORDS = {
    'hike','hiking','trek','trekking','trail','camp','camping','backpack','backpacking','mountain','nature','outdoor','outdoors','wild','summit'
}

def pace_similarity(user, profile):
    return 1 - abs(user['pace'] - profile.get('pace', 2)) / 2

def budget_similarity(user, profile):
    return 1 - abs(user['budget'] - profile.get('budget', 2)) / 2

def interests_similarity(user, profile):
    u = set(user.get('interests', []))
    p = set(profile.get('interests', []))
    if not u and not p:
        return 0.0
    overlap = len(u.intersection(p))
    denom = max(len(u), len(p), 1)
    return overlap / denom

def style_similarity(user, profile):
    return 1.0 if user.get('style') == profile.get('style') else 0.0

def jaccard_overlap(a, b):
    a = set(a or [])
    b = set(b or [])
    if not a and not b:
        return 0.0
    return len(a.intersection(b)) / max(1, len(a.union(b)))

def sleep_similarity(user, profile):
    return jaccard_overlap(user.get('sleep'), profile.get('sleep'))

def habit_match(user_val, profile_val):
    u = (user_val or '').strip().lower()
    p = (profile_val or '').strip().lower()
    if not u or not p:
        return 0.5  # unknown -> neutral
    return 1.0 if u == p else 0.0

def categorical_similarity(user_val, profile_val):
    u = (user_val or '').strip().lower()
    p = (profile_val or '').strip().lower()
    if not u and not p:
        return 0.0
    if not u or not p:
        return 0.5
    return 1.0 if u == p else 0.0

def demographics_score(user, profile):
    # Standard demographics scoring
    score = 0.0
    ug = user.get('gender')
    pg = profile.get('gender')
    if ug is not None and pg is not None:
        if str(ug).lower() == str(pg).lower():
            score += 1.0
    ua = user.get('age')
    pa = profile.get('age')
    if isinstance(ua, int) and isinstance(pa, int):
        diff = abs(ua - pa)
        if diff <= 5:
            score += 1.0
        elif diff <= 10:
            score += 0.5
        else:
            score += 0.0
    return min(score, 2.0) / 2.0

def demographics_strict(user, profile):
    """Stricter demographics scoring prioritizing same-gender match and close age proximity."""
    gender_score = 0.0
    ug = user.get('gender')
    pg = profile.get('gender')
    if ug is not None and pg is not None:
        if str(ug).lower() == str(pg).lower():
            gender_score = 1.0

    age_score = 0.0
    ua = user.get('age')
    pa = profile.get('age')
    if isinstance(ua, int) and isinstance(pa, int):
        diff = abs(ua - pa)
        if diff <= 3:
            age_score = 1.0
        elif diff <= 7:
            age_score = 0.6
        elif diff <= 12:
            age_score = 0.3
        else:
            age_score = 0.0

    # Heavier weight on same-gender (70%) vs age (30%) for safety-focused algorithm
    return 0.7 * gender_score + 0.3 * age_score

def safety_keyword_score(user, profile):
    text = (user.get('bio','') + ' ' + profile.get('bio','')).lower()
    text = replace_punct(text)
    tokens = set(text.split())
    hits = len(tokens.intersection(SAFETY_KEYWORDS))
    return min(1.0, hits / 3.0)

def semantic_bio_score(user, profile):
    user_keywords = set(replace_punct(user.get('bio','').lower()).split())
    profile_keywords = set(replace_punct(profile.get('bio','').lower()).split())
    overlap = len(user_keywords.intersection(profile_keywords))
    return overlap / max(1, len(user_keywords))

def detect_outdoors_from_text(text):
    """Return True if free-text indicates outdoors/hiking interest."""
    if not text:
        return False
    toks = set(replace_punct(text.lower()).split())
    return len(toks.intersection(OUTDOOR_KEYWORDS)) > 0

def trust_multiplier(profile):
    # TrustScore in [0,5] -> T_norm in [0,1]. If profiles store trust in [0,1], treat as T_norm directly.
    t = profile.get('trust', 0.5)
    return max(0.0, min(1.0, t))

def safety_enhanced_empirical_hybrid(user, weights, profiles):
    """
    Safety-Enhanced Empirical Hybrid Algorithm
    
    Based on evaluation results showing Algorithm 3 (Safety+Social) as most preferred (40.9% selections),
    this hybrid algorithm prioritizes safety features while maintaining empirical foundation.
    
    Weight Distribution:
    - Safety-First Components (60%): Demographics (35%) + Bio Safety (5%) + Sleep (3%) + Style (2%) + Habits (10%)
    - Empirical Components (40%): Budget (25%) + Pace (20%) + Interests (10%)
    
    Features:
    - Trust gate (>=0.7) from Algorithm 3 for user safety
    - Survey-derived empirical weights for core preferences
    - Balanced approach between safety-first and empirical matching
    """
    """
    Safety-Enhanced Empirical Hybrid Algorithm
    Combines the best of Algorithm 3 (Safety+Social) and Algorithm 1 (Empirical)
    
    Weight Distribution:
    - Safety Components (55%): Demographics (35%) + Bio Safety (5%) + Sleep (3%) + Style (2%) + Habits (10%)
    - Empirical Components (45%): Budget (25%) + Pace (20%) + Interests (10%)
    
    Features:
    - Trust gate (>=0.7) from Algorithm 3
    - Strict demographics scoring from Algorithm 3
    - Survey-derived empirical weights from Algorithm 1
    - Safety keyword detection
    """
    algorithms = {}
    
    # Soft global trust penalty used across algorithms
    def soft_trust(t: float) -> float:
        # keeps scores in [0.6, 1.0] range based on trust, avoids hard suppression
        return 0.6 + 0.4 * max(0.0, min(1.0, t))
    
    # Safety-Enhanced Empirical Hybrid Algorithm
    W_hybrid = {
        # Safety-First Components (60% total) - prioritized based on evaluation results
        'demographics': 0.35,      # Strict same-gender + age proximity (35%)
        'bio_safety': 0.05,        # Safety keyword detection (5%)
        'sleep': 0.03,             # Sleep compatibility (3%)
        'style': 0.02,             # Travel style matching (2%)
        'smoking': 0.03,           # Habit matching (3%)
        'alcohol': 0.03,           # Habit matching (3%)
        'dietary': 0.02,           # Dietary compatibility (2%)
        'cleanliness': 0.02,       # Cleanliness preferences (2%)
        
        # Empirical Components (40% total) - maintaining survey foundation
        'budget': 0.25,            # Budget compatibility (25%)
        'pace': 0.20,              # Travel pace matching (20%)
        'interests': 0.10,         # Shared interests (10%)
    }
    
    TRUST_GATE = 0.7  # From Algorithm 3 - exclude low-trust profiles
    alg_hybrid = []
    
    for p in profiles:
        Tn = trust_multiplier(p)
        if Tn < TRUST_GATE:
            continue  # Skip low-trust profiles
        
        # Compute all components
        # Safety Components
        demographics_c = demographics_strict(user, p)  # Strict scoring from Algorithm 3
        bio_safety_c = safety_keyword_score(user, p)   # Safety keyword detection
        sleep_c = sleep_similarity(user, p)
        style_c = style_similarity(user, p)
        smoking_c = habit_match(user.get('smoking'), p.get('smoking'))
        alcohol_c = habit_match(user.get('alcohol'), p.get('alcohol'))
        dietary_c = categorical_similarity(user.get('dietary'), p.get('dietary'))
        cleanliness_c = categorical_similarity(user.get('cleanliness'), p.get('cleanliness'))
        
        # Empirical Components
        budget_c = budget_similarity(user, p)
        pace_c = pace_similarity(user, p)
        interests_c = interests_similarity(user, p)
        
        # Calculate weighted score
        weighted = (
            W_hybrid.get('demographics', 0) * demographics_c +
            W_hybrid.get('bio_safety', 0) * bio_safety_c +
            W_hybrid.get('sleep', 0) * sleep_c +
            W_hybrid.get('style', 0) * style_c +
            W_hybrid.get('smoking', 0) * smoking_c +
            W_hybrid.get('alcohol', 0) * alcohol_c +
            W_hybrid.get('dietary', 0) * dietary_c +
            W_hybrid.get('cleanliness', 0) * cleanliness_c +
            W_hybrid.get('budget', 0) * budget_c +
            W_hybrid.get('pace', 0) * pace_c +
            W_hybrid.get('interests', 0) * interests_c
        )
        
        S = weighted / (sum(W_hybrid.values()) or 1.0)
        # Apply softened trust after the gate
        sc = S * soft_trust(Tn)
        alg_hybrid.append((p, sc, S))
    
    algorithms['Safety-Enhanced Empirical'] = sorted(alg_hybrid, key=lambda x: x[1], reverse=True)[:8]
    
    return algorithms

def compute_algorithms(user, weights, profiles):
    """
    Main function to compute the Safety-Enhanced Empirical Hybrid algorithm
    Compatible with existing codebase structure
    """
    return safety_enhanced_empirical_hybrid(user, weights, profiles)

# Additional utility function for algorithm comparison
def compare_with_baseline(user, weights, profiles):
    """
    Compare hybrid algorithm with baseline algorithms for analysis
    Returns results from all algorithms for comparison
    """
    from recommendation_algorithms import compute_algorithms as baseline_algorithms
    
    # Get baseline results
    baseline_results = baseline_algorithms(user, weights, profiles)
    
    # Get hybrid results
    hybrid_results = safety_enhanced_empirical_hybrid(user, weights, profiles)
    
    # Combine for comparison
    all_results = {**baseline_results, **hybrid_results}
    
    return all_results
