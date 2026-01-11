-- Enhanced database schema to capture ALL user journey data
-- This adds: 1) Form submission tracking, 2) All suggested profiles, 3) Clear selection tracking

-- Add new table for tracking complete user journey
CREATE TABLE IF NOT EXISTS user_journey (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    session_id TEXT UNIQUE,  -- To track the complete journey
    
    -- Step 1: Form submission data
    form_submitted_at TIMESTAMP WITH TIME ZONE,
    user_name TEXT,
    user_age INTEGER,
    user_gender TEXT,
    user_budget INTEGER,
    user_pace INTEGER,
    user_style TEXT,
    user_interests TEXT[],
    user_sleep TEXT[],
    user_cleanliness TEXT,
    user_dietary TEXT,
    user_alcohol TEXT,
    user_smoking TEXT,
    user_fitness TEXT,
    user_bio TEXT,
    
    -- Step 2: Algorithm results (all suggested profiles)
    recommendations_generated_at TIMESTAMP WITH TIME ZONE,
    suggested_profiles JSONB,  -- All 6 profiles with full details and scores
    algorithm_version TEXT DEFAULT 'hybrid_v1',
    processing_time_ms INTEGER,
    
    -- Step 3: User selections
    selections_made_at TIMESTAMP WITH TIME ZONE,
    selected_profile_ids INTEGER[],  -- Array of selected profile IDs
    selected_profiles JSONB,  -- Full details of selected profiles
    
    -- Performance metrics
    total_suggested_count INTEGER DEFAULT 6,
    total_selected_count INTEGER,
    selection_rate NUMERIC,  -- selected/suggested ratio
    
    -- Quality metrics
    avg_suggested_trust NUMERIC,
    avg_suggested_compatibility NUMERIC,
    avg_selected_trust NUMERIC,
    avg_selected_compatibility NUMERIC,
    
    -- User feedback
    user_satisfaction INTEGER CHECK (user_satisfaction >= 1 AND user_satisfaction <= 5),
    feedback_text TEXT,
    
    -- Journey completion status
    journey_status TEXT DEFAULT 'incomplete'  -- 'form_only', 'recommendations_viewed', 'selections_made', 'complete'
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_journey_session_id ON user_journey(session_id);
CREATE INDEX IF NOT EXISTS idx_user_journey_created_at ON user_journey(created_at);
CREATE INDEX IF NOT EXISTS idx_user_journey_status ON user_journey(journey_status);
CREATE INDEX IF NOT EXISTS idx_user_journey_selected_profiles ON user_journey USING GIN(selected_profiles);

-- Create function to log form submission (Step 1)
CREATE OR REPLACE FUNCTION log_form_submission(
    p_session_id TEXT,
    p_user_name TEXT,
    p_user_age INTEGER,
    p_user_gender TEXT,
    p_user_budget INTEGER,
    p_user_pace INTEGER,
    p_user_style TEXT,
    p_user_interests TEXT[],
    p_user_sleep TEXT[],
    p_user_cleanliness TEXT,
    p_user_dietary TEXT,
    p_user_alcohol TEXT,
    p_user_smoking TEXT,
    p_user_fitness TEXT,
    p_user_bio TEXT
) RETURNS INTEGER AS $$
DECLARE
    journey_id INTEGER;
BEGIN
    INSERT INTO user_journey (
        session_id, form_submitted_at, user_name, user_age, user_gender, user_budget, user_pace, user_style,
        user_interests, user_sleep, user_cleanliness, user_dietary, user_alcohol, user_smoking, user_fitness, user_bio,
        journey_status
    ) VALUES (
        p_session_id, NOW(), p_user_name, p_user_age, p_user_gender, p_user_budget, p_user_pace, p_user_style,
        p_user_interests, p_user_sleep, p_user_cleanliness, p_user_dietary, p_user_alcohol, p_user_smoking, p_user_fitness, p_user_bio,
        'form_only'
    ) RETURNING id INTO journey_id;
    
    RETURN journey_id;
END;
$$ LANGUAGE plpgsql;

-- Create function to log recommendations (Step 2)
CREATE OR REPLACE FUNCTION log_recommendations(
    p_session_id TEXT,
    p_suggested_profiles JSONB,
    p_processing_time_ms INTEGER DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE user_journey 
    SET 
        recommendations_generated_at = NOW(),
        suggested_profiles = p_suggested_profiles,
        processing_time_ms = p_processing_time_ms,
        total_suggested_count = jsonb_array_length(p_suggested_profiles),
        avg_suggested_trust = (
            SELECT AVG((elem->>'trust')::NUMERIC) 
            FROM jsonb_array_elements(p_suggested_profiles) AS elem
        ),
        avg_suggested_compatibility = (
            SELECT AVG((elem->>'compatibility_score')::NUMERIC) 
            FROM jsonb_array_elements(p_suggested_profiles) AS elem
        ),
        journey_status = 'recommendations_viewed'
    WHERE session_id = p_session_id;
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql;

-- Create function to log selections (Step 3)
CREATE OR REPLACE FUNCTION log_selections(
    p_session_id TEXT,
    p_selected_profile_ids INTEGER[],
    p_selected_profiles JSONB,
    p_user_satisfaction INTEGER DEFAULT NULL,
    p_feedback_text TEXT DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE user_journey 
    SET 
        selections_made_at = NOW(),
        selected_profile_ids = p_selected_profile_ids,
        selected_profiles = p_selected_profiles,
        total_selected_count = array_length(p_selected_profile_ids, 1),
        selection_rate = (array_length(p_selected_profile_ids, 1)::NUMERIC / total_suggested_count),
        avg_selected_trust = (
            SELECT AVG((elem->>'trust')::NUMERIC) 
            FROM jsonb_array_elements(p_selected_profiles) AS elem
        ),
        avg_selected_compatibility = (
            SELECT AVG((elem->>'compatibility_score')::NUMERIC) 
            FROM jsonb_array_elements(p_selected_profiles) AS elem
        ),
        user_satisfaction = p_user_satisfaction,
        feedback_text = p_feedback_text,
        journey_status = 'selections_made'
    WHERE session_id = p_session_id;
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql;

-- Create comprehensive analytics views
CREATE OR REPLACE VIEW journey_analytics AS
SELECT 
    DATE(created_at) as journey_date,
    COUNT(*) as total_journeys,
    COUNT(CASE WHEN journey_status = 'form_only' THEN 1 END) as form_only_count,
    COUNT(CASE WHEN journey_status = 'recommendations_viewed' THEN 1 END) as recommendations_viewed_count,
    COUNT(CASE WHEN journey_status = 'selections_made' THEN 1 END) as selections_made_count,
    ROUND(
        (COUNT(CASE WHEN journey_status = 'selections_made' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0)), 2
    ) as completion_rate_pct,
    AVG(processing_time_ms) as avg_processing_time,
    AVG(avg_suggested_trust) as avg_suggested_trust,
    AVG(avg_suggested_compatibility) as avg_suggested_compatibility,
    AVG(avg_selected_trust) as avg_selected_trust,
    AVG(avg_selected_compatibility) as avg_selected_compatibility,
    AVG(selection_rate) as avg_selection_rate,
    AVG(total_selected_count) as avg_selections_per_user,
    COUNT(CASE WHEN user_satisfaction IS NOT NULL THEN 1 END) as feedback_count,
    AVG(user_satisfaction) as avg_satisfaction
FROM user_journey
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY journey_date DESC;

-- View for profile popularity analysis
CREATE OR REPLACE VIEW profile_popularity AS
SELECT 
    elem->>'id' as profile_id,
    elem->>'name' as profile_name,
    elem->>'age' as profile_age,
    elem->>'gender' as profile_gender,
    COUNT(*) as times_suggested,
    COUNT(CASE WHEN elem->>'id' IN (SELECT unnest(selected_profile_ids) FROM user_journey WHERE selected_profile_ids IS NOT NULL) THEN 1 END) as times_selected,
    ROUND(
        (COUNT(CASE WHEN elem->>'id' IN (SELECT unnest(selected_profile_ids) FROM user_journey WHERE selected_profile_ids IS NOT NULL) THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0)), 2
    ) as selection_rate_pct,
    AVG((elem->>'trust')::NUMERIC) as avg_trust_score,
    AVG((elem->>'compatibility_score')::NUMERIC) as avg_compatibility_score
FROM user_journey, jsonb_array_elements(suggested_profiles) AS elem
WHERE suggested_profiles IS NOT NULL
GROUP BY elem->>'id', elem->>'name', elem->>'age', elem->>'gender'
HAVING COUNT(*) >= 3  -- Only show profiles suggested at least 3 times
ORDER BY times_selected DESC, selection_rate_pct DESC;
