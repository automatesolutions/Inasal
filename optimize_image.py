"""Script to optimize the background image for web"""

import os
from pathlib import Path

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("Pillow (PIL) not installed. Install it with: pip install Pillow")

def optimize_image(input_path: str, output_path: str, max_width: int = 1920, quality: int = 85):
    """Optimize image for web use"""
    if not HAS_PIL:
        print("Cannot optimize - Pillow not installed")
        return False
    
    try:
        # Open image
        img = Image.open(input_path)
        
        # Get original size
        original_size = os.path.getsize(input_path) / (1024 * 1024)  # MB
        
        # Calculate new dimensions maintaining aspect ratio
        width, height = img.size
        # Scale to optimal size for web backgrounds
        if width < 1200:
            # Scale up small images moderately for better quality (but not too much to keep file size reasonable)
            scale_factor = min(1200 / width, 800 / height, 1.5)  # Max 1.5x scale for reasonable file size
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        elif width > max_width:
            # Scale down large images
            ratio = max_width / width
            new_width = max_width
            new_height = int(height * ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Convert to RGB if necessary (removes alpha channel if present)
        if img.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = rgb_img
        
        # Save optimized image
        img.save(output_path, 'JPEG', quality=quality, optimize=True, progressive=True)
        
        new_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
        reduction = ((original_size - new_size) / original_size) * 100
        
        print(f"✅ Image optimized!")
        print(f"   Original: {original_size:.2f} MB ({width}x{height})")
        print(f"   Optimized: {new_size:.2f} MB ({img.size[0]}x{img.size[1]})")
        print(f"   Size reduction: {reduction:.1f}%")
        
        return True
    except Exception as e:
        print(f"❌ Error optimizing image: {e}")
        return False

if __name__ == "__main__":
    # Paths
    input_image = Path("Assets/BcolodinsalFI.jpg")
    output_image = Path("frontend/public/BcolodinsalFI.jpg")
    
    if not input_image.exists():
        print(f"❌ Source image not found: {input_image}")
        exit(1)
    
    print(f"📸 Optimizing image: {input_image}")
    print(f"   Output: {output_image}")
    print()
    
    # Create output directory if needed
    output_image.parent.mkdir(parents=True, exist_ok=True)
    
    # Optimize image
    success = optimize_image(
        str(input_image),
        str(output_image),
        max_width=1920,  # Max width for web (Full HD)
        quality=85       # Good quality balance
    )
    
    if success:
        print(f"\n✅ Optimized image saved to: {output_image}")
    else:
        print(f"\n❌ Failed to optimize image")

