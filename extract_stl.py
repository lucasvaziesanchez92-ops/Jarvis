import re
import base64

with open(r'C:\Users\First\Documents\Python Projects\javis0.0\jarvis-next\New folder (2)\thinking-agent\index-standalone.html', 'r', encoding='utf-8') as f:
    html = f.read()

match = re.search(r'const stlUri="data:model/stl;base64,([^"]+)"', html)
if match:
    b64_data = match.group(1)
    stl_data = base64.b64decode(b64_data)
    with open(r'C:\Users\First\Documents\Python Projects\javis0.0\jarvis-next\web-next\public\models\brain.stl', 'wb') as out_f:
        out_f.write(stl_data)
    print("STL extracted and saved successfully.")
else:
    print("Could not find base64 STL data in html.")
