
import sys
import os
import time
from langchain_core.messages import HumanMessage
from backend.agent.graph import get_graph
from backend.config import settings

def test_full_brain_cycle():
    print(f"--- Iniciando Ciclo Completo de Segundo Cerebro ---")
    graph = get_graph()
    config = {"configurable": {"thread_id": "brain_test_session"}}
    
    # 1. Investigación y Web Search
    print("\n1. Pidiendo investigación externa (Web Search)...")
    q1 = "Investiga brevemente qué es el 'Model Context Protocol' de Anthropic y dime para qué sirve."
    inputs = {"messages": [HumanMessage(content=q1)]}
    
    for output in graph.stream(inputs, config=config):
        for key, value in output.items():
            print(f" >> Nodo: {key}")
            if key == "agent" and hasattr(value['messages'][-1], 'tool_calls'):
                print(f"    Acción: {value['messages'][-1].tool_calls}")

    # 2. Guardar en Wiki
    print("\n2. Solicitando guardar en el Segundo Cerebro (Wiki)...")
    q2 = "Eso es muy interesante. Por favor, guarda un resumen técnico de esto en mi wiki con el título 'Model Context Protocol' y usa etiquetas de Obsidian."
    inputs = {"messages": [HumanMessage(content=q2)]}
    
    for output in graph.stream(inputs, config=config):
        for key, value in output.items():
            print(f" >> Nodo: {key}")
            if key == "agent" and hasattr(value['messages'][-1], 'tool_calls'):
                print(f"    Acción: {value['messages'][-1].tool_calls}")

    # 3. Notas y Todos
    print("\n3. Creando nota y recordatorio...")
    q3 = "Ahora crea una nota titulada 'Estudio de MCP' y pon un recordatorio (todo) para 'Implementar servidor MCP' para el viernes."
    inputs = {"messages": [HumanMessage(content=q3)]}
    
    for output in graph.stream(inputs, config=config):
        for key, value in output.items():
            print(f" >> Nodo: {key}")
            if key == "agent" and hasattr(value['messages'][-1], 'tool_calls'):
                print(f"    Acción: {value['messages'][-1].tool_calls}")

if __name__ == "__main__":
    test_full_brain_cycle()
