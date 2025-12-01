"""Project management endpoints."""
import os
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from sqlmodel import Session, func, select

from ..core.logging import logger
from ..core.rate_limit import limiter, RATE_LIMITS
from ..core.security import get_current_user, get_optional_user
from ..db import get_session
from ..models import Project, User
from ..schemas import (
    ProjectCreate,
    ProjectCreateResponse,
    ProjectListResponse,
    ProjectResponse,
)
from ..services.generator import start_generation_job

router = APIRouter()


@router.post("/", response_model=ProjectCreateResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RATE_LIMITS["generation"])
def create_project(
    request: Request,
    payload: ProjectCreate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Create a new project and start generation."""
    # Use authenticated user or default to anonymous (owner_id=0)
    owner_id = current_user.id if current_user else 0
    
    project = Project(
        owner_id=owner_id,
        name=payload.name,
        spec=payload.spec,
        status="pending"
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    
    logger.info(f"Project created: {project.id} by user {owner_id}")
    
    background_tasks.add_task(start_generation_job, project.id)
    
    return ProjectCreateResponse(
        id=project.id,
        status=project.status,
        message="Project generation started"
    )


@router.get("/", response_model=ProjectListResponse)
def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """List projects with pagination."""
    query = select(Project)
    
    # Filter by owner if authenticated
    if current_user:
        query = query.where(Project.owner_id == current_user.id)
    
    # Filter by status
    if status_filter:
        query = query.where(Project.status == status_filter)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = session.exec(count_query).one()
    
    # Apply pagination
    query = query.order_by(Project.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    projects = session.exec(query).all()
    
    return ProjectListResponse(
        items=[ProjectResponse.model_validate(p) for p in projects],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Get a project by ID."""
    project = session.exec(select(Project).where(Project.id == project_id)).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check ownership if authenticated
    if current_user and project.owner_id != 0 and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this project"
        )
    
    return ProjectResponse.model_validate(project)


@router.get("/{project_id}/download")
@limiter.limit(RATE_LIMITS["download"])
def download_project(
    request: Request,
    project_id: int,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Download the generated project as a ZIP file."""
    project = session.exec(select(Project).where(Project.id == project_id)).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check ownership if authenticated
    if current_user and project.owner_id != 0 and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this project"
        )
    
    if project.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project is not ready (status: {project.status})"
        )
    
    if not project.output_path or not os.path.exists(project.output_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project output file not found"
        )
    
    logger.info(f"Project downloaded: {project.id}")
    
    return FileResponse(
        project.output_path,
        media_type="application/zip",
        filename=f"{project.name}.zip"
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Delete a project (requires authentication)."""
    project = session.exec(select(Project).where(Project.id == project_id)).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this project"
        )
    
    session.delete(project)
    session.commit()
    
    logger.info(f"Project deleted: {project_id} by user {current_user.id}")
