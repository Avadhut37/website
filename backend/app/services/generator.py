"""Project generation service."""
import json
import shutil
import traceback
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import select

from ..ai.engine import call_llm_and_generate
from ..core.config import settings
from ..core.logging import logger
from ..db import session_scope
from ..models import Project
from ..validators.ast_validator import validate_python_code

BASE_WORK_DIR = Path(settings.WORK_DIR)
BASE_WORK_DIR.mkdir(parents=True, exist_ok=True)


def start_generation_job(project_id: int) -> None:
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

        # Prepare output directory
        outdir = BASE_WORK_DIR / str(project_id)
        if outdir.exists():
            shutil.rmtree(outdir)
        outdir.mkdir(parents=True, exist_ok=True)

        # Generate files
        logger.info(f"Calling LLM for project {project_id}")
        files = call_llm_and_generate(spec)
        
        if not files:
            raise ValueError("No files generated")
        
        logger.info(f"Generated {len(files)} files for project {project_id}")

        # Write files with validation
        validation_errors = []
        for relative_path, content in files.items():
            destination = outdir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            # Validate Python files
            if relative_path.endswith(".py"):
                ok, err = validate_python_code(content)
                if not ok:
                    validation_errors.append(f"{relative_path}: {err}")
                    logger.warning(f"Validation error in {relative_path}: {err}")
                    # Still write the file but log the error
            
            destination.write_text(content, encoding="utf-8")
        
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
