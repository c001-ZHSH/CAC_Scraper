import requests
from bs4 import BeautifulSoup
import urllib.parse
import time

def get_session(referer="https://www.cac.edu.tw/apply115/system/ColQry_115xappLyfOrStu_Azd5gP29/TotalGsdShow.htm"):
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Referer': referer
    })
    return session

def get_with_retry(session, url, max_retries=5):
    for attempt in range(max_retries):
        try:
            response = session.get(url, timeout=15)
            response.raise_for_status()
            response.encoding = 'utf-8' # Force utf-8 as CAC usually is
            
            # Check for CAC firewall traffic limit
            if "流量過大，請稍後再試" in response.text:
                print(f"Traffic limit hit on attempt {attempt+1}. Waiting...")
                time.sleep(2 + attempt * 2)
                continue
                
            return response
        except (requests.exceptions.RequestException, ConnectionResetError) as e:
            print(f"Connection error on attempt {attempt+1}: {e}")
            time.sleep(2 + attempt * 2)
            
    raise Exception(f"Failed to fetch {url} after {max_retries} attempts.")

def fetch_universities_list(main_url):
    """
    Fetches the list of universities from the given CAC URL.
    """
    session = get_session()
    response = get_with_retry(session, main_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    links = soup.find_all('a')
    universities = []
    
    base_url_parts = urllib.parse.urlsplit(main_url)
    base_path = main_url.rsplit('/', 1)[0]
    
    for link in links:
        href = link.get('href')
        text = link.text.strip()
        
        if href and 'ShowSchGsd.php' in href and text.startswith('('):
            clean_name = " ".join(text.split())
            full_url = urllib.parse.urljoin(base_path + '/', href)
            
            parsed_href = urllib.parse.urlparse(href)
            qs = urllib.parse.parse_qs(parsed_href.query)
            colno = qs.get('colno', [''])[0]
            
            universities.append({
                'id': colno,
                'name': clean_name,
                'url': full_url
            })
            
    return universities

import re
def fetch_departments(session, univ_url):
    response = get_with_retry(session, univ_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    links = soup.find_all('a')
    dept_links = []
    
    for link in links:
        href = link.get('href', '')
        if 'ShowDeptRule.php' in href or 'ShowDeptGsd.php' in href:
            dept_links.append({
                'name': link.text.strip(),
                'url': urllib.parse.urljoin(univ_url, href)
            })
            
    if not dept_links:
         parsed = urllib.parse.urlparse(univ_url)
         qs = urllib.parse.parse_qs(parsed.query)
         colno = qs.get('colno', [''])[0]
         for link in links:
             if colno in link.get('href', ''):
                 dept_links.append({
                    'name': link.text.strip(),
                    'url': urllib.parse.urljoin(univ_url, link.get('href'))
                 })
    
    # De-duplicate by URL while preserving order
    seen_urls = set()
    unique_depts = []
    for d in dept_links:
        if d['url'] not in seen_urls:
            seen_urls.add(d['url'])
            unique_depts.append(d)
            
    return unique_depts

def parse_department_rules(session, dept_url):
    response = get_with_retry(session, dept_url)
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    data = {}

    colname_elem = soup.find('div', class_='colname')
    gsdname_elem = soup.find('div', class_='gsdname')
    
    data['學校名稱'] = colname_elem.text.strip() if colname_elem else ''
    data['學系名稱'] = gsdname_elem.text.strip() if gsdname_elem else ''

    def get_lb_rb(label):
        lb = soup.find(lambda t: t.name == 'td' and t.text and label in t.text and ('Lb' in t.get('class', []) or 'Bb' in t.get('class', [])))
        if lb:
            rb = lb.find_next_sibling('td')
            if rb:
                return rb.text.strip()
        return ''

    data['校系代碼'] = get_lb_rb('校系代碼')
    data['招生名額'] = get_lb_rb('招生名額')
    data['預計甄試人數'] = get_lb_rb('預計甄試人數')
    data['原住民外加名額'] = get_lb_rb('原住民外加名額')
    data['離島外加名額'] = get_lb_rb('離島外加名額')
    data['願景計畫外加名額'] = get_lb_rb('願景計畫外加名額')

    date_td = soup.find(lambda t: t.name == 'td' and '指定項目' in t.text and '甄試日期' in t.text)
    if date_td:
        date_val = date_td.find_next_sibling('td')
        data['指定項目甄試日期'] = date_val.text.strip() if date_val else ''
    else:
        data['指定項目甄試日期'] = ''

    target_subs = ['國文', '英文', '數學A', '數學B', '社會', '自然', '英聽']
    
    def is_subject_td(t):
        if t.name != 'td' or not t.text: return False
        rowspan = t.get('rowspan')
        if not rowspan: return False
        try:
            if int(rowspan) < 6: return False
        except ValueError:
            return False
        for sub in target_subs:
            if sub in t.text:
                return True
        return False
        
    subj_td = soup.find(is_subject_td)
    for tgt in target_subs:
        data[f'{tgt}檢定標準'] = ''
        data[f'{tgt}篩選倍率'] = ''
        data[f'{tgt}學測成績採計方式'] = ''
    data['其他科目組合名稱'] = ''
    data['檢定標準'] = ''
    data['篩選倍率'] = ''
    data['學測成績採計方式'] = ''
    data['學測佔甄選總成績比例'] = ''
    for i in range(4):
        data[f'第二階段指定項目{i+1}'] = ''

    if subj_td:
        siblings = subj_td.find_next_siblings('td', rowspan=lambda x: x and int(x) >= 6)
        subjects_text = list(subj_td.stripped_strings)
        standards = list(siblings[0].stripped_strings) if len(siblings) > 0 else []
        multipliers = list(siblings[1].stripped_strings) if len(siblings) > 1 else []
        scores = list(siblings[2].stripped_strings) if len(siblings) > 2 else []
        
        ratio = list(siblings[3].stripped_strings) if len(siblings) > 3 else []
        data['學測佔甄選總成績比例'] = ratio[0] if ratio else ''
        
        items = list(siblings[4].stripped_strings) if len(siblings) > 4 else []
        for i in range(4):
            data[f'第二階段指定項目{i+1}'] = items[i] if i < len(items) else ''

        other_names_list = []
        other_stds_list = []
        other_mults_list = []
        other_scores_list = []

        for i, subj in enumerate(subjects_text):
            if subj in target_subs:
                data[f'{subj}檢定標準'] = standards[i] if i < len(standards) else ''
                mult = multipliers[i] if i < len(multipliers) else ''
                data[f'{subj}篩選倍率'] = '' if mult == '--' else mult
                score = scores[i] if i < len(scores) else ''
                data[f'{subj}學測成績採計方式'] = '' if score == '--' else score
            else:
                other_names_list.append(subj)
                std = standards[i] if i < len(standards) else ''
                other_stds_list.append('' if std == '--' else std)
                mult = multipliers[i] if i < len(multipliers) else ''
                other_mults_list.append('' if mult == '--' else mult)
                score = scores[i] if i < len(scores) else ''
                other_scores_list.append('' if score == '--' else score)
                
        if other_names_list:
            data['其他科目組合名稱'] = ' / '.join(other_names_list)
            data['檢定標準'] = ' / '.join(other_stds_list)
            data['篩選倍率'] = ' / '.join(other_mults_list)
            data['學測成績採計方式'] = ' / '.join(other_scores_list)

    for char in "ABCDEFGHIJKLMNOPQRST":
        data[f'審查資料項目{char}'] = ''
        
    project_div = soup.find(lambda tag: tag.name == 'div' and tag.text.strip() == '項目：')
    if project_div:
        content_div = project_div.find_next_sibling('div')
        if content_div:
            text = content_div.text
            matches = re.findall(r'[A-T]', text)
            for m in set(matches):
                data[f'審查資料項目{m}'] = 'true'
                
    data['甄選總成績同分參酌之順序1'] = ''
    data['甄選總成績同分參酌之順序2'] = ''
    data['甄選總成績同分參酌之順序3'] = ''
    data['甄選總成績同分參酌之順序4'] = ''
    
    tie_td = soup.find(lambda t: t.name == 'td' and t.text and '一、' in t.text and '二、' in t.text)
    if tie_td:
        lines = list(tie_td.stripped_strings)
        for i, line in enumerate(lines[:4]):
            clean_line = re.sub(r'^[一二三四五六七八九十]+、', '', line)
            if clean_line == '(無)':
                clean_line = ''
            data[f'甄選總成績同分參酌之順序{i+1}'] = clean_line
            
    # Clean up any remaining '--' in the dictionary values
    for k in data.keys():
        if data[k] == '--':
            data[k] = ''
            
    return data
