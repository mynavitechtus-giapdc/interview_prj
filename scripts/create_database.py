from config.database import db_manager, User, Question, UserInteraction, InterviewSession
from sqlalchemy import inspect
import sys

def create_database():
    """Create database schema"""
    print("\n" + "="*70)
    print("CREATING INTERVIEW SYSTEM DATABASE")
    print("="*70)
    print(f"Database: {db_manager.db_url.split('@')[-1]}")
    
    try:
        # Test connection
        print("\nTesting connection...")
        if not db_manager.test_connection():
            print("✗ Connection failed!")
            sys.exit(1)
        print("✓ Connection successful")
        
        # Create tables
        print("\nCreating tables...")
        db_manager.create_tables()
        
        # Verify tables
        inspector = inspect(db_manager.engine)
        tables = inspector.get_table_names()
        
        print("\n✓ Database created successfully!")
        print("\nTables created:")
        for table in sorted(tables):
            print(f"  ✓ {table}")
        
        # Show current data
        session = db_manager.get_session()
        try:
            user_count = session.query(User).count()
            question_count = session.query(Question).count()
            interaction_count = session.query(UserInteraction).count()
            session_count = session.query(InterviewSession).count()
            
            print(f"\nCurrent data:")
            print(f"  Users: {user_count}")
            print(f"  Questions: {question_count}")
            print(f"  Interactions: {interaction_count}")
            print(f"  Interview Sessions: {session_count}")
            
            print("\n" + "="*70)
            print("SETUP COMPLETE!")
            print("="*70)
            print("\nNext steps:")
            print("  1. Import questions: python scripts/setup_database.py")
            print("  2. Run interview: python main.py")
            print("  3. Start API: python api_server.py")
            print("="*70 + "\n")
            
        finally:
            session.close()
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)

def reset_database():
    """Reset database (DELETE ALL DATA)"""
    print("\n" + "="*70)
    print("RESET DATABASE")
    print("="*70)
    print("\n⚠️  WARNING: This will DELETE ALL DATA!")
    print("="*70)
    
    response = input("\nType '1' to confirm: ")
    if response != '1':
        print("\n✗ Reset cancelled.")
        return
    
    print("\n[1/2] Dropping all tables...")
    db_manager.drop_tables()
    print("  ✓ All tables dropped")
    
    print("\n[2/2] Recreating tables...")
    db_manager.create_tables()
    print("  ✓ All tables recreated")
    
    print("\n" + "="*70)
    print("DATABASE RESET COMPLETE!")
    print("="*70)
    print("\nNext step: Import questions")
    print("  python scripts/setup_database.py")
    print("="*70 + "\n")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        reset_database()
    else:
        create_database()