from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.docstore.document import Document
from typing import List, Dict, Tuple
import os

from config.settings import settings
from src.utils.logger import logger

class VectorStoreManager:

    def __init__(self):
        # Initialize embeddings with proper configuration
        model_name = getattr(settings, 'embedding_model', None)
        if not model_name:
            model_name = 'sentence-transformers/all-MiniLM-L6-v2'
            logger.info(f"Using default embedding model: {model_name}")
        else:
            logger.info(f"Using embedding model: {model_name}")

        try:
            self.embeddings = HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            # Test embedding to ensure model is loaded correctly
            _ = self.embeddings.embed_query("test")
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model '{model_name}': {e}")
            # Fallback to default model
            logger.info("Falling back to default model: sentence-transformers/all-MiniLM-L6-v2")
            self.embeddings = HuggingFaceEmbeddings(
                model_name='sentence-transformers/all-MiniLM-L6-v2',
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            _ = self.embeddings.embed_query("test")

        self.vectorstore = None
        self.load_or_create_vectorstore()

    def load_or_create_vectorstore(self):
        try:
            if os.path.exists(settings.vector_store_path):
                self.vectorstore = FAISS.load_local(
                    settings.vector_store_path,
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                logger.info("Loaded existing vector store")
            else:
                dummy_doc = Document(
                    page_content="Initialization document",
                    metadata={"type": "init"}
                )
                self.vectorstore = FAISS.from_documents([dummy_doc], self.embeddings)
                self.save_vectorstore()
                logger.info("Created new vector store")
        except Exception as e:
            logger.error(f"Error loading vector store: {e}")
            raise

    def add_question(self, question_id: int, question_text: str, answer: str, metadata: Dict = None):
        doc = Document(
            page_content=question_text,
            metadata={
                "question_id": question_id,
                "question": question_text,
                "answer": answer,
                **(metadata or {})
            }
        )
        self.vectorstore.add_documents([doc])
        self.save_vectorstore()
        logger.info(f"Added question #{question_id} to vector store")

    def search_with_score(self, query: str, k: int = None) -> List[Tuple[Document, float]]:
        k = k or settings.top_k_results

        # FAISS returns (document, distance) tuples
        results = self.vectorstore.similarity_search_with_score(query, k=k)

        # Convert L2 distances to similarity scores
        converted_results = []

        logger.info(f"\n=== Vector Search Results for: '{query}' ===")

        for i, (doc, distance) in enumerate(results, 1):
            # Convert L2 distance to similarity
            # Method 1: Exponential decay (works well for most cases)
            similarity = self._distance_to_similarity(distance)

            converted_results.append((doc, similarity))

            # Debug logging
            logger.info(
                f"[{i}] Distance: {distance:.4f} -> Similarity: {similarity:.4f} ({similarity*100:.2f}%) | "
                f"Q: {doc.metadata.get('question', '')[:80]}"
            )

        logger.info("="*80 + "\n")

        return converted_results

    def _distance_to_similarity(self, distance: float) -> float:
        import math
        similarity = math.exp(-distance)

        # Ensure valid range
        return max(0.0, min(1.0, similarity))

    def save_vectorstore(self):
        # Save vector store to disk
        os.makedirs(os.path.dirname(settings.vector_store_path), exist_ok=True)
        self.vectorstore.save_local(settings.vector_store_path)
        logger.info("Saved vector store")
