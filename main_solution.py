#!/usr/bin/env python
"""
Hierarchical RAG System - Single File Solution
Team: Abhijeet
Date: December 1, 2025

Description:
This is a self-contained implementation of the Hierarchical RAG system.
It includes the Borehole Priority Engine (S2 > S1 > Main), Document Processing,
Vector Database, and Judge CLI in a single executable file.

Usage:
    python main_solution.py
"""

import os
import sys
import time
import json
import pickle
import re
import shutil
import logging
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor

# Third-party imports
try:
    import torch
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import google.generativeai as genai
    from PIL import Image
    import pytesseract
    from pdf2image import convert_from_path
    import PyPDF2
    from openpyxl import load_workbook
    from dotenv import load_dotenv
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Please run: pip install -r requirements.txt")
    sys.exit(1)

# Load environment variables
load_dotenv()

# ============================================================================
# 1. CONFIGURATION
# ============================================================================
class Config:
    # Paths
    BASE_DIR = Path(os.getcwd())
    DATA_DIR = BASE_DIR / "DATA"
    DB_PATH = BASE_DIR / "wells_complete_db.pkl"
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    
    # Models
    EMBEDDING_MODEL_NAME = "BAAI/bge-base-en-v1.5"
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    EMBEDDING_DIMENSION = 768
    
    # RAG Settings
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 50
    TOP_K = 5
    MIN_SIMILARITY_THRESHOLD = 0.3
    
    # API Keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("rag_system.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ============================================================================
# 2. BOREHOLE PRIORITY HANDLER (The Breakthrough)
# ============================================================================
class BoreholeHandler:
    """
    Handles borehole priority logic: S2 > S1 > Main Hole
    """
    PRIORITY_MAP = {
        'main': 1, 'main_hole': 1,
        's1': 2, 'sidetrack_1': 2, 'sidetrack 1': 2,
        's2': 3, 'sidetrack_2': 3, 'sidetrack 2': 3,
    }
    
    @staticmethod
    def identify_borehole_type(text: str) -> Tuple[str, int]:
        text_lower = text.lower()
        if re.search(r'\bs2\b', text_lower) or 'sidetrack 2' in text_lower or 'sidetrack-2' in text_lower:
            return ('S2', 3)
        if re.search(r'\bs1\b', text_lower) or 'sidetrack 1' in text_lower or 'sidetrack-1' in text_lower:
            return ('S1', 2)
        return ('Main Hole', 1)
    
    @staticmethod
    def annotate_documents_with_borehole_info(documents: List[Dict]) -> List[Dict]:
        annotated = []
        for doc in documents:
            text = doc.get('text', '') + ' ' + doc.get('filename', '')
            borehole_type, priority = BoreholeHandler.identify_borehole_type(text)
            annotated.append({
                **doc,
                'borehole_type': borehole_type,
                'borehole_priority': priority
            })
        return annotated
    
    @staticmethod
    def filter_by_borehole_priority(documents: List[Dict]) -> List[Dict]:
        if not documents:
            return []
        
        # Group by borehole type
        borehole_groups = {}
        for doc in documents:
            borehole_type = doc['borehole_type']
            priority = doc['borehole_priority']
            
            if borehole_type not in borehole_groups:
                borehole_groups[borehole_type] = {'priority': priority, 'documents': []}
            borehole_groups[borehole_type]['documents'].append(doc)
        
        # Find highest priority group
        if not borehole_groups:
            return documents
            
        highest_priority_type = max(borehole_groups.keys(), 
                                    key=lambda k: borehole_groups[k]['priority'])
        
        return borehole_groups[highest_priority_type]['documents']

    @staticmethod
    def get_summary(documents: List[Dict]) -> str:
        counts = {}
        for doc in documents:
            b_type = doc['borehole_type']
            if b_type not in counts:
                counts[b_type] = 0
            counts[b_type] += 1
        return ", ".join([f"{k}: {v}" for k, v in counts.items()])

# ============================================================================
# 3. DOCUMENT PROCESSOR & OCR
# ============================================================================
class DocumentChunk:
    def __init__(self, text, filename, well_name, chunk_idx, total_chunks, is_from_image=False):
        self.text = text
        self.filename = filename
        self.well_name = well_name
        self.chunk_idx = chunk_idx
        self.total_chunks = total_chunks
        self.embedding = None
        self.is_from_image = is_from_image

class WellData:
    def __init__(self, well_name, folder_path):
        self.well_name = well_name
        self.folder_path = folder_path
        self.documents = []

class DocumentProcessor:
    @staticmethod
    def process_pdf(filepath):
        text_content = ""
        try:
            # 1. Extract Text
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text_content += page.extract_text() + "\n"
            
            # 2. Extract Images (OCR)
            try:
                images = convert_from_path(filepath)
                for img in images:
                    ocr_text = pytesseract.image_to_string(img)
                    if len(ocr_text.strip()) > 50:
                        text_content += f"\n[IMAGE OCR CONTENT]\n{ocr_text}\n"
            except Exception:
                pass # OCR failed or poppler not installed
                
        except Exception as e:
            logger.error(f"Error processing PDF {filepath}: {e}")
        return text_content

    @staticmethod
    def chunk_text(text, chunk_size=500, overlap=50):
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            if len(chunk) > 50:
                chunks.append(chunk)
        return chunks

    @staticmethod
    def process_well_folder(folder_path):
        well_name = os.path.basename(folder_path)
        well_data = WellData(well_name, folder_path)
        
        for root, _, files in os.walk(folder_path):
            for file in files:
                filepath = os.path.join(root, file)
                text = ""
                is_image = False
                
                if file.lower().endswith('.pdf'):
                    text = DocumentProcessor.process_pdf(filepath)
                elif file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    try:
                        text = pytesseract.image_to_string(Image.open(filepath))
                        is_image = True
                    except: pass
                elif file.lower().endswith('.txt'):
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        text = f.read()
                
                if text:
                    chunks = DocumentProcessor.chunk_text(text)
                    for i, chunk_text in enumerate(chunks):
                        chunk = DocumentChunk(chunk_text, file, well_name, i, len(chunks), is_image)
                        well_data.documents.append(chunk)
                        
        return well_data

# ============================================================================
# 4. EMBEDDING & VECTOR DATABASE
# ============================================================================
class EmbeddingModel:
    def __init__(self):
        print(f"🔄 Loading Embedding Model: {Config.EMBEDDING_MODEL_NAME}")
        self.model = SentenceTransformer(Config.EMBEDDING_MODEL_NAME, device=Config.DEVICE)
    
    def encode(self, texts):
        return self.model.encode(texts, convert_to_numpy=True, show_progress_bar=True)

class HierarchicalVectorDB:
    def __init__(self, embedding_model):
        self.embedding_model = embedding_model
        self.wells = []
        self.all_chunks = []
        self.chunk_embeddings = None
    
    def add_wells(self, wells_data):
        self.wells.extend(wells_data)
        new_chunks = []
        for well in wells_data:
            new_chunks.extend(well.documents)
        
        if not new_chunks: return
        
        self.all_chunks.extend(new_chunks)
        texts = [c.text for c in new_chunks]
        embeddings = self.embedding_model.encode(texts)
        
        for chunk, emb in zip(new_chunks, embeddings):
            chunk.embedding = emb
            
        if self.chunk_embeddings is None:
            self.chunk_embeddings = embeddings
        else:
            self.chunk_embeddings = np.vstack([self.chunk_embeddings, embeddings])
            
    def search(self, query, top_k=5, filter_mode='all'):
        if self.chunk_embeddings is None: return []
        
        query_embedding = self.embedding_model.model.encode([f"Represent this sentence for searching relevant passages: {query}"], convert_to_numpy=True)
        similarities = cosine_similarity(query_embedding, self.chunk_embeddings)[0]
        
        # Sort by similarity
        top_indices = np.argsort(similarities)[::-1]
        
        results = []
        count = 0
        for idx in top_indices:
            if count >= top_k * 3: break # Fetch more for filtering
            
            chunk = self.all_chunks[idx]
            score = similarities[idx]
            
            if score < Config.MIN_SIMILARITY_THRESHOLD: continue
            
            # Filter modes
            if filter_mode == 'images_only' and not chunk.is_from_image: continue
            if filter_mode == 'text_only' and chunk.is_from_image: continue
            
            results.append({
                'text': chunk.text,
                'filename': chunk.filename,
                'well_name': chunk.well_name,
                'similarity': float(score),
                'is_from_image': chunk.is_from_image
            })
            count += 1
            
        return results[:top_k*2] # Return ample candidates for priority filtering

    def save(self, path):
        with open(path, 'wb') as f:
            pickle.dump(self, f)
            
    @staticmethod
    def load(path, embedding_model):
        with open(path, 'rb') as f:
            db = pickle.load(f)
            db.embedding_model = embedding_model
            return db

# ============================================================================
# 5. GEMINI AI HANDLER
# ============================================================================
def generate_answer(query, context_docs):
    if not Config.GEMINI_API_KEY:
        return {"success": False, "error": "No API Key"}
        
    genai.configure(api_key=Config.GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
    
    context_text = ""
    for i, doc in enumerate(context_docs, 1):
        context_text += f"Document {i} ({doc['filename']} - {doc['borehole_type']}):\n{doc['text']}\n\n"
        
    prompt = f"""
    You are a senior petroleum engineer. Answer the query based strictly on the provided documents.
    
    CONTEXT:
    {context_text}
    
    QUERY: {query}
    
    INSTRUCTIONS:
    1. Prioritize data from Sidetrack 2 (S2) over Sidetrack 1 (S1) over Main Hole.
    2. Cite the specific document filename for every fact.
    3. If the answer is not in the documents, say "Information not found in the provided documents."
    """
    
    try:
        response = model.generate_content(prompt)
        return {"success": True, "answer": response.text}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ============================================================================
# 6. CLI INTERFACE
# ============================================================================
class CLI:
    def __init__(self):
        self.db = None
        self.model = None
        
    def initialize(self):
        print("\n🔬 INITIALIZING HIERARCHICAL RAG SYSTEM...")
        self.model = EmbeddingModel()
        
        if os.path.exists(Config.DB_PATH):
            print(f"📂 Loading database from {Config.DB_PATH}")
            self.db = HierarchicalVectorDB.load(Config.DB_PATH, self.model)
            print(f"✅ Loaded {len(self.db.all_chunks)} chunks.")
        else:
            print("⚠️  Database not found. Please index data first.")
            self.db = HierarchicalVectorDB(self.model)
            
    def index_data(self):
        print("\n📂 INDEXING DATA...")
        if not os.path.exists(Config.DATA_DIR):
            os.makedirs(Config.DATA_DIR)
            print(f"❌ '{Config.DATA_DIR}' folder created. Please put 'Well X' folders inside it and run again.")
            return
            
        well_folders = [os.path.join(Config.DATA_DIR, d) for d in os.listdir(Config.DATA_DIR) 
                       if os.path.isdir(os.path.join(Config.DATA_DIR, d))]
        
        if not well_folders:
            print("❌ No well folders found in DATA/ directory.")
            return

        wells_data = []
        for folder in well_folders:
            print(f"   Processing {os.path.basename(folder)}...")
            wells_data.append(DocumentProcessor.process_well_folder(folder))
            
        self.db.add_wells(wells_data)
        self.db.save(Config.DB_PATH)
        print(f"✅ Indexing complete! Saved to {Config.DB_PATH}")

    def query_loop(self):
        print("\n" + "="*60)
        print("🎯 RAG SYSTEM READY - INTERACTIVE MODE")
        print("   Borehole Priority: S2 > S1 > Main Hole")
        print("="*60 + "\n")
        
        while True:
            query = input("❓ Enter Query (or 'q' to quit): ").strip()
            if query.lower() in ['q', 'quit', 'exit']: break
            if not query: continue
            
            start_time = time.time()
            
            # 1. Retrieval
            results = self.db.search(query, top_k=10)
            
            if not results:
                print("❌ No documents found.")
                continue
                
            # 2. Borehole Priority Filtering
            annotated = BoreholeHandler.annotate_documents_with_borehole_info(results)
            filtered = BoreholeHandler.filter_by_borehole_priority(annotated)
            
            # 3. Generation
            answer = generate_answer(query, filtered)
            
            end_time = time.time()
            
            # Output
            print("\n" + "-"*60)
            print(f"📍 Borehole Analysis: {BoreholeHandler.get_summary(annotated)}")
            print(f"✅ Using Priority: {filtered[0]['borehole_type'] if filtered else 'None'}")
            print("-" * 60)
            
            if answer['success']:
                print("🤖 ANSWER:")
                print(answer['answer'])
            else:
                print(f"⚠️  AI Generation Failed: {answer.get('error')}")
                print("📄 Top Documents:")
                for doc in filtered[:3]:
                    print(f"   - {doc['filename']} ({doc['borehole_type']})")
            
            print("-" * 60)
            print(f"⏱️  Time: {end_time - start_time:.2f}s")
            print("=" * 60 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hierarchical RAG System")
    parser.add_argument("--index", action="store_true", help="Index data from DATA/ folder")
    args = parser.parse_args()
    
    cli = CLI()
    cli.initialize()
    
    if args.index:
        cli.index_data()
    
    cli.query_loop()
