import os
import re

filepath = r"c:\Users\First\Documents\Python Projects\javis0.0\jarvis-next\web-next\public\brain-standalone.html"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Replace ThinkingBubble z-index in the file if it exists there, but actually ThinkingBubble is a React component.
# I will modify brain-standalone.html material.

# We need to find the brainMaterial definition and replace it.
# It currently looks like:
# const brainMaterial = new THREE.MeshPhysicalMaterial({ ... });

regex = r"const brainMaterial = new THREE\.MeshPhysicalMaterial\(\{.*?\}\);"

new_mat = """const brainMaterial = new THREE.MeshPhysicalMaterial({
            color: 0xc26694, // Dusty rose/pink
            emissive: 0x220011, // Very subtle dark pink emissive
            emissiveIntensity: 0.2,
            metalness: 0.1,
            roughness: 0.25, // Slightly rough to catch light on the facets
            transmission: 0.65, // Translucent but substantial
            transparent: true,
            opacity: 0.85,
            thickness: 1.5,
            ior: 1.45,
            clearcoat: 0.3,
            clearcoatRoughness: 0.2,
            envMap: envMap,
            envMapIntensity: 1.2,
            side: THREE.DoubleSide,
            flatShading: true, // CRITICAL: This gives the faceted low-poly look from the screenshot
        });"""

content = re.sub(regex, new_mat, content, flags=re.DOTALL)

# Let's also make sure the background particles match the cyan/pink vibe
# The particles are handled somewhere else in the HTML or React?
# In brain-standalone.html, there's a particle system? Let's check if there is one.
# If not, I'll just write the file.

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Brain material updated for faceted dusty pink look.")
