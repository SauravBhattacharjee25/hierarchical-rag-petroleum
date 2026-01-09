"""
NodalAnalysis Module (Refactored)
Well production capacity calculation using nodal analysis
Converted from standalone script to importable module
"""

import math
import numpy as np
from typing import Dict, List, Tuple, Optional


# ============================================================================
# Core Calculation Functions
# ============================================================================

def swamee_jain(Re: float, D: float, roughness: float) -> float:
    """
    Calculate friction factor using Swamee-Jain equation
    
    Args:
        Re: Reynolds number
        D: Pipe diameter (m)
        roughness: Pipe roughness (m)
        
    Returns:
        Friction factor
    """
    if Re <= 0:
        return 0.0
    return 0.25 / (math.log10((roughness/(3.7*D)) + (5.74/(Re**0.9))))**2


def pump_interp(flow: float, pump_curve: Dict, key: str) -> float:
    """
    Interpolate pump curve data
    
    Args:
        flow: Flow rate (m3/hr)
        pump_curve: Dictionary with 'flow' and 'head' lists
        key: Key to interpolate ('head' typically)
        
    Returns:
        Interpolated value
    """
    return np.interp(flow, pump_curve["flow"], pump_curve[key])


def calculate_vlp(flow_m3hr: float, segments: List[Tuple], 
                  wellhead_pressure: float, esp_depth: float,
                  pump_curve: Dict, rho: float, mu: float, 
                  g: float, roughness: float) -> float:
    """
    Calculate Vertical Lift Performance (VLP)
    
    Args:
        flow_m3hr: Flow rate in m3/hr
        segments: Well trajectory segments [(L, D, theta), ...]
        wellhead_pressure: Wellhead pressure (bar)
        esp_depth: ESP intake depth (m)
        pump_curve: Pump curve dictionary
        rho: Fluid density (kg/m3)
        mu: Viscosity (Pa.s)
        g: Gravity (m/s2)
        roughness: Pipe roughness (m)
        
    Returns:
        Bottomhole pressure (bar)
    """
    q = flow_m3hr / 3600.0  # m3/hr to m3/s
    dp_total = 0.0
    depth_accum = 0.0
    
    for (L, D, theta) in segments:
        A = math.pi * D**2 / 4.0
        u = q / A
        Re = rho * abs(u) * D / mu
        f = swamee_jain(Re, D, roughness)
        
        dp_fric = f * (L/D) * (rho * u**2 / 2.0)
        dp_grav = rho * g * L * math.sin(theta)
        dp_total += dp_fric + dp_grav
        depth_accum += L * math.sin(theta)
    
    # Apply ESP pump if depth sufficient
    if depth_accum >= esp_depth and pump_curve:
        dp_total -= rho * g * pump_interp(flow_m3hr, pump_curve, "head")
    
    return wellhead_pressure + dp_total/1e5


def calculate_ipr(flow_m3hr: float, reservoir_pressure: float, PI: float) -> float:
    """
    Calculate Inflow Performance Relationship (IPR)
    
    Args:
        flow_m3hr: Flow rate in m3/hr
        reservoir_pressure: Reservoir pressure (bar)
        PI: Productivity Index (m3/hr per bar)
        
    Returns:
        Bottomhole pressure (bar)
    """
    pbh = reservoir_pressure - flow_m3hr / PI
    return max(pbh, 0.0)


def process_well_trajectory(well_trajectory: List[Dict]) -> List[Tuple]:
    """
    Process well trajectory into segments for calculation
    
    Args:
        well_trajectory: List of dicts with MD, TVD, ID
        
    Returns:
        List of segments (L, D, theta)
    """
    segments = []
    for i in range(1, len(well_trajectory)):
        MD = well_trajectory[i]["MD"] - well_trajectory[i-1]["MD"]
        TVD = well_trajectory[i]["TVD"] - well_trajectory[i-1]["TVD"]
        D = well_trajectory[i]["ID"]
        L = MD
        theta = math.atan2(TVD, MD) if MD != 0 else 0.0
        segments.append((L, D, theta))
    return segments


# ============================================================================
# Main Nodal Analysis Function
# ============================================================================

def calculate_nodal_analysis(parameters: Dict) -> Dict:
    """
    Perform nodal analysis calculation with given parameters
    
    Args:
        parameters: Dictionary containing:
            - rho: Fluid density (kg/m3)
            - mu: Viscosity (Pa.s)
            - g: Gravity (m/s2)
            - roughness: Pipe roughness (m)
            - reservoir_pressure: Reservoir pressure (bar)
            - wellhead_pressure: Wellhead pressure (bar)
            - PI: Productivity Index (m3/hr per bar)
            - esp_depth: ESP intake depth (m)
            - well_trajectory: List of dicts with MD, TVD, ID
            - pump_curve: Dict with 'flow' and 'head' lists (optional)
            
    Returns:
        Dictionary with calculation results:
            - success: bool
            - flowrate: float (m3/hr)
            - bottomhole_pressure: float (bar)
            - pump_head: float (m)
            - error: str (if failed)
            - parameters_used: dict
    """
    try:
        # Extract parameters with defaults
        rho = parameters.get('rho', 1000.0)
        mu = parameters.get('mu', 1e-3)
        g = parameters.get('g', 9.81)
        roughness = parameters.get('roughness', 1e-5)
        reservoir_pressure = parameters.get('reservoir_pressure', 230.0)
        wellhead_pressure = parameters.get('wellhead_pressure', 10.0)
        PI = parameters.get('PI', 5.0)
        esp_depth = parameters.get('esp_depth', 500.0)
        
        # Well trajectory
        well_trajectory = parameters.get('well_trajectory', [
            {"MD": 0.0,    "TVD": 0.0,    "ID": 0.3397},
            {"MD": 500.0,  "TVD": 500.0,  "ID": 0.2445},
            {"MD": 1500.0, "TVD": 1500.0, "ID": 0.1778},
            {"MD": 2500.0, "TVD": 2500.0, "ID": 0.1778},
        ])
        
        # Pump curve
        pump_curve = parameters.get('pump_curve', {
            "flow": [0, 100, 200, 300, 400],
            "head": [600, 550, 450, 300, 100],
        })
        
        # Process trajectory
        segments = process_well_trajectory(well_trajectory)
        
        # Calculate VLP and IPR curves
        flows = np.linspace(1, 400, 200)
        p_vlp = np.array([
            calculate_vlp(f, segments, wellhead_pressure, esp_depth, 
                         pump_curve, rho, mu, g, roughness)
            for f in flows
        ])
        p_ipr = np.array([
            calculate_ipr(f, reservoir_pressure, PI)
            for f in flows
        ])
        
        # Find operating point (intersection)
        diff = np.abs(p_vlp - p_ipr)
        idx = np.argmin(diff)
        
        # Check if solution is valid (within tolerance)
        if diff[idx] < 3.0:  # 3 bar tolerance
            sol_flow = float(flows[idx])
            sol_pbh = float(p_vlp[idx])
            sol_head = float(pump_interp(sol_flow, pump_curve, "head"))
            
            return {
                'success': True,
                'flowrate': round(sol_flow, 2),
                'bottomhole_pressure': round(sol_pbh, 2),
                'pump_head': round(sol_head, 1),
                'parameters_used': {
                    'reservoir_pressure': reservoir_pressure,
                    'wellhead_pressure': wellhead_pressure,
                    'PI': PI,
                    'esp_depth': esp_depth,
                    'fluid_density': rho,
                    'viscosity': mu
                }
            }
        else:
            return {
                'success': False,
                'error': 'No intersection found between VLP and IPR curves',
                'min_difference': float(diff[idx])
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': f'Calculation error: {str(e)}'
        }


# ============================================================================
# Validation Function
# ============================================================================

def validate_parameters(parameters: Dict) -> Tuple[bool, Optional[str]]:
    """
    Validate nodal analysis parameters
    
    Args:
        parameters: Parameter dictionary
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check critical parameters
    if 'well_trajectory' in parameters:
        traj = parameters['well_trajectory']
        for i, point in enumerate(traj):
            if 'MD' not in point or 'TVD' not in point or 'ID' not in point:
                return False, f"Well trajectory point {i} missing required fields"
            
            # Sanity check: MD >= TVD
            if point['MD'] < point['TVD']:
                return False, f"Invalid trajectory: MD < TVD at point {i}"
            
            # Check for realistic diameters
            if point['ID'] <= 0 or point['ID'] > 2.0:  # 0-2m reasonable range
                return False, f"Unrealistic inner diameter at point {i}: {point['ID']}m"
    
    # Check physical parameters
    if 'rho' in parameters and parameters['rho'] <= 0:
        return False, "Fluid density must be positive"
    
    if 'mu' in parameters and parameters['mu'] <= 0:
        return False, "Viscosity must be positive"
    
    if 'PI' in parameters and parameters['PI'] <= 0:
        return False, "Productivity Index must be positive"
    
    return True, None


# ============================================================================
# Test/Demo Function (for standalone use)
# ============================================================================

def run_demo():
    """Run a demo calculation with default parameters"""
    print("=" * 70)
    print("NodalAnalysis Demo Calculation")
    print("=" * 70)
    
    # Default parameters
    params = {
        'rho': 1000.0,
        'mu': 1e-3,
        'g': 9.81,
        'roughness': 1e-5,
        'reservoir_pressure': 230.0,
        'wellhead_pressure': 10.0,
        'PI': 5.0,
        'esp_depth': 500.0,
        'well_trajectory': [
            {"MD": 0.0,    "TVD": 0.0,    "ID": 0.3397},
            {"MD": 500.0,  "TVD": 500.0,  "ID": 0.2445},
            {"MD": 1500.0, "TVD": 1500.0, "ID": 0.1778},
            {"MD": 2500.0, "TVD": 2500.0, "ID": 0.1778},
        ],
        'pump_curve': {
            "flow": [0, 100, 200, 300, 400],
            "head": [600, 550, 450, 300, 100],
        }
    }
    
    # Validate
    is_valid, error = validate_parameters(params)
    if not is_valid:
        print(f"❌ Parameter validation failed: {error}")
        return
    
    # Calculate
    results = calculate_nodal_analysis(params)
    
    # Display results
    print("\nResults:")
    if results['success']:
        print(f"✅ Solution found:")
        print(f"   Flowrate: {results['flowrate']} m³/hr")
        print(f"   Bottomhole pressure: {results['bottomhole_pressure']} bar")
        print(f"   Pump head: {results['pump_head']} m")
    else:
        print(f"❌ Calculation failed: {results['error']}")
    
    print("=" * 70)


if __name__ == "__main__":
    # Run demo if executed directly
    run_demo()
