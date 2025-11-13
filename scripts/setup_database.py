from config.database import db_manager, Question
from src.embeddings.vector_store import VectorStoreManager
from src.utils.logger import logger

def import_questions_to_db():
    """Import questions to database first"""
    mock_questions = [
        {
            "name": "Can you explain the difference between var, let, and const in JavaScript?",
            "answer": "var has **function scope** and is fully **hoisted**. let has **block scope** and is partially hoisted (Temporal Dead Zone). const also has **block scope** and prevents **reassignment** of the variable (though object properties can still change). Use **const** by default, and **let** when reassignment is necessary.",
            "category": "technical",
            "level": "junior"
        },
        {
            "name": "How do REST API and GraphQL differ?",
            "answer": "REST uses **multiple endpoints** and often results in **over-fetching** or under-fetching data. GraphQL uses a **single endpoint** and allows the **client to request only the exact data needed**, reducing the number of requests and optimizing bandwidth. GraphQL is preferred for complex apps; REST is simpler for basic CRUD operations.",
            "category": "technical",
            "level": "mid"
        },
        {
            "name": "How do you handle conflicts within your team?",
            "answer": "I **actively listen** to all sides and determine the **root cause** of the conflict. I prioritize **data-driven, objective solutions** over personal opinions. The focus is always on communication, empathy, and aligning the team toward the **common project goal**.",
            "category": "behavioral",
            "level": "all"
        },
        {
            "name": "Tell me about a time you failed in a project and what you learned from it.",
            "answer": "I once **underestimated the testing time** for Project X, which delayed the final release. I learned the critical importance of **realistic estimation**, including buffer time for unexpected issues, and the value of **early, continuous testing**. I subsequently implemented more rigorous TDD (Test-Driven Development) practices.",
            "category": "behavioral",
            "level": "mid"
        },
        {
            "name": "Explain the concept of Microservices and when we should use them.",
            "answer": "Microservices is an architecture where the application is split into **small, independent services** that are separately deployable. It's best used when a team is large, requires **independent scaling** for different components, or needs technology diversity. The main tradeoff is the **increased complexity** in infrastructure and monitoring.",
            "category": "technical",
            "level": "senior"
        },
        {
            "name": "How do you keep up-to-date with new technologies?",
            "answer": "I consistently read technical blogs (e.g., Medium, Dev.to), follow key industry experts, and dedicate **2-3 hours per week** to formal learning through online courses. I ensure practical application by **building small side projects** or contributing to relevant open-source projects.",
            "category": "soft_skills",
            "level": "all"
        },
        {
            "name": "What is database indexing and when should you create an index?",
            "answer": "An index is a data structure that allows the database to **quickly locate data** without scanning the entire table, significantly speeding up **read operations**. Indices should be created on columns used in **`WHERE` clauses, `JOINs`, and `ORDER BY`**. The tradeoff is slower **write operations** (INSERT/UPDATE) and increased storage cost.",
            "category": "technical",
            "level": "mid"
        },
        {
            "name": "How do you prioritize tasks when facing multiple deadlines?",
            "answer": "I primarily use the **Eisenhower Matrix** (Urgent/Important) to categorize and prioritize tasks. I maintain open **communication with stakeholders** about priorities and potential risks. Tasks are broken down into smaller pieces, and I always ensure a small **buffer time** for unexpected issues.",
            "category": "soft_skills",
            "level": "all"
        },
        {
            "name": "What is CI/CD and what are its benefits?",
            "answer": "CI/CD stands for **Continuous Integration** and **Continuous Deployment/Delivery**. CI means developers merge code frequently into a shared repository, triggering **automated tests**. CD automates the process of deploying the code to production. Benefits include **faster delivery cycles**, reduced manual errors, and **early bug detection**.",
            "category": "technical",
            "level": "mid"
        },
        {
            "name": "How do you handle negative feedback from your manager?",
            "answer": "I receive feedback professionally, **listening actively** without becoming defensive, and **ask clarifying questions** to fully understand the specific issue. I focus on creating a concrete **action plan for improvement** and follow up regularly to demonstrate progress. I view negative feedback as an opportunity for professional growth.",
            "category": "behavioral",
            "level": "all"
        }
    ]
    
    session = db_manager.get_session()
    
    try: 
        # Import to database
        added_questions = []
        for i, q in enumerate(mock_questions, 1):
            print(f"  [{i}/{len(mock_questions)}] Adding to DB: {q['name'][:60]}...")
            
            question = Question(
                name=q['name'],
                answer=q['answer'],
                category=q['category'],
                level=q['level']
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
        
        print(f"\n  ✓ Successfully added {len(added_questions)} questions to database")
        return added_questions
        
    except Exception as e:
        session.rollback()
        print(f"\n  ✗ Error importing to database: {e}")
        raise
    finally:
        session.close()


def import_questions_to_vectorstore(questions):
    """Import questions to vector store for semantic search"""
    
    if not questions:
        print("\n  No questions to import to vector store")
        return
    
    print(f"\n[STEP 2] Importing {len(questions)} questions to vector store...")
    
    vector_store = VectorStoreManager()
    
    try:
        for i, q in enumerate(questions, 1):
            print(f"  [{i}/{len(questions)}] Adding to VectorStore: {q['name'][:60]}...")
            
            vector_store.add_question(
                question_id=q['id'],
                question_text=q['name'],
                answer=q['answer'],
                metadata={
                    "category": q['category'],
                    "level": q['level']
                }
            )
        
        print(f"\n  ✓ Successfully added {len(questions)} questions to vector store")
        
    except Exception as e:
        print(f"\n  ✗ Error importing to vector store: {e}")
        raise


def setup_interview_questions():
    """Main setup function - orchestrates the import process"""
    
    print("="*70)
    print("INTERVIEW QUESTIONS SETUP")
    print("="*70)
    
    try:
        # Step 1: Import to database
        questions = import_questions_to_db()
        
        if not questions:
            return
        
        # Step 2: Import to vector store
        import_questions_to_vectorstore(questions)
        
        # Summary
        print("\n" + "="*70)
        print("SETUP COMPLETE!")
        print("="*70)
        print(f"  ✓ Total questions added: {len(questions)}")
        print(f"  ✓ Categories: technical, behavioral, soft_skills")
        print(f"  ✓ Levels: junior, mid, senior, all")
        print("="*70)
        
    except Exception as e:
        print(f"\n✗ Setup failed: {e}")
        logger.error(f"Setup interview questions failed: {e}")
        raise


if __name__ == "__main__":
    setup_interview_questions()