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
        # Fix: version number must be provided
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28',  # Required version number
        }
        self.base_url = 'https://api.notion.com/v1'
        self.uploaded_files = set()  # Record uploaded files
        self.progress_bar = None  # Progress bar reference
        
    def get_existing_pages(self, parent_id):
        """Get all child pages under the parent page"""
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
        """Check if page already exists"""
        existing_pages = self.get_existing_pages(parent_id)
        return title in existing_pages
    
    def get_page_id_by_title(self, parent_id, title):
        """Get page ID by title"""
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
        """Count the number of all summary files"""
        total_files = 0
        folder_path = Path(folder_path)
        
        if not folder_path.exists():
            return 0
            
        # Traverse three-layer structure: source/date/content folder
        for source_folder in folder_path.iterdir():
            if not source_folder.is_dir():
                continue
            for date_folder in source_folder.iterdir():
                if not date_folder.is_dir():
                    continue
                for content_folder in date_folder.iterdir():
                    if not content_folder.is_dir():
                        continue
                    # Count summary files
                    summary_files = [f for f in content_folder.glob("*.md") if f.name.lower().startswith("summary")]
                    total_files += len(summary_files)
        
        return total_files
        
    def markdown_to_blocks(self, markdown_content):
        """Convert markdown content to Notion blocks"""
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
                
            # Handle dividers
            if line == '---' or line == '***':
                if current_block:
                    paragraph_blocks = self.create_paragraph_block(current_block)
                    blocks.extend(paragraph_blocks)
                    current_block = ""
                blocks.append(self.create_divider_block())
                continue
                
            # Handle headings
            if line.startswith('#'):
                if current_block:
                    paragraph_blocks = self.create_paragraph_block(current_block)
                    blocks.extend(paragraph_blocks)
                    current_block = ""
                
                level = len(line) - len(line.lstrip('#'))
                title = line.lstrip('# ').strip()
                blocks.append(self.create_heading_block(title, level))
                
            # Handle code blocks
            elif line.startswith('```'):
                if current_block:
                    paragraph_blocks = self.create_paragraph_block(current_block)
                    blocks.extend(paragraph_blocks)
                    current_block = ""
                # Simplified handling here, can be more complex in practice
                blocks.append(self.create_code_block("code content"))
                
            # Handle unordered lists
            elif line.startswith('- ') or line.startswith('* '):
                if current_block:
                    paragraph_blocks = self.create_paragraph_block(current_block)
                    blocks.extend(paragraph_blocks)
                    current_block = ""
                text = line.lstrip('- *').strip()
                blocks.append(self.create_bullet_block(text))
                
            # Handle ordered lists (numbers, roman numerals, etc.)
            elif re.match(r'^[IVXivx]+\.\s', line) or re.match(r'^\d+\.\s', line) or re.match(r'^[a-zA-Z]\.\s', line):
                if current_block:
                    paragraph_blocks = self.create_paragraph_block(current_block)
                    blocks.extend(paragraph_blocks)
                    current_block = ""
                # Extract list content (remove the numbering prefix)
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
        """Parse markdown format and convert to Notion rich_text"""
        rich_text = []
        i = 0
        
        while i < len(text):
            # Handle bold **text**
            if i < len(text) - 3 and text[i:i+2] == '**':
                # Find the ending **
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
            
            # Handle italic *text* (but not **)
            elif i < len(text) - 2 and text[i] == '*' and (i == 0 or text[i-1:i+1] != '**') and (i+1 >= len(text) or text[i:i+2] != '**'):
                # Find the ending *
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
            
            # Handle normal text
            # Find the position of the next special character
            next_special = len(text)
            for special_char in ['**', '*']:
                pos = text.find(special_char, i)
                if pos != -1 and pos < next_special:
                    next_special = pos
            
            # Extract normal text
            if next_special > i:
                normal_text = text[i:next_special]
                if normal_text:
                    rich_text.append({
                        "type": "text",
                        "text": {"content": normal_text}
                    })
                i = next_special
            else:
                # If no special characters found, add remaining text
                remaining_text = text[i:]
                if remaining_text:
                    rich_text.append({
                        "type": "text",
                        "text": {"content": remaining_text}
                    })
                break
        
        return rich_text if rich_text else [{"type": "text", "text": {"content": text}}]

    def create_paragraph_block(self, text):
        # Split long text to comply with Notion API's 2000 character limit
        blocks = []
        max_length = 1900  # Leave some margin
        
        if len(text) <= max_length:
            rich_text = self.parse_rich_text(text)
            return [{
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": rich_text
                }
            }]
        
        # Split long text
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
        """Create new page"""
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
            "children": content_blocks[:100]  # Notion API limits to 100 blocks per request
        }
        
        response = requests.post(
            f'{self.base_url}/pages',
            headers=self.headers,
            json=data
        )
        
        if response.status_code == 200:
            page_data = response.json()
            page_id = page_data['id']
            
            # If there are more than 100 blocks, need to add them in batches
            if len(content_blocks) > 100:
                remaining_blocks = content_blocks[100:]
                self.add_blocks_to_page(page_id, remaining_blocks)
            
            return page_id
        else:
            print(f"Failed to create page: {response.status_code}, {response.text}")
            return None
    
    def add_blocks_to_page(self, page_id, blocks):
        """Add more blocks to page"""
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
                print(f"Failed to add blocks: {response.status_code}, {response.text}")
            
            time.sleep(0.3)  # Avoid API rate limiting
    
    def upload_folder(self, folder_path, parent_page_id=None):
        """Recursively upload folder, optimized for your three-layer structure"""
        if parent_page_id is None:
            parent_page_id = self.root_page_id
            
        folder_path = Path(folder_path)
        
        if not folder_path.exists():
            if self.progress_bar:
                self.progress_bar.write(f"❌ Folder does not exist: {folder_path}")
            return
        
        # Handle your three-layer structure: source/date/content folder
        for source_folder in folder_path.iterdir():
            if not source_folder.is_dir():
                continue
            
            # Check if source page already exists
            if self.page_exists(parent_page_id, source_folder.name):
                # Get existing page ID
                source_page_id = self.get_page_id_by_title(parent_page_id, source_folder.name)
            else:
                # Create page for source (e.g., AI_Engineer, Bloomberg_Live, etc.)
                paragraph_blocks = self.create_paragraph_block(f"Source category: {source_folder.name}")
                source_page_id = self.create_page(
                    source_folder.name, 
                    parent_page_id, 
                    paragraph_blocks
                )
            
            if not source_page_id:
                continue
                
            time.sleep(0.3)
            
            # Handle date folders
            for date_folder in source_folder.iterdir():
                if not date_folder.is_dir():
                    continue
                
                # Check if date page already exists
                if self.page_exists(source_page_id, date_folder.name):
                    date_page_id = self.get_page_id_by_title(source_page_id, date_folder.name)
                else:
                    # Create page for date
                    date_paragraph_blocks = self.create_paragraph_block(f"Date: {date_folder.name}")
                    date_page_id = self.create_page(
                        date_folder.name,
                        source_page_id,
                        date_paragraph_blocks
                    )
                
                if not date_page_id:
                    continue
                    
                time.sleep(0.3)
                
                # Handle content folders
                for content_folder in date_folder.iterdir():
                    if not content_folder.is_dir():
                        continue
                    
                    # Directly process markdown files in this folder, using folder name as page title
                    self.process_markdown_files_simplified(content_folder, date_page_id)
    
    def process_markdown_files(self, folder_path, parent_page_id):
        """Process markdown files in folder (only files starting with summary)"""
        # Only process markdown files starting with summary
        summary_files = [f for f in folder_path.glob("*.md") if f.name.lower().startswith("summary")]
        
        if not summary_files:
            return
            
        for file_path in summary_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract title from filename (remove .md extension)
                title = file_path.stem
                
                # Check if file has already been uploaded
                if self.page_exists(parent_page_id, title):
                    # Update progress bar (skipped files)
                    if self.progress_bar:
                        self.progress_bar.set_description(f"Skip: {title[:30]}...")
                        self.progress_bar.update(1)
                    continue
                
                # Convert markdown to blocks
                blocks = self.markdown_to_blocks(content)
                
                # Create page
                page_id = self.create_page(title, parent_page_id, blocks)
                
                # Update progress bar
                if self.progress_bar:
                    if page_id:
                        self.progress_bar.set_description(f"✅ {title[:30]}...")
                    else:
                        self.progress_bar.set_description(f"❌ {title[:30]}...")
                    self.progress_bar.update(1)
                
                time.sleep(0.3)  # Avoid API rate limiting
                
            except Exception as e:
                # Update progress bar (error files)
                if self.progress_bar:
                    self.progress_bar.set_description(f"❌ Error: {file_path.name[:25]}...")
                    self.progress_bar.update(1)
    
    def process_markdown_files_simplified(self, folder_path, parent_page_id):
        """Simplified version: use folder name as page title, include summary content"""
        # Only process markdown files starting with summary
        summary_files = [f for f in folder_path.glob("*.md") if f.name.lower().startswith("summary")]
        
        if not summary_files:
            return
        
        # Use folder name as page title
        page_title = folder_path.name
        
        # Check if page already exists
        if self.page_exists(parent_page_id, page_title):
            # Update progress bar (skipped files)
            if self.progress_bar:
                self.progress_bar.set_description(f"Skip: {page_title[:30]}...")
                self.progress_bar.update(len(summary_files))  # Skip all files
            return
        
        # Process all summary file content (usually only one)
        all_content = []
        for file_path in summary_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                all_content.append(content)
                
            except Exception as e:
                if self.progress_bar:
                    self.progress_bar.set_description(f"❌ Read error: {file_path.name[:20]}...")
        
        # Combine all content (if there are multiple summary files)
        combined_content = "\n\n---\n\n".join(all_content) if len(all_content) > 1 else (all_content[0] if all_content else "")
        
        if not combined_content:
            if self.progress_bar:
                self.progress_bar.set_description(f"❌ Empty content: {page_title[:25]}...")
                self.progress_bar.update(len(summary_files))
            return
        
        # Convert markdown to blocks
        blocks = self.markdown_to_blocks(combined_content)
        
        # Create page
        page_id = self.create_page(page_title, parent_page_id, blocks)
        
        # Update progress bar
        if self.progress_bar:
            if page_id:
                self.progress_bar.set_description(f"✅ {page_title[:30]}...")
            else:
                self.progress_bar.set_description(f"❌ {page_title[:30]}...")
            self.progress_bar.update(len(summary_files))
        
        time.sleep(0.3)  # Avoid API rate limiting

def load_notion_settings():
    """Load Notion configuration from .podlens/setting"""
    setting_file = Path('.podlens/setting')
    
    if not setting_file.exists():
        print("❌ Configuration file not found, please run autopodlens first to generate configuration")
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
        print(f"❌ Failed to read configuration file: {e}")
        return None, None
    
    if not notion_token or not notion_page_id:
        print("❌ Notion configuration incomplete")
        print("   Please configure using:")
        print("   autopodlens --notiontoken <your_token>")
        print("   autopodlens --notionpage <your_page_id>")
        return None, None
    
    return notion_token, notion_page_id

def main():
    # Load configuration from settings file
    notion_token, notion_page_id = load_notion_settings()
    
    if not notion_token or not notion_page_id:
        return
    
    # Use outputs folder in current directory
    markdown_folder = os.path.join(os.getcwd(), "outputs")
    
    # Create uploader instance
    uploader = NotionMarkdownUploader(notion_token, notion_page_id)
    
    # First line output
    print("📒 Writing to your Notion...")
    
    # Calculate total files
    total_files = uploader.count_summary_files(markdown_folder)
    
    if total_files == 0:
        print("❌ No summary files found")
        return
    
    # Second line output - create progress bar
    with tqdm(total=total_files, desc="Preparing...", unit="files") as progress_bar:
        uploader.progress_bar = progress_bar
        uploader.upload_folder(markdown_folder)
    
    # Third line output
    print("✅ Import successful!")

if __name__ == "__main__":
    main()