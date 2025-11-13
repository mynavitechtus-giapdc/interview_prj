import csv
import json
import sys
from config.database import db_manager, Question
from src.embeddings.vector_store import VectorStoreManager

def import_from_csv(filepath: str):
    """Import from CSV file"""
    vector_store = VectorStoreManager()
    session = db_manager.get_session()
    
    count = 0
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                question = Question(
                    name=row['name'],
                    answer=row['answer'],
                    category=row.get('category'),
                    level=row.get('level', 'all')
                )
                session.add(question)
                session.flush()
                
                vector_store.add_question(
                    question_id=question.id,
                    question_text=row['name'],
                    answer=row['answer'],
                    metadata={
                        "category": row.get('category'),
                        "level": row.get('level', 'all')
                    }
                )
                
                count += 1
                print(f" [{count}] {row['name'][:60]}...")
        
        session.commit()
        print(f"\n Imported {count} questions from CSV!")
        
    except Exception as e:
        session.rollback()
        print(f"\n Error: {e}")
        raise
    finally:
        session.close()

def import_from_json(filepath: str):
    """Import from JSON file"""
    vector_store = VectorStoreManager()
    session = db_manager.get_session()
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for i, q in enumerate(data, 1):
            question = Question(
                name=q['name'],
                answer=q['answer'],
                category=q.get('category'),
                level=q.get('level', 'all')
            )
            session.add(question)
            session.flush()
            
            vector_store.add_question(
                question_id=question.id,
                question_text=q['name'],
                answer=q['answer'],
                metadata={
                    "category": q.get('category'),
                    "level": q.get('level', 'all')
                }
            )
            
            print(f" [{i}] {q['name'][:60]}...")
        
        session.commit()
        print(f"\n Imported {len(data)} questions from JSON!")
        
    except Exception as e:
        session.rollback()
        print(f"\n Error: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_questions.py <file.csv|file.json>")
        print("\nCSV Format:")
        print("  name,answer,category,level")
        print('  "Question text","Answer text","technical","mid"')
        print("\nJSON Format:")
        print('  [{"name": "...", "answer": "...", "category": "...", "level": "..."}]')
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if filepath.endswith('.csv'):
        import_from_csv(filepath)
    elif filepath.endswith('.json'):
        import_from_json(filepath)
    else:
        print(" File must be .csv or .json")
        sys.exit(1)