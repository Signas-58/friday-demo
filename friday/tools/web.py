"""
Web tools — search, fetch pages, and global news briefings.
"""

import httpx
import xml.etree.ElementTree as ET
import asyncio  # Required for parallel execution
import re
from datetime import datetime

SEED_FEEDS = [
    'https://feeds.bbci.co.uk/news/world/rss.xml',
    'https://www.cnbc.com/id/100727362/device/rss/rss.html',
    'https://rss.nytimes.com/services/xml/rss/nyt/World.xml',
    'https://www.aljazeera.com/xml/rss/all.xml',
    'https://www.herald.co.zw/feed/'
]

FINANCE_SEED_FEEDS = [
    'https://www.cnbc.com/id/10000664/device/rss/rss.html',       # CNBC Finance
    'https://feeds.bloomberg.com/markets/news.rss',                # Bloomberg Markets
    'https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best',  # Reuters
    'https://feeds.marketwatch.com/marketwatch/topstories/',       # MarketWatch
    'https://rss.nytimes.com/services/xml/rss/nyt/Business.xml',  # NYT Business
]

async def fetch_and_parse_feed(client, url):
    """Helper function to handle a single feed request and parse its XML."""
    try:
        response = await client.get(url, headers={'User-Agent': 'Friday-AI/1.0'}, timeout=5.0)
        if response.status_code != 200:
            return []

        root = ET.fromstring(response.content)
        # Extract source name from URL (e.g., 'BBC' or 'NYTIMES')
        source_name = url.split('.')[1].upper()
        
        feed_items = []
        # Get top 5 items per feed
        items = root.findall(".//item")[:5]
        for item in items:
            title = item.findtext("title")
            description = item.findtext("description")
            link = item.findtext("link")
            
            if description:
                description = re.sub('<[^<]+?>', '', description).strip()

            feed_items.append({
                "source": source_name,
                "title": title,
                "summary": description[:200] + "..." if description else "",
                "link": link
            })
        return feed_items
    except Exception as e:
        print(f"Error fetching/parsing feed {url}: {e}")
        # If one feed fails, return an empty list so others can still succeed
        return []

def register(mcp):

    @mcp.tool()
    async def get_world_news() -> str:
        """
        Fetches the latest global headlines from major news outlets simultaneously.
        Use this when the user asks 'What's going on in the world?' or for recent events.
        """
        
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            # 1. Create a list of 'tasks' (one for each URL)
            tasks = [fetch_and_parse_feed(client, url) for url in SEED_FEEDS]
            
            # 2. Fire them all at once and wait for the results
            # results will be a list of lists: [[news from bbc], [news from nyt], ...]
            results_of_lists = await asyncio.gather(*tasks)
            
            # 3. Flatten the list of lists into a single list of articles
            all_articles = [item for sublist in results_of_lists for item in sublist]

        if not all_articles:
            return "The global news grid is unresponsive, sir. I'm unable to pull headlines."

        # 4. Format the final briefing
        report = ["### GLOBAL NEWS BRIEFING (LIVE)\n"]
        # Limit to top 25 items so we don't truncate late-stage feeds (like HERALD)
        for entry in all_articles[:25]:
            report.append(f"**[{entry['source']}]** {entry['title']}")
            report.append(f"{entry['summary']}")
            report.append(f"Link: {entry['link']}\n")

        return "\n".join(report)

    @mcp.tool()
    async def get_world_finance_news() -> str:
        """
        Fetches the latest finance and market headlines from major financial outlets simultaneously.
        Use this when the user asks about finance news, market updates, or economic developments.
        """

        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            tasks = [fetch_and_parse_feed(client, url) for url in FINANCE_SEED_FEEDS]
            results_of_lists = await asyncio.gather(*tasks)
            all_articles = [item for sublist in results_of_lists for item in sublist]

        if not all_articles:
            return "The financial feeds are unresponsive right now, sir. I can't pull market headlines."

        report = ["### FINANCE BRIEFING (LIVE)\n"]
        for entry in all_articles[:12]:
            report.append(f"**[{entry['source']}]** {entry['title']}")
            report.append(f"{entry['summary']}")
            report.append(f"Link: {entry['link']}\n")

        return "\n".join(report)

    @mcp.tool()
    async def search_web(query: str) -> str:
        """Search the web for a given query and return a summary of results."""
        from bs4 import BeautifulSoup
        import urllib.parse
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
                response = await client.get(url, headers=headers)
                if response.status_code != 200:
                    return f"Search engine returned status code {response.status_code}, boss."
                
                soup = BeautifulSoup(response.text, "html.parser")
                results = []
                
                # Organic result elements are inside div with class 'result'
                for result_div in soup.find_all("div", class_="result"):
                    title_elem = result_div.find("a", class_="result__a")
                    snippet_elem = result_div.find("a", class_="result__snippet")
                    
                    if not title_elem:
                        continue
                        
                    title = title_elem.get_text(strip=True)
                    href = title_elem.get("href", "")
                    
                    # Resolve DuckDuckGo redirect link
                    parsed_href = urllib.parse.urlparse(href)
                    query_params = urllib.parse.parse_qs(parsed_href.query)
                    
                    if "uddg" in query_params:
                        target_url = query_params["uddg"][0]
                    else:
                        if href.startswith("//"):
                            target_url = "https:" + href
                        elif href.startswith("/"):
                            target_url = "https://duckduckgo.com" + href
                        else:
                            target_url = href
                            
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else "No description available."
                    
                    results.append({
                        "title": title,
                        "url": target_url,
                        "snippet": snippet
                    })
                    
                    if len(results) >= 5:
                        break
                        
                if not results:
                    return f"I searched the web for '{query}', but no organic results were found, boss."
                    
                lines = [f"### Web Search Results for: {query}\n"]
                for i, r in enumerate(results, 1):
                    lines.append(f"{i}. **[{r['title']}]({r['url']})**")
                    lines.append(f"   {r['snippet']}")
                    lines.append(f"   Link: {r['url']}\n")
                    
                return "\n".join(lines)
        except Exception as e:
            return f"Error executing web search query: {str(e)}"

    @mcp.tool()
    async def fetch_url(url: str) -> str:
        """
        Downloads the content of a URL and extracts clean, readable text.
        Use this when the user wants you to read a webpage or summarize an article.
        """
        from bs4 import BeautifulSoup
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
                response = await client.get(url, headers=headers)
                if response.status_code != 200:
                    return f"Failed to download webpage. Server returned status code: {response.status_code}."
                
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Strip out unwanted elements
                for element in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
                    element.decompose()
                    
                # Extract clean text
                text = soup.get_text(separator=" ")
                
                # Clean up whitespace gaps
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                cleaned_text = "\n".join(chunk for chunk in chunks if chunk)
                
                limit = 5000
                if len(cleaned_text) > limit:
                    return cleaned_text[:limit] + "\n\n[Content truncated by F.R.I.D.A.Y. due to size limits]"
                
                return cleaned_text
        except Exception as e:
            return f"Error downloading webpage content: {str(e)}"
    
    @mcp.tool()
    async def open_world_monitor() -> str:
        """
        Opens the World Monitor dashboard (worldmonitor.app) in the system's web browser.
        Use this when the user wants a visual overview of global events or a real-time map.
        """
        url = "https://www.worldmonitor.app/dashboard?zoom=1.00&view=global&timeRange=7d&layers=conflicts%2Cbases%2Chotspots%2Cnuclear%2Csanctions%2Cweather%2Ceconomic%2Cwaterways%2Coutages%2Cmilitary%2Cnatural"
        
        try:
            import webbrowser
            webbrowser.open(url)
            return "Displaying the World Monitor on your primary screen now, sir."
        except Exception as e:
            return f"I'm unable to initialize the visual monitor: {str(e)}"

    @mcp.tool()
    async def open_finance_world_monitor() -> str:
        """
        Opens the Finance World Monitor dashboard (finance.worldmonitor.app) in the system's web browser.
        Use this when the user wants a visual overview of global financial markets and trends.
        """
        url = "https://finance.worldmonitor.app/dashboard"

        try:
            import webbrowser
            webbrowser.open(url)
            return "Displaying the Finance World Monitor on your primary screen now, sir."
        except Exception as e:
            return f"I'm unable to initialize the finance monitor: {str(e)}"