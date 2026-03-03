import csv
import json
import datetime
import os
import sys
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from time import sleep

try:
    from openai import OpenAI
except ImportError:
    print("Missing dependencies. Run: pip install openai bs4")
    sys.exit(1)

# Use absolute paths relative to the script location for robustness in different environments
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACCOUNT_LIST_PATH = os.path.join(BASE_DIR, "Data/accounts.csv")
# Fallback for local development if Data/accounts.csv is missing
LOCAL_SOURCE_CSV = "/Users/akshay.mehndiratta/Downloads/Account List - Sheet1 (1).csv"
if not os.path.exists(ACCOUNT_LIST_PATH) and os.path.exists(LOCAL_SOURCE_CSV):
    ACCOUNT_LIST_PATH = LOCAL_SOURCE_CSV

OUTPUT_DATA_PATH = os.path.join(BASE_DIR, "signals.json")
OUTPUT_JS_PATH = os.path.join(BASE_DIR, "signals.js")
PRIORITY_TIERS = ['Strategics', 'Enterprises', 'Top']

def load_accounts(path):
    accounts = []
    if not os.path.exists(path):
        print(f"CRITICAL ERROR: Account list not found at {path}")
        return []
    try:
        with open(path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Bucket") in PRIORITY_TIERS:
                    accounts.append({
                        "name": row.get("L1 account Name ( Top Level )"),
                        "domain": row.get("Domain"),
                        "ae": row.get("Account Owner"),
                        "sdr": row.get("SDR Rep Assigned"),
                        "tier": row.get("Bucket"),
                        "state": row.get("State/Province")
                    })
    except Exception as e:
        print(f"Error loading accounts: {e}")
    return accounts

def search_google_news_rss(account_name):
    """Hits the Google News RSS feed for a specific account. Very stable, rarely blocked."""
    query = urllib.parse.quote(f'"{account_name}" healthcare AND (partnership OR acquisition OR IT OR technology OR strategy)')
    url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    
    results = []
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        import warnings
        from bs4 import XMLParsedAsHTMLWarning
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
        soup = BeautifulSoup(resp.read(), 'html.parser')
        
        items = soup.find_all('item')
        for item in items[:2]: # Get top 2 news articles
            title = item.find('title').text if item.find('title') else ""
            link = item.find('link').next_sibling if getattr(item.find('link'), 'next_sibling', None) else item.find('link').text if item.find('link') else "#"
            pubdate = item.find('pubdate').text if item.find('pubdate') else ""
            if title:
                results.append({'title': str(title).strip(), 'href': str(link).strip(), 'date': str(pubdate).strip()})
    except Exception as e:
        print(f"RSS Fetch Error for {account_name}: {e}")
    return results

def search_with_truefoundry(account_name, api_key, base_url):
    """Deep search using TrueFoundry's LLM with web_search MCP tool."""
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    prompt = f"""
    Search for recent strategic news (M&A, digital transformation, RFP announcements, or strategic leadership changes) 
    related to the healthcare organization: "{account_name}" in the context of IT and technology.
    
    If you find meaningful signals, return a structured JSON object:
    {{
      "score": 60 to 95,
      "type": "M&A Activity" | "IT Transformation" | "Leadership Change" | "Market Signal",
      "urgency": "Immediate" | "High" | "Digest",
      "summary": "Concise summary of the findings",
      "url": "https://source.url",
      "whyMatters": ["Specific detail 1", "Specific detail 2"],
      "nextSteps": "Actionable advice",
      "relevantBrands": ["Gravity", "Comet", "Flow", "Atlas", "Story Health", "Galaxy", "Cured", "Humbi", "PQS"]
    }}
    If no meaningful signal is found, return {{"score": 0}}.
    Valid JSON only.
    """
    
    try:
        stream = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a professional sales intelligence bot. Use your web_search tool to find high-intent signals."},
                {"role": "user", "content": prompt},
            ],
            model="analytics-genai/gemini-2-5-pro",
            max_tokens=2500,
            stream=True,
            extra_headers={
                "X-TFY-METADATA": '{}',
                "X-TFY-LOGGING-CONFIG": '{"enabled": true}',
            },
            extra_body={
              "mcp_servers": [
                  {
                      "integration_fqn": "common-tools",
                      "enable_all_tools": False,
                      "tools": [{"name": "web_search"}]
                  }
              ],
              "iteration_limit": 20,
            },
        )
        
        full_response = ""
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                full_response += chunk.choices[0].delta.content
        
        # Clean potential markdown from response
        text = full_response.strip()
        if text.startswith("```json"):
            text = text.replace("```json", "", 1).strip()
        elif text.startswith("```"):
            text = text.replace("```", "", 1).strip()
        if text.endswith("```"):
            text = text[:-3].strip()
        
        return json.loads(text)
    except Exception as e:
        print(f"TrueFoundry Search Error for {account_name}: {e}")
        return {"score": 0}

def analyze_snippets(snippets, account_name, api_key, base_url):
    """Pass search snippets to TrueFoundry to extract structured insights and score."""
    client = OpenAI(api_key=api_key, base_url=base_url)

    prompt = f"""
    Analyze these highly verifiable Google News headlines for {account_name}:
    {json.dumps(snippets)}
    
    If they represent a meaningful sales trigger (M&A, technology adoption, strategic growth, leadership changes), return a STRICT JSON object:
    {{
      "score": 60 to 95,
      "type": "M&A Activity" | "IT Transformation" | "Leadership Change" | "Market Signal",
      "urgency": "Immediate" | "High" | "Digest",
      "whyMatters": ["Specific bullet 1 mentioning details from headline", "Specific bullet 2"],
      "nextSteps": "Actionable advice",
      "relevantBrands": ["Gravity", "Comet", "Flow", "Atlas", "Story Health", "Galaxy", "Cured", "Humbi", "PQS"]
    }}
    
    If it's generic news or irrelevant, return {{"score": 0}}.
    MUST return valid JSON only. NO MARKDOWN.
    """
    
    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a professional sales intelligence bot."},
                {"role": "user", "content": prompt},
            ],
            model="analytics-genai/gemini-2-5-pro",
            max_tokens=2500,
        )
        text = response.choices[0].message.content.strip()
        text = response.choices[0].message.content.strip()
        if text.startswith("```json"):
            text = text.replace("```json", "", 1).strip()
        elif text.startswith("```"):
            text = text.replace("```", "", 1).strip()
        if text.endswith("```"):
            text = text[:-3].strip()
        return json.loads(text)
    except Exception as e:
        print(f"Analysis Error for {account_name}: {e}")
        return {"score": 0}

def process_signals():
    now = datetime.datetime.now().strftime("%b %d, %Y %I:%M %p")
    print(f"[{now}] Initializing Hybrid Intelligence Scan (TrueFoundry Deep + RSS Content Analysis)...")
    
    tfy_api_key = os.environ.get("TFY_API_KEY")
    tfy_base_url = os.environ.get("TFY_BASE_URL", "https://truefoundry.innovaccer.com/api/llm")
    
    accounts = load_accounts(ACCOUNT_LIST_PATH)
    
    # Sort to prioritize Top/Strategics
    accounts = sorted(accounts, key=lambda x: 0 if x['tier'] == 'Strategics' else 1 if x['tier'] == 'Top' else 2)
    
    live_signals = []
    print(f"Executing Deep RSS scan for high-priority accounts...")
    
    for idx, account in enumerate(accounts):
        name = account['name']
        tier = account['tier']
        
        if idx % 5 == 0:
            print(f"[{idx+1}/{len(accounts)}] Scanning segment starting with: {name} ({tier})")
        
        signal = None
        
        # USE DEEP SEARCH FOR STRATEGICS & TOP TIER
        if tfy_api_key and tier in ['Strategics', 'Top']:
            print(f"     [DEEP SEARCH] Analyzing {name} via TrueFoundry...")
            tfy_result = search_with_truefoundry(name, tfy_api_key, tfy_base_url)
            if tfy_result and tfy_result.get("score", 0) >= 50:
                signal = {
                    "score": tfy_result['score'],
                    "account": name,
                    "type": tfy_result.get('type', "Deep Signal"),
                    "urgency": tfy_result.get('urgency', "Digest"),
                    "brands": tfy_result.get('relevantBrands', []),
                    "summary": tfy_result.get('summary', 'No summary provided.'),
                    "ae": account['ae'],
                    "sdr": account['sdr'],
                    "source": "TrueFoundry Web Search",
                    "url": tfy_result.get('url', '#'),
                    "date": now.split(' ')[0], 
                    "tier": tier,
                    "state": account['state'],
                    "angle": tfy_result.get('nextSteps', "Follow up on identified strategic opportunity."),
                    "whyMatters": tfy_result.get('whyMatters', []),
                    "nextSteps": tfy_result.get('nextSteps', "Review recent strategic updates.")
                }
        
        # FALLBACK TO RSS IF NO DEEP SIGNAL OR NOT TOP TIER
        if not signal:
            results = search_google_news_rss(name)
            if results and len(results) > 0:
                llm_result = analyze_snippets(results, name, tfy_api_key, tfy_base_url)
                if llm_result.get("score", 0) >= 50:
                    first_title = str(results[0].get('title', ''))
                    title_snip = first_title[:60]
                    print(f"     [SIGNAL DISCOVERED] {name} - {llm_result.get('type')} ({title_snip}...)")
                    signal = {
                        "score": llm_result['score'],
                        "account": name,
                        "type": llm_result.get('type', "Health IT Update"),
                        "urgency": llm_result.get('urgency', "Digest"),
                        "brands": llm_result.get('relevantBrands', []),
                        "summary": results[0].get('title', 'No snippet available.'),
                        "ae": account['ae'],
                        "sdr": account['sdr'],
                        "source": "Google News RSS",
                        "url": results[0].get('href', '#'),
                        "date": now.split(' ')[0], 
                        "tier": tier,
                        "state": account['state'],
                        "angle": f"Follow up on recent news: {str(results[0].get('title', ''))[:40]}...",
                        "whyMatters": llm_result.get('whyMatters', []),
                        "nextSteps": llm_result.get('nextSteps', "Review recent strategic updates.")
                    }
        
        if signal:
            # IMMEDIATE PERSISTENCE
            try:
                current_signals = []
                if os.path.exists(OUTPUT_DATA_PATH):
                    with open(OUTPUT_DATA_PATH, 'r') as rf:
                        try:
                            data = rf.read().strip()
                            if data:
                                current_signals = json.loads(data)
                        except:
                            pass
                current_signals.append(signal)
                current_signals = sorted(current_signals, key=lambda x: x['score'], reverse=True)
                
                # Save as JSON
                with open(OUTPUT_DATA_PATH, 'w') as wf:
                    json.dump(current_signals, wf, indent=4)
                
                # Save as JS (CORS bypass)
                with open(OUTPUT_JS_PATH, 'w') as wf:
                    wf.write(f"const SIGNALS_DATA = {json.dumps(current_signals, indent=4)};")
                    
            except Exception as save_err:
                print(f"SAVE ERROR: {save_err}")
            
            live_signals.append(signal)
            
        sleep(1.5)
            
    return {
        "last_refresh": now,
        "priority_count": len(accounts),
        "signals_found": len(live_signals)
    }

if __name__ == "__main__":
    scan_meta = process_signals()
    print(f"\nSuccessfully processed scan.")
    print(f"Last Refresh: {scan_meta['last_refresh']}")
    print(f"Discovered {scan_meta['signals_found']} live, verifiable signals mapped to target accounts.")



