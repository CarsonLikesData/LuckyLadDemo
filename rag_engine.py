# RAG Engine for Lucky Lad Invoice Processor
# This module implements a Retrieval-Augmented Generation engine
# to enhance Vertex AI validation accuracy by providing relevant context
# from previously processed invoices.

import os
import numpy as np
import faiss
import pickle
from datetime import datetime
from typing import Dict, List, Any
from sentence_transformers import SentenceTransformer
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("rag_engine")

# Configuration
VECTOR_DB_DIR = "vector_db"
EMBEDDINGS_FILE = os.path.join(VECTOR_DB_DIR, "invoice_embeddings.pkl")
INDEX_FILE = os.path.join(VECTOR_DB_DIR, "invoice_index.faiss")
METADATA_FILE = os.path.join(VECTOR_DB_DIR, "invoice_metadata.pkl")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Lightweight model for embeddings
TOP_K_SIMILAR = 3  # Number of similar invoices to retrieve

class RAGEngine:
    """
    Retrieval-Augmented Generation engine for invoice processing.
    This class handles the storage, retrieval, and augmentation of invoice data
    to enhance Vertex AI validation accuracy.
    """
    
    def __init__(self):
        """Initialize the RAG engine with vector database and embedding model."""
        # Create vector database directory if it doesn't exist
        if not os.path.exists(VECTOR_DB_DIR):
            os.makedirs(VECTOR_DB_DIR)
            logger.info(f"Created vector database directory: {VECTOR_DB_DIR}")
        
        # Initialize embedding model
        try:
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
            logger.info(f"Loaded embedding model: {EMBEDDING_MODEL}")
        except Exception as e:
            logger.error(f"Error loading embedding model: {e}")
            self.embedding_model = None
        
        # Initialize or load vector index
        self.index = None
        self.embeddings = []
        self.metadata = []
        self._load_or_create_index()
    
    def _load_or_create_index(self):
        """Load existing vector index or create a new one if it doesn't exist."""
        try:
            if os.path.exists(INDEX_FILE) and os.path.exists(METADATA_FILE) and os.path.exists(EMBEDDINGS_FILE):
                # Load existing index and metadata
                self.index = faiss.read_index(INDEX_FILE)
                with open(METADATA_FILE, 'rb') as f:
                    self.metadata = pickle.load(f)
                with open(EMBEDDINGS_FILE, 'rb') as f:
                    self.embeddings = pickle.load(f)
                logger.info(f"Loaded existing vector index with {len(self.metadata)} invoices")
            else:
                # Create new index
                self.index = faiss.IndexFlatL2(384)  # Dimension of the embedding model
                self.metadata = []
                self.embeddings = []
                logger.info("Created new vector index")
        except Exception as e:
            logger.error(f"Error loading/creating vector index: {e}")
            # Create new index as fallback
            self.index = faiss.IndexFlatL2(384)
            self.metadata = []
            self.embeddings = []
    
    def _save_index(self):
        """Save the current vector index and metadata to disk."""
        try:
            faiss.write_index(self.index, INDEX_FILE)
            with open(METADATA_FILE, 'wb') as f:
                pickle.dump(self.metadata, f)
            with open(EMBEDDINGS_FILE, 'wb') as f:
                pickle.dump(self.embeddings, f)
            logger.info(f"Saved vector index with {len(self.metadata)} invoices")
        except Exception as e:
            logger.error(f"Error saving vector index: {e}")
    
    def _generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for the given text."""
        if self.embedding_model is None:
            logger.error("Embedding model not initialized")
            return np.zeros(384)  # Return zero vector as fallback
        
        try:
            embedding = self.embedding_model.encode(text)
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return np.zeros(384)  # Return zero vector as fallback
    
    def _prepare_invoice_text(self, document_text: str, entities: Dict[str, Any]) -> str:
        """Prepare invoice text for embedding by combining document text and entities."""
        # Combine document text and entities into a single string for embedding
        text_parts = [document_text[:1000]]  # Limit document text to first 1000 chars
        
        # Add entities as key-value pairs
        for key, value in entities.items():
            if isinstance(value, str):
                text_parts.append(f"{key}: {value}")
        
        return "\n".join(text_parts)
    
    def add_invoice(self, document_text: str, entities: Dict[str, Any], metadata: Dict[str, Any]) -> bool:
        """
        Add a processed invoice to the vector database.
        
        Args:
            document_text: The raw text of the invoice document
            entities: The extracted entities from Document AI
            metadata: Additional metadata about the invoice (filename, date, etc.)
            
        Returns:
            bool: True if the invoice was added successfully, False otherwise
        """
        try:
            # Prepare text for embedding
            invoice_text = self._prepare_invoice_text(document_text, entities)
            
            # Generate embedding
            embedding = self._generate_embedding(invoice_text)
            
            # Add to index
            self.index.add(np.array([embedding], dtype=np.float32))
            self.embeddings.append(embedding)
            
            # Add metadata with timestamp
            invoice_metadata = {
                "timestamp": datetime.now().isoformat(),
                "document_text": document_text[:1000],  # Store truncated text
                "entities": entities,
                "metadata": metadata
            }
            self.metadata.append(invoice_metadata)
            
            # Save index
            self._save_index()
            
            logger.info(f"Added invoice to vector database: {metadata.get('filename', 'Unknown')}")
            return True
        except Exception as e:
            logger.error(f"Error adding invoice to vector database: {e}")
            return False
    
    def retrieve_similar_invoices(self, document_text: str, entities: Dict[str, Any], k: int = TOP_K_SIMILAR) -> List[Dict[str, Any]]:
        """
        Retrieve similar invoices from the vector database.
        
        Args:
            document_text: The raw text of the invoice document
            entities: The extracted entities from Document AI
            k: Number of similar invoices to retrieve
            
        Returns:
            List of similar invoice metadata
        """
        if len(self.metadata) == 0:
            logger.info("Vector database is empty, no similar invoices to retrieve")
            return []
        
        try:
            # Prepare text for embedding
            invoice_text = self._prepare_invoice_text(document_text, entities)
            
            # Generate embedding
            query_embedding = self._generate_embedding(invoice_text)
            
            # Search index
            k = min(k, len(self.metadata))  # Ensure k is not larger than the number of invoices
            distances, indices = self.index.search(np.array([query_embedding], dtype=np.float32), k)
            
            # Get metadata for similar invoices
            similar_invoices = [self.metadata[idx] for idx in indices[0]]
            
            logger.info(f"Retrieved {len(similar_invoices)} similar invoices")
            return similar_invoices
        except Exception as e:
            logger.error(f"Error retrieving similar invoices: {e}")
            return []
    
    def generate_context_for_vertex_ai(self, similar_invoices: List[Dict[str, Any]]) -> str:
        """
        Generate context from similar invoices for Vertex AI prompt augmentation.
        
        Args:
            similar_invoices: List of similar invoice metadata
            
        Returns:
            String containing context from similar invoices
        """
        if not similar_invoices:
            return ""
        
        context_parts = ["CONTEXT FROM SIMILAR INVOICES:"]
        
        for i, invoice in enumerate(similar_invoices):
            entities = invoice.get("entities", {})
            metadata = invoice.get("metadata", {})
            
            context_parts.append(f"\nSimilar Invoice {i+1}:")
            context_parts.append(f"Filename: {metadata.get('filename', 'Unknown')}")
            
            # Add key entities that might be useful for validation
            key_entities = [
                "vendor_name", "invoice_id", "invoice_number", "invoice_date",
                "total_amount", "balance_due", "well_name", "field", "charge"
            ]
            
            for key in key_entities:
                if key in entities and entities[key]:
                    context_parts.append(f"{key}: {entities[key]}")
            
            # Add any well-related information
            for key, value in entities.items():
                if isinstance(value, str) and any(term in key.lower() for term in ["well", "field", "lease", "charge"]):
                    if key not in key_entities:  # Avoid duplicates
                        context_parts.append(f"{key}: {value}")
        
        return "\n".join(context_parts)

# Singleton instance
_rag_engine = None

def get_rag_engine() -> RAGEngine:
    """Get or create the RAG engine singleton instance."""
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine