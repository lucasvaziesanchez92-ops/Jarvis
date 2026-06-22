export class ScreenCapturer {
  private stream: MediaStream | null = null;
  private intervalId: any = null;

  async iniciarCaptura(ws: WebSocket, intervalMs: number = 3000, onCancel: () => void) {
    try {
      // Solicitar el stream nativo de la pantalla completa o ventana al navegador
      this.stream = await navigator.mediaDevices.getDisplayMedia({
        video: { 
          frameRate: { ideal: 1 },
          width: { max: 1920 },
          height: { max: 1080 }
        },
        audio: false
      });

      // Manejar el caso donde el usuario da clic en "Dejar de compartir" en la barra nativa del OS
      this.stream.getVideoTracks()[0].onended = () => {
        this.detenerCaptura();
        onCancel();
      };

      // Bucle reactivo de captura cada 3 segundos
      this.intervalId = setInterval(async () => {
        if (!this.stream || ws.readyState !== WebSocket.OPEN) return;

        try {
          const videoTrack = this.stream.getVideoTracks()[0];
          // Usamos un Canvas invisible para procesar y encoger las dimensiones del frame
          const imageCapture = new (window as any).ImageCapture(videoTrack);
          const bitmap = await imageCapture.grabFrame();
          
          const canvas = document.createElement('canvas');
          canvas.width = bitmap.width;
          canvas.height = bitmap.height;
          const ctx = canvas.getContext('2d');
          ctx?.drawImage(bitmap, 0, 0);

          // Comprimimos a JPEG al 60% para proteger el ancho de banda del WebSocket
          canvas.toBlob((blob) => {
            if (!blob) return;
            const reader = new FileReader();
            reader.readAsDataURL(blob);
            reader.onloadend = () => {
              const base64Data = (reader.result as string).split(',')[1];
              ws.send(JSON.stringify({
                type: "screen_chunk",
                payload: base64Data
              }));
            };
          }, 'image/jpeg', 0.6);

        } catch (e) {
          console.error("[ScreenCapturer] Error al extraer frame óptico:", e);
        }
      }, intervalMs);

    } catch (err) {
      console.warn("[ScreenCapturer] Acceso a la pantalla denegado por el usuario:", err);
      onCancel();
    }
  }

  detenerCaptura() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    console.log("👁️ [ScreenCapturer] Matriz óptica apagada y liberada con éxito.");
  }
}
