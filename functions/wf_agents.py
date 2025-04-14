from models.workflow import Workflow, WorkflowEntity, Run
from sqlalchemy.orm import Session
from functions.agent_team import (
    create_agent_with_config, textModel
)
from agno.agent import Agent, RunResponse
import uuid
from typing import List, Dict, Optional, Union
import logging
from functions.sse import format_sse_event, CONNECTIONS
from pydantic import BaseModel 
logger = logging.getLogger(__name__)


class ResponseModel(BaseModel):
    agent_name: str
    input: str
    output: str
    
# Agent type mapping - connects entity types to agent creation functions
AGENT_TYPE_MAPPING = {
    "lead": {
        "name": "Narrative Lead Agent",
        "role": "Develops the overarching story, worldbuilding, and tone.",
        "instructions": "You are the narrative lead who develops the overarching story."
    },
    "dialogue": {
        "name": "Dialogue Writer Agent",
        "role": "Creates character-driven dialogue and interactions.",
        "instructions": "You are a dialogue writer who creates character-driven conversations."
    },
    "art": {
        "name": "Art Style Director Agent",
        "role": "Translates narrative elements into visual prompts.",
        "instructions": "You are an art director who creates visual imagery from narrative."
    },
    "lore": {
        "name": "Lore Master Agent",
        "role": "Ensures internal consistency in worldbuilding and character arcs.",
        "instructions": "You are a lore master who maintains consistency in the story world."
    },
    "critic": {
        "name": "Critic Agent",
        "role": "Reviews outputs for coherence, tone, engagement.",
        "instructions": "You are a critic who reviews and improves narrative quality."
    },
    "reporter": {
        "name": "Reporter Agent",
        "role": "Summarizes progress and prepares reports.",
        "instructions": "You are a reporter who summarizes information clearly and concisely."
    },
    "innovator": {
        "name": "Innovator Agent",
        "role": "Generates new ideas and concepts based on the narrative.",
        "instructions": "You are an innovator who generates creative and novel ideas."
    }
}

async def create_agent_for_entity(user_message: str, goal: str, entity: WorkflowEntity) -> Agent:
    """Creates an agent based on the workflow entity type"""
    entity_type = entity.type.lower()

    agent_info = AGENT_TYPE_MAPPING.get(entity_type, {
        "name": f"{entity_type.title()} Agent",
        "role": f"Processes content as a {entity_type}",
        "instructions": f"You are a {entity_type} agent."
    })
    
    # Override with entity-specific data if available
    name = entity.label or agent_info["name"]
    instructions = entity.prompt or agent_info["instructions"]
    
    logger.info(f"Creating agent for entity: {entity_type}, Name: {name}")
    
    agent = create_agent_with_config(
        name=name,
        role=agent_info["role"],
        instructions=instructions,
        apply_config=True,
        user_message=user_message,
        goal=goal,
        ResponseModel=ResponseModel,
    )
    
    agent.entity_id = entity.id
    logger.info(f"Agent created successfully for entity ID: {entity.id}")
    
    return agent

async def run_workflow(
    db: Session, 
    workflow_id: str, 
    text: str, 
    agent_prompts: Optional[Union[List[str], Dict[str, str]]] = None
) -> str:
    """Helper function to run workflow from synchronous code"""
    try:
        workflow_uuid = uuid.UUID(workflow_id)
        run_id = uuid.uuid4()
        return await process_workflow_with_chain(db, workflow_uuid, text, run_id, agent_prompts)
    except ValueError:
        return f"Error: Invalid workflow ID format: {workflow_id}"

def process_workflow_with_chain(
    db: Session,
    workflow_id: uuid.UUID, 
    text: str,
    run_id: uuid.UUID,
    agent_prompts: Optional[Union[List[str], Dict[str, str]]] = None
) -> str:
    """
    Process text through a workflow of agents using an agentic team structure.
    Each entity processing is tracked with a Run record.
    """
    logger.info(f"Starting workflow processing for workflow ID: {workflow_id}")
    
    # Find the workflow
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        logger.error(f"Workflow with ID {workflow_id} not found")
        raise ValueError(f"Workflow with ID {workflow_id} not found")
    
    # Get all entities for this workflow, sorted by order
    entities = db.query(WorkflowEntity).filter(
        WorkflowEntity.workflow_id == workflow_id
    ).order_by(WorkflowEntity.order).all()
    
    if not entities:
        logger.error(f"No entities found for workflow '{workflow.name}'")
        raise ValueError(f"No entities found for workflow '{workflow.name}'")
    
    current_input = text
    final_output = ""
    
    # Process each entity sequentially and track with Run records
    for entity in entities:
        logger.info(f"Processing entity {entity.id} ({entity.type})")
        
        # Create or update Run record for this entity with "pending" status
        entity_run = db.query(Run).filter(
            Run.id == run_id,
            Run.workflow_entity_id == entity.id
        ).first()
        
        if entity_run:
            entity_run.status = "processing"
            entity_run.input_text = current_input
        else:
            entity_run = Run(
                id=run_id,
                workflow_id=workflow_id,
                workflow_entity_id=entity.id,
                input_text=current_input,
                output_text="",
                status="processing"
            )
            db.add(entity_run)
        
        db.commit()
        
        try:
            # Create agent for this entity
            agent = create_agent_with_config(
                name=entity.label or f"{entity.type.title()} Agent",
                role=f"Processes content as a {entity.type}",
                instructions=entity.prompt or agent_prompts,
                apply_config=True,
            )
            
            agent_response: RunResponse = agent.run(current_input)
            agent_response_content = agent_response.content  

            # Ensure agent_response is JSON-serializable
            if not isinstance(agent_response, (str, dict, list, int, float, bool, type(None))):
                agent_response = str(agent_response)
            
            # Broadcast SSE event for successful agent response
            if CONNECTIONS:
                sse_data = {
                    "name": agent.name,
                    "role": agent.role,
                    "agent_response": agent_response_content 
                }
                for client_id, queue in CONNECTIONS.items():
                    queue.put_nowait({
                        "event": "agent-response",
                        "data": sse_data
                    })

            # Update run record with completed status and agent response
            entity_run.output_text = agent_response_content 
            entity_run.status = "completed"
            db.commit()
            
            # The output of this entity becomes the input for the next one
            current_input = agent_response_content 
            final_output = agent_response_content  
            
        except Exception as e:
            logger.error(f"Error processing entity {entity.id}: {str(e)}")
            # Rollback transaction to allow a new one
            db.rollback()
            
            # Create a new transaction to update the error status
            try:
                entity_run = db.query(Run).filter(
                    Run.id == run_id,
                    Run.workflow_entity_id == entity.id
                ).first()
                
                if entity_run:
                    entity_run.status = "failed"
                    entity_run.output_text = f"Error: {str(e)}"
                    db.commit()
            except Exception as inner_e:
                logger.error(f"Could not update run status after error: {str(inner_e)}")
                db.rollback()
            
            raise
    
    logger.info(f"Workflow processing completed successfully")
    return final_output

