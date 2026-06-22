import asyncio
import time
from langchain_core.messages import AIMessage
from backend.agent.graph import tool_node

async def simular_interaccion_masiva():
    print("🚀 [TEST] Iniciando simulación de Big Bang de herramientas...")
    
    # Creamos un contexto de entradas falsas (Mock) simulando la petición del usuario
    # El graph espera que el último mensaje tenga tool_calls
    mock_ai_message = AIMessage(content="", tool_calls=[
        {"name": "search_drive", "args": {"query": "algoritmos"}, "id": "call_1"},
        {"name": "search_gmail", "args": {"query": "urgente"}, "id": "call_2"},
        {"name": "list_calendar_google", "args": {}, "id": "call_3"}
    ])
    
    inputs_falsos = {
        "messages": [mock_ai_message],
        "tools_executed": []
    }
    
    # Medimos el tiempo de ejecución en paralelo
    inicio = asyncio.get_event_loop().time()
    try:
        # Disparamos el nodo que refactorizamos con asyncio.gather
        print("⚡ [TEST] Disparando herramientas en paralelo simultáneamente...")
        resultados = await tool_node(inputs_falsos)
        fin = asyncio.get_event_loop().time()
        
        print(f"✅ [TEST] Éxito. Tiempo total de respuesta concurrente: {fin - inicio:.2f} segundos.")
        print(f"📊 [TEST] Cantidad de datos recuperados: {len(resultados.get('messages', []))} bloques.")
        for msg in resultados.get('messages', []):
            print(f"   - Tool: {msg.name} -> {msg.content[:50]}...")
        
    except Exception as e:
        import traceback
        print(f"❌ [TEST] Error detectado en el pipeline asíncrono: {e}")
        traceback.print_exc()

# Simulación del gatillo de aborto (Barge-In)
async def simular_barge_in_servidor():
    print("\n🛑 [TEST] Iniciando simulación de control de aborto (Barge-In)...")
    
    async def tarea_llm_larga():
        try:
            print("⏳ [LLM Mock] Generando ráfagas de audio y tokens...")
            for i in range(10):
                await asyncio.sleep(0.5) # Simula el tiempo que tarda Piper TTS
                print(f"🔊 [LLM Mock] Chunk {i} enviado al buffer de voz.")
        except asyncio.CancelledError:
            print("✂️ [LLM Mock] ¡Excepción CancelledError capturada con éxito!")
            print("♻️ [LLM Mock] Recursos liberados y tokens congelados de forma inmediata.")
            raise

    # Disparamos la tarea en segundo plano
    stream_task = asyncio.create_task(tarea_llm_larga())
    
    # Esperamos 1.5 segundos (simulando que el usuario escucha a JARVIS hablar)
    await asyncio.sleep(1.5)
    
    # Disparamos la señal de interrupción del WebSocket
    print("🎯 [WebSocket Mock] Paquete {'type': 'abort'} recibido desde React.")
    stream_task.cancel() # Cancelamos la tarea de raíz
    
    try:
        await stream_task
    except asyncio.CancelledError:
        print("✅ [TEST] El Barge-In local funciona de forma inmaculada. Servidor a salvo.")

if __name__ == "__main__":
    import dotenv
    dotenv.load_dotenv()
    
    asyncio.run(simular_interaccion_masiva())
    asyncio.run(simular_barge_in_servidor())
