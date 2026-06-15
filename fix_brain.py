import os

filepath = r"c:\Users\First\Documents\Python Projects\javis0.0\jarvis-next\web-next\public\brain-standalone.html"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

old_mat = """        const brainMaterial = new THREE.MeshPhysicalMaterial({
            color: 0xff88cc,
            emissive: 0xaa2266,
            emissiveIntensity: 0.4,
            roughness: 0.15,
            metalness: 0.3,
            transmission: 0.8,
            opacity: 0.9,
            transparent: true,
            ior: 1.4,
            thickness: 0.2,
            wireframe: false,
        });"""

new_mat = """        const brainMaterial = new THREE.MeshPhysicalMaterial({
            color: 0x4a152e,
            emissive: 0xff3399,
            emissiveIntensity: 0.15,
            roughness: 0.05,
            metalness: 0.2,
            transmission: 0.95,
            opacity: 1,
            transparent: true,
            ior: 1.5,
            thickness: 0.5,
            wireframe: false,
        });"""

# also scale it down
old_scale = "model.scale.set(12, 12, 12);"
new_scale = "model.scale.set(10, 10, 10);"

content = content.replace(old_mat, new_mat)
content = content.replace(old_scale, new_scale)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Brain replaced successfully")
