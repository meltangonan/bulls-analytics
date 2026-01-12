"""Instagram-ready graphics using Pillow."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from typing import Optional

from bulls.config import (
    BULLS_RED, BULLS_BLACK, WHITE, DARK_BG, GRAY,
    INSTAGRAM_PORTRAIT, OUTPUT_DIR, FONTS_DIR
)


def load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a font, with fallback to default."""
    font_paths = [
        FONTS_DIR / f"{name}.ttf",
        FONTS_DIR / f"{name}-Regular.ttf",
    ]
    
    for path in font_paths:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    
    # Fallback
    return ImageFont.load_default()


def create_graphic(
    title: str,
    subtitle: str = "",
    stats: dict = None,
    player_name: str = "",
    player_image: Optional[Image.Image] = None,
    footer: str = "@bullsanalytics",
    size: tuple = INSTAGRAM_PORTRAIT,
    save_path: Optional[str] = None,
) -> Image.Image:
    """
    Create an Instagram-ready graphic.
    
    This is a flexible template - customize as needed.
    
    Args:
        title: Main headline
        subtitle: Secondary text
        stats: Dict of stats to display (e.g., {'PTS': 28, 'REB': 5})
        player_name: Player's name to display
        player_image: PIL Image of player headshot
        footer: Attribution text
        size: Image dimensions
        save_path: Path to save (optional)
    
    Returns:
        PIL Image object
    
    Example:
        >>> img = create_graphic(
        ...     title="CLUTCH PERFORMANCE",
        ...     subtitle="Bulls vs Heat • Jan 10, 2026",
        ...     stats={'PTS': 28, 'REB': 5, 'AST': 7},
        ...     player_name="COBY WHITE",
        ...     save_path="output/coby_clutch.png"
        ... )
    """
    # Create canvas
    img = Image.new('RGB', size, DARK_BG)
    draw = ImageDraw.Draw(img)
    
    # Load fonts
    font_title = load_font("BebasNeue", 72)
    font_subtitle = load_font("Inter", 28)
    font_name = load_font("BebasNeue", 56)
    font_stat_value = load_font("BebasNeue", 64)
    font_stat_label = load_font("Inter", 20)
    font_footer = load_font("Inter", 18)
    
    width, height = size
    y_cursor = 80
    
    # Title
    bbox = draw.textbbox((0, 0), title, font=font_title)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) // 2, y_cursor), title, font=font_title, fill=WHITE)
    y_cursor += 90
    
    # Subtitle
    if subtitle:
        bbox = draw.textbbox((0, 0), subtitle, font=font_subtitle)
        text_width = bbox[2] - bbox[0]
        draw.text(((width - text_width) // 2, y_cursor), subtitle, font=font_subtitle, fill=GRAY)
        y_cursor += 60
    
    # Player section
    if player_image or player_name:
        y_cursor += 40
        
        # Player image (if provided)
        if player_image:
            # Resize and paste
            img_size = 250
            player_image = player_image.resize((img_size, img_size), Image.Resampling.LANCZOS)
            paste_x = (width - img_size) // 2
            
            # Create circular mask
            mask = Image.new('L', (img_size, img_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, img_size, img_size), fill=255)
            
            img.paste(player_image, (paste_x, y_cursor), mask)
            y_cursor += img_size + 30
        
        # Player name
        if player_name:
            bbox = draw.textbbox((0, 0), player_name, font=font_name)
            text_width = bbox[2] - bbox[0]
            draw.text(((width - text_width) // 2, y_cursor), player_name, font=font_name, fill=WHITE)
            y_cursor += 70
    
    # Stats
    if stats:
        y_cursor += 30
        stat_spacing = width // (len(stats) + 1)
        
        for i, (label, value) in enumerate(stats.items()):
            x = stat_spacing * (i + 1)
            
            # Value
            value_text = str(value)
            bbox = draw.textbbox((0, 0), value_text, font=font_stat_value)
            text_width = bbox[2] - bbox[0]
            draw.text((x - text_width // 2, y_cursor), value_text, font=font_stat_value, fill=BULLS_RED)
            
            # Label
            bbox = draw.textbbox((0, 0), label, font=font_stat_label)
            text_width = bbox[2] - bbox[0]
            draw.text((x - text_width // 2, y_cursor + 65), label, font=font_stat_label, fill=GRAY)
    
    # Footer
    bbox = draw.textbbox((0, 0), footer, font=font_footer)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) // 2, height - 50), footer, font=font_footer, fill=GRAY)
    
    # Save if path provided
    if save_path:
        OUTPUT_DIR.mkdir(exist_ok=True)
        save_path = Path(save_path)
        img.save(save_path, "PNG")
        print(f"Saved to {save_path}")
    
    return img
