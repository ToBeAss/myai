import json
import requests
from datetime import datetime
from lib.tool import ToolBlueprint
from urllib.parse import quote_plus
import os


# Get the absolute path to the file
    #base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # Go up two levels to project root
    #file_path = os.path.join(base_dir, directory, f"{product_id}.json")


def read_from_memory():
    with open('memory.json', 'r') as f:
        data = json.load(f)
    return data


def write_to_memory(content: str, memory_type: str = "general"):
    """
    Write a new memory to the memory.json file.
    
    :param content: The content of the memory to store
    :param memory_type: The type of memory (personal, project, etc.)
    :return: Confirmation message
    """
    # Read existing memories
    try:
        with open('memory.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {"memories": []}
    
    # Find the next available ID
    existing_ids = [memory["id"] for memory in data["memories"]]
    next_id = max(existing_ids, default=0) + 1
    
    # Create new memory entry
    new_memory = {
        "id": next_id,
        "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "type": memory_type,
        "content": content
    }
    
    # Add to memories list
    data["memories"].append(new_memory)
    
    # Write back to file
    with open('memory.json', 'w') as f:
        json.dump(data, f, indent=4)
    
    return f"Memory saved with ID {next_id}: {content}"


def google_search_simple(query: str, num_results: int = 5):
    """
    Simple Google search using DuckDuckGo (completely free and more reliable).
    
    :param query: The search query
    :param num_results: Number of results to return (default: 5)
    :return: List of search results with titles and URLs
    """
    try:
        # Use DuckDuckGo instead of Google for better reliability
        search_url = "https://html.duckduckgo.com/html/"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        params = {
            'q': query
        }
        
        response = requests.get(search_url, headers=headers, params=params)
        response.raise_for_status()
        
        # Parse DuckDuckGo results
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return "Error: beautifulsoup4 package not installed. Run: pip install beautifulsoup4"
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = []
        search_results = soup.find_all('div', class_='web-result')
        
        for result in search_results[:num_results]:
            title_elem = result.find('h2')
            link_elem = result.find('a', class_='result__a')
            snippet_elem = result.find('a', class_='result__snippet')
            
            if title_elem and link_elem:
                title = title_elem.get_text().strip()
                url = link_elem.get('href')
                snippet = snippet_elem.get_text().strip() if snippet_elem else "No description available"
                
                results.append({
                    'title': title,
                    'url': url,
                    'snippet': snippet
                })
        
        # If no results from DuckDuckGo, try a simpler approach with alternative search
        if not results:
            return search_alternative(query, num_results)
        
        return {
            'query': query,
            'results': results,
            'total_found': len(results)
        }
        
    except Exception as e:
        return f"Search failed: {str(e)}. Try installing beautifulsoup4: pip install beautifulsoup4"


def search_alternative(query: str, num_results: int = 5):
    """
    Alternative search using a different approach when main search fails.
    """
    try:
        # Use Bing search as fallback
        search_url = f"https://www.bing.com/search?q={quote_plus(query)}&count={num_results}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = []
        search_results = soup.find_all('li', class_='b_algo')
        
        for result in search_results[:num_results]:
            title_elem = result.find('h2')
            link_elem = result.find('a')
            snippet_elem = result.find('p') or result.find('div', class_='b_caption')
            
            if title_elem and link_elem:
                title = title_elem.get_text().strip()
                url = link_elem.get('href')
                snippet = snippet_elem.get_text().strip() if snippet_elem else "No description available"
                
                results.append({
                    'title': title,
                    'url': url,
                    'snippet': snippet[:200] + '...' if len(snippet) > 200 else snippet
                })
        
        return {
            'query': query,
            'results': results,
            'total_found': len(results)
        }
        
    except Exception as e:
        return {
            'query': query,
            'results': [{'title': 'Search Error', 'url': '', 'snippet': f'Unable to perform search: {str(e)}'}],
            'total_found': 0
        }


def fetch_page_content(url: str, max_length: int = 2000):
    """
    Fetch and extract readable content from a webpage.
    
    :param url: The URL to fetch content from
    :param max_length: Maximum length of content to return
    :return: Cleaned text content from the page
    """
    try:
        # Clean up DuckDuckGo redirect URLs
        if url.startswith('//duckduckgo.com/l/?uddg='):
            from urllib.parse import unquote
            url = unquote(url.split('uddg=')[1].split('&')[0])
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return "Error: beautifulsoup4 package not installed"
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
            script.decompose()
        
        # Get text content
        text = soup.get_text()
        
        # Clean up the text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Limit length
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        return text
        
    except Exception as e:
        return f"Could not fetch content from {url}: {str(e)}"


def google_search_enhanced(query: str, num_results: int = 3, fetch_content: bool = True):
    """
    Enhanced search that optionally fetches full content from result pages.
    
    :param query: The search query
    :param num_results: Number of results to return (default: 3)
    :param fetch_content: Whether to fetch full page content (default: True)
    :return: Enhanced search results with full content
    """
    # First get the basic search results
    search_results = google_search_simple(query, num_results)
    
    if isinstance(search_results, str):  # Error case
        return search_results
    
    if not fetch_content or not search_results.get('results'):
        return search_results
    
    # Enhance results with full page content
    enhanced_results = []
    for result in search_results['results']:
        enhanced_result = result.copy()
        
        if result['url']:
            #print(f"🔍 Fetching content from: {result['title'][:50]}...")
            content = fetch_page_content(result['url'])
            enhanced_result['full_content'] = content
        else:
            enhanced_result['full_content'] = "No URL available"
            
        enhanced_results.append(enhanced_result)
    
    return {
        'query': query,
        'results': enhanced_results,
        'total_found': len(enhanced_results)
    }


def google_search_api(query: str, num_results: int = 5):
    """
    Google search using Custom Search JSON API (100 free searches per day).
    Requires GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID environment variables.
    
    :param query: The search query  
    :param num_results: Number of results to return (default: 5)
    :return: List of search results with titles, URLs, and snippets
    """
    api_key = os.getenv('GOOGLE_SEARCH_API_KEY')
    search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
    
    if not api_key or not search_engine_id:
        return "Error: Google Search API credentials not found. Set GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID environment variables."
    
    try:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': api_key,
            'cx': search_engine_id,
            'q': query,
            'num': min(num_results, 10)  # API max is 10
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get('items', []):
            results.append({
                'title': item.get('title', ''),
                'url': item.get('link', ''),
                'snippet': item.get('snippet', 'No description available')
            })
        
        return {
            'query': query,
            'results': results,
            'total_found': len(results),
            'search_info': data.get('searchInformation', {})
        }
        
    except Exception as e:
        return f"API search failed: {str(e)}"

read_from_memory_tool_blueprint = ToolBlueprint(
    name="read_from_memory",
    base_description="""
    Use this tool to gather memories from previous conversations.
    The memories are summaries of Tobias's past interactions and experiences, made by you, the AI.
    In any situation where you need to recall past interactions or information about Tobias, or if you think it might be relevant, you can use this tool to access the relevant memories.

    :return: A JSON object containing the memories.
    """,
    function=read_from_memory
)

write_to_memory_tool_blueprint = ToolBlueprint(
    name="write_to_memory",
    base_description="""
    Use this tool to save important information or memories from the current conversation.
    Store significant facts, preferences, decisions, experiences, or insights about Tobias that should be remembered for future interactions.
    Examples: personal preferences, project updates, important decisions, or noteworthy experiences.

    :param content: The memory content to store (required)
    :param memory_type: The type of memory - 'personal', 'project', 'preference', etc. (optional, defaults to 'general')
    :return: Confirmation message with the saved memory ID
    """,
    function=write_to_memory
)

google_search_tool_blueprint = ToolBlueprint(
    name="google_search",
    base_description="""
    Search for current information and fetch detailed content from result pages.
    Use this when you need up-to-date information, facts, news, or research on any topic.
    This tool not only finds relevant pages but also extracts their full content for detailed analysis.

    :param query: The search query (required)
    :param num_results: Number of results to return, 1-5 (optional, defaults to 3)
    :param fetch_content: Whether to fetch full page content for detailed info (optional, defaults to True)
    :return: Dictionary with search results including titles, URLs, snippets, and full page content
    """,
    function=google_search_enhanced
)