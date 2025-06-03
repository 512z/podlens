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
        
        prompt = f"""使用 Tailwind CSS、Alpine.js 和 Font Awesome（均通过 CDN 引入）创建一个现代、视觉惊艳的单页 HTML 网站。

【强制文本可读性规则——适用于每一个文本元素】：

1. 必须添加的 CSS：
<style>
.text-shadow {{ text-shadow: 0 2px 4px rgba(0,0,0,0.5); }}
.text-shadow-strong {{ text-shadow: 0 4px 8px rgba(0,0,0,0.8); }}
</style>

2. 渐变背景模式（严格遵循）：
- 任何渐变背景 → text-white + text-shadow 类
- 英雄区（Hero Section）→ 添加遮罩层：<div class="absolute inset-0 bg-black/20"></div>
- 渐变卡片 → 所有内容包裹在：<div class="bg-white/95 backdrop-blur rounded-2xl p-6">

3. 具体规则：
- 紫/粉/蓝色渐变 → text-white text-shadow
- 橙/红/黄色渐变 → text-white text-shadow-strong
- 绿色/青色渐变 → text-white text-shadow
- 白色/灰色背景 → text-gray-900（无需阴影）

4. 检查清单（每个元素都要检查）：
✓ 导航文本是否可读？
✓ 英雄区标题和副标题是否可读？
✓ 所有卡片内容是否可读？
✓ 各区块标题是否可读？
✓ 每个区块正文是否可读？

5. 渐变卡片模板（请使用此模式）：
<div class="bg-gradient-to-br from-[color1] to-[color2] p-1 rounded-2xl">
  <div class="bg-white/95 backdrop-blur rounded-2xl p-6">
    <h3 class="text-gray-900 font-bold">标题</h3>
    <p class="text-gray-700">内容</p>
  </div>
</div>

6. 渐变背景区块模板：
<section class="relative bg-gradient-to-br from-[color1] to-[color2]">
  <div class="absolute inset-0 bg-black/20"></div>
  <div class="relative z-10 p-8">
    <h2 class="text-white text-shadow text-3xl font-bold">区块标题</h2>
    <p class="text-white/90 text-shadow">区块内容</p>
  </div>
</section>

7. 语言：中文

禁止：
- 在渐变背景上使用灰色文本
- 在渐变背景上使用渐变色文本
- 忘记在渐变背景上加 text-shadow
- 在深色渐变背景上白色文本透明度低于 90

【数据可视化要求】：
遇到内容中的数值数据时，请创建合适的数据可视化：

首先，所用数据必须完全准确，若无数据则不要虚构。

1. 百分比数据（如 GDP 增长、比率等）：
   - 使用带渐变填充的动画进度条
   - 百分比标签在滚动时递增显示
   - 颜色：正向为绿色，负向为红色
   - 示例：
<div class="relative pt-1">
  <div class="flex mb-2 items-center justify-between">
    <span class="text-xs font-semibold inline-block text-blue-600">GDP 增长</span>
    <span class="text-xs font-semibold inline-block text-blue-600">2.9%</span>
  </div>
  <div class="overflow-hidden h-2 mb-4 text-xs flex rounded bg-blue-200">
    <div style="width:29%" class="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-gradient-to-r from-blue-500 to-blue-600"></div>
  </div>
</div>

2. 对比数据：
   - 使用并排柱状图或对比卡片
   - 用箭头、图标等可视化趋势
   - 可做前后对比可视化

3. 关键指标：
   - 用大号数字和图标展示
   - 可用 Alpine.js 实现简单动画计数
   - 示例：
<div x-data="{{ count: 0 }}" x-init="setTimeout(() => {{ let interval = setInterval(() => {{ if(count < 30) {{ count += 1 }} else {{ clearInterval(interval) }} }}, 50) }}, 500)">
  <span class="text-5xl font-bold text-blue-600" x-text="count + '%'"></span>
</div>

4. 时间序列数据：
   - 用简单折线或时间轴卡片表示
   - 可做年度对比并加趋势指示

5. 统计亮点：
   - 关键数字突出显示在高亮卡片中
   - 用渐变和图标让数字更醒目
   - 示例：
<div class="bg-gradient-to-br from-green-400 to-green-600 rounded-2xl p-6 text-white">
  <div class="flex items-center justify-between">
    <div>
      <p class="text-green-100">历史最低</p>
      <p class="text-3xl font-bold">3.5%</p>
      <p class="text-sm text-green-100">失业率</p>
    </div>
    <i class="fas fa-chart-line text-4xl text-green-200"></i>
  </div>
</div>

【绝对文本规则——无例外】：

1. 有色背景（任何颜色）= 只用白色文本
   - 绿色背景 → text-white
   - 蓝色背景 → text-white
   - 紫色背景 → text-white
   - 橙色背景 → text-white
   - 任何渐变 → text-white

2. 仅在以下情况下用深色文本：
   - 纯白背景
   - Gray-50 背景
   - 白色/半透明遮罩

3. 卡片模式（必须用以下之一）：

   方案A - 有色背景白字：
   <div class="bg-gradient-to-br from-green-500 to-green-600 rounded-2xl p-6">
     <h3 class="text-white font-bold">标题</h3>
     <p class="text-white/90">内容</p>
   </div>

   方案B - 白色容器模式：
   <div class="bg-gradient-to-br from-green-500 to-green-600 rounded-2xl p-1">
     <div class="bg-white/95 backdrop-blur rounded-2xl p-6">
       <h3 class="text-gray-900 font-bold">标题</h3>
       <p class="text-gray-700">内容</p>
     </div>
   </div>

禁止：
- 在有色背景上用 text-gray-XXX
- 在有色背景上用 text-black
- 在任何渐变上用深色文本
- 未明确指定文本颜色

【关键数据准确性规则】：

1. 静态与动画数字：
   - 关键数据点必须直接显示最终值
   - 仅在动画可靠时才用动画
   - 优先静态显示，避免动画出错

2. Alpine.js 数据实现：
   - 用更简单的动画模式替代复杂动画
   - 错误示例（可能显示为0）：
<div x-data="{{ count: 0, target: 7 }}" x-init="animate...">
  <span x-text="count + '%'">0%</span>
</div>
   - 正确示例（始终显示正确值）：
<div x-data="{{ value: 7 }}">
  <span x-text="value + '%'">7%</span>
</div>
   - 更佳示例（简单淡入）：
<div x-data="{{ show: false }}" x-init="setTimeout(() => show = true, 500)" 
     x-show="show" x-transition>
  <span class="text-3xl font-bold">7%</span>
</div>

3. 兜底值：
   - HTML 中始终包含实际值作为兜底
   - 示例：<span x-text="count + '%'">7%</span>（而不是仅显示0%）

4. 数据核查清单：
   ✓ 每个数字都与原文完全一致？
   ✓ 即使 JavaScript 失效数字也可见？
   ✓ 动画足够简单、可靠？

5. 优先简单方案：
   - 用 CSS 动画替代复杂 JS
   - 数字先静态显示，动画仅作增强
   - 示例 CSS 计数动画：
@keyframes countUp {{
  from {{ opacity: 0; transform: translateY(20px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}
.number-animate {{
  animation: countUp 0.8s ease-out;
}}

任何数值展示：

方案1 - 静态显示（推荐）：
<div class="text-5xl font-bold text-blue-600">7%</div>

方案2 - 简单显现动画：
<div class="text-5xl font-bold text-blue-600 number-animate">7%</div>

方案3 - 必须用 Alpine.js 时：
<div x-data="{{ value: 7, show: false }}" 
     x-init="setTimeout(() => show = true, 100)">
  <span class="text-5xl font-bold text-blue-600" 
        x-show="show" x-transition
        x-text="value + '%'">7%</span>
</div>

禁止留空或默认0——必须始终显示正确值！

【数据展示规则】：
- 所有数字先静态显示
- 动画仅作增强
- 关键数据可见性不能依赖 JS
- 任何情况下数字都要可读

每张卡片都要检查：所有文本是否清晰可读？所有数据是否准确？

整体风格要现代、极简、未来感。

请只返回 html 代码，不要输出其他内容。

以下是内容，请用优美的方式讲述这个故事：

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
