import asyncio
import json
from backend.app.ai.engine import get_ai_engine

async def main():
    """
    Runs the AI engine to generate a Linktree clone.
    """
    spec = {
        "raw": "Create a Linktree clone. It should have a main page that displays a list of links. There should be an admin page where a user can add, edit, and delete links. The links should be stored in a database."
    }
    project_name = "Linktree Clone"

    print(f"Generating project: {project_name}")
    print(f"Specification: {spec['raw']}")

    ai_engine = get_ai_engine()
    
    # Use the multi-agent orchestrator to generate the project
    generated_files = await ai_engine.generate_project(spec, project_name)

    print(f"\nGenerated {len(generated_files)} files:")
    for file_path, content in generated_files.items():
        print(f"--- {file_path} ---")
        # Print first 10 lines of each file
        print('\n'.join(content.splitlines()[:10]))
        if len(content.splitlines()) > 10:
            print("...")
        print("-" * (len(file_path) + 8))

    # Save the generated files to a directory
    output_dir = "linktree_clone_output"
    import os
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for file_path, content in generated_files.items():
        # Create subdirectories if they don't exist
        dir_name = os.path.dirname(file_path)
        if dir_name and not os.path.exists(os.path.join(output_dir, dir_name)):
            os.makedirs(os.path.join(output_dir, dir_name))
        
        with open(os.path.join(output_dir, file_path), "w") as f:
            f.write(content)
            
    print(f"\nAll generated files have been saved to the '{output_dir}' directory.")

if __name__ == "__main__":
    asyncio.run(main())
