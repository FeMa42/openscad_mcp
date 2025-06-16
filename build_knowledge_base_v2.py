import os
import glob
import re
import time
import torch
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_text_splitters import Language
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    DirectoryLoader
)
from langchain_community.vectorstores import FAISS
from langchain.schema import Document

# API-based embeddings imports
try:
    from langchain_openai import OpenAIEmbeddings
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Install OpenAI: pip install langchain-openai")

# Lightweight local embeddings as fallback
try:
    from langchain_huggingface import HuggingFaceEmbeddings
    LOCAL_EMBEDDINGS_AVAILABLE = True
except ImportError:
    LOCAL_EMBEDDINGS_AVAILABLE = False

# Define the paths
DOCS_DIR = "openscad_test_documents"
DB_FAISS_PATH = "faiss_index_langchain_native_v1"


class EmbeddingModelFactory:
    """Factory to create different types of embedding models"""

    @staticmethod
    def create_openai_embeddings(api_key: str = None, model: str = "text-embedding-3-small"):
        """Create OpenAI embeddings - recommended for quality and cost"""
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "Install langchain-openai: pip install langchain-openai")

        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key

        return OpenAIEmbeddings(
            model=model,
            show_progress_bar=True
        )

    @staticmethod
    def create_local_embeddings():
        """Create lightweight local embeddings that should fit in your memory"""
        if not LOCAL_EMBEDDINGS_AVAILABLE:
            raise ImportError(
                "Install transformers: pip install sentence-transformers")
        if torch.cuda.is_available():
            device = "cude"
        else: 
            device = "cpu"
        return HuggingFaceEmbeddings(
            # "Salesforce/SFR-Embedding-2_R" # Large model 
            # BAAI/bge-base-en-v1.5, # Medium sized model
            # "all-MiniLM-L6-v2",  # 80MB model, very fast
            model_name="Salesforce/SFR-Embedding-2_R",
            model_kwargs={'device': device},
            encode_kwargs={'normalize_embeddings': True}
        )

    @staticmethod
    def get_recommended_embeddings(prefer_api: bool = True, openai_api_key: str = None):
        """Get the best available embeddings model"""

        if prefer_api and OPENAI_AVAILABLE:
            try:
                print("Using OpenAI embeddings (recommended)")
                return EmbeddingModelFactory.create_openai_embeddings(openai_api_key)
            except Exception as e:
                print(f"OpenAI embeddings failed: {e}")

        if LOCAL_EMBEDDINGS_AVAILABLE:
            try:
                print("Using lightweight local embeddings")
                return EmbeddingModelFactory.create_local_embeddings()
            except Exception as e:
                print(f"Local embeddings failed: {e}")

        raise RuntimeError(
            "No embedding models available. Install: pip install langchain-openai")


class LangChainNativeChunker:
    """
    Advanced chunker that uses LangChain's native language support
    for optimal splitting of different file types
    """

    # File extension to LangChain Language mapping
    EXTENSION_TO_LANGUAGE = {
        # Programming languages
        '.py': Language.PYTHON,
        '.js': Language.JS,
        '.ts': Language.TS,
        '.jsx': Language.JS,
        '.tsx': Language.TS,
        '.java': Language.JAVA,
        '.c': Language.C,
        '.cpp': Language.CPP,
        '.cc': Language.CPP,
        '.cxx': Language.CPP,
        '.h': Language.C,
        '.hpp': Language.CPP,
        '.cs': Language.CSHARP,
        '.go': Language.GO,
        '.rs': Language.RUST,
        '.rb': Language.RUBY,
        '.php': Language.PHP,
        '.scala': Language.SCALA,
        '.swift': Language.SWIFT,
        '.kt': Language.KOTLIN,
        '.lua': Language.LUA,
        '.pl': Language.PERL,
        '.hs': Language.HASKELL,
        '.ex': Language.ELIXIR,
        '.ps1': Language.POWERSHELL,
        '.sol': Language.SOL,
        '.proto': Language.PROTO,
        '.cob': Language.COBOL,
        '.scad': Language.C,  # OpenSCAD uses C-like syntax

        # Markup and documentation
        '.md': Language.MARKDOWN,
        '.markdown': Language.MARKDOWN,
        '.rst': Language.RST,
        '.tex': Language.LATEX,
        '.html': Language.HTML,
        '.htm': Language.HTML,
        '.xml': Language.HTML,  # XML can use HTML separators
        '.xhtml': Language.HTML,

        # Special cases - will use default separators
        '.txt': None,
        '.pdf': None,  # PDFs are processed separately
        '.json': Language.JS,  # JSON can use JS separators
        '.yaml': None,
        '.yml': None,
        '.ini': None,
        '.cfg': None,
        '.conf': None,
    }

    def __init__(self,
                 default_chunk_size: int = 1000,
                 default_chunk_overlap: int = 150,
                 code_chunk_size: int = 1500,  # Larger chunks for code
                 code_chunk_overlap: int = 200):

        self.default_chunk_size = default_chunk_size
        self.default_chunk_overlap = default_chunk_overlap
        self.code_chunk_size = code_chunk_size
        self.code_chunk_overlap = code_chunk_overlap

        # Cache for splitters to avoid recreating them
        self._splitter_cache = {}

    def get_file_language(self, filename: str) -> Optional[Language]:
        """Determine the language/format from file extension"""
        ext = Path(filename).suffix.lower()
        return self.EXTENSION_TO_LANGUAGE.get(ext)

    def is_code_file(self, filename: str) -> bool:
        """Check if file is a code file (should get larger chunks)"""
        ext = Path(filename).suffix.lower()
        code_extensions = {'.py', '.js', '.ts', '.java', '.c', '.cpp', '.cs',
                           '.go', '.rs', '.rb', '.php', '.scala', '.swift',
                           '.kt', '.lua', '.pl', '.hs', '.ex', '.ps1', '.sol',
                           '.proto', '.cob', '.scad'}
        return ext in code_extensions

    def get_splitter_for_language(self, language: Optional[Language], filename: str) -> RecursiveCharacterTextSplitter:
        """Get or create a splitter for the given language"""

        # Create cache key
        is_code = self.is_code_file(filename)
        cache_key = (language, is_code)

        if cache_key in self._splitter_cache:
            return self._splitter_cache[cache_key]

        # Determine chunk sizes
        chunk_size = self.code_chunk_size if is_code else self.default_chunk_size
        chunk_overlap = self.code_chunk_overlap if is_code else self.default_chunk_overlap

        # Create splitter
        if language:
            # Use LangChain's native language support
            splitter = RecursiveCharacterTextSplitter.from_language(
                language=language,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                keep_separator=True
            )
            print(
                f"  Created {language.value} splitter for {filename} (chunk_size={chunk_size})")
        else:
            # Use default separators for unknown file types
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", " ", ""],
                keep_separator=True
            )
            print(
                f"  Created default splitter for {filename} (chunk_size={chunk_size})")

        # Cache the splitter
        self._splitter_cache[cache_key] = splitter
        return splitter

    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """Apply language-specific chunking to documents"""
        all_chunks = []

        # Group documents by their optimal splitter
        splitter_groups = {}

        for doc in documents:
            filename = doc.metadata.get('filename', 'unknown')
            file_type = doc.metadata.get('file_type', 'unknown')

            # Skip PDFs for now (they need special handling)
            if file_type == 'pdf':
                # Use default splitter for PDFs
                language = None
            else:
                language = self.get_file_language(filename)

            splitter = self.get_splitter_for_language(language, filename)

            if splitter not in splitter_groups:
                splitter_groups[splitter] = []
            splitter_groups[splitter].append(doc)

        # Process each group with its optimal splitter
        for splitter, docs in splitter_groups.items():
            print(
                f"Processing {len(docs)} documents with specialized splitter...")

            chunks = splitter.split_documents(docs)

            # Add chunking metadata
            for i, chunk in enumerate(chunks):
                chunk.metadata['chunk_index'] = i
                chunk.metadata['chunk_type'] = 'langchain_native'
                if 'filename' in chunk.metadata:
                    language = self.get_file_language(
                        chunk.metadata['filename'])
                    chunk.metadata['detected_language'] = language.value if language else 'default'

            all_chunks.extend(chunks)

        return all_chunks


class BatchProcessor:
    """Process documents in batches to manage memory usage"""

    def __init__(self, batch_size: int = 100, delay_between_batches: float = 1.0):
        self.batch_size = batch_size
        self.delay_between_batches = delay_between_batches

    def process_documents_in_batches(self, chunks: List[Document], embeddings_model) -> FAISS:
        """Create vector store by processing documents in batches"""
        print(
            f"Processing {len(chunks)} chunks in batches of {self.batch_size}")

        vector_store = None

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

                if self.delay_between_batches > 0:
                    time.sleep(self.delay_between_batches)

            except Exception as e:
                print(f"Error processing batch {batch_num}: {e}")
                # Retry with individual documents
                for doc in batch:
                    try:
                        if vector_store is None:
                            vector_store = FAISS.from_documents(
                                [doc], embeddings_model)
                        else:
                            single_store = FAISS.from_documents(
                                [doc], embeddings_model)
                            vector_store.merge_from(single_store)
                        time.sleep(0.5)
                    except Exception as doc_error:
                        print(f"Skipping problematic document: {doc_error}")

        return vector_store


class EnhancedDocumentLoader:
    """Enhanced document loader with metadata extraction"""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)

    def detect_file_type(self) -> str:
        """Detect file type from extension"""
        ext = self.file_path.suffix.lower()

        if ext == '.pdf':
            return 'pdf'
        elif ext in {'.md', '.markdown'}:
            return 'markdown'
        elif ext in {'.html', '.htm', '.xml', '.xhtml'}:
            return 'html'
        elif ext in {'.py', '.js', '.ts', '.java', '.c', '.cpp', '.cs', '.go',
                     '.rs', '.rb', '.php', '.scala', '.swift', '.kt', '.lua',
                     '.pl', '.hs', '.ex', '.ps1', '.sol', '.proto', '.cob', '.scad'}:
            return 'code'
        elif ext in {'.txt', '.rst', '.tex', '.json', '.yaml', '.yml',
                     '.ini', '.cfg', '.conf'}:
            return 'text'
        else:
            return 'unknown'

    def extract_metadata(self, content: str) -> Dict[str, Any]:
        """Extract metadata from file content"""
        metadata = {
            'source': str(self.file_path),
            'filename': self.file_path.name,
            'file_type': self.detect_file_type(),
            'file_extension': self.file_path.suffix.lower(),
            'content_length': len(content),
            'line_count': len(content.split('\n'))
        }

        # Add language-specific metadata
        if metadata['file_type'] == 'code':
            # Count functions, classes, etc.
            if self.file_path.suffix.lower() == '.scad':
                metadata['module_count'] = len(
                    re.findall(r'\bmodule\s+\w+', content))
                metadata['function_count'] = len(
                    re.findall(r'\bfunction\s+\w+', content))
            elif self.file_path.suffix.lower() == '.py':
                metadata['function_count'] = len(
                    re.findall(r'\ndef\s+\w+', content))
                metadata['class_count'] = len(
                    re.findall(r'\nclass\s+\w+', content))

        elif metadata['file_type'] == 'markdown':
            # Count headers
            metadata['header_count'] = len(
                re.findall(r'^#+\s', content, re.MULTILINE))
            metadata['code_block_count'] = len(re.findall(r'```', content))

        elif metadata['file_type'] == 'html':
            # Count HTML elements
            metadata['tag_count'] = len(re.findall(r'<[^>]+>', content))
            metadata['link_count'] = len(re.findall(
                r'<a\s+[^>]*href', content, re.IGNORECASE))

        # Extract description from comments
        doc_comments = []
        if metadata['file_type'] == 'code':
            doc_comments = re.findall(r'//\s*(.+)', content)[:3]
        elif metadata['file_type'] == 'html':
            doc_comments = re.findall(
                r'<!--\s*(.+?)\s*-->', content, re.DOTALL)[:3]

        if doc_comments:
            metadata['description'] = ' '.join(doc_comments)

        return metadata

    def load(self) -> List[Document]:
        """Load document with enhanced metadata"""
        try:
            file_type = self.detect_file_type()

            if file_type == 'pdf':
                loader = PyPDFLoader(str(self.file_path))
                docs = loader.load()
                for doc in docs:
                    doc.metadata.update(
                        self.extract_metadata(doc.page_content))
                return docs
            else:
                # Use TextLoader for all other file types
                loader = TextLoader(str(self.file_path), encoding='utf-8')
                docs = loader.load()
                for doc in docs:
                    doc.metadata.update(
                        self.extract_metadata(doc.page_content))
                return docs

        except Exception as e:
            print(f"Error loading {self.file_path}: {e}")
            return []


def get_all_files_recursively(base_dir: str) -> List[str]:
    """Recursively find all relevant files"""
    supported_extensions = {
        '.pdf', '.md', '.markdown', '.html', '.htm', '.xml', '.xhtml',
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.cs',
        '.go', '.rs', '.rb', '.php', '.scala', '.swift', '.kt', '.lua',
        '.pl', '.hs', '.ex', '.ps1', '.sol', '.proto', '.cob', '.scad',
        '.txt', '.rst', '.tex', '.json', '.yaml', '.yml', '.ini', '.cfg', '.conf'
    }

    all_files = []

    for root, dirs, files in os.walk(base_dir):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for file in files:
            if file.startswith('.'):
                continue

            file_path = os.path.join(root, file)
            file_ext = os.path.splitext(file)[1].lower()

            if file_ext in supported_extensions:
                all_files.append(file_path)

    return all_files


def load_all_documents(file_paths: List[str]) -> List[Document]:
    """Load all documents with enhanced metadata"""
    all_docs = []

    print(f"Loading {len(file_paths)} files...")

    for file_path in file_paths:
        try:
            loader = EnhancedDocumentLoader(file_path)
            docs = loader.load()
            all_docs.extend(docs)
            print(f"  ✓ Loaded: {file_path}")
        except Exception as e:
            print(f"  ✗ Error loading {file_path}: {e}")

    return all_docs


def evaluate_chunking_quality(chunks: List[Document]) -> Dict[str, Any]:
    """Evaluate chunking quality with detailed metrics"""
    metrics = {
        'total_chunks': len(chunks),
        'languages': {},
        'file_types': {},
        'size_distribution': {},
        'avg_chunk_size': 0,
        'language_distribution': {}
    }

    chunk_sizes = []

    for chunk in chunks:
        # Track detected languages
        language = chunk.metadata.get('detected_language', 'default')
        metrics['languages'][language] = metrics['languages'].get(
            language, 0) + 1

        # Track file types
        file_type = chunk.metadata.get('file_type', 'unknown')
        metrics['file_types'][file_type] = metrics['file_types'].get(
            file_type, 0) + 1

        # Track sizes
        size = len(chunk.page_content)
        chunk_sizes.append(size)

    if chunk_sizes:
        metrics['avg_chunk_size'] = sum(chunk_sizes) / len(chunk_sizes)
        metrics['min_chunk_size'] = min(chunk_sizes)
        metrics['max_chunk_size'] = max(chunk_sizes)

        # Size distribution
        size_ranges = [
            (0, 200, 'very_small'),
            (200, 500, 'small'),
            (500, 1000, 'medium'),
            (1000, 2000, 'large'),
            (2000, float('inf'), 'very_large')
        ]

        for min_size, max_size, label in size_ranges:
            count = sum(1 for size in chunk_sizes if min_size <=
                        size < max_size)
            metrics['size_distribution'][label] = count

    return metrics


def create_vector_db(openai_api_key: str = None, use_api_embeddings: bool = True):
    """Create vector database with LangChain native language support"""
    print("=" * 80)
    print("Building Knowledge Base with LangChain Native Language Support")
    print("=" * 80)

    # Check if documentation directory exists
    if not os.path.exists(DOCS_DIR):
        print(f"Error: Documentation directory '{DOCS_DIR}' not found!")
        return

    print(f"Scanning directory: {DOCS_DIR}")

    # Get all supported files
    all_files = get_all_files_recursively(DOCS_DIR)

    # Group by file type for reporting
    file_types = {}
    for file_path in all_files:
        ext = Path(file_path).suffix.lower()
        file_types[ext] = file_types.get(ext, 0) + 1

    print(f"\nFound {len(all_files)} files:")
    for ext, count in sorted(file_types.items()):
        print(f"  {ext}: {count} files")

    if not all_files:
        print("No relevant files found!")
        return

    # Load all documents
    print("\n" + "=" * 80)
    print("LOADING DOCUMENTS")
    print("=" * 80)

    all_docs = load_all_documents(all_files)

    if not all_docs:
        print("No documents were successfully loaded!")
        return

    print(f"\nSuccessfully loaded {len(all_docs)} documents")

    # Initialize embeddings
    print("\n" + "=" * 80)
    print("INITIALIZING EMBEDDINGS")
    print("=" * 80)

    try:
        embeddings = EmbeddingModelFactory.get_recommended_embeddings(
            prefer_api=use_api_embeddings,
            openai_api_key=openai_api_key
        )
        print("✓ Embeddings model initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize embeddings: {e}")
        return

    # Apply LangChain native chunking
    print("\n" + "=" * 80)
    print("APPLYING LANGCHAIN NATIVE CHUNKING")
    print("=" * 80)

    chunker = LangChainNativeChunker(
        default_chunk_size=800,
        default_chunk_overlap=100,
        code_chunk_size=1200,
        code_chunk_overlap=150
    )

    chunks = chunker.chunk_documents(all_docs)
    print(
        f"\nCreated {len(chunks)} optimized chunks using native language support")

    # Evaluate chunking quality
    print("\n" + "=" * 80)
    print("CHUNKING QUALITY EVALUATION")
    print("=" * 80)

    metrics = evaluate_chunking_quality(chunks)
    print(f"Quality Metrics:")
    print(f"  Total chunks: {metrics['total_chunks']}")
    print(f"  Average chunk size: {metrics['avg_chunk_size']:.1f} characters")
    print(
        f"  Size range: {metrics.get('min_chunk_size', 0)} - {metrics.get('max_chunk_size', 0)}")
    print(f"  Detected languages: {metrics['languages']}")
    print(f"  File types: {metrics['file_types']}")
    print(f"  Size distribution: {metrics['size_distribution']}")

    # Calculate estimated cost for OpenAI embeddings
    if use_api_embeddings and OPENAI_AVAILABLE:
        total_tokens = sum(len(chunk.page_content.split())
                           * 1.3 for chunk in chunks)
        # text-embedding-3-small pricing
        estimated_cost = (total_tokens / 1000) * 0.0001
        print(f"  Estimated OpenAI cost: ${estimated_cost:.4f}")

    # Create vector store
    print("\n" + "=" * 80)
    print("CREATING VECTOR STORE")
    print("=" * 80)

    batch_processor = BatchProcessor(
        batch_size=50 if use_api_embeddings else 100,
        delay_between_batches=0.5 if use_api_embeddings else 0
    )

    try:
        db = batch_processor.process_documents_in_batches(chunks, embeddings)
        print("✓ Vector store created successfully")
    except Exception as e:
        print(f"✗ Failed to create vector store: {e}")
        return

    # Save everything
    print(f"\nSaving to '{DB_FAISS_PATH}'...")
    db.save_local(DB_FAISS_PATH)

    # Save metadata
    import json
    metadata_file = f"{DB_FAISS_PATH}_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metrics, f, indent=2)

    print("\n" + "=" * 80)
    print("SUCCESS!")
    print("=" * 80)
    print(f"✓ Created vector database with {len(chunks)} chunks")
    print(
        f"✓ Leveraged LangChain native support for {len(metrics['languages'])} languages")
    print(f"✓ Processed {len(metrics['file_types'])} different file types")
    print(f"✓ Saved to: {DB_FAISS_PATH}")
    print(f"✓ Metadata saved to: {metadata_file}")
    if use_api_embeddings and OPENAI_AVAILABLE:
        print(f"✓ Estimated cost: ${estimated_cost:.4f}")

    print(f"\nSupported languages used:")
    for lang, count in metrics['languages'].items():
        print(f"  - {lang}: {count} chunks")


if __name__ == "__main__":
    # Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    USE_API_EMBEDDINGS = False  # Set to False to use lightweight local models

    if USE_API_EMBEDDINGS and not OPENAI_API_KEY:
        print("Please set OPENAI_API_KEY environment variable")
        print("export OPENAI_API_KEY='your-api-key-here'")
        exit(1)

    create_vector_db(
        openai_api_key=OPENAI_API_KEY,
        use_api_embeddings=USE_API_EMBEDDINGS
    )
