"""Parameter Manager - Manages parameter formatting and substitution."""

from typing import Dict, Any


def format_dict(d: Dict, ctx: Dict) -> Dict:
    """Return copy of dict with string values formatted using context.
    
    Args:
        d: Dictionary to format
        ctx: Context dictionary for string formatting
        
    Returns:
        Formatted dictionary
    """
    if not isinstance(d, dict):
        return d
    
    formatted = {}
    for k, v in d.items():
        if isinstance(v, str):
            try:
                formatted[k] = v.format(**ctx)
            except Exception:
                # If formatting fails, keep original value
                formatted[k] = v
        elif isinstance(v, dict):
            formatted[k] = format_dict(v, ctx)
        else:
            formatted[k] = v
    
    return formatted


def make_context(params: Dict, chain_data: Dict = None) -> Dict:
    """Build context dict from parameters and chain data.
    
    Args:
        params: Parameter dictionary
        chain_data: Optional chain execution data
        
    Returns:
        Context dictionary
    """
    ctx = {}
    
    if isinstance(params, dict):
        for k, v in params.items():
            name = k.lstrip('@')
            ctx[name] = v
    
    if chain_data:
        ctx.update(chain_data)
    
    return ctx
