-- Simplified database schema for WanderTogether (No Performance Metrics)
-- Tracks only: form submission, suggestions, and selections

-- Create table for user journey tracking (minimal)
CREATE TABLE IF NOT EXISTS user_journey (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Step 1: Form submission data
    form_submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_name TEXT,
    user_age INTEGER,
    user_gender TEXT,
    user_budget INTEGER,
    user_pace INTEGER,
    user_style TEXT,
    user_interests TEXT[], -- Array of interests
    user_sleep TEXT[],      -- Array of sleep preferences
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
    
    -- Step 3: User selections (final step - contact revealed)
    selections_made_at TIMESTAMP WITH TIME ZONE,
    selected_profile_ids INTEGER[],  -- Array of selected profile IDs
    selected_profiles JSONB,  -- Full details of selected profiles
    
    -- Simple metrics only
    total_suggested_count INTEGER DEFAULT 6, -- Total recommendations shown
    total_selected_count INTEGER                 -- How many profiles user selected
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_journey_created_at ON user_journey(created_at);
CREATE INDEX IF NOT EXISTS idx_user_journey_selections_made_at ON user_journey(selections_made_at);

-- Add simple view tracking for accurate analytics
CREATE OR REPLACE VIEW journey_tracking AS
SELECT 
    DATE(created_at) as journey_date,
    COUNT(*) as total_form_submissions,
    COUNT(recommendations_generated_at) as recommendations_shown,
    COUNT(selections_made_at) as selections_made,
    ROUND(
        (COUNT(selections_made_at) * 100.0 / NULLIF(COUNT(recommendations_generated_at), 0)), 2
    ) as selection_rate_pct
FROM user_journey
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY journey_date DESC;

-- Create a view for completion funnel analysis
CREATE OR REPLACE VIEW completion_funnel AS
SELECT 
    'form_submissions' as stage,
    COUNT(*) as count
FROM (
    SELECT 'form_submissions' as stage, COUNT(*) as count FROM user_journey WHERE form_submitted_at IS NOT NULL
    UNION ALL
    SELECT 'recommendations_shown' as stage, COUNT(*) as count FROM user_journey WHERE recommendations_generated_at IS NOT NULL
    UNION ALL  
    SELECT 'selections_made' as stage, COUNT(*) as count FROM user_journey WHERE selections_mpletion_at IS NOT NULL
)
GROUP BY stage
ORDER BY 
    CASE 
        WHEN 'form_submissions' THEN 1
        WHEN 'recommendations_shown' THEN 2
        WHEN 'selections_made' THEN 3
    END;

-- View for profile popularity analysis (includes scores)
CREATE OR REPLACE VIEW profile_popularity AS
SELECT 
    elem->>'id' as profile_id,
    elem->>'name' as profile_name,
    elem->>'age' as profile_age,
    elem->>'gender' as profile_gender,
    elem->>'trust' as trust_score,
    elem->>'compatibility_score' as compatibility_score,
    COUNT(*) as times_suggested,
    COUNT(CASE WHEN elem->>'id' IN (SELECT unnest(selected_profile_ids) FROM user_journey WHERE selected_profile_ids IS NOT NULL) THEN 1 END) as times_selected,
    ROUND(
        (COUNT(CASE WHEN elem->>'id' IN (SELECT unnest(selected_profile_ids) FROM user_journey WHERE selected_profile_ids IS NOT NULL) THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0)), 2
    ) as selection_rate_pct,
    AVG((elem->>'trust')::NUMERIC) as avg_trust_score,
    AVG((elem->>'compatibility_score')::NUMERIC) as avg_compatibility_score
FROM user_journey, jsonb_array_elements(suggested_profiles) AS elem
WHERE suggested_profiles IS NOT NULL
GROUP BY elem->>'id', elem->>'name', elem->>'age', elem->>'gender', elem->>'trust', elem->>'compatibility_score'
HAVING COUNT(*) >= 1
ORDER BY times_selected DESC, selection_rate_pct DESC;
