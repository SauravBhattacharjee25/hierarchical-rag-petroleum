"""
NodalAnalysis Integration Module
Bridges RAG system with nodal analysis calculations
"""

import re
from typing import Dict, Optional, List
import google.generativeai as genai

from backend import config


# ============================================================================
# Query Classification
# ============================================================================

def requires_nodal_analysis(query: str) -> bool:
    """
    Determine if a query requires nodal analysis calculations
    
    Args:
        query: User's query
        
    Returns:
        True if nodal analysis is needed
    """
    query_lower = query.lower()
    
    # Check for nodal analysis keywords
    for keyword in config.NODAL_KEYWORDS:
        if keyword in query_lower:
            return True
    
    return False


# ============================================================================
# Parameter Extraction
# ============================================================================

def extract_parameters_with_gemini(documents: List[Dict], api_key: str = None) -> Dict:
    """
    Extract nodal analysis parameters from documents using Gemini
    
    Args:
        documents: List of retrieved document dictionaries
        api_key: Gemini API key
        
    Returns:
        Dictionary of extracted parameters
    """
    if api_key is None:
        api_key = config.GEMINI_API_KEY
    
    try:
        # Use the robust initialization from gemini_handler
        from backend.gemini_handler import initialize_gemini
        model = initialize_gemini(api_key)
        
        # Create extraction prompt
        prompt = """Extract the following nodal analysis parameters from the well documents below.
Return ONLY a Python dictionary format with these keys (use None if not found):

{
    "rho": <fluid density in kg/m3>,
    "mu": <viscosity in Pa.s>,
    "reservoir_pressure": <reservoir pressure in bar>,
    "wellhead_pressure": <wellhead pressure in bar>,
    "PI": <productivity index in m3/hr per bar>,
    "esp_depth": <ESP intake depth in meters>,
    "well_trajectory": <list of dicts with MD, TVD, ID in meters>,
    "pump_curve": <dict with 'flow' and 'head' lists>
}

Documents:
"""
        
        # Add document content
        for doc in documents:
            prompt += f"\n--- {doc['filename']} ---\n"
            prompt += doc['text'][:2000]  # Limit text length
            prompt += "\n\n"
        
        prompt += "\nReturn only the Python dictionary, no other text:"
        
        response = model.generate_content(prompt)
        
        if response and response.text:
            # Try to parse the response as a dictionary
            # This is a simplified approach - production would need more robust parsing
            try:
                # Extract dictionary from response
                params_text = response.text.strip()
                # Remove markdown code blocks if present
                params_text = params_text.replace('```python', '').replace('```', '').strip()
                params = eval(params_text)
                return params
            except:
                if config.DEBUG_MODE:
                    print(f"⚠️  Could not parse Gemini response for parameter extraction")
                return {}
    
    except Exception as e:
        if config.DEBUG_MODE:
            print(f"⚠️  Parameter extraction failed: {e}")
        return {}


def extract_parameters_with_regex(documents: List[Dict]) -> Dict:
    """
    Extract nodal analysis parameters using regex patterns (fallback method)
    
    Args:
        documents: List of retrieved document dictionaries
        
    Returns:
        Dictionary of extracted parameters
    """
    params = {}
    
    # Combine all document text
    all_text = " ".join([doc['text'] for doc in documents])
    
    # Simple regex patterns for common parameters
    patterns = {
        'reservoir_pressure': r'reservoir\s+pressure[:\s]+(\d+\.?\d*)\s*bar',
        'wellhead_pressure': r'wellhead\s+pressure[:\s]+(\d+\.?\d*)\s*bar',
        'PI': r'productivity\s+index[:\s]+(\d+\.?\d*)',
        'esp_depth': r'ESP\s+(?:intake\s+)?depth[:\s]+(\d+\.?\d*)\s*m',
    }
    
    for param_name, pattern in patterns.items():
        match = re.search(pattern, all_text, re.IGNORECASE)
        if match:
            try:
                params[param_name] = float(match.group(1))
            except:
                pass
    
    return params


# ============================================================================
# NodalAnalysis Execution
# ============================================================================

def run_nodal_analysis(parameters: Dict) -> Dict:
    """
    Run nodal analysis with given parameters
    
    Args:
        parameters: Dictionary of nodal analysis parameters
        
    Returns:
        Dictionary with results or error
    """
    try:
        # Import the nodal analysis module
        from NodalAnalysis_module import calculate_nodal_analysis
        
        # Fill in missing parameters with defaults
        final_params = config.DEFAULT_NODAL_PARAMS.copy()
        final_params.update(parameters)
        
        # Run calculation
        results = calculate_nodal_analysis(final_params)
        
        return results
    
    except ImportError:
        return {
            'success': False,
            'error': 'NodalAnalysis module not found'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


# ============================================================================
# Complete Workflow
# ============================================================================

def process_nodal_query(query: str, documents: List[Dict], 
                       api_key: str = None) -> Optional[Dict]:
    """
    Complete workflow for nodal analysis queries
    
    Args:
        query: User's query
        documents: Retrieved documents
        api_key: Gemini API key
        
    Returns:
        Nodal analysis results or None if not applicable
    """
    # Check if nodal analysis is needed
    if not requires_nodal_analysis(query):
        if config.DEBUG_MODE:
            print("ℹ️  Query does not require nodal analysis")
        return None
    
    print("\n🔬 Nodal analysis required - extracting parameters...")
    
    # Try to extract parameters with Gemini first
    params = extract_parameters_with_gemini(documents, api_key)
    
    # Fallback to regex if Gemini extraction failed
    if not params:
        print("   Falling back to regex extraction...")
        params = extract_parameters_with_regex(documents)
    
    if params:
        print(f"   ✓ Extracted {len(params)} parameters")
        if config.DEBUG_MODE:
            for key, value in params.items():
                print(f"     - {key}: {value}")
    else:
        print("   ⚠️  No parameters extracted, using defaults")
    
    # Run nodal analysis
    print("   🔄 Running nodal analysis calculations...")
    results = run_nodal_analysis(params)
    
    if results.get('success'):
        print("   ✅ Nodal analysis completed successfully")
    else:
        print(f"   ❌ Nodal analysis failed: {results.get('error')}")
    
    return results
