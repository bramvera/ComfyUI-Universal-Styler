"""
ComfyUI Universal Styler - NAI Prompt Script Database Management
Kore Teknology - https://github.com/KoreTeknology/ComfyUI-Universal-Styler
Release 0.6.0 (26/07/2025) - Updated for ComfyUI 2025 compatibility

Custom nodes for managing prompt scripts, agents, scenes, motions, cameras, 
lighting, and styles through CSV databases for NAI prompting workflows.
"""

__version__ = "0.6.0"
__title__ = "Universal Styler"
__description__ = "NAI Prompt Script Database Management for ComfyUI"
__author__ = "Kore Teknology"
__keywords__ = ["universal", "styler", "NAI", "prompt", "database", "CSV", "agents", "scenes"]

# Robust import handling for both relative and absolute contexts
try:
    # Try relative import first (ComfyUI context)
    from .scripts_pipeline import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
except ImportError:
    # Fallback to absolute import 
    try:
        from scripts_pipeline import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
    except ImportError:
        # Last resort - import the file directly
        import os
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        import scripts_pipeline
        NODE_CLASS_MAPPINGS = scripts_pipeline.NODE_CLASS_MAPPINGS
        NODE_DISPLAY_NAME_MAPPINGS = scripts_pipeline.NODE_DISPLAY_NAME_MAPPINGS

# Web UI integration directory (optional)
WEB_DIRECTORY = "./web"

# Export all required variables for ComfyUI compatibility  
__all__ = [
    "NODE_CLASS_MAPPINGS", 
    "NODE_DISPLAY_NAME_MAPPINGS",
    "WEB_DIRECTORY"
]