#!/usr/bin/env python3
"""
Visual Story Generator - Direct HTML Generation using Gemini AI (Chinese Version)
"""

import os
import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path

# Enhanced .env loading function
def load_env_robust():
    """Load .env file from multiple possible locations"""
    # Try loading from current working directory first
    if load_dotenv():
        return True
    
    # Try loading from home directory
    home_env = Path.home() / '.env'
    if home_env.exists() and load_dotenv(home_env):
        return True
    
    return False

# Load .env file with robust search
load_env_robust()

def generate_visual_story(input_file: str, output_file: str = None) -> bool:
    """
    Generate an interactive HTML story from content file
    
    Args:
        input_file: Path to the input content file (transcript or summary)
        output_file: Path to save the HTML file (optional, will auto-generate if not provided)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Initialize Gemini AI
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("❌ 环境变量中未找到 GEMINI_API_KEY")
            return False
        
        genai.configure(api_key=api_key)
        client = genai
        
        # Check if input file exists
        input_path = Path(input_file)
        if not input_path.exists():
            print(f"❌ 输入文件未找到: {input_file}")
            return False
        
        # Generate output filename if not provided
        if output_file is None:
            # Extract filename without extension and add _visual suffix
            base_name = input_path.stem
            output_file = input_path.parent / f"Visual_{base_name}.html"
        
        # Read content
        print(f"📖 Reading content: {input_file}")
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Generate interactive HTML
        print("🎨 Generating interactive HTML...")
        
        prompt = f"""请使用 Tailwind CSS、Alpine.js 和 Font Awesome（均通过 CDN）创建一个现代化、视觉效果极佳的单页 HTML 网站。

强制性文本可见性规则 - 适用于每一个文本元素：

1.  需要添加的 CSS（必须包含）：

    <style>
    .text-shadow {{ text-shadow: 0 2px 4px rgba(0,0,0,0.5); }}
    .text-shadow-strong {{ text-shadow: 0 4px 8px rgba(0,0,0,0.8); }}
    </style>


2.  渐变背景模式（严格按照以下方式使用）：
    * 对于任何渐变背景 → `text-white` + `text-shadow` 类
    * 对于主要区域（hero sections） → 添加叠加层：`<div class="absolute inset-0 bg-black/20"></div>`
    * 对于渐变卡片 → 将所有内容包裹在：`<div class="bg-white/95 backdrop-blur rounded-2xl p-6">`

3.  特定规则：
    * 紫色/粉色/蓝色渐变 → `text-white text-shadow`
    * 橙色/红色/黄色渐变 → `text-white text-shadow-strong`
    * 绿色/青色渐变 → `text-white text-shadow`
    * 白色/灰色背景 → `text-gray-900`（无需阴影）

4.  测试清单（检查每个元素）：
    ✓ 我能看清导航文字吗？
    ✓ 我能看清主要区域的标题和副标题吗？
    ✓ 我能看清所有卡片内容吗？
    ✓ 我能看清区段标题吗？
    ✓ 我能看清每个区段的正文文本吗？

5.  渐变卡片模板（使用此模式）：

    <div class="bg-gradient-to-br from-[color1] to-[color2] p-1 rounded-2xl">
      <div class="bg-white/95 backdrop-blur rounded-2xl p-6">
        <h3 class="text-gray-900 font-bold">标题</h3>
        <p class="text-gray-700">内容</p>
      </div>
    </div>


6.  带渐变背景的区段模板：

    <section class="relative bg-gradient-to-br from-[color1] to-[color2]">
      <div class="absolute inset-0 bg-black/20"></div>
      <div class="relative z-10 p-8">
        <h2 class="text-white text-shadow text-3xl font-bold">区段标题</h2>
        <p class="text-white/90 text-shadow">区段内容</p>
      </div>
    </section>

7.语言: 中文

绝不：
* 在渐变上放置灰色文本
* 在渐变背景上使用渐变文本
* 忘记在渐变背景上使用 `text-shadow`
* 在深色渐变上使用透明度低于 90% 的白色文本

数据可视化要求：
遇到数字数据时，创建适当的可视化展示：

1. 百分比数据（如GDP增长、比率）：
   - 使用带渐变填充的动画进度条
   - 包含滚动时递增的百分比标签
   - 颜色编码：正数用绿色，负数用红色

2. 对比数据：
   - 使用并排条形图或对比卡片
   - 趋势的视觉指示器（箭头、图标）
   - 前后对比可视化

3. 关键指标：
   - 带图标的大数字展示
   - 使用Alpine.js的动画计数器

4. 时间序列数据：
   - 简单的线条表示或时间轴卡片
   - 年度对比的视觉指示器

5. 统计亮点：
   - 将关键数字提取到突出显示的统计卡片中
   - 使用渐变和图标使数字突出

绝对文本规范 - 不可违反：

1. 有色背景（任何颜色）= 只能用白色文字
   - 绿色背景 → text-white
   - 蓝色背景 → text-white  
   - 紫色背景 → text-white
   - 橙色背景 → text-white
   - 任何渐变背景 → text-white

2. 仅在以下情况下使用深色文字：
   - 纯白色背景
   - Gray-50（极浅灰）背景
   - 白色/半透明白色叠加层

3. 卡片样式（必须使用以下之一）：

   方案A - 彩色背景白字卡片：
   <div class="bg-gradient-to-br from-green-500 to-green-600 rounded-2xl p-6">
     <h3 class="text-white font-bold">标题</h3>
     <p class="text-white/90">内容</p>
   </div>

   方案B - 白色容器卡片：
   <div class="bg-gradient-to-br from-green-500 to-green-600 rounded-2xl p-1">
     <div class="bg-white/95 backdrop-blur rounded-2xl p-6">
       <h3 class="text-gray-900 font-bold">标题</h3>
       <p class="text-gray-700">内容</p>
     </div>
   </div>

严禁使用：
- 在有色背景上用 text-gray-XXX
- 在有色背景上用 text-black
- 在任何渐变背景上用深色文字
- 未明确指定颜色类的文本

检查每一张卡片：所有文字是否都清晰可读？

风格应该摩登, 简约, 科幻

请仅返回 html 代码，不要包含其他文本。

以下是内容，请优美地展现这个故事：

{content}"""
        
        response = client.GenerativeModel("gemini-2.5-flash-preview-05-20").generate_content(prompt)
        
        # Handle the response properly
        if hasattr(response, 'text'):
            html_content = response.text
        elif hasattr(response, 'candidates') and response.candidates:
            html_content = response.candidates[0].content.parts[0].text
        else:
            print("❌ Gemini API 响应格式异常")
            return False
        
        # Remove markdown code block markers if present
        if html_content.startswith('```html'):
            html_content = html_content[7:]  # Remove ```html
        elif html_content.startswith('```'):
            html_content = html_content[3:]   # Remove ```
        
        if html_content.endswith('```'):
            html_content = html_content[:-3]  # Remove trailing ```
        
        # Clean up any extra whitespace
        html_content = html_content.strip()
        
        # print("✅ 交互式 HTML 生成成功")  # Removed this line
        
        # Save HTML file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"💾 交互式 HTML 已保存至: {output_file}")
        print(f"🌐 在浏览器中打开 {output_file} 查看故事!")
        
        return True
        
    except Exception as e:
        print(f"❌ 生成可视化故事时出错: {e}")
        return False

def main():
    """Main function for standalone execution"""
    # Default behavior for backward compatibility
    input_file = "outputs/Huberman_Lab_Essentials__Machines,_Creativity_&_Love___Dr._Lex_Fridman_transcript.md"
    output_file = "outputs/Interactive_Mindmap_Simple.html"
    
    generate_visual_story(input_file, output_file)

if __name__ == "__main__":
    main()
