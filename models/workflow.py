from sqlalchemy import Column, String, ForeignKey, DateTime, Table, Boolean, Float, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

workflow_connections = Table(
    "workflow_connections",
    Base.metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("source_id", UUID(as_uuid=True), ForeignKey("workflow_entities.id", ondelete="CASCADE")),
    Column("target_id", UUID(as_uuid=True), ForeignKey("workflow_entities.id", ondelete="CASCADE")),
    Column("workflow_id", UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE")),
    Column("label", String, nullable=True),
    Column("style", JSON, nullable=True),
    Column("animated", Boolean, default=True),
)

class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    description = Column(String, nullable=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    # Use string reference to avoid circular imports - DO NOT use back_populates here
    project = relationship("Project")
    entities = relationship("WorkflowEntity", back_populates="workflow", cascade="all, delete-orphan")
    runs = relationship("Run", back_populates="workflow", cascade="all, delete-orphan")

class WorkflowEntity(Base):
    __tablename__ = "workflow_entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id = Column(String, nullable=False) 
    type = Column(String, nullable=False)  
    label = Column(String, nullable=True)
    prompt = Column(String, nullable=True)  
    data = Column(JSON, nullable=True)  
    order = Column(Float, nullable=True) 
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    workflow = relationship("Workflow", back_populates="entities")
    runs = relationship("Run", back_populates="workflow_entity", cascade="all, delete-orphan")
    
    # Define relationships for source and target connections
    source_connections = relationship(
        "WorkflowEntity",
        secondary=workflow_connections,
        primaryjoin=id == workflow_connections.c.source_id,
        secondaryjoin=id == workflow_connections.c.target_id,
        backref="target_connections"
    )
    
class Run(Base):
    __tablename__ = "runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    input_text = Column(String, nullable=False)
    output_text = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    workflow_entity_id = Column(UUID(as_uuid=True), ForeignKey("workflow_entities.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, nullable=False, default="pending")  # e.g., "pending", "completed", "failed"

    workflow = relationship("Workflow", back_populates="runs")
    workflow_entity = relationship("WorkflowEntity", back_populates="runs")
