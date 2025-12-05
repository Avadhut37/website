"""Project generation service."""
import json
import os
import re
import shutil
import traceback
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import select

# Disable tokenizers parallelism warning when forking
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from ..ai.engine import get_ai_engine
from ..core.config import settings
from ..core.logging import logger
from ..db import session_scope
from ..models import Project
from ..validators.ast_validator import validate_python_code
from ..services.vfs import get_vfs, clear_vfs
from ..services.validation import get_validation_service
from ..services.test_runner import get_test_service
from ..services.memory import get_project_memory

BASE_WORK_DIR = Path(settings.WORK_DIR)
BASE_WORK_DIR.mkdir(parents=True, exist_ok=True)


async def start_generation_job(project_id: int) -> None:
    """Generate project files in background."""
    logger.info(f"Starting generation for project {project_id}")
    
    # Fetch spec before closing session
    with session_scope() as session:
        project = session.exec(select(Project).where(Project.id == project_id)).one()
        spec_str = project.spec
        project_name = project.name
        project.status = "generating"
        project.updated_at = datetime.now(timezone.utc)
        session.add(project)
        session.commit()

    try:
        # Parse spec
        try:
            spec = json.loads(spec_str)
        except json.JSONDecodeError:
            spec = {"raw": spec_str, "name": project_name}

        # Extract image data if present
        image_data = spec.get("image")
        if image_data:
            logger.info(f"📸 Image context found for project {project_id}")

        # Initialize VFS for this project
        vfs = get_vfs(project_id)
        
        # Generate files
        logger.info(f"Calling LLM for project {project_id}")
        engine = get_ai_engine()
        files = await engine.generate_project(
            spec, project_name, image_data=image_data, project_id=project_id
        )
        
        if not files:
            raise ValueError("No files generated")
        
        logger.info(f"Generated {len(files)} files for project {project_id}")
        # Post-process: fix hard-coded localhost URLs to use /api proxy
        files = _fix_localhost_urls(files)
        
        # Store generated code in memory for future context
        try:
            memory = get_project_memory(project_id)
            for filepath, content in files.items():
                # Detect language
                if filepath.endswith('.py'):
                    memory.store_code(filepath, content, "python")
                elif filepath.endswith(('.js', '.jsx')):
                    memory.store_code(filepath, content, "javascript")
                elif filepath.endswith(('.ts', '.tsx')):
                    memory.store_code(filepath, content, "typescript")
            
            # Store project preferences from spec
            if "tech_stack" in spec:
                for key, value in spec["tech_stack"].items():
                    memory.store_preference(key, value, category="tech_stack")
            
            logger.info(f"Stored {len(files)} files in project memory")
        except Exception as e:
            logger.warning(f"Failed to store in memory: {e}")

        # Write files to VFS
        for relative_path, content in files.items():
            vfs.write_file(relative_path, content)
        
        # Run validation before commit
        logger.info(f"Running validation for project {project_id}")
        validation_service = get_validation_service()
        all_passed, validation_results = await validation_service.validate_and_report(files)
        
        # Collect validation errors
        validation_errors = []
        if not all_passed:
            for validator_name, result in validation_results.items():
                if not result.passed:
                    logger.warning(
                        f"Validation {validator_name}: {result.error_count} errors, "
                        f"{result.warning_count} warnings"
                    )
                    # Collect error-level issues only
                    validation_errors.extend([
                        issue for issue in result.issues 
                        if issue.severity.value == "error"
                    ])
        
        # Optionally run tests if test files exist
        test_service = get_test_service()
        test_result = await test_service.run_tests(files, runner="auto")
        if test_result.total_tests > 0:
            logger.info(
                f"Tests: {test_result.passed_tests}/{test_result.total_tests} passed"
            )
        
        # Commit to VFS
        commit_id = vfs.commit(f"Initial generation: {project_name}")
        logger.info(f"VFS commit {commit_id} for project {project_id}")
        
        # Export to disk for ZIP creation
        outdir = BASE_WORK_DIR / str(project_id)
        if outdir.exists():
            shutil.rmtree(outdir)
        outdir.mkdir(parents=True, exist_ok=True)
        
        vfs.export_to_disk(outdir)
        
        # Create ZIP archive
        zip_base = BASE_WORK_DIR / str(project_id)
        archive_path = shutil.make_archive(str(zip_base), "zip", outdir)
        
        logger.info(f"Created archive for project {project_id}: {archive_path}")

        # Update project status
        with session_scope() as session:
            project = session.exec(select(Project).where(Project.id == project_id)).one()
            project.output_path = archive_path
            project.status = "ready"
            project.updated_at = datetime.now(timezone.utc)
            session.add(project)
            session.commit()
        
        logger.info(f"Project {project_id} generation completed successfully")
        
        if validation_errors:
            logger.warning(f"Project {project_id} had {len(validation_errors)} validation warnings")
            
    except Exception as e:
        error_msg = f"Generation failed for project {project_id}: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        
        with session_scope() as session:
            project = session.exec(select(Project).where(Project.id == project_id)).one()
            project.status = "failed"
            project.updated_at = datetime.now(timezone.utc)
            session.add(project)
            session.commit()
        
        # Re-raise for debugging in dev
        if settings.DEBUG:
            raise


def _fix_localhost_urls(files: dict) -> dict:
    """Post-process generated files to replace hard-coded localhost URLs with /api proxy."""
    fixed = {}
    
    for filepath, content in files.items():
        if not isinstance(content, str):
            fixed[filepath] = content
            continue
        
        # Replace hard-coded localhost URLs in JavaScript/JSX files
        if filepath.endswith(('.js', '.jsx')):
            # Replace 'http://localhost:8000' or 'http://localhost:3000' with '/api'
            content = content.replace("'http://localhost:8000'", "'/api'")
            content = content.replace('"http://localhost:8000"', '"/api"')
            content = content.replace("'http://localhost:3000'", "'/api'")
            content = content.replace('"http://localhost:3000"', '"/api"')
            
            # Replace BASE_URL = 'http://localhost...' with baseURL: '/api'
            content = re.sub(
                r"const\s+BASE_URL\s*=\s*['\"]http://localhost:\d+['\"]",
                "const BASE_URL = '/api'",
                content
            )
            
            # Replace baseURL: 'http://localhost...' with baseURL: '/api'
            content = re.sub(
                r"baseURL\s*:\s*['\"]http://localhost:\d+['\"]",
                "baseURL: '/api'",
                content
            )
        
        fixed[filepath] = content
    
    logger.info("✅ Post-processed localhost URLs to use /api proxy")
    return fixed
