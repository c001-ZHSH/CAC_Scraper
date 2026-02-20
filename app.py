from flask import Flask, render_template, request, jsonify, Response, send_from_directory
import time
import os
import json
import pandas as pd
from scraper import fetch_universities_list, fetch_departments, parse_department_rules, get_session

import sys
import threading
import webbrowser

# Adjust PyInstaller paths
if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    app = Flask(__name__)

app.secret_key = 'cac_scraper_secret'

def open_browser():
    time.sleep(1.5)
    webbrowser.open('http://127.0.0.1:5000')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/fetch_universities', methods=['POST'])
def fetch_univs():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({'error': '請提供網址'}), 400
        
    try:
        universities = fetch_universities_list(url)
        return jsonify({'universities': universities})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scrape', methods=['POST'])
def scrape_selection():
    data = request.json
    selected_universities = data.get('universities', [])
    base_url = data.get('base_url')
    
    if not selected_universities:
        return jsonify({'error': '未選擇任何大學'}), 400

    def generate():
        try:
            session = get_session()
            total_univs = len(selected_universities)
            start_data = json.dumps({'type': 'start', 'total': total_univs})
            yield f"data: {start_data}\n\n"
            
            all_results = []
            
            for i, univ in enumerate(selected_universities):
                msg1 = f"正在擷取 【{univ['name']}】 的學系列表..."
                prog_data1 = json.dumps({'type': 'progress', 'current': i, 'total': total_univs, 'message': msg1})
                yield f"data: {prog_data1}\n\n"
                
                try:
                    depts = fetch_departments(session, univ['url'])
                except Exception as e:
                    msg_err = f"擷取 【{univ['name']}】 失敗: {str(e)}"
                    err_data = json.dumps({'type': 'progress', 'current': i, 'total': total_univs, 'message': msg_err})
                    yield f"data: {err_data}\n\n"
                    continue
                
                for j, dept in enumerate(depts):
                    msg2 = f"擷取 【{univ['name']}】: {dept['name']}..."
                    prog_data2 = json.dumps({'type': 'progress', 'current': i + (j/len(depts)), 'total': total_univs, 'message': msg2})
                    yield f"data: {prog_data2}\n\n"
                    
                    try:
                        details = parse_department_rules(session, dept['url'])
                        if not details.get('學校名稱'):
                            details['學校名稱'] = univ['name']
                        if not details.get('學系名稱'):
                            details['學系名稱'] = dept['name']
                            
                        all_results.append(details)
                    except Exception as e:
                        print(f"Error parsing {dept['url']}: {e}")
                        
                    time.sleep(0.5) # Gentle rate limiting
                    
            cols = ['學校名稱', '學系名稱', '校系代碼', '招生名額', '預計甄試人數', '原住民外加名額', '離島外加名額', '願景計畫外加名額', '指定項目甄試日期', '國文檢定標準', '國文篩選倍率', '國文學測成績採計方式', '英文檢定標準', '英文篩選倍率', '英文學測成績採計方式', '數學A檢定標準', '數學A篩選倍率', '數學A學測成績採計方式', '數學B檢定標準', '數學B篩選倍率', '數學B學測成績採計方式', '社會檢定標準', '社會篩選倍率', '社會學測成績採計方式', '自然檢定標準', '自然篩選倍率', '自然學測成績採計方式', '英聽檢定標準', '英聽篩選倍率', '英聽學測成績採計方式', '其他科目組合名稱', '檢定標準', '篩選倍率', '學測成績採計方式', '學測佔甄選總成績比例', '第二階段指定項目1', '第二階段指定項目2', '第二階段指定項目3', '第二階段指定項目4']
            for char in "ABCDEFGHIJKLMNOPQRST":
                cols.append(f'審查資料項目{char}')
            cols.extend(['甄選總成績同分參酌之順序1', '甄選總成績同分參酌之順序2', '甄選總成績同分參酌之順序3', '甄選總成績同分參酌之順序4'])
            
            df = pd.DataFrame(all_results)
            df = df.reindex(columns=cols, fill_value='')
            
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
            else:
                base_dir = os.path.abspath(os.path.dirname(__name__))
                
            downloads_dir = os.path.join(base_dir, 'static', 'downloads')
            os.makedirs(downloads_dir, exist_ok=True)
            
            csv_filename = "cac_rules.csv"
            csv_path = os.path.join(downloads_dir, csv_filename)
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            
            complete_data = json.dumps({'type': 'complete', 'download_url': f'/static/downloads/{csv_filename}'})
            yield f"data: {complete_data}\n\n"
            
        except Exception as e:
            error_data = json.dumps({'type': 'error', 'message': str(e)})
            yield f"data: {error_data}\n\n"

    return Response(generate(), mimetype='text/event-stream')

@app.route('/static/downloads/<path:filename>')
def download_file(filename):
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.abspath(os.path.dirname(__name__))
    downloads_dir = os.path.join(base_dir, 'static', 'downloads')
    return send_from_directory(downloads_dir, filename, as_attachment=True)

if __name__ == '__main__':
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(port=5000)
