import sys
import urllib.parse
from scraper import get_session, get_with_retry
from bs4 import BeautifulSoup

URL = "https://www.cac.edu.tw/apply115/system/ColQry_115xappLyfOrStu_Azd5gP29/ShowSchGsd.php?colno=001"

try:
    session = get_session()
    response = get_with_retry(session, URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    links = soup.find_all('a')
    print(f"Total links on dept list page: {len(links)}")
    
    dept_links = []
    for link in links:
        href = link.get('href', '')
        if 'ShowDeptRule.php' in href or 'ShowDeptGsd.php' in href:
            dept_links.append((link.text.strip(), href))
            
    if not dept_links:
         for link in links:
             if "001" in link.get('href', ''):
                 dept_links.append((link.text.strip(), link.get('href')))

    print("Found potential dept links:")
    for text, href in dept_links[:5]:
        print(f"{text}: {href}")
        # Fetch the first one and save its HTML for analysis
        first_dept_url = urllib.parse.urljoin(URL, dept_links[0][1])
        print(f"Fetching first dept detailed page: {first_dept_url}")
        
        dept_res = get_with_retry(session, first_dept_url)
        
        with open('sample_dept.html', 'w', encoding='utf-8') as f:
            f.write(dept_res.text)
        print("Saved detailed HTML to sample_dept.html")
        break
        
except Exception as e:
    print(f"Error: {e}")

