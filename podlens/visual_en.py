#!/usr/bin/env python3
"""
Visual Story Generator - Direct HTML Generation using Gemini AI (English Version)
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
            print("❌ GEMINI_API_KEY not found in environment variables")
            return False
        
        genai.configure(api_key=api_key)
        client = genai
        
        # Check if input file exists
        input_path = Path(input_file)
        if not input_path.exists():
            print(f"❌ Input file not found: {input_file}")
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
        
        prompt = f"""Create a modern, visually stunning single-page HTML website using Tailwind CSS, Alpine.js, and Font Awesome (all via CDN).

MANDATORY TEXT VISIBILITY RULES - APPLY TO EVERY SINGLE TEXT ELEMENT:

1. CSS TO ADD (MUST INCLUDE):
<style>
.text-shadow {{ text-shadow: 0 2px 4px rgba(0,0,0,0.5); }}
.text-shadow-strong {{ text-shadow: 0 4px 8px rgba(0,0,0,0.8); }}
</style>

2. GRADIENT BACKGROUND PATTERNS (USE EXACTLY):
- For ANY gradient background → text-white + text-shadow class
- For hero sections → add overlay: <div class="absolute inset-0 bg-black/20"></div>
- For gradient cards → wrap ALL content in: <div class="bg-white/95 backdrop-blur rounded-2xl p-6">

3. SPECIFIC RULES:
- Purple/Pink/Blue gradients → text-white text-shadow
- Orange/Red/Yellow gradients → text-white text-shadow-strong
- Green/Teal gradients → text-white text-shadow
- White/Gray backgrounds → text-gray-900 (no shadow needed)

4. TESTING CHECKLIST (CHECK EVERY ELEMENT):
✓ Can I read the navigation text?
✓ Can I read the hero title and subtitle?
✓ Can I read all card content?
✓ Can I read section headings?
✓ Can I read body text in every section?

5. GRADIENT CARD TEMPLATE (USE THIS PATTERN):
<div class="bg-gradient-to-br from-[color1] to-[color2] p-1 rounded-2xl">
  <div class="bg-white/95 backdrop-blur rounded-2xl p-6">
    <h3 class="text-gray-900 font-bold">Title</h3>
    <p class="text-gray-700">Content</p>
  </div>
</div>

6. SECTION WITH GRADIENT BACKGROUND TEMPLATE:
<section class="relative bg-gradient-to-br from-[color1] to-[color2]">
  <div class="absolute inset-0 bg-black/20"></div>
  <div class="relative z-10 p-8">
    <h2 class="text-white text-shadow text-3xl font-bold">Section Title</h2>
    <p class="text-white/90 text-shadow">Section content</p>
  </div>
</section>

7. LANGUAGE: ENGLISH

NEVER:
- Put gray text on gradients
- Use gradient text on gradient backgrounds  
- Forget text-shadow on gradient backgrounds
- Use opacity less than 90 for white text on dark gradients

DATA VISUALIZATION REQUIREMENTS:
When encountering numerical data in the content, create appropriate visualizations:

1. PERCENTAGE DATA (e.g., GDP growth, rates):
   - Use animated progress bars with gradient fills
   - Include percentage labels that count up on scroll
   - Color code: green for positive, red for negative
   - Example: <div class="relative pt-1">
              <div class="flex mb-2 items-center justify-between">
                <span class="text-xs font-semibold inline-block text-blue-600">GDP Growth</span>
                <span class="text-xs font-semibold inline-block text-blue-600">2.9%</span>
              </div>
              <div class="overflow-hidden h-2 mb-4 text-xs flex rounded bg-blue-200">
                <div style="width:29%" class="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-gradient-to-r from-blue-500 to-blue-600"></div>
              </div>
            </div>

2. COMPARISON DATA:
   - Use side-by-side bar charts or comparison cards
   - Visual indicators (arrows, icons) for trends
   - Before/after visualizations

3. KEY METRICS:
   - Large number displays with icons
   - Animated counters using Alpine.js
   - Example: <div x-data="{{ count: 0 }}" x-init="setTimeout(() => {{ let interval = setInterval(() => {{ if(count < 30) {{ count += 1 }} else {{ clearInterval(interval) }} }}, 50) }}, 500)">
              <span class="text-5xl font-bold text-blue-600" x-text="count + '%'"></span>
            </div>

4. TIME-SERIES DATA:
   - Simple line representations or timeline cards
   - Year-over-year comparisons with visual indicators

5. STATISTICAL HIGHLIGHTS:
   - Pull out key numbers into highlighted stat cards
   - Use gradients and icons to make numbers stand out
   - Example: <div class="bg-gradient-to-br from-green-400 to-green-600 rounded-2xl p-6 text-white">
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-green-100">Record Low</p>
                  <p class="text-3xl font-bold">3.5%</p>
                  <p class="text-sm text-green-100">Unemployment Rate</p>
                </div>
                <i class="fas fa-chart-line text-4xl text-green-200"></i>
              </div>
            </div>

ABSOLUTE TEXT RULES - NO EXCEPTIONS:

1. COLORED BACKGROUNDS (ANY COLOR) = WHITE TEXT ONLY
   - Green backgrounds → text-white
   - Blue backgrounds → text-white  
   - Purple backgrounds → text-white
   - Orange backgrounds → text-white
   - ANY gradient → text-white

2. ONLY USE DARK TEXT ON:
   - Pure white backgrounds
   - Gray-50 backgrounds
   - White/semi-transparent overlays

3. CARD PATTERN (MUST USE ONE OF THESE):

   Option A - White text on color:
   <div class="bg-gradient-to-br from-green-500 to-green-600 rounded-2xl p-6">
     <h3 class="text-white font-bold">Title</h3>
     <p class="text-white/90">Content</p>
   </div>

   Option B - White container pattern:
   <div class="bg-gradient-to-br from-green-500 to-green-600 rounded-2xl p-1">
     <div class="bg-white/95 backdrop-blur rounded-2xl p-6">
       <h3 class="text-gray-900 font-bold">Title</h3>
       <p class="text-gray-700">Content</p>
     </div>
   </div>

NEVER USE:
- text-gray-XXX on colored backgrounds
- text-black on colored backgrounds
- Dark text on ANY gradient
- Text without explicit color classes

TEST EVERY CARD: Can I clearly read all text?

The overall style should be modern, minimal, and futuristic.

Please return the html code only, no other text.

below are the content, tell this story beautifully:

{content}"""
        
        response = client.GenerativeModel("gemini-2.5-flash-preview-05-20").generate_content(prompt)
        
        # Handle the response properly
        if hasattr(response, 'text'):
            html_content = response.text
        elif hasattr(response, 'candidates') and response.candidates:
            html_content = response.candidates[0].content.parts[0].text
        else:
            print("❌ Gemini API response format abnormal")
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
        
        # print("✅ Interactive HTML generated successfully")  # Removed this line
        
        # Save HTML file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"💾 Interactive HTML saved to: {output_file}")
        print(f"🌐 Open {output_file} in your web browser to view the story!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error generating visual story: {e}")
        return False

def main():
    """Main function for standalone execution"""
    # Default behavior for backward compatibility
    input_file = "outputs/Huberman_Lab_Essentials__Machines,_Creativity_&_Love___Dr._Lex_Fridman_transcript.md"
    output_file = "outputs/Interactive_Mindmap_Simple.html"
    
    generate_visual_story(input_file, output_file)

if __name__ == "__main__":
    main()
