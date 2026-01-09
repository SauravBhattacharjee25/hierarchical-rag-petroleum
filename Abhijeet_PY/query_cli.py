#!/usr/bin/env python
"""
RAG System CLI - For Judges
Production-ready command-line interface for querying the RAG system
"""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend import config
from backend.rag_system import HierarchicalVectorDB, EmbeddingModel
from backend.gemini_handler import answer_query
from backend.nodal_integration import process_nodal_query
from backend.borehole_handler import BoreholeHandler


class RAGSystemCLI:
    """Command-line interface for RAG system"""
    
    def __init__(self):
        self.vector_db = None
        self.embedding_model = None
        self.database_path = 'wells_complete_db.pkl'
    
    def print_header(self):
        """Print CLI header"""
        print("\n" + "=" * 80)
        print("🔬 HIERARCHICAL RAG SYSTEM - COMMAND LINE INTERFACE")
        print("=" * 80)
        print("🎯 Petroleum Well Data Analysis with AI")
        print("📍 Automatic Borehole Priority: S2 > S1 > Main Hole")
        print("=" * 80 + "\n")
    
    def initialize(self):
        """Initialize the RAG system"""
        print("🔄 Initializing system...")
        
        try:
            # Check if database exists
            if not os.path.exists(self.database_path):
                print(f"\n❌ ERROR: Database not found!")
                print(f"   Expected: {self.database_path}")
                print(f"\n📝 Please run the web interface first to index your wells:")
                print(f"   python run_simple.py")
                print(f"   Then upload your well folders via http://localhost:5000")
                return False
            
            # Initialize embedding model
            print("   Loading embedding model...")
            self.embedding_model = EmbeddingModel()
            
            # Load database
            print(f"   Loading database: {self.database_path}")
            self.vector_db = HierarchicalVectorDB.load(
                self.database_path, 
                self.embedding_model
            )
            
            # Display stats
            stats = self.vector_db.get_statistics()
            image_stats = self.vector_db.get_image_statistics()
            
            print(f"\n✅ System Ready!")
            print(f"   📊 Wells: {stats['num_wells']}")
            print(f"   📄 Total Chunks: {stats['num_chunks']}")
            print(f"   🖼️  Image Chunks: {image_stats['image_chunks']}")
            print(f"   📝 Text Chunks: {image_stats['text_chunks']}")
            print(f"   🤖 Gemini AI: {'Enabled' if config.GEMINI_API_KEY else 'Disabled'}")
            
            if stats['num_wells'] > 0:
                print(f"\n📂 Available Wells:")
                for well in stats['wells']:
                    print(f"   • {well['name']}: {well['num_documents']} chunks")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Initialization failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def query(self, question, mode='all'):
        """Execute a query"""
        if not self.vector_db or len(self.vector_db.all_chunks) == 0:
            print("\n❌ Database is empty!")
            return None
        
        print(f"\n🔍 Query: \"{question}\"")
        print(f"📊 Mode: {mode.upper()}")
        print("-" * 80)
        
        try:
            # Search for documents
            print("   Searching documents...")
            if mode == 'images_only':
                top_docs = self.vector_db.search_images_only(question, top_k=config.TOP_K)
            elif mode == 'text_only':
                top_docs = self.vector_db.search_text_only(question, top_k=config.TOP_K)
            else:
                top_docs = self.vector_db.search(question, top_k=config.TOP_K)
            
            if not top_docs:
                print("\n❌ No relevant documents found.\n")
                return None
            
            # Apply borehole priority filtering
            print("   Applying borehole priority (S2 > S1 > Main Hole)...")
            annotated_docs = BoreholeHandler.annotate_documents_with_borehole_info(top_docs)
            filtered_docs = BoreholeHandler.filter_by_borehole_priority(annotated_docs)
            
            # Show borehole analysis
            print("\n📍 Borehole Analysis:")
            borehole_summary = BoreholeHandler.get_borehole_summary(annotated_docs)
            for line in borehole_summary.split('\n'):
                print(f"   {line}")
            
            if filtered_docs:
                print(f"\n✅ Using Highest Priority: {filtered_docs[0]['borehole_type']}")
                print(f"   Filtered from {len(annotated_docs)} to {len(filtered_docs)} documents")
            
            top_docs = filtered_docs
            
            # Check for nodal analysis
            nodal_results = None
            if config.GEMINI_API_KEY:
                print("\n   Checking for nodal analysis requirements...")
                nodal_results = process_nodal_query(question, top_docs, config.GEMINI_API_KEY)
            
            # Generate answer
            if config.GEMINI_API_KEY:
                print("   Generating AI answer with Gemini...")
                import time
                start_time = time.time()
                
                answer_data = answer_query(question, top_docs, config.GEMINI_API_KEY, nodal_results)
                
                end_time = time.time()
                execution_time = end_time - start_time
                
                if answer_data and answer_data.get('success'):
                    print("\n" + "=" * 80)
                    print("🤖 AI-GENERATED ANSWER:")
                    print("=" * 80)
                    print(answer_data['answer'])
                    print("\n" + "=" * 80)
                    print(f"⏱️  Response Time: {execution_time:.2f} seconds")
                    print("=" * 80)
                    print("📚 SOURCES:")
                    print("=" * 80)
                    for source in answer_data.get('sources', []):
                        print(f"   • {source['file']}")
                        print(f"     Well: {source['well']}")
                        print(f"     Relevance: {source['similarity']:.1%}")
                    print("=" * 80 + "\n")
                    
                    return answer_data['answer']
                else:
                    print(f"\n❌ Failed to generate answer: {answer_data.get('error', 'Unknown error')}")
                    
            else:
                print("\n⚠️  Gemini API key not configured.")
                print("   Showing retrieved documents only:\n")
                
                for doc in top_docs[:5]:
                    print(f"\n📄 [{doc['rank']}] {doc['filename']}")
                    print(f"   Well: {doc['well_name']}")
                    print(f"   Borehole: {doc.get('borehole_type', 'Unknown')}")
                    print(f"   Similarity: {doc['similarity']:.1%}")
                    print(f"   Preview: {doc['preview'][:200]}...")
                    print("-" * 80)
            
            return None
            
        except Exception as e:
            print(f"\n❌ Query failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def interactive_mode(self):
        """Run in interactive mode"""
        print("\n🎯 INTERACTIVE MODE")
        print("=" * 80)
        print("Enter your questions below. Type 'exit', 'quit', or 'q' to stop.")
        print("=" * 80 + "\n")
        
        while True:
            try:
                question = input("❓ Your question: ").strip()
                
                if question.lower() in ['exit', 'quit', 'q', '']:
                    print("\n👋 Thank you for using the RAG System!\n")
                    break
                
                self.query(question)
                
            except KeyboardInterrupt:
                print("\n\n👋 Thank you for using the RAG System!\n")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}\n")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='🔬 Hierarchical RAG System - CLI for Judges',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (recommended for judges)
  python query_cli.py
  
  # Single query
  python query_cli.py --query "What is the TVD of Well 1?"
  
  # Query with specific mode
  python query_cli.py --query "Show production data" --mode images_only

Query Modes:
  all          - Search both text and images (default)
  text_only    - Search only text documents
  images_only  - Search only image-extracted content

Note: The system automatically applies borehole priority (S2 > S1 > Main Hole)
        """
    )
    
    parser.add_argument(
        '--query', '-q',
        type=str,
        help='Query to execute (if not provided, enters interactive mode)'
    )
    
    parser.add_argument(
        '--mode', '-m',
        choices=['all', 'text_only', 'images_only'],
        default='all',
        help='Query mode (default: all)'
    )
    
    args = parser.parse_args()
    
    # Initialize CLI
    cli = RAGSystemCLI()
    cli.print_header()
    
    if not cli.initialize():
        sys.exit(1)
    
    # Run query or interactive mode
    if args.query:
        cli.query(args.query, args.mode)
    else:
        cli.interactive_mode()


if __name__ == '__main__':
    main()
