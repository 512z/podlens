import os
import requests
import json
import time
from pathlib import Path
import re
from tqdm import tqdm

class NotionMarkdownUploader:
    def __init__(self, token, root_page_id):
        self.token = token
        self.root_page_id = root_page_id
        # 修正：必须提供版本号
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28',  # 必需的版本号
        }
        self.base_url = 'https://api.notion.com/v1'
        self.uploaded_files = set()  # 记录已上传的文件
        self.progress_bar = None  # 进度条引用
        
    def get_existing_pages(self, parent_id):
        """获取父页面下的所有子页面"""
        response = requests.get(
            f'{self.base_url}/blocks/{parent_id}/children',
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            existing_titles = []
            for block in data.get('results', []):
                if block.get('type') == 'child_page':
                    title = block.get('child_page', {}).get('title', '')
                    existing_titles.append(title)
            return existing_titles
        return []
        
    def page_exists(self, parent_id, title):
        """检查页面是否已存在"""
        existing_pages = self.get_existing_pages(parent_id)
        return title in existing_pages
    
    def get_page_id_by_title(self, parent_id, title):
        """根据标题获取页面ID"""
        response = requests.get(
            f'{self.base_url}/blocks/{parent_id}/children',
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            for block in data.get('results', []):
                if block.get('type') == 'child_page':
                    page_title = block.get('child_page', {}).get('title', '')
                    if page_title == title:
                        return block.get('id')
        return None
    
    def count_summary_files(self, folder_path):
        """计算所有summary文件的数量"""
        total_files = 0
        folder_path = Path(folder_path)
        
        if not folder_path.exists():
            return 0
            
        # 遍历三层结构：来源/日期/内容文件夹
        for source_folder in folder_path.iterdir():
            if not source_folder.is_dir():
                continue
            for date_folder in source_folder.iterdir():
                if not date_folder.is_dir():
                    continue
                for content_folder in date_folder.iterdir():
                    if not content_folder.is_dir():
                        continue
                    # 统计summary文件
                    summary_files = [f for f in content_folder.glob("*.md") if f.name.lower().startswith("summary")]
                    total_files += len(summary_files)
        
        return total_files
        
    def markdown_to_blocks(self, markdown_content):
        """将markdown内容转换为Notion blocks"""
        blocks = []
        lines = markdown_content.split('\n')
        current_block = ""
        
        for line in lines:
            line = line.strip()
            
            if not line:
                if current_block:
                    paragraph_blocks = self.create_paragraph_block(current_block)
                    blocks.extend(paragraph_blocks)
                    current_block = ""
                continue
                
            # 处理分隔线
            if line == '---' or line == '***':
                if current_block:
                    paragraph_blocks = self.create_paragraph_block(current_block)
                    blocks.extend(paragraph_blocks)
                    current_block = ""
                blocks.append(self.create_divider_block())
                continue
                
            # 处理标题
            if line.startswith('#'):
                if current_block:
                    paragraph_blocks = self.create_paragraph_block(current_block)
                    blocks.extend(paragraph_blocks)
                    current_block = ""
                
                level = len(line) - len(line.lstrip('#'))
                title = line.lstrip('# ').strip()
                blocks.append(self.create_heading_block(title, level))
                
            # 处理代码块
            elif line.startswith('```'):
                if current_block:
                    paragraph_blocks = self.create_paragraph_block(current_block)
                    blocks.extend(paragraph_blocks)
                    current_block = ""
                # 这里简化处理，实际可以更复杂
                blocks.append(self.create_code_block("code content"))
                
            # 处理无序列表
            elif line.startswith('- ') or line.startswith('* '):
                if current_block:
                    paragraph_blocks = self.create_paragraph_block(current_block)
                    blocks.extend(paragraph_blocks)
                    current_block = ""
                text = line.lstrip('- *').strip()
                blocks.append(self.create_bullet_block(text))
                
            # 处理有序列表（数字、罗马数字等）
            elif re.match(r'^[IVXivx]+\.\s', line) or re.match(r'^\d+\.\s', line) or re.match(r'^[a-zA-Z]\.\s', line):
                if current_block:
                    paragraph_blocks = self.create_paragraph_block(current_block)
                    blocks.extend(paragraph_blocks)
                    current_block = ""
                # 提取列表内容（去掉前面的序号）
                text = re.sub(r'^[IVXivx\d\w]+\.\s*', '', line).strip()
                blocks.append(self.create_numbered_block(text))
                
            else:
                if current_block:
                    current_block += "\n" + line
                else:
                    current_block = line
        
        if current_block:
            paragraph_blocks = self.create_paragraph_block(current_block)
            blocks.extend(paragraph_blocks)
            
        return blocks
    
    def parse_rich_text(self, text):
        """解析markdown格式并转换为Notion rich_text"""
        rich_text = []
        i = 0
        
        while i < len(text):
            # 处理加粗 **text**
            if i < len(text) - 3 and text[i:i+2] == '**':
                # 查找结束的 **
                end_pos = text.find('**', i + 2)
                if end_pos != -1:
                    bold_text = text[i+2:end_pos]
                    rich_text.append({
                        "type": "text",
                        "text": {"content": bold_text},
                        "annotations": {"bold": True}
                    })
                    i = end_pos + 2
                    continue
            
            # 处理斜体 *text* (但不是 **)
            elif i < len(text) - 2 and text[i] == '*' and (i == 0 or text[i-1:i+1] != '**') and (i+1 >= len(text) or text[i:i+2] != '**'):
                # 查找结束的 *
                end_pos = text.find('*', i + 1)
                if end_pos != -1 and (end_pos + 1 >= len(text) or text[end_pos:end_pos+2] != '**'):
                    italic_text = text[i+1:end_pos]
                    rich_text.append({
                        "type": "text",
                        "text": {"content": italic_text},
                        "annotations": {"italic": True}
                    })
                    i = end_pos + 1
                    continue
            
            # 处理普通文本
            # 找到下一个特殊字符的位置
            next_special = len(text)
            for special_char in ['**', '*']:
                pos = text.find(special_char, i)
                if pos != -1 and pos < next_special:
                    next_special = pos
            
            # 提取普通文本
            if next_special > i:
                normal_text = text[i:next_special]
                if normal_text:
                    rich_text.append({
                        "type": "text",
                        "text": {"content": normal_text}
                    })
                i = next_special
            else:
                # 如果没有找到特殊字符，添加剩余文本
                remaining_text = text[i:]
                if remaining_text:
                    rich_text.append({
                        "type": "text",
                        "text": {"content": remaining_text}
                    })
                break
        
        return rich_text if rich_text else [{"type": "text", "text": {"content": text}}]

    def create_paragraph_block(self, text):
        # 分割长文本以符合Notion API的2000字符限制
        blocks = []
        max_length = 1900  # 留一些余量
        
        if len(text) <= max_length:
            rich_text = self.parse_rich_text(text)
            return [{
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": rich_text
                }
            }]
        
        # 分割长文本
        words = text.split(' ')
        current_chunk = ""
        
        for word in words:
            if len(current_chunk + " " + word) <= max_length:
                if current_chunk:
                    current_chunk += " " + word
                else:
                    current_chunk = word
            else:
                if current_chunk:
                    rich_text = self.parse_rich_text(current_chunk)
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": rich_text
                        }
                    })
                current_chunk = word
        
        if current_chunk:
            rich_text = self.parse_rich_text(current_chunk)
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": rich_text
                }
            })
        
        return blocks
    
    def create_heading_block(self, text, level):
        rich_text = self.parse_rich_text(text)
        heading_type = f"heading_{min(level, 3)}"
        return {
            "object": "block",
            "type": heading_type,
            heading_type: {
                "rich_text": rich_text
            }
        }
    
    def create_bullet_block(self, text):
        rich_text = self.parse_rich_text(text)
        return {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": rich_text
            }
        }
    
    def create_numbered_block(self, text):
        rich_text = self.parse_rich_text(text)
        return {
            "object": "block",
            "type": "numbered_list_item",
            "numbered_list_item": {
                "rich_text": rich_text
            }
        }
    
    def create_divider_block(self):
        return {
            "object": "block",
            "type": "divider",
            "divider": {}
        }
    
    def create_code_block(self, code):
        return {
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": code
                        }
                    }
                ],
                "language": "plain text"
            }
        }
    
    def create_page(self, title, parent_id, content_blocks):
        """创建新页面"""
        data = {
            "parent": {
                "type": "page_id",
                "page_id": parent_id
            },
            "properties": {
                "title": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                }
            },
            "children": content_blocks[:100]  # Notion API限制每次最多100个blocks
        }
        
        response = requests.post(
            f'{self.base_url}/pages',
            headers=self.headers,
            json=data
        )
        
        if response.status_code == 200:
            page_data = response.json()
            page_id = page_data['id']
            
            # 如果有超过100个blocks，需要分批添加
            if len(content_blocks) > 100:
                remaining_blocks = content_blocks[100:]
                self.add_blocks_to_page(page_id, remaining_blocks)
            
            return page_id
        else:
            print(f"创建页面失败: {response.status_code}, {response.text}")
            return None
    
    def add_blocks_to_page(self, page_id, blocks):
        """向页面添加更多blocks"""
        batch_size = 100
        for i in range(0, len(blocks), batch_size):
            batch = blocks[i:i + batch_size]
            data = {
                "children": batch
            }
            
            response = requests.patch(
                f'{self.base_url}/blocks/{page_id}/children',
                headers=self.headers,
                json=data
            )
            
            if response.status_code != 200:
                print(f"添加blocks失败: {response.status_code}, {response.text}")
            
            time.sleep(0.3)  # 避免API限制
    
    def upload_folder(self, folder_path, parent_page_id=None):
        """递归上传文件夹，针对您的三层结构优化"""
        if parent_page_id is None:
            parent_page_id = self.root_page_id
            
        folder_path = Path(folder_path)
        
        if not folder_path.exists():
            if self.progress_bar:
                self.progress_bar.write(f"❌ 文件夹不存在: {folder_path}")
            return
        
        # 处理您的三层结构：来源/日期/内容文件夹
        for source_folder in folder_path.iterdir():
            if not source_folder.is_dir():
                continue
            
            # 检查来源页面是否已存在
            if self.page_exists(parent_page_id, source_folder.name):
                # 获取已存在页面的ID
                source_page_id = self.get_page_id_by_title(parent_page_id, source_folder.name)
            else:
                # 为来源创建页面（如 AI_Engineer, Bloomberg_Live等）
                paragraph_blocks = self.create_paragraph_block(f"来源分类: {source_folder.name}")
                source_page_id = self.create_page(
                    source_folder.name, 
                    parent_page_id, 
                    paragraph_blocks
                )
            
            if not source_page_id:
                continue
                
            time.sleep(0.3)
            
            # 处理日期文件夹
            for date_folder in source_folder.iterdir():
                if not date_folder.is_dir():
                    continue
                
                # 检查日期页面是否已存在
                if self.page_exists(source_page_id, date_folder.name):
                    date_page_id = self.get_page_id_by_title(source_page_id, date_folder.name)
                else:
                    # 为日期创建页面
                    date_paragraph_blocks = self.create_paragraph_block(f"日期: {date_folder.name}")
                    date_page_id = self.create_page(
                        date_folder.name,
                        source_page_id,
                        date_paragraph_blocks
                    )
                
                if not date_page_id:
                    continue
                    
                time.sleep(0.3)
                
                # 处理内容文件夹
                for content_folder in date_folder.iterdir():
                    if not content_folder.is_dir():
                        continue
                    
                    # 直接处理该文件夹中的markdown文件，用文件夹名作为页面标题
                    self.process_markdown_files_simplified(content_folder, date_page_id)
    
    def process_markdown_files(self, folder_path, parent_page_id):
        """处理文件夹中的markdown文件（只处理summary开头的文件）"""
        # 只处理summary开头的markdown文件
        summary_files = [f for f in folder_path.glob("*.md") if f.name.lower().startswith("summary")]
        
        if not summary_files:
            return
            
        for file_path in summary_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 从文件名提取标题（去掉.md扩展名）
                title = file_path.stem
                
                # 检查文件是否已上传
                if self.page_exists(parent_page_id, title):
                    # 更新进度条（跳过的文件）
                    if self.progress_bar:
                        self.progress_bar.set_description(f"跳过: {title[:30]}...")
                        self.progress_bar.update(1)
                    continue
                
                # 转换markdown为blocks
                blocks = self.markdown_to_blocks(content)
                
                # 创建页面
                page_id = self.create_page(title, parent_page_id, blocks)
                
                # 更新进度条
                if self.progress_bar:
                    if page_id:
                        self.progress_bar.set_description(f"✅ {title[:30]}...")
                    else:
                        self.progress_bar.set_description(f"❌ {title[:30]}...")
                    self.progress_bar.update(1)
                
                time.sleep(0.3)  # 避免API限制
                
            except Exception as e:
                # 更新进度条（错误的文件）
                if self.progress_bar:
                    self.progress_bar.set_description(f"❌ 错误: {file_path.name[:25]}...")
                    self.progress_bar.update(1)
    
    def process_markdown_files_simplified(self, folder_path, parent_page_id):
        """简化版：直接用文件夹名作为页面标题，包含summary内容"""
        # 只处理summary开头的markdown文件
        summary_files = [f for f in folder_path.glob("*.md") if f.name.lower().startswith("summary")]
        
        if not summary_files:
            return
        
        # 用文件夹名作为页面标题
        page_title = folder_path.name
        
        # 检查页面是否已存在
        if self.page_exists(parent_page_id, page_title):
            # 更新进度条（跳过的文件）
            if self.progress_bar:
                self.progress_bar.set_description(f"跳过: {page_title[:30]}...")
                self.progress_bar.update(len(summary_files))  # 跳过所有文件
            return
        
        # 处理所有summary文件的内容（通常只有一个）
        all_content = []
        for file_path in summary_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                all_content.append(content)
                
            except Exception as e:
                if self.progress_bar:
                    self.progress_bar.set_description(f"❌ 读取错误: {file_path.name[:20]}...")
        
        # 合并所有内容（如果有多个summary文件）
        combined_content = "\n\n---\n\n".join(all_content) if len(all_content) > 1 else (all_content[0] if all_content else "")
        
        if not combined_content:
            if self.progress_bar:
                self.progress_bar.set_description(f"❌ 空内容: {page_title[:25]}...")
                self.progress_bar.update(len(summary_files))
            return
        
        # 转换markdown为blocks
        blocks = self.markdown_to_blocks(combined_content)
        
        # 创建页面
        page_id = self.create_page(page_title, parent_page_id, blocks)
        
        # 更新进度条
        if self.progress_bar:
            if page_id:
                self.progress_bar.set_description(f"✅ {page_title[:30]}...")
            else:
                self.progress_bar.set_description(f"❌ {page_title[:30]}...")
            self.progress_bar.update(len(summary_files))
        
        time.sleep(0.3)  # 避免API限制

def load_notion_settings():
    """从.podlens/setting读取Notion配置"""
    setting_file = Path('.podlens/setting')
    
    if not setting_file.exists():
        print("❌ 未找到配置文件，请先运行 autopod 生成配置文件")
        return None, None
    
    notion_token = None
    notion_page_id = None
    
    try:
        with open(setting_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key == 'notion_token' and not value.startswith('#'):
                        notion_token = value
                    elif key == 'notion_page_id' and not value.startswith('#'):
                        notion_page_id = value
    except Exception as e:
        print(f"❌ 读取配置文件失败: {e}")
        return None, None
    
    if not notion_token or not notion_page_id:
        print("❌ Notion 配置不完整")
        print("   请使用以下命令配置:")
        print("   autopod --notiontoken <your_token>")
        print("   autopod --notionpage <your_page_id>")
        return None, None
    
    return notion_token, notion_page_id

def main():
    # 从配置文件读取设置
    notion_token, notion_page_id = load_notion_settings()
    
    if not notion_token or not notion_page_id:
        return
    
    # 使用当前目录下的outputs文件夹
    markdown_folder = os.path.join(os.getcwd(), "outputs")
    
    # 创建上传器实例
    uploader = NotionMarkdownUploader(notion_token, notion_page_id)
    
    # 第一行输出
    print("📒 正在写入您的notion")
    
    # 计算总文件数
    total_files = uploader.count_summary_files(markdown_folder)
    
    if total_files == 0:
        print("❌ 未找到任何summary文件")
        return
    
    # 第二行输出 - 创建进度条
    with tqdm(total=total_files, desc="准备中...", unit="文件") as progress_bar:
        uploader.progress_bar = progress_bar
        uploader.upload_folder(markdown_folder)
    
    # 第三行输出
    print("✅ 导入成功!")

if __name__ == "__main__":
    main()