import configparser
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from urllib.parse import urljoin
import webbrowser
import markdown2
import time
import os
import urllib3
from urllib3.exceptions import InsecureRequestWarning
import random

# 禁用SSL警告 - 注意：这会降低安全性，仅在开发/测试环境使用
urllib3.disable_warnings(InsecureRequestWarning)

# 常见的用户代理列表，模拟真实浏览器
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36'
]

def get_random_headers():
    """生成随机的HTTP请求头，模拟真实浏览器"""
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0'
    }

def load_config(filename="config.ini"):
    """从 .ini 文件加载配置"""
    config = configparser.ConfigParser()
    # 指定UTF-8编码以正确读取包含中文字符的配置文件
    config.read(filename, encoding='utf-8')
    return config

def format_file_size(size_bytes):
    """将字节数转换为人类可读的格式"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    if i == 0:  # 字节数
        return f"{int(size)} {size_names[i]}"
    else:
        return f"{size:.1f} {size_names[i]}"

def get_js_file_size(url):
    """获取JavaScript文件的大小，使用反爬虫措施"""
    try:
        headers = get_random_headers()
        
        # 使用HEAD请求先尝试获取Content-Length
        response = requests.head(url, timeout=10, verify=False, headers=headers)
        content_length = response.headers.get('content-length')
        if content_length:
            return int(content_length)
        
        # 如果HEAD请求没有返回Content-Length，则使用GET请求
        # 添加随机延迟，模拟人类行为
        time.sleep(random.uniform(0.5, 2.0))
        response = requests.get(url, timeout=10, verify=False, headers=headers)
        response.raise_for_status()
        return len(response.content)
    except Exception as e:
        print(f"获取文件大小时出错 ({url}): {e}")
        return 0

def get_js_urls_from_page(url):
    """从给定的URL中提取所有JavaScript文件的URL，并获取文件大小"""
    try:
        headers = get_random_headers()
        
        # 禁用SSL证书验证，忽略自签证书和过期证书问题，使用随机User-Agent
        response = requests.get(url, timeout=15, verify=False, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        js_files = []
        
        for script_tag in soup.find_all('script', src=True):
            js_url = script_tag.get('src')
            # 确保js_url是字符串
            if isinstance(js_url, str):
                # 将相对URL转换为绝对URL
                absolute_js_url = urljoin(url, js_url)
                print(f"  正在获取文件大小: {absolute_js_url}")
                
                # 添加随机延迟，避免请求过于频繁
                time.sleep(random.uniform(0.3, 1.5))
                file_size = get_js_file_size(absolute_js_url)
                
                js_files.append({
                    'url': absolute_js_url,
                    'size': file_size,
                    'size_formatted': format_file_size(file_size)
                })
        return js_files
    except requests.RequestException as e:
        print(f"获取页面内容时出错: {e}")
        return []

def get_js_content(url):
    """获取单个JS文件的内容，使用反爬虫措施"""
    try:
        headers = get_random_headers()
        
        # 添加随机延迟，模拟人类行为
        time.sleep(random.uniform(1.0, 3.0))
        
        # 禁用SSL证书验证，忽略自签证书和过期证书问题，使用随机User-Agent
        response = requests.get(url, timeout=15, verify=False, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"下载JS文件时出错 ({url}): {e}")
        return None

def chunk_string(string, length):
    """将字符串按指定长度分割"""
    return (string[0+i:length+i] for i in range(0, len(string), length))

def analyze_js_with_gemini(config, js_code):
    """使用Gemini API分析JavaScript代码，支持分块"""
    proxy_set = False
    try:
        # 为gRPC设置代理 (google-generativeai 使用 gRPC)
        if config.has_section('Proxy') and config.get('Proxy', 'type', fallback=''):
            proxy_type = config.get('Proxy', 'type')
            host = config.get('Proxy', 'host')
            port = config.get('Proxy', 'port')
            # grpcio 库会识别 'https_proxy' (全小写) 环境变量
            proxy_url = f"{proxy_type}://{host}:{port}"
            os.environ['https_proxy'] = proxy_url
            proxy_set = True
        
        # 禁用gRPC的SSL验证以忽略证书问题
        os.environ['GRPC_SSL_CIPHER_SUITES'] = 'HIGH+ECDSA'
        os.environ['PYTHONHTTPSVERIFY'] = '0'

        # 配置Gemini
        api_key = config.get('Gemini', 'api_key')
        model_name = config.get('Gemini', 'model')
        max_chunk_size = config.getint('Gemini', 'max_chunk_size', fallback=15000)
        prompt_template = config.get('Prompt', 'custom_prompt')
        chunk_prompt_template = config.get('Prompt', 'chunk_prompt')

        if not api_key or api_key == "YOUR_GEMINI_API_KEY":
            print("错误: 请在 config.ini 文件中配置您的Gemini API key。")
            return None

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        # 检查是否需要分块
        if len(js_code) <= max_chunk_size:
            # 不分块
            prompt = prompt_template.format(js_code=js_code)
            response = model.generate_content(prompt)
            return response.text
        else:
            # 分块处理
            print(f"  代码过长 ({len(js_code)} 字符)，将分块发送...")
            chunks = list(chunk_string(js_code, max_chunk_size))
            full_analysis = []
            
            # 处理第一块
            print(f"  正在分析第 1/{len(chunks)} 块...")
            first_prompt = prompt_template.format(js_code=chunks[0])
            response = model.generate_content(first_prompt)
            full_analysis.append(response.text)
            
            # 处理后续块
            for i, chunk in enumerate(chunks[1:], start=2):
                print(f"  正在分析第 {i}/{len(chunks)} 块...")
                next_prompt = chunk_prompt_template.format(js_code=chunk)
                response = model.generate_content(next_prompt)
                full_analysis.append(response.text)
            
            # 对所有分块结果进行最终总结
            print("  所有分块分析完成，正在进行最终总结...")
            summary_prompt_template = config.get('Prompt', 'summary_prompt')
            combined_reports = "\n\n--- 单独报告分割线 ---\n\n".join(full_analysis)
            summary_prompt = summary_prompt_template.format(analysis_reports=combined_reports)
            
            summary_response = model.generate_content(summary_prompt)
            return summary_response.text

    except Exception as e:
        print(f"调用Gemini API时出错: {e}")
        return None
    finally:
        # 清理环境变量，以免影响其他可能的网络调用
        if proxy_set:
            del os.environ['https_proxy']
        # 清理SSL相关环境变量
        if 'GRPC_SSL_CIPHER_SUITES' in os.environ:
            del os.environ['GRPC_SSL_CIPHER_SUITES']
        if 'PYTHONHTTPSVERIFY' in os.environ:
            del os.environ['PYTHONHTTPSVERIFY']

def main():
    """主函数"""
    config = load_config()
    
    target_url = input("请输入要分析的网站URL: ")
    
    print(f"\n[1] 正在从 {target_url} 提取JS文件链接...")
    js_files = get_js_urls_from_page(target_url)
    
    if not js_files:
        print("未能找到任何JS文件链接。")
        return
        
    print(f"找到 {len(js_files)} 个JS文件链接:")
    for i, js_file in enumerate(js_files, 1):
        print(f"  {i}. {js_file['url']} [{js_file['size_formatted']}]")

    # 让用户选择要分析的文件
    while True:
        choice = input("\n请输入要分析的JS文件编号 (用逗号分隔, 或输入 'all' 分析全部): ").strip().lower()
        if choice == 'all':
            selected_indices = range(len(js_files))
            break
        else:
            try:
                selected_indices = [int(i.strip()) - 1 for i in choice.split(',')]
                if all(0 <= i < len(js_files) for i in selected_indices):
                    break
                else:
                    print("错误: 输入的编号超出范围，请重新输入。")
            except ValueError:
                print("错误: 输入无效，请输入数字编号。")

    # 分析选定的文件
    for index in selected_indices:
        js_file = js_files[index]
        js_url = js_file['url']
        print(f"\n[2] 正在分析选定的文件: {js_url} [{js_file['size_formatted']}]")
        js_content = get_js_content(js_url)
        
        if js_content:
            print("[3] 已获取JS代码，正在发送到Gemini进行分析...")
            analysis_result = analyze_js_with_gemini(config, js_content)
            if analysis_result:
                print("[4] 分析完成，正在生成HTML报告...")
                html_content = markdown2.markdown(analysis_result, extras=["fenced-code-blocks", "tables"])
                
                # 添加一些CSS样式
                html_template = f"""
                <!DOCTYPE html>
                <html lang="zh-CN">
                <head>
                    <meta charset="UTF-8">
                    <title>JS代码安全分析报告</title>
                    <style>
                        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; line-height: 1.6; margin: 2em; background-color: #f9f9f9; color: #333; }}
                        .container {{ max-width: 800px; margin: auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                        h1, h2, h3 {{ color: #2c3e50; }}
                        code {{ background-color: #eee; padding: 2px 4px; border-radius: 4px; font-family: "Courier New", Courier, monospace; }}
                        pre {{ background-color: #2d2d2d; color: #f8f8f2; padding: 1em; border-radius: 5px; overflow-x: auto; }}
                        pre code {{ background-color: transparent; padding: 0; }}
                        table {{ border-collapse: collapse; width: 100%; margin-bottom: 1em; }}
                        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                        th {{ background-color: #f2f2f2; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>JS代码安全分析报告</h1>
                        <h2>分析对象: {js_url}</h2>
                        <hr>
                        {html_content}
                    </div>
                </body>
                </html>
                """
                
                # 创建reports目录（如果不存在）
                if not os.path.exists('reports'):
                    os.makedirs('reports')
                
                report_filename = os.path.join('reports', f"report_{int(time.time())}.html")
                with open(report_filename, "w", encoding="utf-8") as f:
                    f.write(html_template)
                
                print(f"[5] 报告已生成: {report_filename}")
                webbrowser.open(report_filename)
                print("--- 分析结束 ---\n")
            else:
                print("未能获取分析结果。")
        else:
            print("未能获取JS内容，跳过分析。")

if __name__ == "__main__":
    main()
