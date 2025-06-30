import configparser
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from urllib.parse import urljoin
import os

def load_config(filename="config.ini"):
    """从 .ini 文件加载配置"""
    config = configparser.ConfigParser()
    # 指定UTF-8编码以正确读取包含中文字符的配置文件
    config.read(filename, encoding='utf-8')
    return config

def get_proxy_config(config):
    """获取代理配置"""
    if config.has_section('Proxy') and config.get('Proxy', 'type'):
        proxy_type = config.get('Proxy', 'type')
        host = config.get('Proxy', 'host')
        port = config.get('Proxy', 'port')
        return {
            "http": f"{proxy_type}://{host}:{port}",
            "https": f"{proxy_type}://{host}:{port}"
        }
    return None

def get_js_urls_from_page(url):
    """从给定的URL中提取所有JavaScript文件的URL"""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        js_urls = []
        for script_tag in soup.find_all('script', src=True):
            js_url = script_tag.get('src')
            # 确保js_url是字符串
            if isinstance(js_url, str):
                # 将相对URL转换为绝对URL
                absolute_js_url = urljoin(url, js_url)
                js_urls.append(absolute_js_url)
        return js_urls
    except requests.RequestException as e:
        print(f"获取页面内容时出错: {e}")
        return []

def get_js_content(url):
    """获取单个JS文件的内容"""
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"下载JS文件时出错 ({url}): {e}")
        return None

def analyze_js_with_gemini(config, js_code):
    """使用Gemini API分析JavaScript代码"""
    # 为Gemini API调用设置代理
    proxy_config = get_proxy_config(config)
    if proxy_config:
        os.environ['HTTPS_PROXY'] = proxy_config['https']
        os.environ['HTTP_PROXY'] = proxy_config['http']

    api_key = config.get('Gemini', 'api_key')
    model_name = config.get('Gemini', 'model')
    prompt_template = config.get('Prompt', 'custom_prompt')

    if not api_key or api_key == "YOUR_GEMINI_API_KEY":
        print("错误: 请在 config.ini 文件中配置您的Gemini API key。")
        return None

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    
    prompt = prompt_template.format(js_code=js_code)
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"调用Gemini API时出错: {e}")
        return None
    finally:
        # 清理环境变量，以免影响其他可能的网络调用
        if 'HTTPS_PROXY' in os.environ:
            del os.environ['HTTPS_PROXY']
        if 'HTTP_PROXY' in os.environ:
            del os.environ['HTTP_PROXY']

def main():
    """主函数"""
    config = load_config()
    
    target_url = input("请输入要分析的网站URL: ")
    
    print(f"\n[1] 正在从 {target_url} 提取JS文件链接...")
    js_urls = get_js_urls_from_page(target_url)
    
    if not js_urls:
        print("未能找到任何JS文件链接。")
        return
        
    print(f"找到 {len(js_urls)} 个JS文件链接:")
    for i, url in enumerate(js_urls, 1):
        print(f"  {i}. {url}")

    for i, js_url in enumerate(js_urls, 1):
        print(f"\n[2] 正在分析第 {i}/{len(js_urls)} 个JS文件: {js_url}")
        js_content = get_js_content(js_url)
        
        if js_content:
            print("[3] 已获取JS代码，正在发送到Gemini进行分析...")
            analysis_result = analyze_js_with_gemini(config, js_content)
            if analysis_result:
                print("\n--- Gemini分析结果 ---")
                print(analysis_result)
                print("--- 分析结束 ---\n")
            else:
                print("未能获取分析结果。")
        else:
            print("未能获取JS内容，跳过分析。")

if __name__ == "__main__":
    main()
