"""
Configuration module for Hierarchical RAG System
Contains all configuration parameters and environment variable handling
"""

import os
from pathlib import Path

# ============================================================================
# API Keys and Authentication
# ============================================================================

# Gemini API Key (required for answer generation)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyBrFMhJzP-Tl_H5F_017JhKj5ySFPdWvVM")

# HuggingFace Token (optional, for private models)
HF_TOKEN = os.environ.get("HF_TOKEN", "")

# ============================================================================
# Model Configuration
# ============================================================================

# Embedding model from HuggingFace
EMBEDDING_MODEL_NAME = "BAAI/bge-base-en-v1.5"

# Maximum sequence length for embeddings
MAX_SEQUENCE_LENGTH = 512

# Embedding dimension (BGE-base produces 768-dim vectors)
EMBEDDING_DIMENSION = 768

# Device for model inference
DEVICE = "cpu"  # Use "cuda" if GPU available (but hackathon requires CPU-only)

# ============================================================================
# Document Processing Configuration
# ============================================================================

# Text chunking parameters (Optimized for better retrieval quality)
CHUNK_SIZE = 800  # Characters per chunk (smaller = more granular retrieval)
CHUNK_OVERLAP = 250  # Overlap between chunks for better context preservation

# Maximum file size to process (in MB)
MAX_FILE_SIZE_MB = 100

# ============================================================================
# Image Processing & OCR Configuration
# ============================================================================

# Enable OCR for image extraction
ENABLE_IMAGE_OCR = True

# Enable image extraction from PDFs
ENABLE_PDF_IMAGE_EXTRACTION = True

# OCR language (use 'eng' for English, 'eng+spa' for multiple languages)
OCR_LANGUAGE = 'eng'

# Path to Tesseract executable (auto-detection with fallbacks)
# System will try these paths in order:
import os
import shutil

TESSERACT_PATH = None

# Try to find Tesseract automatically
_tesseract_paths = [
    r'C:\Program Files\Tesseract-OCR\tesseract.exe',  # Windows default
    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',  # Windows 32-bit
    shutil.which('tesseract'),  # System PATH (Mac/Linux/Windows)
]

for path in _tesseract_paths:
    if path and os.path.exists(path):
        TESSERACT_PATH = path
        break

# If still not found, check if it's in PATH (for Mac/Linux)
if not TESSERACT_PATH:
    TESSERACT_PATH = shutil.which('tesseract')

# Minimum image size to process (skip tiny images)
MIN_IMAGE_WIDTH = 100
MIN_IMAGE_HEIGHT = 100

# Image file extensions to support
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp'}

# Add image extensions to supported extensions
SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.txt', '.xlsx'} | IMAGE_EXTENSIONS


# ============================================================================
# Retrieval Configuration
# ============================================================================

# Number of top documents to retrieve (increased for better borehole filtering)
TOP_K = 5

# Minimum similarity threshold (0-1 range)
MIN_SIMILARITY_THRESHOLD = 0.0  # No threshold by default, return top-k

# Hierarchical search weights
WELL_LEVEL_WEIGHT = 0.3  # Weight for well-level similarity
DOCUMENT_LEVEL_WEIGHT = 0.7  # Weight for document-level similarity

# ============================================================================
# Vector Database Configuration
# ============================================================================

# Default database filename
DEFAULT_DB_FILENAME = "wells_vector_db.pkl"

# Cache directory for embeddings
CACHE_DIR = Path(".cache/embeddings")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# Gemini Configuration
# ============================================================================

# Gemini model name
# Gemini model ladder (tried in order)
GEMINI_MODELS_LADDER = [
    "gemini-2.5-flash",
    "gemini-2.5-pro-preview-03-25",
    "gemini-2.0-flash-exp",
    "gemini-1.5-flash",
    "gemini-1.5-pro"
]

# Default model (will be overwritten by the working model found)
GEMINI_MODEL_NAME = GEMINI_MODELS_LADDER[0]

# Maximum tokens for Gemini response
GEMINI_MAX_TOKENS = 2048

# Temperature for generation
GEMINI_TEMPERATURE = 0.3  # Lower for more focused, factual responses

# ============================================================================
# NodalAnalysis Configuration
# ============================================================================

# Keywords that trigger nodal analysis
NODAL_KEYWORDS = [
    "calculate", "production", "flowrate", "nodal", "analysis",
    "capacity", "estimate", "performance", "VLP", "IPR"
]

# Default parameters for NodalAnalysis (if not extracted)
DEFAULT_NODAL_PARAMS = {
    "rho": 1000.0,
    "mu": 1e-3,
    "g": 9.81,
    "roughness": 1e-5,
    "reservoir_pressure": 230.0,
    "wellhead_pressure": 10.0,
    "PI": 5.0,
    "esp_depth": 500.0
}

# ============================================================================
# Logging Configuration
# ============================================================================

# Enable debug mode
DEBUG_MODE = os.environ.get("DEBUG", "false").lower() == "true"

# Log file path
LOG_FILE = "rag_system.log"

# ============================================================================
# Validation
# ============================================================================

def validate_config():
    """Validate configuration and print warnings for missing values"""
    warnings = []
    
    if not GEMINI_API_KEY:
        warnings.append("⚠️  GEMINI_API_KEY not set - answer generation will fail")
    
    if DEBUG_MODE:
        print("=" * 70)
        print("🔧 Configuration Loaded")
        print("=" * 70)
        print(f"Embedding Model: {EMBEDDING_MODEL_NAME}")
        print(f"Gemini Model: {GEMINI_MODEL_NAME}")
        print(f"Top-K Retrieval: {TOP_K}")
        print(f"Chunk Size: {CHUNK_SIZE} chars (overlap: {CHUNK_OVERLAP})")
        print(f"Device: {DEVICE}")
        print(f"Supported Extensions: {', '.join(SUPPORTED_EXTENSIONS)}")
        
        if warnings:
            print("\n" + "\n".join(warnings))
        else:
            print("\n✅ All critical configurations valid")
        
        print("=" * 70)
        print()

# Run validation on import
validate_config()
