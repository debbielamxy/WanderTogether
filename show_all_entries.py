#!/usr/bin/env python3
"""
Show All Database Entries
Display all user journey data from database
"""

import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

def show_all_entries():
    print("🗃️ WanderTogether Database - All User Journey Entries")
    print("=" * 60)
    
    # Database connection
    DATABASE_URL = "postgresql://wandertogetherdb_user:94Wr3w5tONCj72N6D9oGnlUU87b2AiNs@dpg-d58fuimr433s73f8dndg-a.oregon-postgres.render.com/wandertogetherdb"
    
    conn = psycopg2.connect(DATABASE_URL)
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get all entries with complete information
            cur.execute("""
                SELECT 
                    id,
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
                    created_at,
                    form_submitted_at,
                    recommendations_generated_at,
                    selections_made_at,
                    suggested_profiles,
                    selected_profiles,
                    selected_profile_ids,
                    total_suggested_count,
                    total_selected_count,
                    algorithm_version
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
                print(f"   📝 Form submitted: {entry['form_submitted_at']}")
                print(f"   🤖 Recommendations generated: {entry['recommendations_generated_at']}")
                print(f"   ✅ Selections made: {entry['selections_made_at']}")
                print(f"   📊 Total suggested: {entry['total_suggested_count']}")
                print(f"   🎯 Total selected: {entry['total_selected_count']}")
                
                # Algorithm suggestions
                if entry['recommendations_generated_at']:
                    print(f"   🤖 Recommendations generated: {entry['recommendations_generated_at']}")
                    print(f"   📝 Form submitted: {entry['form_submitted_at']}")
                    
                    if entry['suggested_profiles']:
                        try:
                            # Handle both string and object types
                            if isinstance(entry['suggested_profiles'], str):
                                suggested = json.loads(entry['suggested_profiles'])
                            else:
                                suggested = entry['suggested_profiles']
                            
                            print(f"   📋 Suggested profiles: {len(suggested)}")
                            
                            # Show all suggested profiles with scores
                            for j, profile in enumerate(suggested, 1):
                                trust = profile.get('trust', 0)
                                compat = profile.get('compatibility_score', 0)
                                print(f"      {j}. {profile['name']} - Trust: {trust:.3f}, Compatibility: {compat:.3f}")
                        except Exception as e:
                            print(f"   ⚠️  Could not parse suggested profiles data: {e}")
                            print(f"   📄 Raw data type: {type(entry['suggested_profiles'])}")
                            print(f"   📄 Raw data: {entry['suggested_profiles'][:100]}...")
                    
                    # User selections
                    if entry['selections_made_at']:
                        print(f"\n   ✅ User Selections:")
                        print(f"      Selections made at: {entry['selections_made_at']}")
                        
                        if entry['selected_profiles']:
                            try:
                                # Handle both string and object types
                                if isinstance(entry['selected_profiles'], str):
                                    selected = json.loads(entry['selected_profiles'])
                                else:
                                    selected = entry['selected_profiles']
                                
                                print(f"      📋 Selected profiles: {len(selected)}")
                                
                                # Show all selected profiles with scores
                                for j, profile in enumerate(selected, 1):
                                    trust = profile.get('trust', 0)
                                    compat = profile.get('compatibility_score', 0)
                                    print(f"         {j}. {profile['name']} - Trust: {trust:.3f}, Compatibility: {compat:.3f}")
                            except Exception as e:
                                print(f"      ⚠️  Could not parse selected profiles data: {e}")
                        else:
                            print(f"      📋 Selected profiles: 0")
                            print(f"         💡 User clicked 'No match found!' - no suitable companions selected")
                            
                            # Show suggested profiles even when no selections made
                            if entry['suggested_profiles']:
                                try:
                                    # Handle both string and object types
                                    if isinstance(entry['suggested_profiles'], str):
                                        suggested = json.loads(entry['suggested_profiles'])
                                    else:
                                        suggested = entry['suggested_profiles']
                                    
                                except Exception as e:
                                    print(f"   ⚠️  Could not parse suggested profiles data: {e}")
                                    print(f"   📄 Raw data type: {type(entry['suggested_profiles'])}")
                                    print(f"   📄 Raw data: {entry['suggested_profiles'][:100]}...")
                
                print("   " + "-" * 60)
    
    except Exception as e:
        print(f"❌ Database error: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    show_all_entries()
