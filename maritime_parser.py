"""
XML Parser for Norwegian Maritime Regulations (Sjøtrafikkforskriften)
Extracts paragraphs from Chapter 3 (Kapittel 3)
"""

import re
import sys
from typing import List, Dict, Optional

# Force UTF-8 encoding for output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')


class Chapter3Parser:
    """Parser for Chapter 3 of the maritime traffic regulations."""
    
    def __init__(self, xml_file: str):
        """Initialize parser with XML file path."""
        self.xml_file = xml_file
        self.paragraphs = []
        self._parse()
    
    def _parse(self):
        """Parse the XML file and extract paragraphs."""
        with open(self.xml_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # First, extract all sections with their titles and IDs
        section_pattern = r'<section class="section"[^>]*id="(kapittel-3-kapittel-\d+)"[^>]*>.*?<h3>(.*?)</h3>'
        sections = re.findall(section_pattern, content, re.DOTALL)
        
        # Build a mapping of section IDs to titles
        section_titles = {}
        for section_id, title in sections:
            clean_title = re.sub(r'<[^>]+>', '', title).strip()
            section_titles[section_id] = clean_title
        
        # Pattern to match legal articles in Chapter 3
        # Match articles with id starting with "kapittel-3-" (both main and subsections)
        # kapittel-3-paragraf-X for § 13 (main chapter intro)
        # kapittel-3-kapittel-Y-paragraf-X for §§ 14-164 (subsections)
        pattern = r'<article class="legalArticle"[^>]*id="kapittel-3-(?:kapittel-)?[^"]*"[^>]*>.*?</article>(?=\s*(?:<article class="legalArticle"|</section>|<section class="section"))'
        articles = re.findall(pattern, content, re.DOTALL)
        
        for article in articles:
            # Extract paragraph number
            num_match = re.search(r'<span class="legalArticleValue">(§\s*\d+)</span>', article)
            if not num_match:
                continue
            
            para_num = num_match.group(1).strip()
            
            # Extract the article ID to determine which section it belongs to
            id_match = re.search(r'id="(kapittel-3-kapittel-\d+)-paragraf-\d+"', article)
            subchapter = None
            if id_match:
                section_id = id_match.group(1)
                subchapter = section_titles.get(section_id, None)
            
            # Extract title
            title_match = re.search(r'<span class="legalArticleTitle">\((.*?)\)</span>', article)
            title = title_match.group(1).strip() if title_match else ""
            
            # Extract all paragraph content (legalP elements)
            content_pattern = r'<article class="legalP"[^>]*>(.*?)</article>'
            content_matches = re.findall(content_pattern, article, re.DOTALL)
            
            # Clean up HTML tags from content
            cleaned_content = []
            for content_text in content_matches:
                clean_text = re.sub(r'<[^>]+>', '', content_text)
                clean_text = clean_text.replace('&nbsp;', ' ').strip()
                if clean_text:
                    cleaned_content.append(clean_text)
            
            if cleaned_content:
                self.paragraphs.append({
                    'number': para_num,
                    'title': title,
                    'subchapter': subchapter,
                    'content': cleaned_content
                })
    
    def get_by_number(self, number: str) -> Optional[Dict[str, str]]:
        """Get a specific paragraph by number (e.g., '113')."""
        for para in self.paragraphs:
            if number in para['number']:
                return para
        return None
    
    def get_all(self) -> List[Dict[str, str]]:
        """Get all paragraphs."""
        return self.paragraphs
    
    def search(self, keyword: str) -> List[Dict[str, str]]:
        """Search paragraphs by keyword in title or content."""
        keyword_lower = keyword.lower()
        results = []
        for para in self.paragraphs:
            if (keyword_lower in para['title'].lower() or 
                any(keyword_lower in content.lower() for content in para['content'])):
                results.append(para)
        return results
    
    @staticmethod
    def format(para: Dict[str, str]) -> str:
        """Format a paragraph for display."""
        output = ""
        # Add subchapter title if available
        if para.get('subchapter'):
            output += f"{para['subchapter']}\n\n"
        
        output += f"{para['number']}. ({para['title']})\n"
        for content in para['content']:
            output += f"\n{content}"
        return output


def main():
    """Main function demonstrating usage."""
    # Parse the XML file
    parser = Chapter3Parser("sf-20210210-0523.xml")
    
    print(f"Found {len(parser.get_all())} paragraphs in Chapter 3\n")
    print("=" * 80)
    
    # Example 1: Get a specific paragraph
    print("\nExample 1: Get § 113")
    print("=" * 80)
    para_113 = parser.get_by_number('113')
    if para_113:
        print(parser.format(para_113))
    
    # Example 2: Search by keyword
    print("\n\n" + "=" * 80)
    print("Example 2: Search for paragraphs about 'Sauda'")
    print("=" * 80)
    sauda_results = parser.search('Sauda')
    for para in sauda_results:
        print(f"\n{parser.format(para)}")
        print("-" * 80)
    
    # Example 3: Get paragraphs in a range
    print("\n\n" + "=" * 80)
    print("Example 3: Paragraphs 110-116 (Rogaland area)")
    print("=" * 80)
    for num in range(110, 117):
        para = parser.get_by_number(str(num))
        if para:
            print(f"\n{parser.format(para)}")
            print("-" * 80)


if __name__ == "__main__":
    main()
