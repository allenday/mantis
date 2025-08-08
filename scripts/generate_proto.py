#!/usr/bin/env python3
"""
Generate Python protobuf bindings for Mantis.

Simple, clean proto generation with proper import fixing.
"""

import subprocess
import sys
import re
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run a shell command and return the result."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    if result.stdout:
        print(result.stdout)
    return True


def fix_imports(proto_file, output_dir):
    """Fix malformed imports in generated proto files."""
    content = proto_file.read_text()
    original_content = content
    
    # Fix the specific malformed pattern: "from a2a.v1 from ... import"
    content = re.sub(
        r'from\s+a2a\.v1\s+from\s+\.\.\.\s+import\s+([a-zA-Z0-9_]+)\s+as\s+([a-zA-Z0-9_]+)',
        r'from ... import \1 as \2',
        content
    )
    
    # Fix absolute imports that should be relative 
    if 'mantis/v1' in str(proto_file):
        # For nested files, use ... to go up to mantis.proto
        content = re.sub(
            r'^import\s+([a-zA-Z0-9_]+_pb2)\s+as\s+([a-zA-Z0-9_]+)',
            r'from ... import \1 as \2',
            content,
            flags=re.MULTILINE
        )
    elif proto_file.parent == output_dir:
        # For root level files, use relative imports within the same package
        content = re.sub(
            r'^import\s+([a-zA-Z0-9_]+_pb2)\s+as\s+([a-zA-Z0-9_]+)',
            r'from . import \1 as \2',
            content,
            flags=re.MULTILINE
        )
    
    # Fix validate imports for nested files
    if 'mantis/v1' in str(proto_file):
        # Fix remaining absolute validate imports
        content = re.sub(
            r'^from validate import validate_pb2 as validate_dot_validate__pb2',
            r'from ...validate import validate_pb2 as validate_dot_validate__pb2',
            content,
            flags=re.MULTILINE
        )
    
    # Write back if changed
    if content != original_content:
        proto_file.write_text(content)
        print(f"    ✅ Fixed imports in {proto_file.name}")
        return True
    else:
        print(f"    ℹ️  No imports to fix in {proto_file.name}")
        return False


def test_imports(output_dir):
    """Test that generated proto files can be imported."""
    print("🧪 Testing imports...")
    
    pb2_files = list(output_dir.glob("*_pb2.py"))
    if not pb2_files:
        print("⚠️  No _pb2.py files found to test")
        return True
        
    # Test root level files only for now
    import sys
    import importlib.util
    
    proto_package_path = str(output_dir.parent)  # src/mantis
    if proto_package_path not in sys.path:
        sys.path.insert(0, proto_package_path)
        
    success = True
    for pb2_file in pb2_files:
        module_name = f"mantis.proto.{pb2_file.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, pb2_file)
            if spec is None or spec.loader is None:
                continue
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            print(f"  ✅ Successfully imported {pb2_file.name}")
            
        except Exception as e:
            print(f"  ❌ Failed to import {pb2_file.name}: {str(e)}")
            success = False
            
    if proto_package_path in sys.path:
        sys.path.remove(proto_package_path)
        
    return success


def main():
    # Get project root
    project_root = Path(__file__).parent.parent
    proto_dir = project_root / "proto"
    output_dir = project_root / "src" / "mantis" / "proto"

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "__init__.py").touch()

    print(f"Project root: {project_root}")
    print(f"Proto dir: {proto_dir}")
    print(f"Output dir: {output_dir}")

    # Set up include paths
    import google.api.annotations_pb2
    import grpc_tools

    google_package_path = Path(google.api.annotations_pb2.__file__).parents[2]
    grpc_tools_proto_path = Path(grpc_tools.__file__).parent / "_proto"

    include_paths = [
        str(proto_dir),
        str(project_root / "third_party" / "A2A" / "specification" / "grpc"),
        str(project_root / "third_party" / "a2a-registry" / "proto"),
        str(google_package_path),
        str(grpc_tools_proto_path),
    ]

    # Proto files to generate - start with just validate and one simple file
    proto_files = [
        "validate/validate.proto",
        "mantis/v1/mantis_persona.proto",
    ]

    for proto_file in proto_files:
        proto_path = proto_dir / proto_file
        if not proto_path.exists():
            print(f"Warning: {proto_path} does not exist, skipping...")
            continue

        # Build protoc command
        cmd = [
            sys.executable,
            "-m",
            "grpc_tools.protoc",
            f"--python_out={output_dir}",
            f"--grpc_python_out={output_dir}",
            f"--pyi_out={output_dir}",
        ]

        # Add include paths
        for include_path in include_paths:
            if Path(include_path).exists():
                cmd.extend(["-I", include_path])

        cmd.append(str(proto_path))

        # Run the command
        if not run_command(cmd, cwd=project_root):
            print(f"Failed to generate {proto_file}")
            return 1

    # Generate A2A dependencies
    a2a_proto = project_root / "third_party" / "A2A" / "specification" / "grpc" / "a2a.proto"
    registry_proto = project_root / "third_party" / "a2a-registry" / "proto" / "registry.proto"

    for dep_proto in [a2a_proto, registry_proto]:
        if dep_proto.exists():
            cmd = [
                sys.executable,
                "-m",
                "grpc_tools.protoc",
                f"--python_out={output_dir}",
                f"--grpc_python_out={output_dir}",
                f"--pyi_out={output_dir}",
            ]

            for include_path in include_paths:
                if Path(include_path).exists():
                    cmd.extend(["-I", include_path])

            cmd.append(str(dep_proto))

            print(f"Generating dependency: {dep_proto.name}")
            if not run_command(cmd, cwd=project_root):
                print(f"Warning: Failed to generate {dep_proto.name}")

    print("✅ Protobuf generation completed!")
    
    # Fix imports
    print("🔧 Fixing imports...")
    pb2_files = list(output_dir.rglob("*_pb2.py"))
    for pb2_file in pb2_files:
        fix_imports(pb2_file, output_dir)
    
    # Test imports
    import_success = test_imports(output_dir)
    
    if not import_success:
        print("\n❌ Some imports failed.")
        return 1
    else:
        print("\n✅ All imports successful!")

    return 0


if __name__ == "__main__":
    sys.exit(main())