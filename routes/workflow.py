from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
import uuid

from models.workflow import Workflow, WorkflowEntity, workflow_connections
from database import get_db
from schemas.workflow_schema import (
    WorkflowCreate, 
    WorkflowResponse, 
    WorkflowEntityCreate, 
    WorkflowEntityResponse,
)
import logging
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Workflow"])

# -----WORKFLOWS-----
@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
def create_workflow(workflow: WorkflowCreate, db: Session = Depends(get_db)):
    """Create a new workflow"""
    db_workflow = Workflow(
        name=workflow.name,
        type=workflow.type,
        description=workflow.description,
        project_id=workflow.project_id
    )
    db.add(db_workflow)
    db.commit()
    db.refresh(db_workflow)
    return db_workflow

@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(workflow_id: UUID, db: Session = Depends(get_db)):
    """Delete a workflow"""
    db_workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not db_workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    db.delete(db_workflow)
    db.commit()
    return None

@router.get("/project/{project_id}", response_model=List[WorkflowResponse])
def get_workflows(
    project_id: Optional[UUID] = None, 
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """Get all workflows, optionally filtered by project ID"""
    query = db.query(Workflow)
    
    if project_id:
        query = query.filter(Workflow.project_id == project_id)
    
    workflows = query.offset(skip).limit(limit).all()
    return workflows
# -----NODES-----
@router.post("/{workflow_id}/entities/", response_model=WorkflowEntityResponse, status_code=status.HTTP_201_CREATED)
def create_workflow_entity(workflow_id: UUID, entity: WorkflowEntityCreate, db: Session = Depends(get_db)):
    """Create a new workflow entity/node"""
    # Check if workflow exists
    db_workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not db_workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    db_entity = WorkflowEntity(
        external_id=entity.external_id,
        type=entity.type,
        label=entity.label,
        prompt=entity.prompt,
        data=entity.data,
        workflow_id=workflow_id,
        order=entity.order if entity.order is not None else 0,  
    )

    db.add(db_entity)
    db.commit()
    db.refresh(db_entity)
    
    # Handle connections if provided
    if entity.connections:
        for connection in entity.connections:
            # Find target entity
            target_entity = db.query(WorkflowEntity).filter(
                WorkflowEntity.external_id == connection.target_id, 
                WorkflowEntity.workflow_id == workflow_id
            ).first()
            
            if target_entity:
                # Add connection
                db.execute(
                    workflow_connections.insert().values(
                        id=uuid.uuid4(),
                        source_id=db_entity.id,
                        target_id=target_entity.id,
                        workflow_id=workflow_id,
                        label=connection.label,
                        style=connection.style,
                        animated=connection.animated
                    )
                )
                db.commit()
    
    return db_entity


@router.delete("/entities/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow_entity(entity_id: UUID, db: Session = Depends(get_db)):
    """Delete a workflow entity/node"""
    db_entity = db.query(WorkflowEntity).filter(WorkflowEntity.id == entity_id).first()
    if not db_entity:
        raise HTTPException(status_code=404, detail="Workflow entity not found")
    
    db.delete(db_entity)
    db.commit()
    return None



@router.get("/{workflow_id}/entities/", response_model=List[WorkflowEntityResponse])
def get_workflow_entities(workflow_id: UUID, db: Session = Depends(get_db)):
    """Get all entities/nodes for a specific workflow"""
    # Check if workflow exists
    db_workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not db_workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    entities = db.query(WorkflowEntity).filter(WorkflowEntity.workflow_id == workflow_id).all()
    return entities

