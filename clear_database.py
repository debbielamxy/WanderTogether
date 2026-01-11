#!/usr/bin/env python3
"""
Clear Database Script
Removes all entries from user_journey table
Use with caution - this will delete all data!
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL', "postgresql://wandertogetherdb_user:94Wr3w5tONCj72N6D9oGnlUU87b2AiNs@dpg-d58fuimr433s73f8dndg-a.oregon-postgres.render.com/wandertogetherdb")

def clear_database():
    print("🗑️  WanderTogether Database Clear Script")
    print("=" * 50)
    print("⚠️  WARNING: This will delete ALL user journey data!")
    print("=" * 50)
    
    # Show current data before clearing
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Count current entries
            cur.execute("SELECT COUNT(*) as count FROM user_journey")
            current_count = cur.fetchone()['count']
            
            print(f"📊 Current database entries: {current_count}")
            
            if current_count == 0:
                print("✅ Database is already empty")
                return
            
            # Show recent entries
            cur.execute("""
                SELECT user_name, created_at, total_selected_count 
                FROM user_journey 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            recent = cur.fetchall()
            
            if recent:
                print("\n📋 Recent entries that will be deleted:")
                for entry in recent:
                    selections = entry['total_selected_count'] or 0
                    print(f"   • {entry['user_name']} - {entry['created_at']} - {selections} selections")
            
            print("\n" + "=" * 50)
            print("🔍 To proceed with clearing, type 'y' or 'Y' and press Enter:")
            print("🔍 To cancel, press Enter without typing anything:")
            print("=" * 50)
            
            # Get user confirmation
            confirmation = input("Delete all entries? (y/N): ").strip()
            
            if confirmation.lower() != 'y':
                print("❌ Cancelled - Database not cleared")
                return
            
            print("\n🗑️  Clearing database...")
            
            # Delete all entries
            cur.execute("DELETE FROM user_journey")
            deleted_count = cur.rowcount
            conn.commit()
            
            print(f"✅ Successfully deleted {deleted_count} entries")
            
            # Verify deletion
            cur.execute("SELECT COUNT(*) as count FROM user_journey")
            new_count = cur.fetchone()['count']
            print(f"📊 New database entries: {new_count}")
            
            if new_count == 0:
                print("✅ Database is now completely empty")
            else:
                print(f"⚠️  {new_count} entries remain (unexpected)")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def reset_sequence():
    """Reset the ID sequence to start from 1"""
    print("\n🔄 Resetting ID sequence...")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            # Reset the sequence
            cur.execute("ALTER SEQUENCE user_journey_id_seq RESTART WITH 1")
            conn.commit()
            print("✅ ID sequence reset to start from 1")
            
    except Exception as e:
        print(f"❌ Error resetting sequence: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def show_status():
    """Show current database status"""
    print("\n📊 Database Status:")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Count entries
            cur.execute("SELECT COUNT(*) as count FROM user_journey")
            count = cur.fetchone()['count']
            
            # Get database size
            cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
            size = cur.fetchone()[0]
            
            print(f"   Total entries: {count}")
            print(f"   Database size: {size}")
            
            if count > 0:
                cur.execute("SELECT MIN(created_at) as earliest, MAX(created_at) as latest FROM user_journey")
                dates = cur.fetchone()
                print(f"   Date range: {dates['earliest']} to {dates['latest']}")
            
    except Exception as e:
        print(f"❌ Error getting status: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    """Main function"""
    print("🗑️  WanderTogether Database Management")
    print("=" * 50)
    
    # Show current status
    show_status()
    
    print("\n" + "=" * 50)
    print("Options:")
    print("1. Clear all entries (DELETE ALL DATA)")
    print("2. Show status only")
    print("3. Exit")
    print("=" * 50)
    
    choice = input("Choose option (1-3): ").strip()
    
    if choice == '1':
        clear_database()
        reset_sequence()
        show_status()
    elif choice == '2':
        show_status()
    elif choice == '3':
        print("👋 Goodbye!")
    else:
        print("❌ Invalid choice")

if __name__ == '__main__':
    main()
