import urllib.request
import urllib.parse
import re

url = "https://search.yahoo.com/search?p=" + urllib.parse.quote("apple stock price")
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
html = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')

titles = re.findall(r'<h3 class="title"><a[^>]*>(.*?)</a></h3>', html, re.IGNORECASE)
snippets = re.findall(r'<div class="compTitle.*?<div class="compText.*?>(.*?)</div>', html, re.IGNORECASE | re.DOTALL)

for i in range(min(2, len(titles))):
    print("Title:", re.sub(r'<[^>]+>', '', titles[i]))
print("Snippets:", len(snippets))
