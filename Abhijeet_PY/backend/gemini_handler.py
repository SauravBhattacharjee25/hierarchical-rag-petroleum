"""
Gemini API Handler
Manages interactions with Google Gemini for answer generation
"""

import google.generativeai as genai
from typing import List, Dict, Optional

from backend import config


# ============================================================================
# Gemini Model Initialization
# ============================================================================

def get_working_model(api_key: str) -> genai.GenerativeModel:
    """
    Iterate through the model ladder to find a working model
    """
    for model_name in config.GEMINI_MODELS_LADDER:
        try:
            print(f"🔄 Testing model: {model_name}...")
            model = genai.GenerativeModel(model_name)
            
            # Simple test generation
            response = model.generate_content("Hello")
            if response:
                print(f"✅ Found working model: {model_name}")
                config.GEMINI_MODEL_NAME = model_name  # Update config with working model
                return model
        except Exception as e:
            print(f"⚠️  Model {model_name} failed: {e}")
            continue
            
    raise ValueError("❌ No working Gemini models found. Please check your API key and quota.")

def initialize_gemini(api_key: str = None) -> genai.GenerativeModel:
    """
    Initialize Gemini model with API key and fallback strategy
    
    Args:
        api_key: Gemini API key (uses config if None)
        
    Returns:
        GenerativeModel instance
    """
    if api_key is None:
        api_key = config.GEMINI_API_KEY
    
    if not api_key:
        raise ValueError("Gemini API key not provided. Set GEMINI_API_KEY environment variable.")
    
    try:
        genai.configure(api_key=api_key)
        
        # Use fallback strategy to get a working model
        model = get_working_model(api_key)
        
        # Apply configuration to the selected model
        model.generation_config = genai.types.GenerationConfig(
            temperature=config.GEMINI_TEMPERATURE,
            max_output_tokens=config.GEMINI_MAX_TOKENS
        )
        
        return model
    
    except Exception as e:
        print(f"❌ Failed to initialize Gemini: {e}")
        raise


# ============================================================================
# Prompt Engineering
# ============================================================================

def create_rag_prompt(query: str, top_documents: List[Dict], 
                      nodal_results: Optional[Dict] = None) -> str:
    """
    Create a RAG prompt for Gemini with retrieved context
    
    Args:
        query: User's query
        top_documents: List of retrieved document dictionaries
        nodal_results: Optional nodal analysis results
        
    Returns:
        Formatted prompt string
    """
    prompt = """You are a senior petroleum engineering consultant providing professional technical analysis based on well data documentation.

ROLE & TONE:
- Provide responses in a professional, corporate, and technically accurate manner
- Use clear, precise language suitable for engineering reports and technical documentation
- Maintain objectivity and cite specific sources for all claims
- When uncertain, clearly state the limitations of available data

RESPONSE GUIDELINES:
1. **Data Fidelity**: Base ALL answers strictly on the provided documents. Never speculate or add external knowledge.
2. **Source Attribution**: Always cite the specific document(s) and well(s) referenced (e.g., "According to [filename] from Well [name]...")
3. **Unavailable Information**: If information is not in the documents, respond professionally: "The requested information is not available in the current documentation. Additional data sources would be required to address this query."
4. **Technical Precision**: Use proper petroleum engineering terminology, units, and standards
5. **Structured Responses**: For complex queries, use clear formatting:
   - Summary/Direct Answer first
   - Supporting details with citations
   - Relevant technical specifications
   - Calculations or analysis (if applicable)
   - Limitations or caveats (if any)
6. **Ethical Standards**: Maintain professional integrity; do not fabricate data or make unsupported claims

FORMAT YOUR RESPONSE:
- Start with a concise direct answer
- Follow with detailed explanation only if needed
- Use bullet points or numbered lists for clarity
- Include relevant technical values with proper units
- End with data source references

"""
    
    # Add retrieved documents context
    prompt += "=" * 70 + "\n"
    prompt += "RETRIEVED DOCUMENTS:\n"
    prompt += "=" * 70 + "\n\n"
    
    for doc in top_documents:
        prompt += f"Document {doc['rank']}: {doc['filename']}\n"
        prompt += f"Well: {doc['well_name']}\n"
        prompt += f"Relevance Score: {doc['similarity']:.1%}\n"
        prompt += f"Content:\n{doc['text']}\n"
        prompt += "\n" + "-" * 70 + "\n\n"
    
    # Add nodal analysis results if available
    if nodal_results:
        prompt += "=" * 70 + "\n"
        prompt += "NODAL ANALYSIS CALCULATIONS:\n"
        prompt += "=" * 70 + "\n\n"
        prompt += format_nodal_results(nodal_results)
        prompt += "\n" + "-" * 70 + "\n\n"
    
    # Add user query
    prompt += "=" * 70 + "\n"
    prompt += "USER QUESTION:\n"
    prompt += "=" * 70 + "\n"
    prompt += query + "\n\n"
    
    prompt += "=" * 70 + "\n"
    prompt += "YOUR ANSWER:\n"
    prompt += "=" * 70 + "\n"
    
    return prompt


def format_nodal_results(nodal_results: Dict) -> str:
    """
    Format nodal analysis results for inclusion in prompt
    
    Args:
        nodal_results: Dictionary with nodal analysis results
        
    Returns:
        Formatted string
    """
    if not nodal_results:
        return ""
    
    formatted = "Nodal Analysis Results:\n\n"
    
    if nodal_results.get('success'):
        formatted += f"✅ Solution Found:\n"
        formatted += f"  - Production Rate: {nodal_results.get('flowrate', 'N/A')} m³/hr\n"
        formatted += f"  - Bottomhole Pressure: {nodal_results.get('bottomhole_pressure', 'N/A')} bar\n"
        formatted += f"  - Pump Head: {nodal_results.get('pump_head', 'N/A')} m\n\n"
        
        if 'parameters_used' in nodal_results:
            formatted += "Parameters Used:\n"
            for key, value in nodal_results['parameters_used'].items():
                formatted += f"  - {key}: {value}\n"
    else:
        formatted += f"❌ Calculation Error: {nodal_results.get('error', 'Unknown error')}\n"
    
    return formatted


# ============================================================================
# Answer Generation
# ============================================================================

def generate_answer(model: genai.GenerativeModel, prompt: str) -> str:
    """
    Generate answer using Gemini model
    
    Args:
        model: Gemini GenerativeModel instance
        prompt: Formatted prompt
        
    Returns:
        Generated answer text
    """
    try:
        response = model.generate_content(prompt)
        
        if response and response.text:
            return response.text
        else:
            return "Sorry, I couldn't generate a response. Please try again."
    
    except Exception as e:
        print(f"❌ Error generating answer: {e}")
        return f"Error generating answer: {str(e)}"


def answer_query(query: str, top_documents: List[Dict], 
                 api_key: str = None, nodal_results: Optional[Dict] = None) -> Dict:
    """
    Complete workflow: Create prompt and generate answer
    
    Args:
        query: User's query
        top_documents: Retrieved documents from vector search
        api_key: Gemini API key (optional)
        nodal_results: Optional nodal analysis results
        
    Returns:
        Dictionary with query, answer, and metadata
    """
    print("\n🤖 Generating answer with Gemini...")
    
    try:
        # Initialize Gemini
        model = initialize_gemini(api_key)
        
        # Create prompt
        prompt = create_rag_prompt(query, top_documents, nodal_results)
        
        if config.DEBUG_MODE:
            print(f"\n📝 Prompt length: {len(prompt)} characters")
        
        # Generate answer
        answer = generate_answer(model, prompt)
        
        print("✅ Answer generated successfully!\n")
        
        return {
            'success': True,
            'query': query,
            'answer': answer,
            'sources': [
                {
                    'well': doc['well_name'],
                    'file': doc['filename'],
                    'similarity': doc['similarity']
                }
                for doc in top_documents
            ],
            'nodal_analysis_performed': nodal_results is not None
        }
    
    except Exception as e:
        print(f"❌ Error in answer generation: {e}\n")
        return {
            'success': False,
            'query': query,
            'error': str(e)
        }


# ============================================================================
# Interactive Chat Support
# ============================================================================

def chat_with_context(model: genai.GenerativeModel, question: str, 
                      context: str) -> str:
    """
    Handle follow-up questions with existing context
    
    Args:
        model: Gemini model instance
        question: Follow-up question
        context: Previous context/documents
        
    Returns:
        Answer text
    """
    prompt = f"""Based on the documents we analyzed earlier:

{context}

User's follow-up question: {question}

Please provide a clear, concise answer based on the document content."""
    
    return generate_answer(model, prompt)
