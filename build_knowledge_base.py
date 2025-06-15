import os
import glob
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader, 
    TextLoader,
    DirectoryLoader
)
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document

# Define the paths
DOCS_DIR = "openscad_documentation"
DB_FAISS_PATH = "faiss_index"


class CustomSCADLoader:
    """Custom loader for OpenSCAD (.scad) files"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
    
    def load(self):
        try:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Create metadata for the document
            metadata = {
                'source': self.file_path,
                'file_type': 'scad',
                'filename': os.path.basename(self.file_path)
            }
            
            return [Document(page_content=content, metadata=metadata)]
        except Exception as e:
            print(f"Error loading {self.file_path}: {e}")
            return []


def get_all_files_recursively(base_dir: str):
    """
    Recursively find all relevant files in the documentation directory
    Returns lists of files by type
    """
    pdf_files = []
    md_files = []
    scad_files = []
    
    # Walk through all directories recursively
    for root, dirs, files in os.walk(base_dir):
        # Skip hidden directories and files
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            if file.startswith('.'):
                continue
                
            file_path = os.path.join(root, file)
            file_ext = os.path.splitext(file)[1].lower()
            
            if file_ext == '.pdf':
                pdf_files.append(file_path)
            elif file_ext == '.md':
                md_files.append(file_path)
            elif file_ext == '.scad':
                scad_files.append(file_path)
    
    return pdf_files, md_files, scad_files


def load_documents_by_type(pdf_files, md_files, scad_files):
    """
    Load documents from different file types
    """
    all_docs = []
    
    # Load PDF files
    print(f"Loading {len(pdf_files)} PDF files...")
    for pdf_file in pdf_files:
        try:
            loader = PyPDFLoader(pdf_file)
            docs = loader.load()
            # Add file type to metadata
            for doc in docs:
                doc.metadata['file_type'] = 'pdf'
                doc.metadata['filename'] = os.path.basename(pdf_file)
            all_docs.extend(docs)
            print(f"  ✓ Loaded: {pdf_file}")
        except Exception as e:
            print(f"  ✗ Error loading {pdf_file}: {e}")
    
    # Load Markdown files
    print(f"Loading {len(md_files)} Markdown files...")
    for md_file in md_files:
        try:
            loader = TextLoader(md_file, encoding='utf-8')
            docs = loader.load()
            # Add file type to metadata
            for doc in docs:
                doc.metadata['file_type'] = 'markdown'
                doc.metadata['filename'] = os.path.basename(md_file)
            all_docs.extend(docs)
            print(f"  ✓ Loaded: {md_file}")
        except Exception as e:
            print(f"  ✗ Error loading {md_file}: {e}")
    
    # Load SCAD files
    print(f"Loading {len(scad_files)} SCAD files...")
    for scad_file in scad_files:
        try:
            loader = CustomSCADLoader(scad_file)
            docs = loader.load()
            all_docs.extend(docs)
            print(f"  ✓ Loaded: {scad_file}")
        except Exception as e:
            print(f"  ✗ Error loading {scad_file}: {e}")
    
    return all_docs


def create_vector_db():
    """
    Creates a comprehensive vector database from all OpenSCAD documentation,
    including PDFs, Markdown files, and SCAD code examples.
    """
    print("=" * 60)
    print("Building Comprehensive OpenSCAD Knowledge Base v2")
    print("=" * 60)
    
    # Check if documentation directory exists
    if not os.path.exists(DOCS_DIR):
        print(f"Error: Documentation directory '{DOCS_DIR}' not found!")
        return
    
    print(f"Scanning directory: {DOCS_DIR}")
    
    # Get all files recursively
    pdf_files, md_files, scad_files = get_all_files_recursively(DOCS_DIR)
    
    print(f"\nFound files:")
    print(f"  - PDF files: {len(pdf_files)}")
    print(f"  - Markdown files: {len(md_files)}")
    print(f"  - SCAD files: {len(scad_files)}")
    print(f"  - Total files: {len(pdf_files) + len(md_files) + len(scad_files)}")
    
    if not any([pdf_files, md_files, scad_files]):
        print("No relevant files found!")
        return
    
    print("\n" + "=" * 60)
    print("LOADING DOCUMENTS")
    print("=" * 60)
    
    # Load all documents
    all_docs = load_documents_by_type(pdf_files, md_files, scad_files)
    
    if not all_docs:
        print("No documents were successfully loaded!")
        return
    
    print(f"\nSuccessfully loaded {len(all_docs)} document chunks")
    
    print("\n" + "=" * 60)
    print("SPLITTING DOCUMENTS")
    print("=" * 60)
    
    # Split documents into chunks
    # Use different chunk sizes for different file types
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=150,
        separators=["\n\n", "\n", " ", ""]
    )
    
    splits = text_splitter.split_documents(all_docs)
    print(f"Created {len(splits)} text chunks")
    
    print("\n" + "=" * 60)
    print("CREATING EMBEDDINGS AND BUILDING INDEX")
    print("=" * 60)
    
    # Create embeddings using a high-quality model
    print("Initializing embeddings model...")
    embeddings = HuggingFaceEmbeddings(
        model_name="Salesforce/SFR-Embedding-2_R",  # BAAI/bge-base-en-v1.5
        model_kwargs={'device': 'mps'}
    )
    
    print("Building FAISS vector store...")
    # Create the vector store from the document chunks
    db = FAISS.from_documents(splits, embeddings)
    
    # Save the vector store locally
    print(f"Saving to '{DB_FAISS_PATH}'...")
    db.save_local(DB_FAISS_PATH)
    
    print("\n" + "=" * 60)
    print("KNOWLEDGE BASE CREATION COMPLETE!")
    print("=" * 60)
    print(f"✓ Processed {len(pdf_files)} PDF files")
    print(f"✓ Processed {len(md_files)} Markdown files") 
    print(f"✓ Processed {len(scad_files)} SCAD files")
    print(f"✓ Created {len(splits)} searchable chunks")
    print(f"✓ Saved vector database to '{DB_FAISS_PATH}'")
    print("\nYour OpenSCAD agent can now search through all this documentation!")


if __name__ == "__main__":
    create_vector_db() 