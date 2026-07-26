import json
import hashlib
import zipfile
from pathlib import Path
from typing import Optional, Dict, Any

def export_style(slug: str, mode: str, output_path: str, profile_data: str, yaml_content: Optional[str] = None) -> str:
    """
    Exports a style to a .voice-style.zip archive containing:
    - profile.json
    - style.yaml (if provided)
    - manifest.json with SHA-256 checksums and metadata
    """
    profile_filename = "profile.json"
    yaml_filename = f"{slug}.yaml"
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Write profile
        zf.writestr(profile_filename, profile_data)
        
        # Compute checksums
        checksums = {
            profile_filename: hashlib.sha256(profile_data.encode('utf-8')).hexdigest()
        }
        
        # Write yaml if exists
        if yaml_content:
            zf.writestr(yaml_filename, yaml_content)
            checksums[yaml_filename] = hashlib.sha256(yaml_content.encode('utf-8')).hexdigest()
            
        manifest = {
            "slug": slug,
            "mode": mode,
            "schema_version": "1.0",
            "checksums": checksums
        }
        
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        
    return output_path


def import_style(zip_path: str, extract_to: str) -> Dict[str, Any]:
    """
    Imports a style from a .voice-style.zip archive.
    Validates:
    - manifest.json existence
    - SHA-256 checksums
    - Path traversal prevention
    """
    extract_dir = Path(extract_to)
    
    with zipfile.ZipFile(zip_path, 'r') as zf:
        namelist = zf.namelist()
        
        if "manifest.json" not in namelist:
            raise ValueError("Invalid archive: manifest.json is missing.")
            
        # Prevent path traversal
        for name in namelist:
            # Check for absolute paths or path traversal syntax
            if name.startswith('/') or name.startswith('\\') or '..' in name:
                raise ValueError(f"Invalid archive: path traversal detected in {name}")
                
        # Read and parse manifest
        manifest_data = zf.read("manifest.json")
        try:
            manifest = json.loads(manifest_data)
        except json.JSONDecodeError:
            raise ValueError("Invalid archive: manifest.json is not valid JSON")
            
        checksums = manifest.get("checksums", {})
        
        # Validate checksums
        for filename, expected_hash in checksums.items():
            if filename not in namelist:
                raise ValueError(f"Missing file declared in manifest: {filename}")
            
            file_data = zf.read(filename)
            actual_hash = hashlib.sha256(file_data).hexdigest()
            
            if actual_hash != expected_hash:
                raise ValueError(f"Checksum mismatch for {filename}. Expected {expected_hash}, got {actual_hash}")
                
        # Extract files safely
        for name in namelist:
            if name != "manifest.json":
                # Ensure extract path is safely within the target directory
                target_path = (extract_dir / name).resolve()
                if not str(target_path).startswith(str(extract_dir.resolve())):
                    raise ValueError(f"Security error: extract path {target_path} is outside {extract_dir}")
                
                # Create parent dirs if necessary
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(target_path, 'wb') as f:
                    f.write(zf.read(name))
                    
        return manifest
