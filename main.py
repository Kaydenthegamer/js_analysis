import configparser
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from urllib.parse import urljoin
import socket
import socks
import webbrowser
import markdown2
import time

def load_config(filename="config.ini"):
    """从 .ini 文件加载配置"""
    config = configparser.ConfigParser()
    # 指定UTF-8编码以正确读取包含中文字符的配置文件
    config.read(filename, encoding='utf-8')
    return config

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

def chunk_string(string, length):
    """将字符串按指定长度分割"""
    return (string[0+i:length+i] for i in range(0, len(string), length))

def analyze_js_with_gemini(config, js_code):
    """使用Gemini API分析JavaScript代码，支持分块"""
    original_socket = socket.socket
    proxy_applied = False
    try:
        # 检查并应用SOCKS5代理
        if config.has_section('Proxy') and config.get('Proxy', 'type', fallback='').lower() == 'socks5':
            proxy_host = config.get('Proxy', 'host')
            proxy_port = int(config.get('Proxy', 'port'))
            socks.set_default_proxy(socks.SOCKS5, proxy_host, proxy_port)
            socket.socket = socks.socksocket
            proxy_applied = True

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
        # 无论成功或失败，都恢复原始的socket设置
        if proxy_applied:
            socket.socket = original_socket

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

    # 让用户选择要分析的文件
    while True:
        choice = input("\n请输入要分析的JS文件编号 (用逗号分隔, 或输入 'all' 分析全部): ").strip().lower()
        if choice == 'all':
            selected_indices = range(len(js_urls))
            break
        else:
            try:
                selected_indices = [int(i.strip()) - 1 for i in choice.split(',')]
                if all(0 <= i < len(js_urls) for i in selected_indices):
                    break
                else:
                    print("错误: 输入的编号超出范围，请重新输入。")
            except ValueError:
                print("错误: 输入无效，请输入数字编号。")

    # 分析选定的文件
    for index in selected_indices:
        js_url = js_urls[index]
        print(f"\n[2] 正在分析选定的文件: {js_url}")
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
                
                report_filename = f"report_{int(time.time())}.html"
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
