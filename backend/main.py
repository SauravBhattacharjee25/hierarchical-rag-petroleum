"""
Main CLI Interface for Hierarchical RAG System
Handles indexing of wells and querying the vector database
"""

import argparse
import sys
from pathlib import Path

# Fix for Windows console Unicode encoding
import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import config
from document_processor import process_multiple_wells
from rag_system import HierarchicalVectorDB, EmbeddingModel
from gemini_handler import answer_query
from nodal_integration import process_nodal_query


# Set Gemini API key
config.GEMINI_API_KEY = "AIzaSyBrFMhJzP-Tl_H5F_017JhKj5ySFPdWvVM"

# ============================================================================
# Indexing Command
# ============================================================================

def index_wells(well_paths: list, output_path: str):
    """
    Index new wells and save vector database
    
    Args:
        well_paths: List of paths to well folders
        output_path: Path to save the database
    """
    print("\n" + "=" * 70)
    print("🔧 INDEXING MODE: Building Vector Database")
    print("=" * 70)
    
    # Process well folders
    wells = process_multiple_wells(well_paths)
    
    if not wells:
        print("\n❌ No wells processed. Exiting.")
        sys.exit(1)
    
    # Create vector database
    print("\n🔄 Creating vector database...")
    embedding_model = EmbeddingModel()
    vector_db = HierarchicalVectorDB(embedding_model)
    
    # Add wells and compute embeddings
    vector_db.add_wells(wells)
    
    # Save database
    vector_db.save(output_path)
    
    # Print statistics
    stats = vector_db.get_statistics()
    print("\n" + "=" * 70)
    print("📊 Database Statistics")
    print("=" * 70)
    print(f"Total Wells: {stats['num_wells']}")
    print(f"Total Chunks: {stats['num_chunks']}")
    print("\nWells:")
    for well_stat in stats['wells']:
        print(f"  - {well_stat['name']}: {well_stat['num_documents']} chunks "
              f"({well_stat['unique_files']} files)")
    print("=" * 70)
    print(f"\n✅ Indexing complete! Database saved to: {output_path}\n")


# ============================================================================
# Query Command
# ============================================================================

def query_database(database_path: str, query: str, show_sources: bool = True):
    """
    Query the vector database and generate answer
    
    Args:
        database_path: Path to saved vector database
        query: User's query
        show_sources: Whether to show source documents
    """
    print("\n" + "=" * 70)
    print("🔍 QUERY MODE: Searching Vector Database")
    print("=" * 70)
    
    # Check if database exists
    if not Path(database_path).exists():
        print(f"\n❌ Database not found: {database_path}")
        print("   Run with --index first to create a database.\n")
        sys.exit(1)
    
    # Load database
    embedding_model = EmbeddingModel()
    vector_db = HierarchicalVectorDB.load(database_path, embedding_model)
    
    # Search for relevant documents
    top_docs = vector_db.search(query, top_k=config.TOP_K)
    
    if not top_docs:
        print("\n⚠️  No relevant documents found.\n")
        return
    
    # Check if nodal analysis is needed
    nodal_results = None
    if config.GEMINI_API_KEY:
        nodal_results = process_nodal_query(query, top_docs, config.GEMINI_API_KEY)
    
    # Generate answer with Gemini
    if config.GEMINI_API_KEY:
        result = answer_query(query, top_docs, config.GEMINI_API_KEY, nodal_results)
        
        print("=" * 70)
        print("💡 ANSWER")
        print("=" * 70)
        print(result['answer'])
        print("=" * 70)
        
        if show_sources:
            print("\n📚 SOURCES")
            print("=" * 70)
            for source in result['sources']:
                print(f"  [{source['well']}] {source['file']} "
                      f"(Similarity: {source['similarity']:.1%})")
            print("=" * 70)
        
        if result.get('nodal_analysis_performed'):
            print("\n✅ Nodal analysis calculations were performed")
    else:
        print("\n⚠️  Gemini API key not set. Showing top documents only.\n")
        print("=" * 70)
        print("📄 TOP DOCUMENTS")
        print("=" * 70)
        for doc in top_docs:
            print(f"\n{doc['rank']}. [{doc['well_name']}] {doc['filename']}")
            print(f"   Similarity: {doc['similarity']:.1%}")
            print(f"   Preview: {doc['preview']}")
            print("   " + "-" * 65)
        print("=" * 70)
    
    print()


# ============================================================================
# Interactive Mode
# ============================================================================

def interactive_mode(database_path: str):
    """
    Interactive query mode with continuous question-answer loop
    
    Args:
        database_path: Path to saved vector database
    """
    print("\n" + "=" * 70)
    print("💬 INTERACTIVE MODE")
    print("=" * 70)
    print("Type your questions and press Enter.")
    print("Type 'quit', 'exit', or 'q' to exit.")
    print("=" * 70)
    
    # Check if database exists
    if not Path(database_path).exists():
        print(f"\n❌ Database not found: {database_path}")
        print("   Run with --index first to create a database.\n")
        sys.exit(1)
    
    # Load database once
    print("\n🔄 Loading vector database...")
    embedding_model = EmbeddingModel()
    vector_db = HierarchicalVectorDB.load(database_path, embedding_model)
    print("✅ Database loaded!\n")
    
    # Interactive loop
    while True:
        try:
            # Get user input
            query = input("\n❓ Your question: ").strip()
            
            # Check for exit commands
            if query.lower() in ['quit', 'exit', 'q', '']:
                print("\n👋 Goodbye!\n")
                break
            
            # Search
            top_docs = vector_db.search(query, top_k=config.TOP_K)
            
            if not top_docs:
                print("⚠️  No relevant documents found.")
                continue
            
            # Check for nodal analysis
            nodal_results = None
            if config.GEMINI_API_KEY:
                nodal_results = process_nodal_query(query, top_docs, config.GEMINI_API_KEY)
            
            # Generate answer
            if config.GEMINI_API_KEY:
                result = answer_query(query, top_docs, config.GEMINI_API_KEY, nodal_results)
                
                print("\n" + "=" * 70)
                print("💡 ANSWER")
                print("=" * 70)
                print(result['answer'])
                print("=" * 70)
                
                print("\n📚 Sources:")
                for source in result['sources']:
                    print(f"  • [{source['well']}] {source['file']} ({source['similarity']:.1%})")
            else:
                print("\n⚠️  Gemini API key not set. Top documents:")
                for doc in top_docs:
                    print(f"  {doc['rank']}. [{doc['well_name']}] {doc['filename']} ({doc['similarity']:.1%})")
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


# ============================================================================
# Main CLI
# ============================================================================

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Hierarchical RAG System for Petroleum Well Data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Index wells
  python main.py --index "Well 1" "Well 2" --output wells_db.pkl

  # Query database
  python main.py --database wells_db.pkl --query "What is the TVD of Well 1?"

  # Interactive mode
  python main.py --database wells_db.pkl --interactive

  # Enable debug mode
  set DEBUG=true
  python main.py --database wells_db.pkl --query "Summarize Well 1"
        """
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        '--index',
        nargs='+',
        metavar='WELL_PATH',
        help='Index mode: Provide paths to well folders to index'
    )
    mode_group.add_argument(
        '--query',
        type=str,
        metavar='QUERY',
        help='Query mode: Ask a question about the wells'
    )
    mode_group.add_argument(
        '--interactive',
        action='store_true',
        help='Interactive mode: Continuous question-answer loop'
    )
    
    # Common arguments
    parser.add_argument(
        '--database',
        type=str,
        default=config.DEFAULT_DB_FILENAME,
        help=f'Path to vector database file (default: {config.DEFAULT_DB_FILENAME})'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output path for indexed database (for --index mode)'
    )
    parser.add_argument(
        '--top-k',
        type=int,
        default=config.TOP_K,
        help=f'Number of top documents to retrieve (default: {config.TOP_K})'
    )
    parser.add_argument(
        '--no-sources',
        action='store_true',
        help='Do not show source documents in query results'
    )
    
    args = parser.parse_args()
    
    # Update config if top-k specified
    if args.top_k:
        config.TOP_K = args.top_k
    
    # Execute based on mode
    if args.index:
        # Index mode
        output_path = args.output or args.database
        index_wells(args.index, output_path)
    
    elif args.query:
        # Query mode
        query_database(args.database, args.query, show_sources=not args.no_sources)
    
    elif args.interactive:
        # Interactive mode
        interactive_mode(args.database)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}\n")
        if config.DEBUG_MODE:
            import traceback
            traceback.print_exc()
        sys.exit(1)
