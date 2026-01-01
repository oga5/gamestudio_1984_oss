"""
Asset Tracker for GameStudio 1984 v0.4

Tracks successfully created assets and provides context for programmer agent.
"""

import os
import glob


class AssetTracker:
    """Track successfully created assets."""

    def __init__(self, asset_dir: str = "/public/assets"):
        self.asset_dir = asset_dir
        self.created_images = []
        self.created_sounds = []
        self.project_root = os.environ.get("PROJECT_ROOT", "/")

    def scan_assets(self):
        """Scan and record existing assets."""
        full_asset_dir = os.path.join(self.project_root, self.asset_dir.lstrip("/"))

        # Scan images
        images_dir = os.path.join(full_asset_dir, "images")
        if os.path.exists(images_dir):
            self.created_images = glob.glob(os.path.join(images_dir, "*.png"))
            # Convert to relative paths
            self.created_images = [
                os.path.relpath(f, self.project_root) for f in self.created_images
            ]

        # Scan sounds
        sounds_dir = os.path.join(full_asset_dir, "sounds")
        if os.path.exists(sounds_dir):
            self.created_sounds = glob.glob(os.path.join(sounds_dir, "*.wav"))
            # Convert to relative paths
            self.created_sounds = [
                os.path.relpath(f, self.project_root) for f in self.created_sounds
            ]

    def get_asset_count(self) -> dict:
        """Get count of assets."""
        return {
            "images": len(self.created_images),
            "sounds": len(self.created_sounds),
            "total": len(self.created_images) + len(self.created_sounds)
        }

    def get_asset_context(self) -> str:
        """
        Return context string for programmer agent.

        This string should be injected into the programmer's prompt to ensure
        they only use assets that actually exist.
        """
        if not self.created_images and not self.created_sounds:
            return """
## Available Assets (USE ONLY THESE)

WARNING: No assets found! Verify that asset creation phase is complete.

### Images
- (none)

### Sounds
- (none)

CRITICAL: Do NOT reference any assets! Wait for assets to be created first.
"""

        context = """
## Available Assets (USE ONLY THESE)

The following assets have been created and validated. ONLY use these assets in your code.

### Images
"""
        if self.created_images:
            for img in sorted(self.created_images):
                # Get just the filename for cleaner display
                filename = os.path.basename(img)
                context += f"- {filename}\n"
        else:
            context += "- (none)\n"

        context += "\n### Sounds\n"
        if self.created_sounds:
            for snd in sorted(self.created_sounds):
                # Get just the filename for cleaner display
                filename = os.path.basename(snd)
                context += f"- {filename}\n"
        else:
            context += "- (none)\n"

        context += "\nCRITICAL: Do NOT reference any assets not listed above!\n"

        return context

    def validate_all_assets(self) -> dict:
        """
        Validate all tracked assets.

        Returns:
            Dict with validation results
        """
        results = {
            "valid": [],
            "invalid": [],
            "missing": []
        }

        full_asset_dir = os.path.join(self.project_root, self.asset_dir.lstrip("/"))

        # Check images
        for img_path in self.created_images:
            full_path = os.path.join(self.project_root, img_path)
            if not os.path.exists(full_path):
                results["missing"].append(img_path)
                continue

            # Check PNG header
            try:
                with open(full_path, 'rb') as f:
                    header = f.read(8)
                png_header = b'\x89PNG\r\n\x1a\n'
                if header == png_header:
                    results["valid"].append(img_path)
                else:
                    results["invalid"].append(img_path)
            except Exception:
                results["invalid"].append(img_path)

        # Check sounds
        for snd_path in self.created_sounds:
            full_path = os.path.join(self.project_root, snd_path)
            if not os.path.exists(full_path):
                results["missing"].append(snd_path)
                continue

            # Check WAV header
            try:
                with open(full_path, 'rb') as f:
                    header = f.read(12)
                if header[:4] == b'RIFF' and header[8:12] == b'WAVE':
                    results["valid"].append(snd_path)
                else:
                    results["invalid"].append(snd_path)
            except Exception:
                results["invalid"].append(snd_path)

        return results

    def get_validation_summary(self) -> str:
        """Get summary of asset validation."""
        results = self.validate_all_assets()

        summary = f"Asset Validation Results:\n"
        summary += f"- Valid: {len(results['valid'])}\n"
        summary += f"- Invalid: {len(results['invalid'])}\n"
        summary += f"- Missing: {len(results['missing'])}\n"

        if results["invalid"]:
            summary += "\nInvalid assets (will be renamed to .err):\n"
            for asset in results["invalid"]:
                summary += f"- {asset}\n"

        if results["missing"]:
            summary += "\nMissing assets:\n"
            for asset in results["missing"]:
                summary += f"- {asset}\n"

        if len(results["valid"]) == len(self.created_images) + len(self.created_sounds):
            summary += "\n✓ All assets are valid!"
        else:
            summary += "\n✗ Some assets have issues. Asset creation phase may need to be re-run."

        return summary
