from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from datetime import datetime

class WorkflowConnectionCreate(BaseModel):
    target_id: str  # external_id of the target node
    label: Optional[str] = None
    style: Optional[Dict[str, Any]] = None
    animated: Optional[bool] = True

class WorkflowConnectionResponse(BaseModel):
    id: UUID
    source_id: UUID
    target_id: UUID
    workflow_id: UUID
    label: Optional[str] = None
    style: Optional[Dict[str, Any]] = None
    animated: bool

    class Config:
        orm_mode = True

class WorkflowEntityCreate(BaseModel):
    external_id: str
    type: str
    label: Optional[str] = None
    prompt: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    order: Optional[float] = None
    connections: Optional[List[WorkflowConnectionCreate]] = None

class WorkflowEntityResponse(BaseModel):
    id: UUID
    external_id: str
    type: str
    label: Optional[str] = None
    prompt: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    order: Optional[float] = None
    workflow_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class WorkflowCreate(BaseModel):
    name: str
    type: str
    description: Optional[str] = None
    project_id: UUID

class WorkflowResponse(BaseModel):
    id: UUID
    name: str
    type: str
    description: Optional[str] = None
    project_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class WorkflowRunRequest(BaseModel):
    input_text: str
    agent_prompts: Optional[Union[List[str], Dict[str, str]]] = None

class WorkflowRunResponse(BaseModel):
    run_id: UUID
    workflow_id: UUID
    message: str

class RunStatusResponse(BaseModel):
    id: UUID
    workflow_id: UUID
    status: str
    input_text: str
    output_text: Optional[str] = None
    entity_id: UUID