from scraper import get_session, fetch_departments, fetch_universities_list, parse_department_rules

url114 = 'https://www.cac.edu.tw/apply114/system/ColQry_114applyXForStu_Fd87eO2q/TotalGsdShow.htm'
# fetch univs
univs = fetch_universities_list(url114)
print(f"Found {len(univs)} universities in 114")

soochow = [u for u in univs if '東吳' in u['name']][0]
print("Soochow URL:", soochow['url'])

session = get_session(referer=url114)
depts = fetch_departments(session, soochow['url'])
print(f"Found {len(depts)} departments in Soochow 114")

if depts:
    target = [d for d in depts if '中國' in d['name'] or '005012' in d['url']][0]
    print(f"Target Dept: {target['name']} -> {target['url']}")
    
    # Save the HTML for analysis
    from scraper import get_with_retry
    r = get_with_retry(session, target['url'])
    with open('soochow_chinese_114.html', 'w', encoding='utf-8') as f:
        f.write(r.text)
    print("Saved HTML")
    
    # Try parsing
    res = parse_department_rules(session, target['url'])
    for k, v in res.items():
        if v:
            print(f"{k}: {v}")
