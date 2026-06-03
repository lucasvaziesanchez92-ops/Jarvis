
import sys
import os
from langchain_core.messages import HumanMessage
from backend.agent.graph import get_graph
from backend.config import settings

def test_agent_connection():
    from backend.llm import get_llm
    llm = get_llm()
    print(f"--- Iniciando prueba del Agente (Provider: {type(llm).__name__}) ---")
    graph = get_graph()
    
    # Configuramos una sesión de prueba
    config = {"configurable": {"thread_id": "test_session_1"}}
    
    # 1. Prueba de comunicación básica
    print("\n1. Probando comunicación básica...")
    try:
        inputs = {"messages": [HumanMessage(content="Hola, ¿quién eres y qué hora es?")]}
        for output in graph.stream(inputs, config=config):
            for key, value in output.items():
                if key == "agent":
                    print(f"Respuesta del Agente: {value['messages'][-1].content}")
    except Exception as e:
        print(f"Error en comunicación básica: {str(e)}")

    # 2. Prueba de herramientas (Wiki)
    print("\n2. Probando acceso a la Wiki local...")
    try:
        inputs = {"messages": [HumanMessage(content="Busca en mi wiki qué es un API Gateway")]}
        for output in graph.stream(inputs, config=config):
            for key, value in output.items():
                print(f"Nodo activo: {key}")
                if key == "agent" and hasattr(value['messages'][-1], 'tool_calls'):
                    print(f"¡El agente decidió usar herramientas!: {value['messages'][-1].tool_calls}")
    except Exception as e:
        print(f"Error en prueba de herramientas: {str(e)}")

if __name__ == "__main__":
    test_agent_connection()
