from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import uuid
from models.workflow import Workflow, Run
from database import get_db
from schemas.workflow_schema import (
    WorkflowRunRequest,
    WorkflowRunResponse,
    RunStatusResponse
)
from functions.wf_agents import process_workflow_with_chain
import logging
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Run"])

@router.post("/workflow/{workflow_id}", response_model=WorkflowRunResponse)
def execute_workflow(
    workflow_id: UUID,
    run_request: WorkflowRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Execute a workflow with the provided input text.
    
    Creates a run ID and processes each entity in the workflow, 
    tracking each entity's processing with a Run record.
    """
    # Check if workflow exists
    db_workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not db_workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Create a unique run ID for this execution
    run_id = uuid.uuid4()
    logger.info(f"Created run ID: {run_id} for workflow ID: {workflow_id}")
    
    # Process the workflow synchronously - Run records are created/updated inside
    try:
        process_workflow_with_chain(
            db, 
            workflow_id, 
            run_request.input_text, 
            run_id, 
            run_request.agent_prompts
        )
    except Exception as e:
        logger.error(f"Error executing workflow: {str(e)}")
        # Ensure we have a clean session
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error executing workflow: {str(e)}")

    return {
        "run_id": run_id,
        "workflow_id": workflow_id,
        "message": "Workflow execution completed successfully"
    }

@router.get("/workflow/{workflow_id}", response_model=List[RunStatusResponse])
def get_workflow_runs(workflow_id: UUID, db: Session = Depends(get_db)):
    """Get all runs for a specific workflow"""
    # Check if workflow exists
    db_workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not db_workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    runs = db.query(Run).filter(Run.workflow_id == workflow_id).all()
    
    return [
        {
            "id": run.id,
            "workflow_id": run.workflow_id,
            "status": run.status,
            "input_text": run.input_text,
            "output_text": run.output_text,
            "entity_id": run.workflow_entity_id
        }
        for run in runs
    ]

@router.get("/{run_id}", response_model=List[RunStatusResponse])
def get_run_status(run_id: UUID, db: Session = Depends(get_db)):
    """Get status of all entities for a specific run"""
    runs = db.query(Run).filter(Run.id == run_id).all()
    if not runs:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return [
        {
            "id": run.id,
            "workflow_id": run.workflow_id,
            "status": run.status,
            "input_text": run.input_text,
            "output_text": run.output_text,
            "entity_id": run.workflow_entity_id
        }
        for run in runs
    ]

@router.get("/{run_id}/entity/{entity_id}", response_model=RunStatusResponse)
def get_entity_run_status(run_id: UUID, entity_id: UUID, db: Session = Depends(get_db)):
    """Get status of a specific entity within a run"""
    run = db.query(Run).filter(
        Run.id == run_id,
        Run.workflow_entity_id == entity_id
    ).first()
    
    if not run:
        raise HTTPException(
            status_code=404, 
            detail=f"Run not found for run_id={run_id} and entity_id={entity_id}"
        )
    
    return {
        "id": run.id,
        "workflow_id": run.workflow_id,
        "status": run.status,
        "input_text": run.input_text,
        "output_text": run.output_text,
        "entity_id": run.workflow_entity_id
    }
