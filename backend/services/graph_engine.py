"""Graph Engine — Queries and navigates the PostgreSQL Graph DB."""
from typing import List, Dict
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.storage import get_store
from backend.storage.models import GraphNodeModel, GraphEdgeModel


def search_graph(query: str) -> str:
    """
    Search the graph database for entities mentioned in the query.
    Returns a formatted string of the relevant subgraph to inject into the LLM context.
    """
    store = get_store()
    session: Session = store.get_session()
    
    try:
        # 1. Fetch all nodes to see if any are mentioned in the query
        all_nodes = session.query(GraphNodeModel).all()
        if not all_nodes:
            return ""
            
        matched_node_ids = []
        query_lower = query.lower()
        
        for node in all_nodes:
            # Simple keyword matching: if the node's label/id is in the query
            if node.id.lower() in query_lower:
                matched_node_ids.append(node.id)
                
        if not matched_node_ids:
            return ""
            
        # 2. Find all edges connected to the matched nodes (1-hop)
        edges = session.query(GraphEdgeModel).filter(
            or_(
                GraphEdgeModel.source_id.in_(matched_node_ids),
                GraphEdgeModel.target_id.in_(matched_node_ids)
            )
        ).all()
        
        if not edges:
            return ""
            
        # 3. Fetch descriptions for nodes involved in these edges
        involved_node_ids = set()
        for e in edges:
            involved_node_ids.add(e.source_id)
            involved_node_ids.add(e.target_id)
            
        involved_nodes = session.query(GraphNodeModel).filter(
            GraphNodeModel.id.in_(list(involved_node_ids))
        ).all()
        
        node_map = {n.id: n for n in involved_nodes}
        
        # 4. Format the output
        lines = ["\n## CONTEXTO ESTRUCTURADO (GRAPH KNOWLEDGE)\n"]
        lines.append("Las siguientes relaciones directas han sido recuperadas de tu memoria estructurada:")
        
        for e in edges:
            src = node_map.get(e.source_id)
            tgt = node_map.get(e.target_id)
            if not src or not tgt: continue
            
            lines.append(f"- [{src.type}] {src.id}  --({e.relation})-->  [{tgt.type}] {tgt.id}")
            
        # Add descriptions for the matched nodes
        lines.append("\n**Detalles de las entidades clave:**")
        for n_id in matched_node_ids:
            node = node_map.get(n_id)
            if node and node.description:
                lines.append(f"- **{node.id}**: {node.description}")
                
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Error searching graph DB: {e}")
        return ""
    finally:
        session.close()
