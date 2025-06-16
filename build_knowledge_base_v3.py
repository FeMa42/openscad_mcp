"""
Advanced document processing using Unstructured library for superior 
semantic understanding and structure preservation.

This approach leverages Unstructured's native chunking capabilities
which are more sophisticated than traditional text splitting.
"""

import os
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

# Core LangChain imports
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

# Unstructured integration (install: pip install langchain-unstructured)
try:
    from langchain_unstructured import UnstructuredLoader
    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    print("Install Unstructured: pip install langchain-unstructured")
    UNSTRUCTURED_AVAILABLE = False

# Embeddings
try:
    from langchain_openai import OpenAIEmbeddings
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from langchain_huggingface import HuggingFaceEmbeddings
    LOCAL_EMBEDDINGS_AVAILABLE = True
except ImportError:
    LOCAL_EMBEDDINGS_AVAILABLE = False


class UnstructuredDocumentProcessor:
    """
    Advanced document processor using Unstructured for semantic-aware processing.
    
    Key advantages:
    - Automatic file type detection and optimized processing
    - Semantic chunking that respects document structure
    - Element-based processing (titles, paragraphs, lists, etc.)
    - Better handling of complex documents (PDFs, HTML, etc.)
    """

    def __init__(self,
                 chunking_strategy: str = "by_title",
                 max_characters: int = 1000,
                 new_after_n_chars: int = 800,
                 overlap: int = 100):

        if not UNSTRUCTURED_AVAILABLE:
            raise ImportError(
                "Unstructured not available. Install: pip install langchain-unstructured")

        self.chunking_strategy = chunking_strategy
        self.max_characters = max_characters
        self.new_after_n_chars = new_after_n_chars
        self.overlap = overlap

    def load_documents_with_unstructured(self, file_paths: List[str]) -> List[Document]:
        """
        Load documents using Unstructured with semantic chunking.
        
        Unstructured's chunking is superior because it:
        - Respects document structure (headers, paragraphs, lists)
        - Maintains semantic coherence
        - Handles complex formats automatically
        """
        print(f"Loading {len(file_paths)} files with Unstructured...")

        # Configure Unstructured loader with semantic chunking
        loader = UnstructuredLoader(
            file_path=file_paths,
            # Chunking configuration
            chunking_strategy=self.chunking_strategy,
            max_characters=self.max_characters,
            new_after_n_chars=self.new_after_n_chars,
            overlap=self.overlap,

            # Processing configuration
            mode="elements",  # Process as semantic elements
            strategy="auto",  # Auto-detect best processing strategy

            # Post-processing
            post_processors=[
                # Clean extra whitespace
                lambda text: " ".join(text.split())
            ]
        )

        try:
            documents = loader.load()
            print(f"✓ Loaded {len(documents)} semantic chunks")
            return documents
        except Exception as e:
            print(f"✗ Error loading with Unstructured: {e}")
            return []

    def get_file_paths_by_type(self, directory: str) -> Dict[str, List[str]]:
        """
        Organize files by type for optimized processing.
        """
        file_types = {
            'pdf': [],
            'code': [],
            'markdown': [],
            'text': [],
            'other': []
        }

        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            for file in files:
                if file.startswith('.'):
                    continue

                file_path = os.path.join(root, file)
                ext = Path(file).suffix.lower()

                if ext == '.pdf':
                    file_types['pdf'].append(file_path)
                elif ext in {'.scad', '.py', '.js', '.cpp', '.c', '.java'}:
                    file_types['code'].append(file_path)
                elif ext in {'.md', '.markdown', '.rst'}:
                    file_types['markdown'].append(file_path)
                elif ext in {'.txt', '.log'}:
                    file_types['text'].append(file_path)
                else:
                    file_types['other'].append(file_path)

        return file_types

    def process_by_file_type(self, directory: str) -> List[Document]:
        """
        Process different file types with optimized configurations.
        """
        file_types = self.get_file_paths_by_type(directory)
        all_documents = []

        for file_type, file_paths in file_types.items():
            if not file_paths:
                continue

            print(f"\nProcessing {len(file_paths)} {file_type} files...")

            # Optimize chunking strategy per file type
            if file_type == 'pdf':
                # PDFs: Respect page structure
                loader = UnstructuredLoader(
                    file_path=file_paths,
                    chunking_strategy="by_page",
                    max_characters=1200,
                    new_after_n_chars=1000,
                    overlap=150
                )
            elif file_type == 'code':
                # Code: Larger chunks to preserve function integrity
                loader = UnstructuredLoader(
                    file_path=file_paths,
                    chunking_strategy="basic",
                    max_characters=1500,
                    new_after_n_chars=1200,
                    overlap=200
                )
            elif file_type == 'markdown':
                # Markdown: Respect header structure
                loader = UnstructuredLoader(
                    file_path=file_paths,
                    chunking_strategy="by_title",
                    max_characters=800,
                    new_after_n_chars=600,
                    overlap=100
                )
            else:
                # Default configuration
                loader = UnstructuredLoader(
                    file_path=file_paths,
                    chunking_strategy=self.chunking_strategy,
                    max_characters=self.max_characters,
                    new_after_n_chars=self.new_after_n_chars,
                    overlap=self.overlap
                )

            try:
                documents = loader.load()

                # Add file type metadata
                for doc in documents:
                    doc.metadata['file_type'] = file_type
                    doc.metadata['processing_method'] = 'unstructured_semantic'

                all_documents.extend(documents)
                print(f"  ✓ Generated {len(documents)} chunks")

            except Exception as e:
                print(f"  ✗ Error processing {file_type} files: {e}")

        return all_documents

    def analyze_semantic_structure(self, documents: List[Document]) -> Dict[str, Any]:
        """
        Analyze the semantic structure of processed documents.
        """
        analysis = {
            'total_chunks': len(documents),
            'elements_by_category': {},
            'file_types': {},
            'chunk_sizes': [],
            'average_chunk_size': 0
        }

        for doc in documents:
            # Analyze element categories (from Unstructured)
            category = doc.metadata.get('category', 'Unknown')
            analysis['elements_by_category'][category] = analysis['elements_by_category'].get(
                category, 0) + 1

            # File type distribution
            file_type = doc.metadata.get('file_type', 'unknown')
            analysis['file_types'][file_type] = analysis['file_types'].get(
                file_type, 0) + 1

            # Chunk size analysis
            chunk_size = len(doc.page_content)
            analysis['chunk_sizes'].append(chunk_size)

        if analysis['chunk_sizes']:
            analysis['average_chunk_size'] = sum(
                analysis['chunk_sizes']) / len(analysis['chunk_sizes'])
            analysis['min_chunk_size'] = min(analysis['chunk_sizes'])
            analysis['max_chunk_size'] = max(analysis['chunk_sizes'])

        return analysis


def create_unstructured_knowledge_base(docs_dir: str,
                                       output_path: str,
                                       use_openai: bool = False,
                                       openai_api_key: str = None):
    """
    Create knowledge base using Unstructured for superior document processing.
    """
    print("=" * 80)
    print("UNSTRUCTURED SEMANTIC KNOWLEDGE BASE BUILDER")
    print("=" * 80)

    if not os.path.exists(docs_dir):
        print(f"Error: Documentation directory '{docs_dir}' not found!")
        return None

    # Initialize processor
    processor = UnstructuredDocumentProcessor(
        chunking_strategy="by_title",
        max_characters=1000,
        new_after_n_chars=800,
        overlap=100
    )

    # Process documents with semantic awareness
    print("\n🧠 SEMANTIC DOCUMENT PROCESSING")
    print("-" * 50)
    documents = processor.process_by_file_type(docs_dir)

    if not documents:
        print("No documents processed!")
        return None

    # Analyze semantic structure
    print("\n📊 SEMANTIC STRUCTURE ANALYSIS")
    print("-" * 50)
    analysis = processor.analyze_semantic_structure(documents)

    print(f"Total semantic chunks: {analysis['total_chunks']}")
    print(f"Element categories: {analysis['elements_by_category']}")
    print(f"File types: {analysis['file_types']}")
    print(
        f"Average chunk size: {analysis['average_chunk_size']:.1f} characters")

    # Initialize embeddings
    print("\n🔗 EMBEDDING GENERATION")
    print("-" * 50)

    if use_openai and OPENAI_AVAILABLE and openai_api_key:
        print("Using OpenAI embeddings...")
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=openai_api_key
        )
    elif LOCAL_EMBEDDINGS_AVAILABLE:
        print("Using local embeddings...")
        embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-base-en-v1.5",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
    else:
        print("No embedding models available!")
        return None

    # Build vector store
    print("\n🏗️  VECTOR STORE CONSTRUCTION")
    print("-" * 50)

    try:
        # Process in batches for large datasets
        batch_size = 50 if use_openai else 100
        vector_store = None

        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(documents) + batch_size - 1) // batch_size

            print(f"Processing batch {batch_num}/{total_batches}...")

            if vector_store is None:
                vector_store = FAISS.from_documents(batch, embeddings)
            else:
                batch_store = FAISS.from_documents(batch, embeddings)
                vector_store.merge_from(batch_store)

            # Rate limiting for API-based embeddings
            if use_openai:
                time.sleep(0.5)

        # Save vector store
        vector_store.save_local(output_path)

        # Save analysis metadata
        metadata_file = f"{output_path}_analysis.json"
        with open(metadata_file, 'w') as f:
            json.dump(analysis, f, indent=2)

        print("\n" + "=" * 80)
        print("✅ UNSTRUCTURED KNOWLEDGE BASE COMPLETE!")
        print("=" * 80)
        print(f"📁 Vector store: {output_path}")
        print(f"📊 Analysis: {metadata_file}")
        print(
            f"🧠 Semantic elements: {len(analysis['elements_by_category'])} types")
        print(f"📄 Document types: {len(analysis['file_types'])}")

        return vector_store

    except Exception as e:
        print(f"✗ Error building vector store: {e}")
        return None


def test_semantic_search(vector_store, query: str = "OpenSCAD cube"):
    """
    Test the semantic search capabilities.
    """
    print(f"\n🔍 Testing semantic search: '{query}'")
    print("-" * 50)

    try:
        results = vector_store.similarity_search(query, k=5)

        for i, doc in enumerate(results):
            print(f"\nResult {i+1}:")
            print(f"  Content: {doc.page_content[:200]}...")
            print(f"  Category: {doc.metadata.get('category', 'Unknown')}")
            print(f"  File: {doc.metadata.get('filename', 'Unknown')}")
            print(f"  Type: {doc.metadata.get('file_type', 'Unknown')}")

    except Exception as e:
        print(f"Search failed: {e}")


if __name__ == "__main__":
    # Configuration
    DOCS_DIR = "openscad_documentation"
    OUTPUT_PATH = "faiss_index_unstructured"
    USE_OPENAI = False
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # Create knowledge base
    vector_store = create_unstructured_knowledge_base(
        docs_dir=DOCS_DIR,
        output_path=OUTPUT_PATH,
        use_openai=USE_OPENAI,
        openai_api_key=OPENAI_API_KEY
    )

    if vector_store:
        # Test semantic search
        test_semantic_search(vector_store, "OpenSCAD module examples")
        test_semantic_search(vector_store, "3D printing design patterns")
