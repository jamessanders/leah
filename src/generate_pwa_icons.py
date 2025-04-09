#!/usr/bin/env python3

"""
Generate PWA icons from an existing image.
This script creates the necessary icon files for a Progressive Web App.
"""

import os
from PIL import Image

def generate_icons(source_image_path, output_dir):
    """Generate PWA icons from a source image."""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Open the source image
    with Image.open(source_image_path) as img:
        # Convert to RGBA if not already
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Generate 192x192 icon
        icon_192 = img.resize((192, 192), Image.LANCZOS)
        icon_192.save(os.path.join(output_dir, 'icon-192.png'))
        
        # Generate 512x512 icon
        icon_512 = img.resize((512, 512), Image.LANCZOS)
        icon_512.save(os.path.join(output_dir, 'icon-512.png'))
        
        print(f"Icons generated successfully in {output_dir}")

if __name__ == '__main__':
    # Path to the source image
    source_image = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web', 'img', 'avatar.png')
    
    # Output directory
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web', 'img')
    
    # Generate icons
    generate_icons(source_image, output_dir) 