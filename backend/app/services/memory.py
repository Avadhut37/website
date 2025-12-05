"""Project memory service with vector embeddings and semantic search."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from ..core.config import settings
from ..core.logging import logger

# Initialize embedding model (lazy loading)
_embedding_model: Optional[SentenceTransformer] = None

# ChromaDB client (lazy loading)
_chroma_client: Optional[chromadb.Client] = None


def get_embedding_model() -> SentenceTransformer:
    """Get or create embedding model singleton."""
    global _embedding_model
    if _embedding_model is None:
        logger.info("Loading sentence-transformers model...")
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("✅ Embedding model loaded (384 dimensions)")
    return _embedding_model


def get_chroma_client() -> chromadb.Client:
    """Get or create ChromaDB client singleton."""
    global _chroma_client
    if _chroma_client is None:
        persist_dir = Path(settings.WORK_DIR) / "memory" / "chroma"
        persist_dir.mkdir(parents=True, exist_ok=True)
        
        _chroma_client = chromadb.Client(Settings(
            persist_directory=str(persist_dir),
            anonymized_telemetry=False
        ))
        logger.info(f"✅ ChromaDB initialized at {persist_dir}")
    return _chroma_client


class ProjectMemory:
    """Project memory with vector embeddings for semantic search."""
    
    def __init__(self, project_id: int):
        self.project_id = project_id
        self.embedding_model = get_embedding_model()
        self.client = get_chroma_client()
        
        # Collections for different memory types
        self.code_collection = self._get_or_create_collection("code")
        self.decisions_collection = self._get_or_create_collection("decisions")
        self.preferences_collection = self._get_or_create_collection("preferences")
        self.constraints_collection = self._get_or_create_collection("constraints")
    
    def _get_or_create_collection(self, memory_type: str):
        """Get or create a ChromaDB collection."""
        collection_name = f"project_{self.project_id}_{memory_type}"
        return self.client.get_or_create_collection(
            name=collection_name,
            metadata={"project_id": self.project_id, "type": memory_type}
        )
    
    def _generate_id(self, content: str, memory_type: str) -> str:
        """Generate unique ID for memory entry."""
        hash_input = f"{self.project_id}:{memory_type}:{content}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
    
    def store_code(
        self,
        filepath: str,
        code: str,
        language: str,
        description: Optional[str] = None
    ):
        """Store code snippet with embeddings.
        
        Args:
            filepath: Path to the code file
            code: Code content
            language: Programming language
            description: Optional description of the code
        """
        # Create searchable text
        text = f"{filepath}\n{language}\n{description or ''}\n{code}"
        
        # Generate embedding
        embedding = self.embedding_model.encode(text).tolist()
        
        # Generate ID
        doc_id = self._generate_id(code, "code")
        
        # Store in ChromaDB
        self.code_collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[code],
            metadatas=[{
                "filepath": filepath,
                "language": language,
                "description": description or "",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": "code"
            }]
        )
        
        logger.debug(f"Stored code: {filepath} ({language})")
    
    def store_decision(
        self,
        decision: str,
        reasoning: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """Store a development decision.
        
        Args:
            decision: The decision made
            reasoning: Why this decision was made
            context: Additional context (tools used, alternatives considered, etc.)
        """
        # Create searchable text
        text = f"{decision}\n{reasoning}"
        if context:
            text += f"\n{json.dumps(context, indent=2)}"
        
        # Generate embedding
        embedding = self.embedding_model.encode(text).tolist()
        
        # Generate ID
        doc_id = self._generate_id(decision, "decision")
        
        # Store in ChromaDB
        self.decisions_collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[{
                "decision": decision,
                "reasoning": reasoning,
                "context": json.dumps(context or {}),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": "decision"
            }]
        )
        
        logger.debug(f"Stored decision: {decision[:50]}...")
    
    def store_preference(
        self,
        key: str,
        value: Any,
        category: str = "general"
    ):
        """Store a project preference.
        
        Args:
            key: Preference key (e.g., "ui_framework", "database")
            value: Preference value
            category: Category (e.g., "frontend", "backend", "styling")
        """
        # Create searchable text
        text = f"{category}: {key} = {value}"
        
        # Generate embedding
        embedding = self.embedding_model.encode(text).tolist()
        
        # Generate ID
        doc_id = self._generate_id(f"{key}:{value}", "preference")
        
        # Store in ChromaDB
        self.preferences_collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[{
                "key": key,
                "value": str(value),
                "category": category,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": "preference"
            }]
        )
        
        logger.debug(f"Stored preference: {key} = {value}")
    
    def store_constraint(
        self,
        constraint: str,
        severity: str = "must",
        scope: str = "global"
    ):
        """Store a project constraint.
        
        Args:
            constraint: The constraint description
            severity: "must", "should", or "nice-to-have"
            scope: "global", "frontend", "backend", or specific module
        """
        # Create searchable text
        text = f"{severity.upper()}: {constraint} (scope: {scope})"
        
        # Generate embedding
        embedding = self.embedding_model.encode(text).tolist()
        
        # Generate ID
        doc_id = self._generate_id(constraint, "constraint")
        
        # Store in ChromaDB
        self.constraints_collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[{
                "constraint": constraint,
                "severity": severity,
                "scope": scope,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": "constraint"
            }]
        )
        
        logger.debug(f"Stored constraint: {constraint[:50]}...")
    
    def search_code(
        self,
        query: str,
        n_results: int = 5,
        language: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar code snippets.
        
        Args:
            query: Search query
            n_results: Number of results to return
            language: Optional language filter
            
        Returns:
            List of matching code snippets with metadata
        """
        # Generate query embedding
        query_embedding = self.embedding_model.encode(query).tolist()
        
        # Build filter
        where_filter = {}
        if language:
            where_filter["language"] = language
        
        # Search
        results = self.code_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter if where_filter else None
        )
        
        # Format results
        return self._format_results(results)
    
    def search_decisions(
        self,
        query: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar past decisions.
        
        Args:
            query: Search query
            n_results: Number of results to return
            
        Returns:
            List of matching decisions with reasoning
        """
        # Generate query embedding
        query_embedding = self.embedding_model.encode(query).tolist()
        
        # Search
        results = self.decisions_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        return self._format_results(results)
    
    def search_preferences(
        self,
        query: str,
        n_results: int = 10,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for project preferences.
        
        Args:
            query: Search query
            n_results: Number of results to return
            category: Optional category filter
            
        Returns:
            List of matching preferences
        """
        # Generate query embedding
        query_embedding = self.embedding_model.encode(query).tolist()
        
        # Build filter
        where_filter = {}
        if category:
            where_filter["category"] = category
        
        # Search
        results = self.preferences_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter if where_filter else None
        )
        
        return self._format_results(results)
    
    def search_constraints(
        self,
        query: str,
        n_results: int = 10,
        severity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for project constraints.
        
        Args:
            query: Search query
            n_results: Number of results to return
            severity: Optional severity filter ("must", "should", "nice-to-have")
            
        Returns:
            List of matching constraints
        """
        # Generate query embedding
        query_embedding = self.embedding_model.encode(query).tolist()
        
        # Build filter
        where_filter = {}
        if severity:
            where_filter["severity"] = severity
        
        # Search
        results = self.constraints_collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter if where_filter else None
        )
        
        return self._format_results(results)
    
    def get_all_preferences(self) -> Dict[str, Any]:
        """Get all project preferences as a dictionary.
        
        Returns:
            Dictionary of key-value preferences
        """
        results = self.preferences_collection.get()
        
        preferences = {}
        if results and results.get("metadatas"):
            for metadata in results["metadatas"]:
                key = metadata.get("key")
                value = metadata.get("value")
                if key and value:
                    preferences[key] = value
        
        return preferences
    
    def get_all_constraints(self, severity: Optional[str] = None) -> List[str]:
        """Get all project constraints.
        
        Args:
            severity: Optional severity filter
            
        Returns:
            List of constraint strings
        """
        where_filter = {"severity": severity} if severity else None
        results = self.constraints_collection.get(where=where_filter)
        
        constraints = []
        if results and results.get("metadatas"):
            for metadata in results["metadatas"]:
                constraint = metadata.get("constraint")
                if constraint:
                    constraints.append(constraint)
        
        return constraints
    
    def _format_results(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format ChromaDB results into clean dictionaries.
        
        Args:
            results: Raw ChromaDB query results
            
        Returns:
            List of formatted result dictionaries
        """
        formatted = []
        
        if not results or not results.get("ids"):
            return formatted
        
        ids = results["ids"][0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        
        for i, doc_id in enumerate(ids):
            formatted.append({
                "id": doc_id,
                "content": documents[i] if i < len(documents) else "",
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "similarity": 1 - (distances[i] if i < len(distances) else 1.0),
                "distance": distances[i] if i < len(distances) else 1.0
            })
        
        return formatted
    
    def get_context_for_generation(
        self,
        query: str,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """Get comprehensive context for code generation.
        
        Args:
            query: Generation context/description
            max_results: Max results per category
            
        Returns:
            Dictionary with relevant code, decisions, preferences, constraints
        """
        return {
            "similar_code": self.search_code(query, n_results=max_results),
            "past_decisions": self.search_decisions(query, n_results=max_results),
            "preferences": self.get_all_preferences(),
            "constraints": self.get_all_constraints(severity="must"),
            "suggestions": self.get_all_constraints(severity="should")
        }
    
    def clear_memory(self, memory_type: Optional[str] = None):
        """Clear project memory.
        
        Args:
            memory_type: Specific type to clear, or None for all
        """
        if memory_type is None or memory_type == "code":
            self.code_collection.delete(where={})
            logger.info(f"Cleared code memory for project {self.project_id}")
        
        if memory_type is None or memory_type == "decisions":
            self.decisions_collection.delete(where={})
            logger.info(f"Cleared decisions memory for project {self.project_id}")
        
        if memory_type is None or memory_type == "preferences":
            self.preferences_collection.delete(where={})
            logger.info(f"Cleared preferences memory for project {self.project_id}")
        
        if memory_type is None or memory_type == "constraints":
            self.constraints_collection.delete(where={})
            logger.info(f"Cleared constraints memory for project {self.project_id}")


# Memory service singleton registry
_project_memories: Dict[int, ProjectMemory] = {}


def get_project_memory(project_id: int) -> ProjectMemory:
    """Get or create project memory.
    
    Args:
        project_id: Project ID
        
    Returns:
        ProjectMemory instance
    """
    if project_id not in _project_memories:
        _project_memories[project_id] = ProjectMemory(project_id)
        logger.info(f"✅ Created memory for project {project_id}")
    return _project_memories[project_id]


def clear_project_memory(project_id: int):
    """Clear and remove project memory.
    
    Args:
        project_id: Project ID
    """
    if project_id in _project_memories:
        _project_memories[project_id].clear_memory()
        del _project_memories[project_id]
        logger.info(f"✅ Cleared memory for project {project_id}")
