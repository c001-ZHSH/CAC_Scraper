import requests
from bs4 import BeautifulSoup
import sys

URL = "https://www.cac.edu.tw/apply115/system/ColQry_115xappLyfOrStu_Azd5gP29/TotalGsdShow.htm"
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

try:
    print(f"Fetching {URL}...")
    response = requests.get(URL, headers=headers, timeout=10)
    response.raise_for_status()
    print("Success! Encoding:", response.encoding)
    response.encoding = 'utf-8' # or big5 if needed, will check content
    content = response.text
    
    soup = BeautifulSoup(content, 'html.parser')
    links = soup.find_all('a')
    print(f"Found {len(links)} links. Top 5:")
    for link in links[:5]:
        print(f" - Text: {link.text.strip()}, Href: {link.get('href')}")
        
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
