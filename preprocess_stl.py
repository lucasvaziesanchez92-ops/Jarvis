#!/usr/bin/env python3
"""
Procesa model.stl (Cerebro 3D real) y exporta vertices muestreados
para usar como particulas en Three.js (brain_v3.html)
"""
import struct, json, os, sys

STL_PATH = r"C:\Users\First\Downloads\model.stl"
JSON_OUT = os.path.join(os.path.dirname(__file__), "brain_vertices.json")
TARGET_VERTICES = 8000  # cantidad de particulas (rendimiento visual optimo)

def parse_binary_stl(path):
    with open(path, 'rb') as f:
        data = f.read()

    # 80 bytes header + 4 bytes face count
    face_count = struct.unpack('<I', data[80:84])[0]
    print(f"[STL] Rostros (faces): {face_count:,}")
    print(f"[STL] Vertices totales: {face_count * 3:,}")

    vertices = []
    offset = 84
    for i in range(face_count):
        # 12 bytes normal (float32 x3)
        # 36 bytes vertices (float32 x9)
        # 2 bytes atribute byte count
        v_start = offset + 12
        vx1, vy1, vz1 = struct.unpack('<fff', data[v_start:v_start+12])
        vx2, vy2, vz2 = struct.unpack('<fff', data[v_start+12:v_start+24])
        vx3, vz3, vy3 = struct.unpack('<fff', data[v_start+24:v_start+36])
        # Nota: algunos STLs tienen Y/Z invertida; ajustamos si es necesario luego
        vertices.extend([vx1, vy1, vz1, vx2, vy2, vz2, vx3, vy3, vz3])
        offset += 50
        if i % 500000 == 0 and i > 0:
            print(f"[STL] Procesados {i:,} rostros...")

    return vertices

def subsample_uniform(vertices, target):
    """Muestrea uniformemente N vertices de la lista"""
    total = len(vertices) // 3
    if total <= target:
        return vertices
    step = total / target
    sampled = []
    for i in range(target):
        idx = int(i * step) * 3
        sampled.extend([vertices[idx], vertices[idx+1], vertices[idx+2]])
    print(f"[SAMPLE] Vertices finales: {len(sampled)//3:,}")
    return sampled

def normalize_and_center(vertices):
    """Centra en origen y normaliza escala para Three.js"""
    xs = []; ys = []; zs = []
    for i in range(0, len(vertices), 3):
        xs.append(vertices[i])
        ys.append(vertices[i+1])
        zs.append(vertices[i+2])

    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    minz, maxz = min(zs), max(zs)

    cx = (minx + maxx) / 2
    cy = (miny + maxy) / 2
    cz = (minz + maxz) / 2

    # Normalizar a escala ~3.0 unidades (para que quepa bien en camara Three.js)
    scale = 3.0 / max(maxx-minx, maxy-miny, maxz-minz)

    out = []
    for i in range(0, len(vertices), 3):
        out.append((vertices[i]   - cx) * scale)
        out.append((vertices[i+1] - cy) * scale)
        out.append((vertices[i+2] - cz) * scale)

    print(f"[NORMALIZE] Rango: X[{minx:.1f},{maxx:.1f}] Y[{miny:.1f},{maxy:.1f}] Z[{minz:.1f},{maxz:.1f}]")
    print(f"[NORMALIZE] Centro: ({cx:.2f}, {cy:.2f}, {cz:.2f})  Escala: {scale:.4f}")
    return out

def main():
    if not os.path.exists(STL_PATH):
        print(f"ERROR: No se encontro {STL_PATH}")
        sys.exit(1)

    print(f"[INFO] Leyendo STL de {os.path.getsize(STL_PATH)/(1024*1024):.1f} MB...")
    raw_verts = parse_binary_stl(STL_PATH)
    sampled = subsample_uniform(raw_verts, TARGET_VERTICES)
    normalized = normalize_and_center(sampled)

    data = {
        "count": len(normalized) // 3,
        "positions": normalized,
        "format": "float32 array [x,y,z,...]"
    }
    with open(JSON_OUT, 'w') as f:
        json.dump(data, f)

    print(f"\n[EXITO] Guardado: {JSON_OUT}")
    print(f"[INFO] Tamano JSON: {os.path.getsize(JSON_OUT)/1024:.1f} KB")
    print("[INFO] Ahora abri brain_v3.html para ver el cerebro de particulas")

if __name__ == "__main__":
    main()
