#!/usr/bin/env python3
"""
Generate Python protobuf bindings for Mantis.

This script generates Python code from our protobuf definitions,
including proper imports and dependencies.
"""

import subprocess
import sys
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

    # Set up include paths - find googleapis dynamically
    import google.api.annotations_pb2  # Import a specific proto module
    import grpc_tools

    # Find the google package location from a specific proto file
    google_package_path = Path(google.api.annotations_pb2.__file__).parents[2]  # Go up to site-packages level
    grpc_tools_proto_path = Path(grpc_tools.__file__).parent / "_proto"

    include_paths = [
        str(proto_dir),
        str(project_root / "third_party" / "A2A" / "specification" / "grpc"),
        str(project_root / "third_party" / "a2a-registry" / "proto"),
        str(google_package_path),  # This includes google/api/* protos
        str(grpc_tools_proto_path),  # This includes google/protobuf/* protos
    ]

    print(f"Google package path: {google_package_path}")
    print(f"GRPC tools proto path: {grpc_tools_proto_path}")

    # Proto files to generate
    proto_files = [
        "validate/validate.proto",  # Generate validation support first
        "mantis/v1/mantis_core.proto",
        "mantis/v1/mantis_service.proto",
        "mantis/v1/mantis_persona.proto",
        "mantis/v1/prompt_composition.proto",
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
            f"--pyi_out={output_dir}",  # Generate type stubs
        ]

        # Add include paths
        for include_path in include_paths:
            if Path(include_path).exists():
                cmd.extend(["-I", include_path])

        # Add the proto file
        cmd.append(str(proto_path))

        # Run the command
        if not run_command(cmd, cwd=project_root):
            print(f"Failed to generate {proto_file}")
            return 1

    # Generate A2A dependencies if needed
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

            # Add include paths
            for include_path in include_paths:
                if Path(include_path).exists():
                    cmd.extend(["-I", include_path])

            cmd.append(str(dep_proto))

            print(f"Generating dependency: {dep_proto.name}")
            if not run_command(cmd, cwd=project_root):
                print(f"Warning: Failed to generate {dep_proto.name}")

    print("✅ Protobuf generation completed!")
    print(f"Generated files in: {output_dir}")

    # Fix imports to use relative imports for generated modules in the same package
    def fix_imports():
        """Fix absolute imports to relative imports for generated pb2 modules."""
        print("🔧 Fixing imports in generated files...")

        if not output_dir.exists():
            return

        pb2_files = list(output_dir.rglob("*_pb2.py"))
        grpc_files = list(output_dir.rglob("*_pb2_grpc.py"))
        all_files = pb2_files + grpc_files

        if not all_files:
            print("⚠️  No generated files found to fix")
            return

        # Build a mapping of module names to their relative paths
        pb2_modules = {}
        for f in pb2_files:
            # Get relative path from output_dir
            rel_path = f.relative_to(output_dir)
            pb2_modules[f.stem] = rel_path.parent

        for proto_file in all_files:
            print(f"  Fixing imports in {proto_file.name}")

            # Read the file
            content = proto_file.read_text()
            original_content = content

            # Get the directory of this proto file relative to output_dir
            proto_file_dir = proto_file.relative_to(output_dir).parent

            # Fix specific validate import (only for files in mantis/v1 subdirectory)
            if "mantis/v1" in str(proto_file):
                content = content.replace(
                    "from validate import validate_pb2 as validate_dot_validate__pb2",
                    "from ...validate import validate_pb2 as validate_dot_validate__pb2",
                )

            # Fix imports for each pb2 module (skip validate_pb2 as it's handled above)
            for module_name, module_dir in pb2_modules.items():
                if (
                    module_name != proto_file.stem and module_name != "validate_pb2"
                ):  # Don't fix self-imports or validate
                    # Calculate the relative import path
                    if module_dir == proto_file_dir:
                        # Same directory - use simple relative import
                        import_pattern = f"import {module_name} as"
                        relative_import = f"from . import {module_name} as"
                        content = content.replace(import_pattern, relative_import)
                    elif module_dir == Path("."):
                        # Module is in root, we're in subdirectory - need to go up
                        dots = "." + "." * len(proto_file_dir.parts)  # One dot per directory level up
                        import_pattern = f"import {module_name} as"
                        relative_import = f"from {dots} import {module_name} as"
                        content = content.replace(import_pattern, relative_import)

            # Fix mantis.v1 imports to be relative within the same package
            if "mantis/v1" in str(proto_file):
                # Fix broken double imports first
                content = content.replace("from mantis.v1 from . import", "from . import")
                # Then fix regular mantis.v1 imports
                content = content.replace("from mantis.v1 import", "from . import")

            # Write back if changed
            if content != original_content:
                proto_file.write_text(content)
                print(f"    ✅ Fixed imports in {proto_file.name}")
            else:
                print(f"    ℹ️  No imports to fix in {proto_file.name}")

    fix_imports()

    # List generated files
    if output_dir.exists():
        generated_files = list(output_dir.rglob("*.py"))
        if generated_files:
            print("\nGenerated files:")
            for f in sorted(generated_files):
                # Show relative path from output_dir
                rel_path = f.relative_to(output_dir)
                print(f"  - {rel_path}")
        else:
            print("⚠️  No Python files were generated")

    return 0


if __name__ == "__main__":
    sys.exit(main())
