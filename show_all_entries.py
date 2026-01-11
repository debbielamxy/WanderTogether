#!/usr/bin/env python3
"""
Show All Database Entries
Displays all user journey records in the database
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
import json
from datetime import datetime

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL', "postgresql://wandertogetherdb_user:94Wr3w5tONCj72N6D9oGnlUU87b2AiNs@dpg-d58fuimr433s73f8dndg-a.oregon-postgres.render.com/wandertogetherdb")

def show_all_entries():
    print("🗃️ WanderTogether Database - All User Journey Entries")
    print("=" * 60)
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get all entries
            cur.execute("""
                SELECT 
                    id,
                    created_at,
                    form_submitted_at,
                    recommendations_generated_at,
                    selections_made_at,
                    user_name,
                    user_age,
                    user_gender,
                    user_budget,
                    user_pace,
                    user_style,
                    user_interests,
                    user_sleep,
                    user_cleanliness,
                    user_dietary,
                    user_alcohol,
                    user_smoking,
                    user_fitness,
                    user_bio,
                    suggested_profiles,
                    selected_profiles,
                    total_suggested_count,
                    total_selected_count
                FROM user_journey
                ORDER BY created_at DESC
            """)
            
            entries = cur.fetchall()
            
            if not entries:
                print("❌ No entries found in database")
                return
            
            print(f"📊 Total Entries: {len(entries)}")
            print("=" * 60)
            
            for i, entry in enumerate(entries, 1):
                print(f"\n👤 Entry #{i}: {entry['user_name']} (ID: {entry['id']})")
                print(f"   🕐 Created: {entry['created_at']}")
                
                # Form submission info
                if entry['form_submitted_at']:
                    print(f"   📝 Form submitted: {entry['form_submitted_at']}")
                    print(f"   👤 Age: {entry['user_age']}, Gender: {entry['user_gender']}")
                    print(f"   💰 Budget: {entry['user_budget']}, Pace: {entry['user_pace']}, Style: {entry['user_style']}")
                    
                    # Handle interests (may be stored as array or string)
                    interests = entry['user_interests']
                    if interests:
                        if isinstance(interests, list):
                            interests_str = ', '.join(interests[:3]) + ('...' if len(interests) > 3 else '')
                        else:
                            interests_str = str(interests)[:50]
                        print(f"   🎯 Interests: {interests_str}")
                    
                    # Handle sleep (may be stored as array or string)
                    sleep = entry['user_sleep']
                    if sleep:
                        if isinstance(sleep, list):
                            sleep_str = ', '.join(sleep[:3]) + ('...' if len(sleep) > 3 else '')
                        else:
                            sleep_str = str(sleep)[:50]
                        print(f"   😴 Sleep: {sleep_str}")
                    
                    if entry['user_bio']:
                        bio = entry['user_bio']
                        print(f"   📄 Bio: {bio[:50]}{'...' if len(bio) > 50 else ''}")
                
                # Algorithm suggestions
                if entry['recommendations_generated_at']:
                    print(f"   🤖 Recommendations generated: {entry['recommendations_generated_at']}")
                    if entry['suggested_profiles']:
                        try:
                            # Handle both string and object types
                            if isinstance(entry['suggested_profiles'], str):
                                suggested = json.loads(entry['suggested_profiles'])
                            else:
                                suggested = entry['suggested_profiles']
                            
                            print(f"   📋 Suggested profiles: {len(suggested)}")
                            
                            # Show top 3 suggested profiles with scores
                            for j, profile in enumerate(suggested[:3], 1):
                                trust = profile.get('trust', 0)
                                compat = profile.get('compatibility_score', 0)
                                print(f"      {j}. {profile['name']} - Trust: {trust:.3f}, Compatibility: {compat:.3f}")
                        except Exception as e:
                            print(f"   ⚠️  Could not parse suggested profiles data: {e}")
                            print(f"   📄 Raw data type: {type(entry['suggested_profiles'])}")
                            print(f"   📄 Raw data: {entry['suggested_profiles'][:100]}...")
                
                # User selections
                if entry['selections_made_at']:
                    print(f"   ✅ Selections made: {entry['selections_made_at']}")
                    print(f"   🎯 Selected: {entry['total_selected_count']}/{entry['total_suggested_count']} profiles")
                    
                    if entry['selected_profiles']:
                        try:
                            # Handle both string and object types
                            if isinstance(entry['selected_profiles'], str):
                                selected = json.loads(entry['selected_profiles'])
                            else:
                                selected = entry['selected_profiles']
                            
                            print(f"   📋 Selected profiles:")
                            for j, profile in enumerate(selected, 1):
                                trust = profile.get('trust', 0)
                                compat = profile.get('compatibility_score', 0)
                                print(f"      {j}. {profile['name']} - Trust: {trust:.3f}, Compatibility: {compat:.3f}")
                        except Exception as e:
                            print(f"   ⚠️  Could not parse selected profiles data: {e}")
                            print(f"   📄 Raw data type: {type(entry['selected_profiles'])}")
                            print(f"   📄 Raw data: {entry['selected_profiles'][:100]}...")
                else:
                    print(f"   ❌ No selections made")
                
                print("   " + "-" * 50)
            
            # Summary statistics
            print(f"\n📈 Summary Statistics:")
            print(f"   Total journeys: {len(entries)}")
            
            completed = sum(1 for entry in entries if entry['selections_made_at'])
            print(f"   Completed journeys (with selections): {completed}")
            
            if len(entries) > 0:
                completion_rate = (completed / len(entries)) * 100
                print(f"   Completion rate: {completion_rate:.1f}%")
                
                completed_entries = [entry for entry in entries if entry['total_selected_count']]
                if completed_entries:
                    avg_selections = sum(entry['total_selected_count'] for entry in completed_entries) / len(completed_entries)
                    print(f"   Avg selections per completed journey: {avg_selections:.1f}")
            
            print(f"\n🎯 Database Size: {len(entries)} user journeys stored")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    show_all_entries()
