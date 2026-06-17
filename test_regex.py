import re

text = """
Aquí tienes el output JSON:
[
  { "a": 1 },
  { "b": 2 }
]
"""

match = re.search(r'\[\s*\{.*?\}\s*\]', text, re.DOTALL)
print("MATCH:", match.group(0) if match else "None")
