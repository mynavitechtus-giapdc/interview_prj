from config.database import db_manager, Question, UserInteraction
from sqlalchemy import inspect
import sys

def create_database():
    """Create database schema"""
    print(" Creating Interview System Database...")
    print(f"   Database: {db_manager.db_url.split('@')[-1]}")
    
    try:
        if not db_manager.test_connection():
            sys.exit(1)
        
        db_manager.create_tables()
        
        inspector = inspect(db_manager.engine)
        tables = inspector.get_table_names()
        
        print("\n Database created successfully!")
        print(f"   Tables: {', '.join(tables)}")
        
        session = db_manager.get_session()
        try:
            question_count = session.query(Question).count()
            interaction_count = session.query(UserInteraction).count()
            
            print(f"\n Current data:")
            print(f"   Questions: {question_count}")
            print(f"   Interactions: {interaction_count}")
        finally:
            session.close()
            
    except Exception as e:
        print(f"\n Error: {e}")
        sys.exit(1)

def reset_database():
    """Reset database (DELETE ALL DATA)"""
    response = input("\n  This will DELETE all data! Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled.")
        return
    
    print("\n  Dropping all tables...")
    db_manager.drop_tables()
    
    print(" Recreating tables...")
    db_manager.create_tables()
    
    print(" Database reset complete!")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        reset_database()
    else:
        create_database()