import re

html = open('ddg.html', encoding='utf-8').read()
results = re.findall(r'<div class="result.*?>(.*?)</div>\s*</div>', html, re.DOTALL)
for i, res in enumerate(results[:5]):
    title = re.search(r'<h2 class="result__title">.*?<a[^>]*>(.*?)</a>', res, re.IGNORECASE | re.DOTALL)
    snippet = re.search(r'<a class="result__snippet[^>]*>(.*?)</a>', res, re.IGNORECASE | re.DOTALL)
    is_ad = "result--ad" in res or "badge--ad" in res
    print(f"Result {i}: Ad={is_ad}")
    if title: print("Title:", re.sub(r'<[^>]+>', '', title.group(1)).strip())
    if snippet: print("Snippet:", re.sub(r'<[^>]+>', '', snippet.group(1)).strip())
    print("-" * 20)
