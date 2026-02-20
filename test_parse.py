from bs4 import BeautifulSoup
import re

def parse_html(html_path):
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    soup = BeautifulSoup(html, 'html.parser')
    data = {}

    # Basic Info
    colname_elem = soup.find('div', class_='colname')
    gsdname_elem = soup.find('div', class_='gsdname')
    
    data['學校名稱'] = colname_elem.text.strip() if colname_elem else ''
    data['學系名稱'] = gsdname_elem.text.strip() if gsdname_elem else ''

    # Helper for simple Lb-Rb pairs
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

    # Date
    date_td = soup.find(lambda t: t.name == 'td' and '指定項目' in t.text and '甄試日期' in t.text)
    if date_td:
        date_val = date_td.find_next_sibling('td')
        data['指定項目甄試日期'] = date_val.text.strip() if date_val else ''
    else:
        data['指定項目甄試日期'] = ''

    # Subjects Table (Rowspan block)
    # The subject table rows are typically marked by class 'g3' or similar.
    # Let's find the td containing 國文 and 英文 inside 'g3' text.
    subj_td = soup.find(lambda t: t.name == 'td' and t.text and '國文' in t.text and 'g3' in t.get('class', []))
    
    if subj_td:
        # siblings: 檢定 (standards), 倍率 (multipliers), 採計 (scores), % (ratio), items (items), item_standards, item_ratios
        # It's actually safer to just grab the next 7 siblings with rowspan=7 (if ratio is one of them)
        siblings = subj_td.find_next_siblings('td', rowspan=lambda x: x and int(x) >= 6)
        
        subjects_text = list(subj_td.stripped_strings)
        standards = list(siblings[0].stripped_strings) if len(siblings) > 0 else []
        multipliers = list(siblings[1].stripped_strings) if len(siblings) > 1 else []
        scores = list(siblings[2].stripped_strings) if len(siblings) > 2 else []
        
        ratio = list(siblings[3].stripped_strings) if len(siblings) > 3 else []
        data['學測佔甄選總成績比例'] = ratio[0] if ratio else ''
        
        items = list(siblings[4].stripped_strings) if len(siblings) > 4 else []
        for i in range(4): # up to 4 items
            data[f'第二階段指定項目{i+1}'] = items[i] if i < len(items) else ''
        
        # Mapping subjects
        target_subs = ['國文', '英文', '數學A', '數學B', '社會', '自然', '其他科目組合']
        
        for tgt in target_subs:
            data[f'{tgt}檢定標準'] = ''
            data[f'{tgt}篩選倍率'] = ''
            data[f'{tgt}學測成績採計方式'] = ''

        for i, subj in enumerate(subjects_text):
            if subj in target_subs:
                prefix = subj
            else:
                prefix = '其他科目組合'
                
            data[f'{prefix}檢定標準'] = standards[i] if i < len(standards) else ''
            
            # CAC often uses `--` to mean nothing
            mult = multipliers[i] if i < len(multipliers) else ''
            data[f'{prefix}篩選倍率'] = '' if mult == '--' else mult
            
            score = scores[i] if i < len(scores) else ''
            data[f'{prefix}學測成績採計方式'] = '' if score == '--' else score
            
    # Review Items (A-T)
    # Look for "項目：" inside the html
    for char in "ABCDEFGHIJKLMNOPQRST":
        data[f'審查資料項目{char}'] = ''
        
    project_div = soup.find(lambda tag: tag.name == 'div' and tag.text.strip() == '項目：')
    if project_div:
        content_div = project_div.find_next_sibling('div')
        if content_div:
            text = content_div.text
            # Use regex to find letters between parentheses or brackets
            # Like: 修課紀錄(A)、課程學習成果(B、C、D) -> extract A, B, C, D
            # Actually, standard string search in the text might just work since it's A-T, but we want to avoid matching words.
            # CAC puts them in English uppercase.
            import re
            matches = re.findall(r'[A-T]', text)
            for m in set(matches):
                data[f'審查資料項目{m}'] = 'true'
                
    # Tie Breaker Order
    # <td class="Rb" rowspan="4" style="text-align:left;vertical-align:text-top;">一、學科能力測驗成績<br>二、語文測驗筆試<br>三、寫作筆試</td>
    data['甄選總成績同分參酌之順序1'] = ''
    data['甄選總成績同分參酌之順序2'] = ''
    data['甄選總成績同分參酌之順序3'] = ''
    
    # We can search for text "一、" inside a td with rowspan >= 3
    tie_td = soup.find(lambda t: t.name == 'td' and t.text and '一、' in t.text and '二、' in t.text)
    if tie_td:
        lines = list(tie_td.stripped_strings)
        for i, line in enumerate(lines[:3]):
            # remove prefix like "一、"
            clean_line = re.sub(r'^[一二三四五六七八九十]+、', '', line)
            data[f'甄選總成績同分參酌之順序{i+1}'] = clean_line
            
    return data

if __name__ == "__main__":
    result = parse_html('sample_dept.html')
    for k, v in result.items():
        print(f"{k}: {v}")
