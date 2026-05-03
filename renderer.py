"""
Vehicle SVG Renderer

This module handles:
1. SVG parsing and rendering to PNG using CairoSVG
2. Visual enhancements (shadows, gradients, depth effects)
3. Proportional scaling to fit within max dimensions
4. Watermark application
"""

import io
import uuid
import base64
import logging
from typing import Optional, Tuple
from PIL import Image, ImageFilter, ImageEnhance, ImageDraw
import cairosvg

logger = logging.getLogger(__name__)


class VehicleRenderer:
    """
    Renderer for vehicle SVG illustrations with visual enhancement.
    
    Uses CairoSVG for high-quality SVG rendering, then applies
    visual enhancements using Pillow for post-processing.
    """
    
    # Default rendering parameters
    DEFAULT_DPI = 150
    MAX_DPI = 300
    
    # Visual enhancement defaults
    SHADOW_OPACITY = 0.25
    SHADOW_BLUR = 15
    SHADOW_OFFSET = (8, 12)
    SHADOW_COLOR = (0, 0, 0)
    
    # Gradient/enhancement defaults
    HIGHLIGHT_INTENSITY = 0.08
    AMBIENT_INTENSITY = 0.05
    
    # Watermark defaults
    WATERMARK_OPACITY = 0.4
    WATERMARK_MARGIN = 30
    WATERMARK_SCALE = 0.15  # Scale relative to image width
    
    def __init__(self):
        """Initialize the renderer."""
        logger.info("Initializing VehicleRenderer")
    
    def render(
        self,
        vehicle_svg: str,
        watermark_svg: Optional[str] = None,
        max_width: int = 800,
        max_height: int = 600
    ) -> bytes:
        """
        Main render pipeline.
        
        Args:
            vehicle_svg: The vehicle SVG as a string
            watermark_svg: Optional watermark SVG as string
            max_width: Maximum output width
            max_height: Maximum output height
            
        Returns:
            PNG image as bytes
        """
        # Step 1: Render SVG to PIL Image
        png_data = cairosvg.svg2png(
            bytestring=vehicle_svg.encode('utf-8'),
            output_width=None,  # Let Cairo determine
            output_height=None
        )
        
        vehicle_img = Image.open(io.BytesIO(png_data)).convert('RGBA')
        orig_width, orig_height = vehicle_img.size
        
        logger.info(f"Original SVG rendered: {orig_width}x{orig_height}")
        
        # Step 2: Apply visual enhancements
        vehicle_img = self._apply_visual_enhancements(vehicle_img)
        
        # Step 3: Scale to fit within max dimensions
        vehicle_img = self._scale_proportionally(vehicle_img, max_width, max_height)
        
        # Step 4: Apply watermark if provided
        if watermark_svg:
            vehicle_img = self._apply_watermark(vehicle_img, watermark_svg)
        
        # Step 5: Convert to optimized PNG
        output = io.BytesIO()
        vehicle_img.save(output, format='PNG', optimize=True)
        output.seek(0)
        
        return output.getvalue()
    
    def _apply_visual_enhancements(self, img: Image.Image) -> Image.Image:
        """
        Apply visual enhancements to make the vehicle look more polished and dimensional.
        
        Enhancements:
        - Soft ground shadow
        - Subtle edge enhancement
        - Controlled highlights
        """
        # Work with RGBA
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Create a copy for compositing
        result = img.copy()
        
        # Convert to RGB for processing (without alpha)
        rgb_img = img.convert('RGB')
        
        # 1. Apply subtle shadow beneath the vehicle
        shadow_img = self._create_ground_shadow(img)
        
        # 2. Blend shadow with vehicle
        result = Image.alpha_composite(shadow_img, result)
        
        # 3. Apply subtle edge enhancement
        result = self._apply_edge_enhancement(result)
        
        # 4. Apply subtle sharpening for crispness
        result = result.filter(ImageFilter.UnsharpMask(
            radius=1,
            percent=80,
            threshold=3
        ))
        
        logger.debug("Visual enhancements applied")
        return result
    
    def _create_ground_shadow(self, img: Image.Image) -> Image.Image:
        """
        Create a soft ground shadow beneath the vehicle.
        
        The shadow appears below the vehicle illustration to ground it.
        """
        width, height = img.size
        
        # Create transparent background
        shadow = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        
        # Get the bounding box of non-transparent content
        alpha = img.split()[-1]
        
        # Find the bottom area where shadow should be
        # Many vehicle SVGs have the vehicle centered, so we create shadow at bottom
        bbox = alpha.getbbox()
        
        if bbox:
            # Calculate shadow position: below the vehicle content
            left, top, right, bottom = bbox
            
            # Shadow area: below the vehicle, extending down
            shadow_top = bottom + 5
            shadow_bottom = min(height, bottom + self.SHADOW_BLUR + 15)
            
            if shadow_top < shadow_bottom:
                # Create elliptical shadow
                shadow_draw = ImageDraw.Draw(shadow)
                
                # Shadow bounds
                shadow_left = left + 20
                shadow_right = right - 20
                
                # Draw soft elliptical shadow
                shadow_box = [
                    shadow_left,
                    shadow_top,
                    shadow_right,
                    shadow_bottom
                ]
                
                # Draw shadow with gradient effect (achieved through blur)
                shadow_draw.ellipse(
                    shadow_box,
                    fill=(0, 0, 0, int(255 * self.SHADOW_OPACITY))
                )
                
                # Apply Gaussian blur for soft edges
                shadow = shadow.filter(ImageFilter.GaussianBlur(self.SHADOW_BLUR / 2))
        
        return shadow
    
    def _apply_edge_enhancement(self, img: Image.Image) -> Image.Image:
        """
        Apply subtle depth/ambient occlusion around edges.
        """
        # Convert to RGB for processing
        rgb = img.convert('RGB')
        
        # Apply slight contrast enhancement
        enhancer = ImageEnhance.Contrast(rgb)
        rgb = enhancer.enhance(1.05)
        
        # Apply slight sharpness
        enhancer = ImageEnhance.Sharpness(rgb)
        rgb = enhancer.enhance(1.03)
        
        # Convert back to RGBA
        result = rgb.convert('RGBA')
        
        # Preserve original alpha
        original_alpha = img.split()[-1]
        result.putalpha(original_alpha)
        
        return result
    
    def _scale_proportionally(
        self,
        img: Image.Image,
        max_width: int,
        max_height: int
    ) -> Image.Image:
        """
        Scale image to fit within max dimensions while preserving aspect ratio.
        
        This implements "fit inside box" scaling:
        - Preserve aspect ratio
        - Do not crop
        - Do not distort
        - Scale according to whichever constraint is reached first
        """
        width, height = img.size
        
        # Calculate scaling factors for each dimension
        width_ratio = max_width / width
        height_ratio = max_height / height
        
        # Use the smaller ratio to fit inside both constraints
        scale_ratio = min(width_ratio, height_ratio, 1.0)  # Don't upscale
        
        if scale_ratio < 1.0:
            new_width = int(width * scale_ratio)
            new_height = int(height * scale_ratio)
            
            # Use high-quality resampling
            img = img.resize(
                (new_width, new_height),
                Image.Resampling.LANCZOS
            )
            
            logger.debug(f"Scaled from {width}x{height} to {new_width}x{new_height}")
        
        return img
    
    def _apply_watermark(
        self,
        img: Image.Image,
        watermark_svg: str
    ) -> Image.Image:
        """
        Apply watermark to the image.
        
        Watermark is placed at bottom-right with sensible opacity.
        """
        # First render watermark SVG
        try:
            watermark_png = cairosvg.svg2png(
                bytestring=watermark_svg.encode('utf-8'),
                output_width=None,
                output_height=None
            )
            wm_img = Image.open(io.BytesIO(watermark_png)).convert('RGBA')
        except Exception as e:
            logger.warning(f"Failed to render watermark: {e}")
            return img  # Return original if watermark fails
        
        # Calculate watermark size (relative to output image)
        img_width, img_height = img.size
        target_wm_width = int(img_width * self.WATERMARK_SCALE)
        
        # Scale watermark proportionally
        wm_ratio = target_wm_width / wm_img.width
        target_wm_height = int(wm_img.height * wm_ratio)
        
        wm_img = wm_img.resize(
            (target_wm_width, target_wm_height),
            Image.Resampling.LANCZOS
        )
        
        # Apply watermark opacity
        wm_alpha = wm_img.split()[-1]
        wm_alpha = wm_alpha.point(
            lambda p: int(p * self.WATERMARK_OPACITY)
        )
        wm_img.putalpha(wm_alpha)
        
        # Calculate position (bottom-right with margin)
        x = img_width - target_wm_width - self.WATERMARK_MARGIN
        y = img_height - target_wm_height - self.WATERMARK_MARGIN
        
        # Ensure positive position
        x = max(self.WATERMARK_MARGIN, x)
        y = max(self.WATERMARK_MARGIN, y)
        
        # Create result image
        result = img.copy()
        
        # Paste watermark using alpha blending
        result.paste(wm_img, (x, y), wm_img)
        
        logger.debug(f"Watermark applied at ({x}, {y})")
        
        return result


def create_default_watermark() -> str:
    """
    Create a simple default watermark SVG.
    
    Returns a minimal watermark that can be used as placeholder.
    """
    return '''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="50" viewBox="0 0 200 50">
  <text x="100" y="35" font-family="Arial, sans-serif" font-size="24" 
        fill="#333" text-anchor="middle" opacity="0.5">RENDERED</text>
</svg>'''