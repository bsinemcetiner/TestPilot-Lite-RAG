from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    format = Column(String(50), nullable=False)
    source_type = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    vector_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class GenerationRun(Base):
    __tablename__ = "generation_runs"

    id = Column(String(36), primary_key=True, index=True)
    feature = Column(String(255), nullable=False)
    query = Column(Text, nullable=True)
    provider = Column(String(100), nullable=False)
    output_format = Column(String(50), nullable=False)
    requested_count = Column(Integer, nullable=False)
    retrieved_chunks_count = Column(Integer, nullable=False, default=0)
    is_pinned = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Store evaluation metrics as JSON
    evaluation_metrics = Column(JSON, nullable=True)
    formatted_output = Column(Text, nullable=True)
    
    test_cases = relationship("GeneratedTestCase", back_populates="run", cascade="all, delete-orphan")


class GeneratedTestCase(Base):
    __tablename__ = "generated_test_cases"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(36), ForeignKey("generation_runs.id"), nullable=False)
    
    case_index = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    priority = Column(String(50), nullable=False)
    expected_result = Column(Text, nullable=False)
    confidence = Column(Float, nullable=True)
    
    # Store array data as JSON to keep model simple
    preconditions = Column(JSON, nullable=False)
    steps = Column(JSON, nullable=False)
    source_references = Column(JSON, nullable=True)
    
    run = relationship("GenerationRun", back_populates="test_cases")
