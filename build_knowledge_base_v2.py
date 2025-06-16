import os
import time
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

# Use separate imports to avoid circular dependencies
from langchain_community.document_loaders import DirectoryLoader, UnstructuredFileLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

# Import text splitters separately
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    TEXT_SPLITTERS_AVAILABLE = True
except ImportError:
    # Fallback to older import if new package has issues
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    TEXT_SPLITTERS_AVAILABLE = True

# Embeddings imports
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

# Configuration
DOCS_DIR = "openscad_test_documents"
DB_FAISS_PATH = "faiss_index_modern"


class ModernDocumentProcessor:
    """
    Modern LangChain-based document processor using best practices.
    Uses UnstructuredLoader for automatic file type detection and processing.
    """

    def __init__(self,
                 chunk_size: int = 1000,
                 chunk_overlap: int = 150,
                 use_unstructured: bool = True):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.use_unstructured = use_unstructured

        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )

    def load_documents_from_directory(self, directory_path: str) -> List[Document]:
        """
        Load documents using the modern DirectoryLoader approach.
        This automatically handles multiple file types.
        """
        print(f"Loading documents from: {directory_path}")

        if self.use_unstructured:
            # Use UnstructuredFileLoader as the default loader
            # This automatically detects and handles different file types
            loader = DirectoryLoader(
                directory_path,
                glob="**/*",  # Load all files
                # Exclude JSON files that cause NDJSON errors
                exclude=["**/*.json", "**/*.jsonl", "**/*.ndjson"],
                loader_cls=UnstructuredFileLoader,
                loader_kwargs={
                    "mode": "elements",  # Split into semantic elements
                    "strategy": "fast"   # Use fast processing
                },
                recursive=True,
                show_progress=True,
                use_multithreading=True,
                max_concurrency=4, 
                silent_errors=True  # Continue processing even if some files fail
            )
        else:
            # Fallback to basic approach
            loader = DirectoryLoader(
                directory_path,
                glob="**/*",
                recursive=True,
                show_progress=True
            )

        try:
            documents = loader.load()
            print(f"Successfully loaded {len(documents)} documents")
            return documents
        except Exception as e:
            print(f"Error loading documents: {e}")
            return []

    def enhance_metadata(self, documents: List[Document]) -> List[Document]:
        """
        Enhance document metadata for better retrieval.
        """
        enhanced_docs = []

        for doc in documents:
            # Extract file information
            source = doc.metadata.get('source', '')
            file_path = Path(source)

            # Add enhanced metadata
            doc.metadata.update({
                'filename': file_path.name,
                'file_extension': file_path.suffix.lower(),
                'file_size': len(doc.page_content),
                'word_count': len(doc.page_content.split()),
                'line_count': len(doc.page_content.split('\n'))
            })

            # Add content type classification
            if file_path.suffix.lower() in {'.scad', '.py', '.js', '.cpp', '.c'}:
                doc.metadata['content_type'] = 'code'
            elif file_path.suffix.lower() in {'.md', '.markdown', '.txt'}:
                doc.metadata['content_type'] = 'documentation'
            elif file_path.suffix.lower() == '.pdf':
                doc.metadata['content_type'] = 'pdf'
            else:
                doc.metadata['content_type'] = 'other'

            enhanced_docs.append(doc)

        return enhanced_docs

    def apply_smart_chunking(self, documents: List[Document]) -> List[Document]:
        """
        Apply intelligent chunking based on content type.
        """
        all_chunks = []

        # Group documents by content type for optimized processing
        content_groups = {}
        for doc in documents:
            content_type = doc.metadata.get('content_type', 'other')
            if content_type not in content_groups:
                content_groups[content_type] = []
            content_groups[content_type].append(doc)

        # Process each group with optimized settings
        for content_type, docs in content_groups.items():
            print(f"Processing {len(docs)} {content_type} documents...")

            if content_type == 'code':
                # Larger chunks for code to preserve function integrity
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1500,
                    chunk_overlap=200,
                    separators=["\n\nmodule ",
                                "\n\nfunction ", "\n\n", "\n", " ", ""]
                )
            elif content_type == 'documentation':
                # Standard chunking for documentation
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=800,
                    chunk_overlap=100,
                    separators=["\n\n", "\n", ". ", " ", ""]
                )
            else:
                # Default chunking
                splitter = self.text_splitter

            chunks = splitter.split_documents(docs)

            # Add chunk metadata
            for i, chunk in enumerate(chunks):
                chunk.metadata['chunk_id'] = f"{content_type}_{i}"
                chunk.metadata['chunk_size'] = len(chunk.page_content)
                chunk.metadata['processing_method'] = 'smart_chunking'

            all_chunks.extend(chunks)

        return all_chunks

    def get_embedding_model(self, use_openai: bool = False, openai_api_key: str = None):
        """
        Get the best available embedding model.
        """
        if use_openai and OPENAI_AVAILABLE and openai_api_key:
            print("Using OpenAI embeddings")
            return OpenAIEmbeddings(
                model="text-embedding-3-small",
                api_key=openai_api_key
            )
        elif LOCAL_EMBEDDINGS_AVAILABLE:
            print("Using local embeddings")
            return HuggingFaceEmbeddings(
                # "Salesforce/SFR-Embedding-Code-2B_R", # "Salesforce/SFR-Embedding-2_R",  # BAAI/bge-base-en-v1.5
                model_name="BAAI/bge-base-en-v1.5",
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
        else:
            raise RuntimeError("No embedding models available")


class BatchVectorStoreBuilder:
    """
    Build vector store in batches to handle large datasets efficiently.
    """

    def __init__(self, batch_size: int = 100, delay: float = 0.5):
        self.batch_size = batch_size
        self.delay = delay

    def build_vector_store(self,
                           chunks: List[Document],
                           embeddings_model,
                           save_path: str) -> FAISS:
        """
        Build vector store with batch processing and error handling.
        """
        print(f"Building vector store with {len(chunks)} chunks...")

        vector_store = None
        processed_count = 0

        # Process in batches
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (len(chunks) + self.batch_size -
                             1) // self.batch_size

            print(
                f"Processing batch {batch_num}/{total_batches} ({len(batch)} chunks)")

            try:
                if vector_store is None:
                    vector_store = FAISS.from_documents(
                        batch, embeddings_model)
                else:
                    batch_store = FAISS.from_documents(batch, embeddings_model)
                    vector_store.merge_from(batch_store)

                processed_count += len(batch)
                print(f"  ✓ Processed {processed_count}/{len(chunks)} chunks")

                # Small delay to prevent overwhelming the embedding service
                if self.delay > 0:
                    time.sleep(self.delay)

            except Exception as e:
                print(f"  ✗ Error processing batch {batch_num}: {e}")
                # Try processing individual documents in this batch
                for doc in batch:
                    try:
                        if vector_store is None:
                            vector_store = FAISS.from_documents(
                                [doc], embeddings_model)
                        else:
                            single_store = FAISS.from_documents(
                                [doc], embeddings_model)
                            vector_store.merge_from(single_store)
                        processed_count += 1
                    except Exception as doc_error:
                        print(
                            f"    ✗ Skipping problematic document: {doc_error}")

        # Save the vector store
        print(f"Saving vector store to: {save_path}")
        vector_store.save_local(save_path)

        return vector_store


def create_modern_knowledge_base(docs_dir: str = DOCS_DIR,
                                 output_path: str = DB_FAISS_PATH,
                                 use_openai: bool = False,
                                 openai_api_key: str = None):
    """
    Create a modern knowledge base using current LangChain best practices.
    """
    print("=" * 80)
    print("MODERN LANGCHAIN KNOWLEDGE BASE BUILDER")
    print("=" * 80)

    if not os.path.exists(docs_dir):
        print(f"Error: Documentation directory '{docs_dir}' not found!")
        return None

    # Initialize processor
    processor = ModernDocumentProcessor(
        chunk_size=1000,
        chunk_overlap=150,
        use_unstructured=True
    )

    # Step 1: Load documents
    print("\n📂 LOADING DOCUMENTS")
    print("-" * 40)
    documents = processor.load_documents_from_directory(docs_dir)

    if not documents:
        print("No documents loaded!")
        return None

    # Step 2: Enhance metadata
    print("\n🏷️  ENHANCING METADATA")
    print("-" * 40)
    documents = processor.enhance_metadata(documents)

    # Step 3: Apply smart chunking
    print("\n✂️  APPLYING SMART CHUNKING")
    print("-" * 40)
    chunks = processor.apply_smart_chunking(documents)

    print(f"Created {len(chunks)} chunks from {len(documents)} documents")

    # Step 4: Analyze chunks
    print("\n📊 CHUNK ANALYSIS")
    print("-" * 40)
    content_types = {}
    total_size = 0

    for chunk in chunks:
        content_type = chunk.metadata.get('content_type', 'unknown')
        content_types[content_type] = content_types.get(content_type, 0) + 1
        total_size += len(chunk.page_content)

    print(f"Content types: {content_types}")
    print(f"Average chunk size: {total_size / len(chunks):.1f} characters")

    # Step 5: Initialize embeddings
    print("\n🧠 INITIALIZING EMBEDDINGS")
    print("-" * 40)
    try:
        embeddings = processor.get_embedding_model(use_openai, openai_api_key)
    except Exception as e:
        print(f"Failed to initialize embeddings: {e}")
        return None

    # Step 6: Build vector store
    print("\n🔗 BUILDING VECTOR STORE")
    print("-" * 40)
    builder = BatchVectorStoreBuilder(
        batch_size=50 if use_openai else 100,
        delay=0.5 if use_openai else 0.1
    )

    try:
        vector_store = builder.build_vector_store(
            chunks, embeddings, output_path)
    except Exception as e:
        print(f"Failed to build vector store: {e}")
        return None

    # Step 7: Save metadata
    metadata = {
        'total_documents': len(documents),
        'total_chunks': len(chunks),
        'content_types': content_types,
        'chunk_size': processor.chunk_size,
        'chunk_overlap': processor.chunk_overlap,
        'embedding_model': 'openai' if use_openai else 'local',
        'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
    }

    metadata_file = f"{output_path}_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)

    print("\n" + "=" * 80)
    print("✅ SUCCESS!")
    print("=" * 80)
    print(f"📁 Vector database: {output_path}")
    print(f"📋 Metadata: {metadata_file}")
    print(f"📊 Documents: {len(documents)} → {len(chunks)} chunks")
    print(f"🏷️  Content types: {list(content_types.keys())}")

    return vector_store


if __name__ == "__main__":
    # Configuration
    USE_OPENAI = False  # Set to True to use OpenAI embeddings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    # Create the knowledge base
    vector_store = create_modern_knowledge_base(
        docs_dir=DOCS_DIR,
        output_path=DB_FAISS_PATH,
        use_openai=USE_OPENAI,
        openai_api_key=OPENAI_API_KEY
    )

    if vector_store:
        # Test the vector store with better debugging
        print("\n🔍 TESTING VECTOR STORE")
        print("-" * 40)
        try:
            results = vector_store.similarity_search(
                "OpenSCAD cube example", k=3)
            for i, doc in enumerate(results):
                content = doc.page_content.strip()
                lines = content.split('\n')
                first_line = next((line.strip() for line in lines if line.strip()), 'No content found')
                
                print(f"Result {i+1}:")
                print(f"  Source: {doc.metadata.get('filename', 'unknown')}")
                print(f"  Content type: {doc.metadata.get('content_type', 'unknown')}")
                print(f"  Content length: {len(content)} characters")
                print(f"  Content preview: {content[:200]}...")
                print(f"  First non-empty line: {first_line}")
                print()
        except Exception as e:
            print(f"Test failed: {e}")
