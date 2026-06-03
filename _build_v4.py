import json, os

p = r'C:\Users\First\Documents\Python Projects\javis0.0\jarvis\brain_vertices.json'
with open(p) as f:
    data = json.load(f)

verts = data['positions']
print(f'Loaded {len(verts)//3} vertices')

# Build inline JS array (5000 particles to balance quality vs file size)
js_array = ','.join(f'{v:.6f}' for v in verts[:5000])
print(f'JS array length: {len(js_array)} chars')

# Read the v3 template
html_path = r'C:\Users\First\Documents\Python Projects\javis0.0\jarvis\brain_v3.html'
with open(html_path) as f:
    html = f.read()

# Replace the fetch block with inline vertices
old_block = """fetch('brain_vertices.json')
    .then(function(r){ return r.json(); })
    .then(function(data){
      log('[2/4] Modelo cargado: '+data.count.toLocaleString()+' particulas');
      buildBrain(data.positions);
      document.getElementById('loader').classList.add('hidden');
    })
    .catch(function(e){
      log('[ERROR] No pude cargar brain_vertices.json: '+e.message);
      log('Intenta ejecutar: python preprocess_stl.py');
    });"""

new_block = f"""var BRAIN_VERTICES = [{js_array}];
    log('[2/4] Modelo embebido: '+(BRAIN_VERTICES.length/3).toLocaleString()+' particulas');
    buildBrain(BRAIN_VERTICES);
    document.getElementById('loader').classList.add('hidden');"""

if old_block in html:
    html = html.replace(old_block, new_block)
    print('Replaced fetch block with inline vertices')
else:
    print('WARNING: Could not find exact fetch block, trying partial match...')
    # Fallback: find the start of fetch and replace from there
    import re
    pattern = r"fetch\('brain_vertices\.json'\)[\s\S]*?\.catch\(function\(e\)\{[\s\S]*?}\);"
    html = re.sub(pattern, new_block, html)
    print('Replaced via regex')

out_path = r'C:\Users\First\Documents\Python Projects\javis0.0\jarvis\brain_v4.html'
with open(out_path, 'w') as f:
    f.write(html)

print(f'Wrote brain_v4.html ({os.path.getsize(out_path)/1024:.0f} KB)')
