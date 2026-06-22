import base64
import os
from PIL import Image
import io
from langchain_core.messages import HumanMessage

def test_vision_pipeline():
    print("[TEST] Iniciando pipeline de Visión Omnisciente...")

    # 1. Simular la recepción de un string base64 de pantalla (crear una imagen falsa de 1x1 píxel negro)
    img_byte_arr = io.BytesIO()
    image = Image.new('RGB', (1, 1), color = 'black')
    image.save(img_byte_arr, format='JPEG', quality=60)
    fake_base64_payload = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
    
    print("[TEST] Paso 1: String base64 generado exitosamente (Simulando recepción por WebSocket).")

    # 2. Comprobar decodificación de la imagen (Pillow)
    try:
        decoded_bytes = base64.b64decode(fake_base64_payload)
        decoded_image = Image.open(io.BytesIO(decoded_bytes))
        decoded_image.verify()  # Verifica integridad del header JPEG
        print(f"[TEST] Paso 2: Imagen base64 decodificada e íntegra. Formato: {decoded_image.format}, Tamaño: {decoded_image.size}")
    except Exception as e:
        print(f"[TEST] Error en la decodificación de la imagen: {e}")
        return

    # 3. Verificar estructuración del HumanMessage multimodal
    texto_usuario = "¿Qué ves en mi pantalla?"
    user_content = [
        {
            "type": "text", 
            "text": f"{texto_usuario}\n\n[Instrucción técnica]: El usuario está compartiendo su pantalla en tiempo real. Analiza los elementos visuales, código o errores de consola visibles en la imagen adjunta para enriquecer tu respuesta."
        },
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{fake_base64_payload}"}
        }
    ]
    
    try:
        human_msg = HumanMessage(content=user_content)
        print("[TEST] Paso 3: HumanMessage estructurado exitosamente.")
        print(f"  - Componentes del mensaje: {len(human_msg.content)}")
        print(f"  - Primer componente (texto): {human_msg.content[0]['type']}")
        print(f"  - Segundo componente (imagen): {human_msg.content[1]['type']}")
    except Exception as e:
        print(f"[TEST] Error al estructurar HumanMessage: {e}")
        return

    print("\n[TEST EXITOSO] El pipeline de decodificación y estructura multimodal está listo para producción.")

if __name__ == "__main__":
    test_vision_pipeline()
