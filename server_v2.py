#!/usr/bin/env python3
"""
AI Lab CoPilot - 輕量升級版
加入：
- 年份過濾（近4年）
- 改進萃取邏輯
- 對話式 UI
"""

import os
import requests
import json
import re
from flask import Flask, render_template, request, jsonify, session
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'ai-lab-copilot-secret-key'

# Favicon 路由
@app.route('/favicon.svg')
def favicon():
    from flask import send_from_directory
    return send_from_directory('.', 'favicon.svg', mimetype='image/svg+xml')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename) = 'ai-lab-copilot-secret-key'

# API 配置
PUBMED_API_KEY = "475cc6bec6ab03e64d2acc533b97bd641609"

def search_pubmed(query, max_results=5):
    """搜尋 PubMed - 支援中英文，自動轉換"""
    current_year = datetime.now().year
    year_filter = f"{current_year-4}:{current_year}[DP]"
    # 先用4年
    year_filter_4y = year_filter
    year_filter_10y = f"{current_year-10}:{current_year}[DP]"
    
    # 中英文關鍵字映射
    translation = {
        '細胞': 'cell',
        '培養': 'culture',
        '如何': '',
        '什麼': '',
        '怎麼': '',
        '搜尋': '',
        '找': '',
        '卵巢': 'ovarian',
        '肺癌': 'lung cancer',
        '乳癌': 'breast cancer',
        '肝癌': 'liver cancer',
        '攝護腺': 'prostate',
        '白血病': 'leukemia',
        '結腸': 'colon',
        '直腸': 'rectal',
        '遷移': 'migration',
        '侵襲': 'invasion',
        '傷口': 'wound',
        '癒合': 'healing',
        '萃取': 'extraction',
        '純化': 'purification',
        '轉染': 'transfection',
        '轉染': 'transduction',
        '病毒': 'virus',
        '蛋白': 'protein',
        '基因': 'gene',
        'RNA': 'RNA',
        'DNA': 'DNA',
        '西方墨點': 'western blot',
        'PCR': 'PCR',
        '流式': 'flow cytometry',
        '紫杉醇': 'paclitaxel',
        '順鉑': 'cisplatin',
        '卡鉑': 'carboplatin',
        '阿黴素': 'doxorubicin',
    }
    
    # 翻譯並分割關鍵字
    search_query = query
    for cn, en in translation.items():
        search_query = search_query.replace(cn, en)
    
    # 分割成關鍵字，用 OR 連接
    keywords = search_query.split()
    if len(keywords) > 1:
        search_query = " OR ".join(keywords)
    
    # 如果翻譯後跟原本不一樣，用翻譯版
    if search_query != query:
        enhanced_query = f"({search_query}) AND {year_filter}"
    else:
        enhanced_query = f"{query} AND {year_filter}"
    
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": enhanced_query,
        "retmode": "json",
        "retmax": max_results,
        "api_key": PUBMED_API_KEY,
        "sort": "relevance"
    }
    
    response = requests.get(url, params=params)
    data = response.json()
    results = data.get("esearchresult", {}).get("idlist", [])
    
    # 如果4年沒找到，放寬到10年
    if not results:
        year_filter = f"{current_year-10}:{current_year}[DP]"
        if search_query != query:
            enhanced_query = f"({search_query}) AND {year_filter}"
        else:
            enhanced_query = f"{query} AND {year_filter}"
        params["term"] = enhanced_query
        response = requests.get(url, params=params)
        data = response.json()
        results = data.get("esearchresult", {}).get("idlist", [])
    
    # 如果10年也沒找到，搜全部
    if not results:
        if search_query != query:
            enhanced_query = f"({search_query})"
        else:
            enhanced_query = query
        params["term"] = enhanced_query
        response = requests.get(url, params=params)
        data = response.json()
        results = data.get("esearchresult", {}).get("idlist", [])
    
    return results

def fetch_paper_details(pmids):
    """擷取論文詳細內容"""
    if not pmids:
        return []
    
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        "api_key": PUBMED_API_KEY
    }
    
    response = requests.get(url, params=params)
    return response.text

def parse_papers(xml_data):
    """解析 XML"""
    papers = []
    articles = re.findall(r'<PubmedArticle>(.*?)</PubmedArticle>', xml_data, re.DOTALL)
    
    for article in articles[:5]:
        paper = {}
        
        pmid_match = re.search(r'<PMID[^>]*>(.*?)</PMID>', article)
        paper['pmid'] = pmid_match.group(1) if pmid_match else ""
        
        title_match = re.search(r'<ArticleTitle>(.*?)</ArticleTitle>', article)
        paper['title'] = title_match.group(1) if title_match else ""
        
        abstract_match = re.search(r'<AbstractText[^>]*>(.*?)</AbstractText>', article)
        paper['abstract'] = abstract_match.group(1) if abstract_match else ""
        
        journal_match = re.search(r'<Journal><Title>(.*?)</Title>', article)
        paper['journal'] = journal_match.group(1) if journal_match else ""
        
        year_match = re.search(r'<PubDate><Year>(\d{4})</Year>', article)
        paper['year'] = year_match.group(1) if year_match else ""
        
        doi_match = re.search(r'<ELocationID[^>]*doi[^>]*>(.*?)</ELocationID>', article)
        paper['doi'] = doi_match.group(1) if doi_match else ""
        
        papers.append(paper)
    
    return papers

def extract_methodology(paper):
    """萃取實驗方法 - 通用版本"""
    abstract = paper.get('abstract', '')
    title = paper.get('title', '')
    combined = f"{title} {abstract}"
    
    methodology = {
        "cell_line": "",
        "drug": "",
        "concentration": "",
        "method": "",
        "duration": ""
    }
    
    # 細胞株 - 全面模式
    cell_patterns = [
        r'([A-Z][a-z]+\d*[a-z]*(?:\s*株|\s*cell|\s*cells?))',
        r'(HeLa|MCF-7|A549|HUVEC|1A9|A2780|OVCAR-3|ES-2|MES-OV|K562|HepG2|MDA-MB-231|SK-OV-3)',
    ]
    for pattern in cell_patterns:
        match = re.search(pattern, combined, re.IGNORECASE)
        if match:
            methodology['cell_line'] = match.group(1)
            break
    
    # 藥物/試劑
    drug_patterns = [
        r'(paclitaxel|docetaxel|zampanolide|peloruside|ixabepilone)',
        r'(TRIzol|chloroform|isopropanol|ethanol|DMSO)',
        r'(doxorubicin| cisplatin|carboplatin)',
    ]
    for pattern in drug_patterns:
        match = re.search(pattern, combined, re.IGNORECASE)
        if match:
            methodology['drug'] = match.group(1)
            break
    
    # 濃度
    conc_match = re.search(r'(\d+(?:\.\d+)?)\s*(μM|mM|nM|M|g\/L|mg\/mL|µg\/mL)', combined, re.IGNORECASE)
    if conc_match:
        methodology['concentration'] = f"{conc_match.group(1)} {conc_match.group(2)}"
    
    # 實驗方法
    method_patterns = [
        r'(wound\s*healing|scratch\s*assay)',
        r'(cell\s*(migration|invasion)\s*assay)',
        r'(transwell)',
        r'(western\s*blot|WB)',
        r'(RT-PCR|qPCR)',
        r'(RNA\s*extraction|TRIzol)',
        r'(MTT|MTS|WST|CCK-8)',
        r'(flow\s*cytometry)',
    ]
    for pattern in method_patterns:
        match = re.search(pattern, combined, re.IGNORECASE)
        if match:
            methodology['method'] = match.group(1)
            break
    
    # 時間
    time_match = re.search(r'(\d+)\s*(hours?|h|minutes?|min|overnight)', combined, re.IGNORECASE)
    if time_match:
        methodology['duration'] = time_match.group(0)
    
    return methodology

def process_message(user_message):
    """處理用戶訊息"""
    papers = []
    response = ""
    msg_lower = user_message.lower()
    
    # 判斷意圖
    if any(k in msg_lower for k in ['搜尋', '找', '論文', 'paper', 'search', '文獻']):
        intent = "搜尋"
    elif any(k in msg_lower for k in ['sop', '流程', '步驟', '怎麼做', 'protocol', '教學']):
        intent = "SOP"
    else:
        intent = "both"
    
    # 提取搜尋關鍵字
    search_terms = re.findall(r'[\w]+', user_message)
    search_term = ' '.join(search_terms[:5])
    
    if not search_term:
        search_term = user_message
    
    # 搜尋論文
    pmids = search_pubmed(search_term, 5)
    if pmids:
        xml_data = fetch_paper_details(pmids)
        papers = parse_papers(xml_data)
    
    # 生成回覆 - 永遠生成 SOP（如果找到論文）
    if intent == "搜尋" and papers:
        # 改為同時生成 SOP
        intent = "both"
    
    if intent == "搜尋":
        if papers:
            response = "📚 找到以下相關文獻：\n\n"
            for i, p in enumerate(papers, 1):
                response += f"【{i}】{p['title']}\n"
                response += f"   PMID: {p['pmid']} | {p['journal']} ({p['year']})\n"
                response += f"   DOI: https://doi.org/{p['doi']}\n\n"
        else:
            response = "抱歉，找不到相關文獻。請試試其他關鍵字。"
    
    if intent == "SOP" or intent == "both":
        # 生成 SOP - 先分析論文內容，再生成
        sop_intro = "📋 根據文獻資料，以下是實驗流程：\n\n" if papers else "📋 以下是實驗流程：\n\n"
        
        # 從論文摘要提取關鍵資訊
        extracted_info = {}
        if papers:
            for p in papers[:3]:
                abstract = p.get('abstract', '')
                # 提取細胞株
                cells = re.findall(r'([A-Z][a-z]+\d*[a-z]*(?:cell|cells|Line))', abstract, re.IGNORECASE)
                if cells:
                    extracted_info['cells'] = list(set(cells))[:3]
                # 提取藥物
                drugs = re.findall(r'((?:paclitaxel|docetaxel|cisplatin|carboplatin|doxorubicin)\w*)', abstract, re.IGNORECASE)
                if drugs:
                    extracted_info['drugs'] = list(set(drugs))[:3]
                # 提取濃度
                concs = re.findall(r'(\d+(?:\.\d+)?\s*(?:nM|μM|mM|μg/ml|mg/ml))', abstract, re.IGNORECASE)
                if concs:
                    extracted_info['concentrations'] = list(set(concs))[:3]
        
        if any(k in msg_lower for k in ['rna', '萃取', 'extraction']):
            sop = """
【RNA 萃取標準流程】

📌 實驗概述：
從細胞或組織中提取總 RNA

📦 所需材料：
• TRIzol 試劑
• 氯仿 (Chloroform)
• 異丙醇 (Isopropanol)
• 75% 乙醇
• DEPC 處理水
• 離心管 (1.5 mL)

📝 詳細步驟：

Day 1 - 樣品準備
1. 收集細胞 (1-5 × 10⁶)
2. 加入 1 mL TRIzol
3. 室溫孵育 5 分鐘

Day 2 - RNA 分離
1. 加入 200 μL 氯仿
2. 室溫孵育 2-3 分鐘
3. 離心 15 分鐘 (12,000 g, 4°C)
4. 取上清 (約 500 μL)

Day 2 - RNA 沉澱
1. 加入 500 μL 異丙醇
2. 室溫孵育 10 分鐘
3. 離心 10 分鐘 (12,000 g, 4°C)
4. 移除上清

Day 2 - 洗滌與乾燥
1. 加入 1 mL 75% 乙醇
2. 離心 5 分鐘 (7,500 g, 4°C)
3. 移除乙醇
4. 空氣乾燥 5-10 分鐘

Day 2 - 溶解
1. 加入 20-50 μL DEPC 水
2. 55°C 加熱 10 分鐘
3. NanoDrop 定量
4. -80°C 保存
"""
        elif any(k in msg_lower for k in ['培養', 'culture']):
            # 細胞培養 SOP
            cell_type = ', '.join(extracted_info.get('cells', [])) if extracted_info.get('cells') else '適當細胞'
            sop = f"""
【細胞培養標準流程】

📌 實驗概述：
{cell_type} 細胞的常規培養與傳代

📦 所需材料：
• 培養基 (DMEM 或 RPMI-1640)
• 10% FBS
• 1% Penicillin-Streptomycin
• PBS
• Trypsin-EDTA
• 培養皿/瓶

📝 詳細步驟：

Day 1 - 細胞種植
1. 準備培養基 (室溫)
2. 從液態氮取出細胞，快速回溫
3. 加入培養基稀釋 (1:10)
4. 種植於培養皿
5. 搖勻，放入 CO2 培養箱

Day 2-3 - 觀察
1. 顯微鏡觀察細胞狀態
2. 確認無污染且貼附良好
3. 更換新鮮培養基

每 2-3 天傳代：
1. 移除培養基
2. PBS 清洗
3. 加入 Trypsin-EDTA (室溫)
4. 37°C 孵育 3-5 分鐘
5. 加入培養基終止消化
6. 離心 (1000 rpm, 5 分鐘)
7. 重懸後種植新培養皿

⏱️ 傳代比例：1:3 至 1:5
"""
        
        elif any(k in msg_lower for k in ['wound', 'healing', 'migration', 'scratch', '遷移']):
            # 使用提取的資訊
            cell_line = ', '.join(extracted_info.get('cells', [])) if extracted_info.get('cells') else '適當細胞'
            drug = ', '.join(extracted_info.get('drugs', [])) if extracted_info.get('drugs') else 'paclitaxel'
            conc = ', '.join(extracted_info.get('concentrations', [])) if extracted_info.get('concentrations') else '依文獻建議濃度'
            
            sop = f"""
【Wound Healing / Migration Assay 標準流程】

📌 實驗概述：
測試細胞遷移能力，常用於評估藥物對細胞移動的影響

📦 所需材料：
• 6-well plate
• 200 μL pipette tip
• PBS
• 無血清培養基 (1-2% FBS)
• 藥物 ({drug})
• 顯微鏡

📝 詳細步驟：

Day 1 - 細胞種植
1. 種植 {cell_line} 於 6-well plate
2. 密度: 2-3 × 10⁵ cells/well
3. 培養過夜至 90% 融合

Day 2 - 傷口製造與藥物處理
1. 移除培養基，PBS 清洗
2. 加入無血清培養基 (1-2% FBS)
3. 使用 200 μL pipette tip 垂直畫傷口
4. PBS 清洗去除懸浮細胞
5. 加入 {drug} ({conc})
6. 放入培養箱

Day 2-3 - 影像拍攝
1. T0: 立即拍攝 (0 hr)
2. 每 6-12 小時拍攝一次
3. 使用 ImageJ 分析傷口癒合率

📊 計算公式：
傷口癒合率 (%) = (1 - 剩餘傷口面積 / 初始傷口面積) × 100%

⏱️ 建議時間點：
0, 6, 12, 24, 48 小時
"""
        elif any(k in msg_lower for k in ['western', 'wb', '西方']):
            sop = """
【Western Blot 標準流程】

📌 實驗概述：
檢測蛋白質表現水平

📦 所需材料：
• RIPA 裂解 buffer
• 蛋白酶抑制劑
• BCA 試劑
• SDS-PAGE 膠
• PVDF 膜
• 一級抗體、二級抗體
• ECL 顯影試劑

📝 詳細步驟：

Day 1 - 蛋白質萃取
1. 收集細胞，冷 PBS 清洗
2. 加入 RIPA 裂解 buffer (含 protease inhibitor)
3. 冰上孵育 30 分鐘
4. 超聲波破碎 (3次, 10秒)
5. 離心 15 分鐘 (12,000 g, 4°C)
6. 取上清

Day 1 - 蛋白質定量
1. BCA 法定量
2. 調整濃度至 2 μg/μL
3. 加入 5X loading buffer
4. 95°C 變性 5 分鐘

Day 1 - 電泳
1. 準備 SDS-PAGE 膠
2. 每孔上樣 20-30 μg 蛋白
3. 80V 跑 30 分鐘
4. 120V 跑至染料到底

Day 1 - 轉印
1. 濕轉至 PVDF 膜
2. 100V, 1 小時 (4°C)
3. 5% 脫脂奶粉 blocking 1 小時

Day 1-2 - 抗體孵育
1. 一級抗體孵育過夜 (4°C)
2. TBST 洗滌 3 次 (每次 10 分鐘)
3. 二級抗體孵育 1 小時
4. TBST 洗滌 3 次

Day 2 - 顯影
1. ECL 顯影試劑處理
2. 曝光顯影
3. ImageJ 定量分析
"""
        else:
            sop = """
【通用實驗流程】

1. 實驗設計
   - 確定實驗目的
   - 設計對照組與實驗組

2. 材料準備
   - 細胞/試劑/耗材
   - 儀器校準

3. 執行實驗
   - 按照標準流程操作
   - 記錄時間與觀察

4. 數據分析
   - 統計分析
   - 圖表製作

5. 結論撰寫
   - 結果描述
   - 討論與建議
"""
        
        # 加入文獻參考
        if papers:
            sop += "\n\n📚 參考文獻：\n"
            for p in papers[:3]:
                sop += f"- PMID: {p['pmid']} | {p['journal']} ({p['year']})\n"
        
        response = sop_intro + sop if not response else response + "\n\n" + sop
    
    return {
        "response": response,
        "papers": [{"title": p['title'], "pmid": p['pmid'], "journal": p['journal'], "year": p['year'], "doi": p['doi'], "methodology": extract_methodology(p)} for p in papers]
    }

@app.route('/')
def index():
    return render_template('chat_v2.html')

@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.json
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({'error': '請輸入訊息'})
    
    result = process_message(user_message)
    
    return jsonify(result)

if __name__ == '__main__':
    print("🚀 AI Lab CoPilot (輕量升級版) 啟動中...")
    print("📍 網址: http://localhost:5001")
    app.run(debug=True, port=5001)
