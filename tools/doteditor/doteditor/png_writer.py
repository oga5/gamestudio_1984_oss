"""
PNG Writer
Writes image arrays to PNG files
"""
import numpy as np
from pathlib import Path
from typing import Optional

try:
    from PIL import Image
except ImportError:
    Image = None


class PNGWriter:
    """Writes pixel art images to PNG files"""

    def __init__(self):
        """Initialize the PNG writer"""
        if Image is None:
            raise ImportError(
                "PIL/Pillow is required for PNG writing. "
                "Install it with: pip install Pillow"
            )

    def write(self, filename: str, image_array: np.ndarray, scale: int = 1) -> None:
        """
        Write image array to PNG file

        Args:
            filename: Output PNG filename
            image_array: numpy array of shape (height, width, 4) with RGBA values
            scale: Scale factor for output (1=original size, 2=2x, etc.)

        Raises:
            ValueError: If image array is invalid
            IOError: If file cannot be written
        """
        # Validate image array
        if image_array.ndim != 3 or image_array.shape[2] != 4:
            raise ValueError(
                f"Invalid image array shape: {image_array.shape}. "
                f"Expected (height, width, 4)"
            )

        if image_array.dtype != np.uint8:
            raise ValueError(
                f"Invalid image array dtype: {image_array.dtype}. "
                f"Expected uint8"
            )

        # Validate scale
        if not isinstance(scale, int) or scale < 1:
            raise ValueError(f"Scale must be a positive integer, got: {scale}")

        # Create PIL Image
        height, width = image_array.shape[:2]
        img = Image.fromarray(image_array, mode='RGBA')

        # Scale if needed
        if scale > 1:
            new_width = width * scale
            new_height = height * scale
            # Use NEAREST for pixel art (no smoothing)
            img = img.resize((new_width, new_height), Image.NEAREST)

        # Ensure output directory exists
        output_path = Path(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write PNG
        try:
            img.save(filename, 'PNG', optimize=False)
        except Exception as e:
            raise IOError(f"Failed to write PNG file: {filename}") from e

    def write_with_info(
        self,
        filename: str,
        image_array: np.ndarray,
        scale: int = 1,
        quiet: bool = False
    ) -> dict:
        """
        Write image and return file info

        Args:
            filename: Output PNG filename
            image_array: numpy array of shape (height, width, 4) with RGBA values
            scale: Scale factor for output
            quiet: If True, suppress info output

        Returns:
            Dictionary with file information
        """
        self.write(filename, image_array, scale)

        # Get file info
        file_path = Path(filename)
        file_size = file_path.stat().st_size
        height, width = image_array.shape[:2]

        info = {
            'filename': filename,
            'original_size': (width, height),
            'output_size': (width * scale, height * scale),
            'scale': scale,
            'file_size': file_size,
            'file_size_kb': file_size / 1024
        }

        if not quiet:
            print(f"PNG file written: {filename}")
            print(f"  Original size: {width}x{height}")
            print(f"  Output size: {width*scale}x{height*scale}")
            print(f"  Scale: {scale}x")
            print(f"  File size: {file_size} bytes ({file_size/1024:.2f} KB)")

        return info
