import subprocess
import os
import webbrowser
import sys

def main():
    project_root = os.path.dirname(os.path.abspath(__file__))
    web_dir = os.path.join(project_root, 'web')
    
    if not os.path.exists(web_dir):
        print('[X] ERROR: No se encontro la carpeta web/')
        print('    Ejecuta este script desde el root del proyecto.')
        input('Presiona ENTER para salir...')
        return
    
    os.chdir(web_dir)
    
    # Build si no existe dist/brain.html
    dist_brain = os.path.join('dist', 'brain.html')
    if not os.path.exists(dist_brain):
        print('[*] Compilando frontend (primera vez)...')
        print('    Esto tarda ~10 segundos.')
        result = subprocess.run(['npm', 'run', 'build'], shell=True)
        if result.returncode != 0:
            print('[X] Error de compilacion.')
            input('Presiona ENTER para salir...')
            return
    else:
        print('[OK] Build ya existente.')
    
    print()
    print('=' * 50)
    print('   JARVIS NEURAL BRAIN')
    print('   Cerebro 3D interactivo')
    print('=' * 50)
    print()
    print('[*] URLs disponibles:')
    print('    http://localhost:8765/brain.html   (Solo Cerebro)')
    print('    http://localhost:8765/index.html   (App completa)')
    print()
    
    # Abrir navegador
    webbrowser.open('http://localhost:8765/brain.html')
    
    # Iniciar servidor Vite Preview
    print('[*] Iniciando servidor en puerto 8765...')
    print('[*] Presiona Ctrl+C para detener.')
    print()
    
    try:
        subprocess.run(['npx', 'vite', 'preview', '--port', '8765', '--host'], shell=True)
    except KeyboardInterrupt:
        print()
        print('[*] Servidor detenido.')

if __name__ == '__main__':
    main()
