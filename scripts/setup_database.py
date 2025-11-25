from config.database import db_manager, Question
from langchain_community.embeddings import HuggingFaceEmbeddings
from config.settings import settings
from src.utils.logger import logger
import csv
import os

def load_questions_from_csv(csv_path: str = "data/imports/sample_questions.csv"):
    """Load questions from CSV file"""
    questions = []
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            questions.append({
                'name': row['name'],
                'answer': row['answer'],
                'category': row['category'],
                'level': row['level']
            })
    
    return questions


def import_questions_to_db():
    """Import questions from CSV to database with pgvector embeddings"""
    
    print("\n[STEP 1] Loading questions from CSV...")
    questions_data = load_questions_from_csv()
    print(f"  ✓ Loaded {len(questions_data)} questions from CSV")
    
    print("\n[STEP 2] Initializing embedding model...")
    embeddings_model = HuggingFaceEmbeddings(
        model_name=settings.embedding_model
    )
    print(f"  ✓ Loaded embedding model: {settings.embedding_model}")
    
    session = db_manager.get_session()
    
    try: 
        print("\n[STEP 3] Importing questions to database with embeddings...")
        added_questions = []
        
        for i, q in enumerate(questions_data, 1):
            print(f"  [{i}/{len(questions_data)}] Processing: {q['name'][:60]}...")
            
            # Generate embedding for question text
            embedding_vector = embeddings_model.embed_query(q['name'])
            
            question = Question(
                name=q['name'],
                answer=q['answer'],
                category=q['category'],
                level=q['level'],
                embedding=embedding_vector
            )
            session.add(question)
            session.flush()  # Get ID immediately
            
            added_questions.append({
                'id': question.id,
                'name': q['name'],
                'answer': q['answer'],
                'category': q['category'],
                'level': q['level']
            })
        
        session.commit()
        
        print(f"\n  ✓ Successfully added {len(added_questions)} questions with embeddings to database")
        return added_questions
        
    except Exception as e:
        session.rollback()
        print(f"\n  ✗ Error importing to database: {e}")
        raise
    finally:
        session.close()


def setup_interview_questions():
    """Main setup function - import questions from CSV with pgvector embeddings"""
    
    print("="*70)
    print("INTERVIEW QUESTIONS SETUP (CSV + PGVECTOR)")
    print("="*70)
    
    try:
        # Import to database with embeddings
        questions = import_questions_to_db()
        
        if not questions:
            return
        
        # Summary
        print("\n" + "="*70)
        print("SETUP COMPLETE!")
        print("="*70)
        print(f"  ✓ Total questions imported: {len(questions)}")
        print(f"  ✓ Source: data/imports/sample_questions.csv")
        print(f"  ✓ Embeddings: Stored in PostgreSQL with pgvector")
        print(f"  ✓ Categories: technical, behavioral, soft_skills")
        print(f"  ✓ Levels: junior, mid, senior, all")
        print("="*70)
        
    except Exception as e:
        print(f"\n✗ Setup failed: {e}")
        logger.error(f"Setup interview questions failed: {e}")
        raise


if __name__ == "__main__":
    setup_interview_questions()