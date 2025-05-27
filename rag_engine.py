# RAG Engine for Lucky Lad Invoice Processor
# This module implements a Retrieval-Augmented Generation engine
# to enhance Vertex AI validation accuracy by providing relevant context
# from previously processed invoices.

import os
import numpy as np
import pickle
from typing import Dict, List, Any
import logging

# Improved dependency checking
try:
    import faiss

    FAISS_AVAILABLE = True
    print("✅ FAISS imported successfully")
except ImportError as e:
    FAISS_AVAILABLE = False
    faiss = None
    print(f"❌ FAISS import failed: {e}")

try:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
    print("✅ SentenceTransformers imported successfully")
except ImportError as e:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None
    print(f"❌ SentenceTransformers import failed: {e}")

# Configuration
VECTOR_DB_DIR = "vector_db"
EMBEDDINGS_FILE = os.path.join(VECTOR_DB_DIR, "invoice_embeddings.pkl")
INDEX_FILE = os.path.join(VECTOR_DB_DIR, "invoice_index.faiss")
METADATA_FILE = os.path.join(VECTOR_DB_DIR, "invoice_metadata.pkl")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
TOP_K_SIMILAR = 3

logger = logging.getLogger("rag_engine")


class RAGEngine:
    def __init__(self):
        """Initialize the RAG engine with vector database and embedding model."""
        print("🚀 Initializing RAG Engine...")

        # Create vector database directory if it doesn't exist
        if not os.path.exists(VECTOR_DB_DIR):
            os.makedirs(VECTOR_DB_DIR)
            logger.info(f"Created vector database directory: {VECTOR_DB_DIR}")

        # Check dependencies first
        self._check_dependencies()

        # Initialize embedding model
        self.embedding_model = None
        self._initialize_embedding_model()

        # Initialize or load vector index
        self.index = None
        self.embeddings = []
        self.metadata = []
        self._load_or_create_index()

        # Final verification
        self._verify_initialization()

    def _check_dependencies(self):
        """Check if required dependencies are available."""
        missing_deps = []

        print("🔍 Checking dependencies...")
        print(f"   FAISS_AVAILABLE: {FAISS_AVAILABLE}")
        print(f"   SENTENCE_TRANSFORMERS_AVAILABLE: {SENTENCE_TRANSFORMERS_AVAILABLE}")

        if not FAISS_AVAILABLE:
            missing_deps.append("faiss-cpu")
            logger.error("FAISS not available. Install with: pip install faiss-cpu")

        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            missing_deps.append("sentence-transformers")
            logger.error(
                "SentenceTransformers not available. Install with: pip install sentence-transformers"
            )

        if missing_deps:
            raise ImportError(
                f"Missing required dependencies: {', '.join(missing_deps)}"
            )

    def _initialize_embedding_model(self):
        """Initialize the sentence transformer model."""
        print("🤖 Initializing embedding model...")

        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.error(
                "Cannot initialize embedding model: SentenceTransformers not available"
            )
            return

        try:
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
            logger.info(f"Loaded embedding model: {EMBEDDING_MODEL}")

            # Test the model
            test_embedding = self.embedding_model.encode("test")
            logger.info(
                f"Embedding model test successful. Dimension: {len(test_embedding)}"
            )
            print("✅ Embedding model loaded successfully")

        except Exception as e:
            logger.error(f"Error loading embedding model: {e}")
            print(f"   ❌ Embedding model failed: {e}")
            self.embedding_model = None

    def _load_or_create_index(self):
        """Load existing vector index or create a new one if it doesn't exist."""
        print("📊 Loading or creating vector index...")

        if not FAISS_AVAILABLE:
            logger.error("Cannot create index: FAISS not available")
            print("   ❌ FAISS not available")
            return

        try:
            # Try to load existing index
            if (
                os.path.exists(INDEX_FILE)
                and os.path.exists(METADATA_FILE)
                and os.path.exists(EMBEDDINGS_FILE)
            ):
                logger.info("Loading existing vector index...")
                print("   📂 Loading existing index...")

                self.index = faiss.read_index(INDEX_FILE)

                with open(METADATA_FILE, "rb") as f:
                    self.metadata = pickle.load(f)

                with open(EMBEDDINGS_FILE, "rb") as f:
                    self.embeddings = pickle.load(f)

                logger.info(
                    f"Loaded existing vector index with {len(self.metadata)} invoices"
                )
                print(f"   ✅ Loaded existing index with {len(self.metadata)} invoices")

            else:
                # Create new index
                logger.info("Creating new vector index...")
                print("   🆕 Creating new index...")
                self._create_new_index()

        except Exception as e:
            logger.error(f"Error in _load_or_create_index: {e}")
            print(f"   ⚠️ Error loading index: {e}")
            logger.info("Attempting to create new index as fallback...")
            print("   🔄 Creating fallback index...")

            try:
                self._create_new_index()
            except Exception as e2:
                logger.error(f"Failed to create fallback index: {e2}")
                print(f"   ❌ Fallback index creation failed: {e2}")
                logger.error("RAG Engine initialization failed!")
                self.index = None

    def _create_new_index(self):
        """Create a new FAISS index."""
        print("   🏗️ Creating new FAISS index...")

        if not FAISS_AVAILABLE:
            raise RuntimeError("Cannot create index: FAISS not available")

        try:
            # Test FAISS functionality first
            test_index = faiss.IndexFlatL2(384)
            print("   ✅ FAISS test successful")

            # Create new index with dimension 384 (all-MiniLM-L6-v2 embedding size)
            self.index = faiss.IndexFlatL2(384)
            self.metadata = []
            self.embeddings = []

            logger.info("Created new vector index")
            print("   ✅ New vector index created")

            # Save the empty index immediately to verify we can write
            self._save_index()
            print("   ✅ Index saved successfully")

        except Exception as e:
            logger.error(f"Error creating new FAISS index: {e}")
            print(f"   ❌ FAISS index creation failed: {e}")
            raise

    def _verify_initialization(self):
        """Verify that all components are properly initialized."""
        print("✅ Verifying initialization...")
        issues = []

        if not FAISS_AVAILABLE:
            issues.append("FAISS not available")
        elif self.index is None:
            issues.append("FAISS index is None")

        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            issues.append("SentenceTransformers not available")
        elif self.embedding_model is None:
            issues.append("Embedding model is None")

        if self.metadata is None:
            issues.append("Metadata is None")
            self.metadata = []

        if self.embeddings is None:
            issues.append("Embeddings is None")
            self.embeddings = []

        if issues:
            error_msg = f"RAG Engine initialization issues: {', '.join(issues)}"
            logger.error(error_msg)
            print(f"   ❌ {error_msg}")
            raise RuntimeError(error_msg)
        else:
            logger.info("✅ RAG Engine initialized successfully")
            logger.info(f"Index type: {type(self.index)}")
            logger.info(f"Embedding model type: {type(self.embedding_model)}")
            logger.info(f"Current invoice count: {len(self.metadata)}")

            print("   ✅ All components verified")
            print(f"   📊 Index type: {type(self.index)}")
            print(f"   🤖 Embedding model: {type(self.embedding_model)}")
            print(f"   📁 Current invoices: {len(self.metadata)}")

    def _create_new_index(self):
        """Create a new FAISS index."""
        if not FAISS_AVAILABLE:
            raise RuntimeError("Cannot create index: FAISS not available")

        try:
            # Create new index with dimension 384 (all-MiniLM-L6-v2 embedding size)
            self.index = faiss.IndexFlatL2(384)
            self.metadata = []
            self.embeddings = []

            logger.info("Created new vector index")

            # Save the empty index immediately to verify we can write
            self._save_index()

        except Exception as e:
            logger.error(f"Error creating new FAISS index: {e}")
            raise

    def get_status(self):
        """Get the current status of the RAG engine."""
        return {
            "embedding_model_loaded": self.embedding_model is not None,
            "index_initialized": self.index is not None,
            "num_invoices": len(self.metadata) if self.metadata else 0,
            "index_dimension": self.index.d if self.index else None,
            "vector_db_dir": VECTOR_DB_DIR,
            "files_exist": {
                "index": os.path.exists(INDEX_FILE),
                "metadata": os.path.exists(METADATA_FILE),
                "embeddings": os.path.exists(EMBEDDINGS_FILE),
            },
        }

    def _save_index(self):
        """Save the current vector index and metadata to disk."""
        try:
            faiss.write_index(self.index, INDEX_FILE)
            with open(METADATA_FILE, "wb") as f:
                pickle.dump(self.metadata, f)
            with open(EMBEDDINGS_FILE, "wb") as f:
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

    def _prepare_invoice_text(
        self, document_text: str, entities: Dict[str, Any]
    ) -> str:
        """Prepare invoice text for embedding by combining document text and entities."""
        # Combine document text and entities into a single string for embedding
        text_parts = [document_text[:1000]]  # Limit document text to first 1000 chars

        # Add entities as key-value pairs
        for key, value in entities.items():
            if isinstance(value, str):
                text_parts.append(f"{key}: {value}")

        return "\n".join(text_parts)

    def add_invoice(
        self, document_text: str, entities: Dict[str, Any], metadata: Dict[str, Any]
    ) -> bool:
        """Add a processed invoice to the vector database."""
        # Check prerequisites
        if self.index is None:
            logger.error("Cannot add invoice: FAISS index is None")
            return False

        if self.embedding_model is None:
            logger.error("Cannot add invoice: Embedding model is None")
            return False

        try:
            # Prepare text for embedding
            invoice_text = self._prepare_invoice_text(document_text, entities)

            # Generate embedding
            embedding = self._generate_embedding(invoice_text)

            # Add to index
            self.index.add(np.array([embedding], dtype=np.float32))
            self.embeddings.append(embedding)

            # Add metadata with timestamp
            from datetime import datetime

            invoice_metadata = {
                "timestamp": datetime.now().isoformat(),
                "document_text": document_text[:1000],  # Store truncated text
                "entities": entities,
                "metadata": metadata,
            }
            self.metadata.append(invoice_metadata)

            # Save index
            self._save_index()

            logger.info(
                f"Added invoice to vector database: {metadata.get('filename', 'Unknown')}"
            )
            return True

        except Exception as e:
            logger.error(f"Error adding invoice to vector database: {e}")
            import traceback

            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def retrieve_similar_invoices(
        self, document_text: str, entities: Dict[str, Any], k: int = TOP_K_SIMILAR
    ) -> List[Dict[str, Any]]:
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
            k = min(
                k, len(self.metadata)
            )  # Ensure k is not larger than the number of invoices
            distances, indices = self.index.search(
                np.array([query_embedding], dtype=np.float32), k
            )

            # Get metadata for similar invoices
            similar_invoices = [self.metadata[idx] for idx in indices[0]]

            logger.info(f"Retrieved {len(similar_invoices)} similar invoices")
            return similar_invoices
        except Exception as e:
            logger.error(f"Error retrieving similar invoices: {e}")
            return []

    def generate_context_for_vertex_ai(
        self, similar_invoices: List[Dict[str, Any]]
    ) -> str:
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

            context_parts.append(f"\nSimilar Invoice {i + 1}:")
            context_parts.append(f"Filename: {metadata.get('filename', 'Unknown')}")

            # Add key entities that might be useful for validation
            key_entities = [
                "vendor_name",
                "invoice_id",
                "invoice_number",
                "invoice_date",
                "total_amount",
                "balance_due",
                "well_name",
                "field",
                "charge",
            ]

            for key in key_entities:
                if key in entities and entities[key]:
                    context_parts.append(f"{key}: {entities[key]}")

            # Add any well-related information
            for key, value in entities.items():
                if isinstance(value, str) and any(
                    term in key.lower() for term in ["well", "field", "lease", "charge"]
                ):
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
