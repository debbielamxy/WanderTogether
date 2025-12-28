from datetime import datetime
import re

def replace_punct(s):
    return re.sub(r"[^a-z0-9\s]", "", s)

SAFETY_KEYWORDS = {
    'female-only','verified','low-key','cautious','quiet','calm','safe','safety','trust','id-verified','blockchain','respectful'
}

# Keywords for simple NLP-style detection of outdoors / hiking preference from free-text bios
OUTDOOR_KEYWORDS = {
    'hike','hiking','trek','trekking','trail','camp','camping','backpack','backpacking','mountain','nature','outdoor','outdoors','wild','summit'
}

def pace_similarity(user, profile):
    return 1 - abs(user['pace'] - profile.get('pace', 2)) / 2

def budget_similarity(user, profile):
    return 1 - abs(user['budget'] - profile.get('budget', 2)) / 2

def interests_similarity(user, profile):
    u = user.get('interests', set())
    p = set(profile.get('interests', []))
    if not u and not p:
        return 0.0
    overlap = len(u.intersection(p))
    denom = max(len(u), len(p), 1)
    return overlap / denom

def style_similarity(user, profile):
    return 1.0 if user.get('style') == profile.get('style') else 0.0

def demographics_score(user, profile):
    # gender match (if available) and age proximity
    score = 0.0
    # gender
    ug = user.get('gender')
    pg = profile.get('gender')
    if ug is not None and pg is not None:
        score += 1.0 if str(ug).lower() == str(pg).lower() else 0.0
    # age proximity
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
    # normalize to [0,1] with max 2 components
    return min(score, 2.0) / 2.0

def safety_keyword_score(user, profile):
    text = (user.get('bio','') + ' ' + profile.get('bio','')).lower()
    text = replace_punct(text)
    tokens = set(text.split())
    hits = len(tokens.intersection(SAFETY_KEYWORDS))
    return min(1.0, hits / 3.0)  # cap for stability

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


def demographics_strict(user, profile):
    """Stricter demographics score prioritizing gender match and close age proximity.

    Returns a value in [0,1] where gender match counts more than age proximity.
    """
    gender_score = 0.0
    ug = user.get('gender')
    pg = profile.get('gender')
    if ug is not None and pg is not None:
        gender_score = 1.0 if str(ug).lower() == str(pg).lower() else 0.0

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

    # heavier weight on gender (70%) vs age (30%) for safety-focused algorithm
    return 0.7 * gender_score + 0.3 * age_score

def base_score(user, profile, w, bio_mode='none'):
    pace = pace_similarity(user, profile)
    budget = budget_similarity(user, profile)
    interests = interests_similarity(user, profile)
    style = style_similarity(user, profile)
    # bio component
    if bio_mode == 'semantic':
        bio = semantic_bio_score(user, profile)
    elif bio_mode == 'safety':
        bio = safety_keyword_score(user, profile)
    elif bio_mode == 'tie':
        # tiny bump if everything else ties: use overlap as weak signal
        bio = 0.03 * semantic_bio_score(user, profile)
    else:
        bio = 0.0
    demo = demographics_score(user, profile)

    weighted = (
        w.get('pace',0)*pace +
        w.get('budget',0)*budget +
        w.get('interests',0)*interests +
        w.get('style',0)*style +
        w.get('bio',0)*bio +
        w.get('demographics',0)*demo
    )
    total_w = sum(w.values()) or 1.0
    return weighted / total_w

def trust_multiplier(profile):
    # TrustScore in [0,5] -> T_norm in [0,1]. If profiles store trust in [0,1], treat as T_norm directly.
    t = profile.get('trust', 0.5)
    return max(0.0, min(1.0, t))

def compute_algorithms(user, weights, profiles):
    algorithms = {}

    # Algorithm 1: Direct Application (uses empirical weights derived from survey)
    # These weights reflect the survey-derived ratios (end-to-end research → design → implementation)
    W1 = {'pace':0.28, 'budget':0.26, 'interests':0.20, 'style':0.20, 'bio':0.03, 'demographics':0.03}
    alg1 = []
    for p in profiles:
        S = base_score(user, p, W1, bio_mode='tie')
        Tn = trust_multiplier(p)
        sc = S * Tn
        alg1.append((p, sc, S))
    algorithms['Empirical'] = sorted(alg1, key=lambda x: x[1], reverse=True)[:1]

    # Algorithm 2: Scientific Control (Pure Compatibility)
    # Trust multiplier is set to 1.0 to create a baseline that ignores verification signals.
    W2 = {'pace':0.45, 'budget':0.45, 'interests':0.05, 'style':0.05, 'bio':0.0, 'demographics':0.0}
    alg2 = []
    for p in profiles:
        S = base_score(user, p, W2, bio_mode='none')
        # Ignore trust entirely for pure mathematical similarity
        sc = S * 1.0
        alg2.append((p, sc, S))
    algorithms['Logistics+Trust'] = sorted(alg2, key=lambda x: x[1], reverse=True)[:1]

    # Algorithm 3: Safety Stress-Test (prioritizes gender and age heavily)
    # This algorithm uses a stricter demographics function and enforces a trust gate
    W3 = {'pace':0.10, 'budget':0.10, 'interests':0.10, 'style':0.10, 'bio':0.20, 'demographics':0.40}
    TRUST_GATE = 0.7
    alg3 = []
    for p in profiles:
        Tn = trust_multiplier(p)
        if Tn < TRUST_GATE:
            continue
        # compute components explicitly so we can replace demographics with a stricter variant
        pace_c = pace_similarity(user, p)
        budget_c = budget_similarity(user, p)
        interests_c = interests_similarity(user, p)
        style_c = style_similarity(user, p)
        bio_c = safety_keyword_score(user, p)  # use safety-oriented bio scoring
        demo_c = demographics_strict(user, p)

        weighted = (
            W3.get('pace', 0) * pace_c +
            W3.get('budget', 0) * budget_c +
            W3.get('interests', 0) * interests_c +
            W3.get('style', 0) * style_c +
            W3.get('bio', 0) * bio_c +
            W3.get('demographics', 0) * demo_c
        )
        total_w = sum(W3.values()) or 1.0
        S = weighted / total_w
        sc = S * Tn
        alg3.append((p, sc, S))
    algorithms['Safety+Social'] = sorted(alg3, key=lambda x: x[1], reverse=True)[:1]

    # Algorithm 4: Innovation / Semantic (NLP on bio to infer interests)
    # Uses semantic bio scoring and also infers outdoors interest from free-text bios.
    W4 = {'pace':0.10, 'budget':0.10, 'interests':0.25, 'style':0.10, 'bio':0.40, 'demographics':0.05}
    alg4 = []
    user_outdoor = detect_outdoors_from_text(user.get('bio',''))
    for p in profiles:
        # Base components
        pace_c = pace_similarity(user, p)
        budget_c = budget_similarity(user, p)
        # start with normal interests similarity
        interests_c = interests_similarity(user, p)
        style_c = style_similarity(user, p)
        bio_c = semantic_bio_score(user, p)
        demo_c = demographics_score(user, p)

        # If user bio implies outdoors interest but user didn't select the tag,
        # boost the interest match when the profile indicates outdoors behavior.
        profile_outdoor = detect_outdoors_from_text(p.get('bio','')) or ('Hiking & Trekking' in (p.get('interests') or []))
        if user_outdoor and profile_outdoor:
            # increase interests matching as an inferred signal (cap at 1.0)
            interests_c = min(1.0, interests_c + 0.35)

        weighted = (
            W4.get('pace', 0) * pace_c +
            W4.get('budget', 0) * budget_c +
            W4.get('interests', 0) * interests_c +
            W4.get('style', 0) * style_c +
            W4.get('bio', 0) * bio_c +
            W4.get('demographics', 0) * demo_c
        )
        total_w = sum(W4.values()) or 1.0
        S = weighted / total_w
        Tn = trust_multiplier(p)
        sc = S * Tn
        alg4.append((p, sc, S))
    algorithms['SemanticBio'] = sorted(alg4, key=lambda x: x[1], reverse=True)[:1]

    return algorithms
