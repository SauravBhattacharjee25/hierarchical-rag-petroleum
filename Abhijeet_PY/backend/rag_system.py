"""
Hierarchical Retrieval-Augmented Generation (RAG) System
Implements a multi-level RAG architecture for petroleum well data
"""

import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Tuple
import pickle
from pathlib import Path

from backend import config
from backend.document_processor import WellData, DocumentChunk
from backend.borehole_handler import BoreholeHandler


# ============================================================================
# Embedding Model
# ============================================================================

class EmbeddingModel:
    """Wrapper for BAAI/bge-base-en-v1.5 embedding model"""
    
    def __init__(self):
        """Initialize the embedding model"""
        print("=" * 70)
        print("🔄 Loading Embedding Model from HuggingFace")
        print("=" * 70)
        print(f"Model: {config.EMBEDDING_MODEL_NAME}")
        print("Note: First time download ~220MB (cached afterwards)")
        print()
        
        try:
            # Load model using sentence-transformers (optimized for BGE models)
            self.model = SentenceTransformer(
                config.EMBEDDING_MODEL_NAME,
                device=config.DEVICE
            )
            
            print("✅ Model loaded successfully!")
            print(f"   Embedding dimension: {config.EMBEDDING_DIMENSION}")
            print(f"   Device: {config.DEVICE}")
            print("=" * 70)
            print()
            
        except Exception as e:
            print(f"❌ Error loading embedding model: {e}")
            print("\nTroubleshooting:")
            print("  1. Check internet connection")
            print("  2. Verify model name is correct")
            print("  3. Model download may be in progress")
            raise
    
    def encode(self, texts: List[str], show_progress: bool = False) -> np.ndarray:
        """
        Generate embeddings for a list of texts
        
        Args:
            texts: List of text strings to embed
            show_progress: Whether to show progress bar
            
        Returns:
            Numpy array of embeddings (shape: [num_texts, embedding_dim])
        """
        if not texts:
            return np.array([])
        
        # For BGE models, add instruction prefix
        # Query: "Represent this sentence for searching relevant passages:"
        # Passage: (no prefix needed for BGE)
        
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=show_progress,
            batch_size=32
        )
        
        return embeddings
    
    def encode_query(self, query: str) -> np.ndarray:
        """
        Generate embedding for a query
        
        Args:
            query: Query text
            
        Returns:
            Numpy array of embedding (shape: [1, embedding_dim])
        """
        # BGE models use special instruction for queries
        query_with_instruction = f"Represent this sentence for searching relevant passages: {query}"
        embedding = self.model.encode(
            [query_with_instruction],
            convert_to_numpy=True
        )
        return embedding


# ============================================================================
# Hierarchical Vector Database
# ============================================================================

class HierarchicalVectorDB:
    """
    Hierarchical vector database with Well → Document → Chunk structure
    """
    
    def __init__(self, embedding_model: EmbeddingModel = None):
        """
        Initialize the vector database
        
        Args:
            embedding_model: EmbeddingModel instance (creates new if None)
        """
        self.embedding_model = embedding_model or EmbeddingModel()
        self.wells: List[WellData] = []
        self.all_chunks: List[DocumentChunk] = []
        self.chunk_embeddings: np.ndarray = None
        self.well_embeddings: Dict[str, np.ndarray] = {}
    
    def add_wells(self, wells: List[WellData]):
        """
        Add wells to the database and compute embeddings
        
        Args:
            wells: List of WellData objects
        """
        print("=" * 70)
        print("🧮 Computing Embeddings for Vector Database")
        print("=" * 70)
        
        self.wells.extend(wells)
        
        # Collect all chunks
        new_chunks = []
        for well in wells:
            new_chunks.extend(well.documents)
        
        self.all_chunks.extend(new_chunks)
        
        # Generate embeddings for all chunks
        print(f"\n📊 Encoding {len(new_chunks)} document chunks...")
        chunk_texts = [chunk.text for chunk in new_chunks]
        new_embeddings = self.embedding_model.encode(chunk_texts, show_progress=True)
        
        # Store embeddings in chunk objects
        for chunk, embedding in zip(new_chunks, new_embeddings):
            chunk.embedding = embedding
        
        # Stack all chunk embeddings
        if self.chunk_embeddings is None:
            self.chunk_embeddings = new_embeddings
        else:
            self.chunk_embeddings = np.vstack([self.chunk_embeddings, new_embeddings])
        
        # Compute well-level embeddings (average of all chunks in well)
        print(f"\n📊 Computing well-level embeddings...")
        for well in wells:
            if len(well.documents) == 0:
                continue
            
            well_chunks_embeddings = np.array([chunk.embedding for chunk in well.documents])
            well_embedding = np.mean(well_chunks_embeddings, axis=0, keepdims=True)
            self.well_embeddings[well.well_name] = well_embedding
            
            if config.DEBUG_MODE:
                print(f"  ✓ {well.well_name}: {len(well.documents)} chunks")
        
        print(f"\n✅ Vector database updated!")
        print(f"   Total wells: {len(self.wells)}")
        print(f"   Total chunks: {len(self.all_chunks)}")
        print("=" * 70)
        print()
    
    def search(self, query: str, top_k: int = None) -> List[Dict]:
        """
        Search for most relevant document chunks using hierarchical approach
        
        Args:
            query: Search query
            top_k: Number of top results to return (default from config)
            
        Returns:
            List of dictionaries containing chunk info and similarity scores
        """
        if top_k is None:
            top_k = config.TOP_K
        
        if len(self.all_chunks) == 0:
            print("⚠️  Vector database is empty!")
            return []
        
        print(f"\n🔍 Searching for: '{query}'")
        print(f"   Database size: {len(self.all_chunks)} chunks across {len(self.wells)} wells")
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode_query(query)
        
        # Method: Direct similarity search across all chunks
        # (Hierarchical weighting can be added later if needed)
        
        # Compute cosine similarity with all chunks
        similarities = cosine_similarity(query_embedding, self.chunk_embeddings)[0]
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        # Prepare results
        results = []
        for rank, idx in enumerate(top_indices, 1):
            chunk = self.all_chunks[idx]
            similarity = float(similarities[idx])
            
            # Skip if below threshold
            if similarity < config.MIN_SIMILARITY_THRESHOLD:
                continue
            
            results.append({
                'rank': rank,
                'well_name': chunk.well_name,
                'filename': chunk.filename,
                'filepath': chunk.filepath,
                'chunk_idx': chunk.chunk_idx,
                'total_chunks': chunk.total_chunks,
                'similarity': similarity,
                'text': chunk.text,
                'preview': chunk.text[:500] + '...' if len(chunk.text) > 500 else chunk.text,
                'is_from_image': getattr(chunk, 'is_from_image', False),
                'image_metadata': getattr(chunk, 'image_metadata', {})
            })
        
        # Print results summary
        if results:
            print(f"\n✅ Top {len(results)} Results:")
            for result in results:
                source_type = "🖼️ IMAGE" if result.get('is_from_image') else "📄 TEXT"
                print(f"   {result['rank']}. [{result['well_name']}] {result['filename']} "
                      f"(chunk {result['chunk_idx']+1}/{result['total_chunks']}) "
                      f"[{source_type}] - Similarity: {result['similarity']:.2%}")
        else:
            print("   ⚠️  No results found")
        
        print()
        
        return results

    def search_images_only(self, query: str, top_k: int = None) -> List[Dict]:
        """
        Search only for image-sourced document chunks
        """
        if top_k is None:
            top_k = config.TOP_K
            
        # Get all results first (fetch more to filter)
        all_results = self.search(query, top_k=top_k * 5)
        
        # Filter for images
        image_results = [r for r in all_results if r.get('is_from_image', False)]
        
        # Return top k
        return image_results[:top_k]

    def search_text_only(self, query: str, top_k: int = None) -> List[Dict]:
        """
        Search only for text-sourced document chunks
        """
        if top_k is None:
            top_k = config.TOP_K
            
        # Get all results first (fetch more to filter)
        all_results = self.search(query, top_k=top_k * 5)
        
        # Filter for text (not images)
        text_results = [r for r in all_results if not r.get('is_from_image', False)]
        
        # Return top k
        return text_results[:top_k]

    def get_image_statistics(self) -> Dict:
        """
        Get statistics about image chunks
        """
        image_chunks = [c for c in self.all_chunks if getattr(c, 'is_from_image', False)]
        
        return {
            'total_chunks': len(self.all_chunks),
            'image_chunks': len(image_chunks),
            'text_chunks': len(self.all_chunks) - len(image_chunks),
            'image_percentage': (len(image_chunks) / len(self.all_chunks) * 100) if self.all_chunks else 0
        }
    
    def save(self, filepath: str):
        """
        Save the vector database to disk
        
        Args:
            filepath: Path to save the database
        """
        print(f"\n💾 Saving vector database to: {filepath}")
        
        # Prepare data for serialization
        db_data = {
            'wells': self.wells,
            'all_chunks': self.all_chunks,
            'chunk_embeddings': self.chunk_embeddings,
            'well_embeddings': self.well_embeddings
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(db_data, f)
        
        file_size_mb = Path(filepath).stat().st_size / (1024 * 1024)
        print(f"✅ Database saved successfully ({file_size_mb:.2f} MB)")
    
    @classmethod
    def load(cls, filepath: str, embedding_model: EmbeddingModel = None):
        """
        Load vector database from disk
        
        Args:
            filepath: Path to load the database from
            embedding_model: EmbeddingModel instance (creates new if None)
            
        Returns:
            HierarchicalVectorDB instance
        """
        print(f"\n📂 Loading vector database from: {filepath}")
        
        if not Path(filepath).exists():
            raise FileNotFoundError(f"Database file not found: {filepath}")
        
        with open(filepath, 'rb') as f:
            db_data = pickle.load(f)
        
        # Create instance
        db = cls(embedding_model=embedding_model)
        
        # Restore data
        db.wells = db_data['wells']
        db.all_chunks = db_data['all_chunks']
        db.chunk_embeddings = db_data['chunk_embeddings']
        db.well_embeddings = db_data['well_embeddings']
        
        print(f"✅ Database loaded successfully!")
        print(f"   Wells: {len(db.wells)}")
        print(f"   Total chunks: {len(db.all_chunks)}")
        
        return db
    
    def get_statistics(self) -> Dict:
        """
        Get statistics about the vector database
        
        Returns:
            Dictionary with statistics
        """
        stats = {
            'num_wells': len(self.wells),
            'num_chunks': len(self.all_chunks),
            'wells': []
        }
        
        for well in self.wells:
            well_stats = {
                'name': well.well_name,
                'path': well.well_path,
                'num_documents': len(well.documents),
                'unique_files': len(set(doc.filepath for doc in well.documents))
            }
            stats['wells'].append(well_stats)
        
        return stats
