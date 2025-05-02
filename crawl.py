import schedule
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
from urllib.parse import urljoin
import time

# === Debugging Setup ===
DEBUG = True
TARGET_URLS = [
    'https://www.notion.so/blog',
    'https://evernote.com/blog',
    'https://blog.todoist.com',
    'https://www.onenote.com/blog'
]

# === MongoDB connection ===
MONGO_URI = 'mongodb+srv://nakzuwu:Nakzuwu1!@cluster0.yqfbchb.mongodb.net/test?retryWrites=true&w=majority'
client = MongoClient(MONGO_URI)
db = client['notion_clone']
collection = db['crawled_data']

def debug_print(message):
    if DEBUG:
        print(f"[DEBUG] {message}")

def crawl_single_url(url):
    try:
        debug_print(f"Fetching URL: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        debug_print(f"Status {response.status_code} for {url}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try different selectors for articles
        possible_selectors = [
            {'name': 'article', 'selector': 'article'},
            {'name': 'div.post', 'selector': 'div.post'},
            {'name': 'div.blog-post', 'selector': 'div.blog-post'},
            {'name': 'div.article', 'selector': 'div.article'},
        ]
        
        articles = []
        for selector in possible_selectors:
            articles = soup.select(selector['selector'])
            if articles:
                debug_print(f"Found {len(articles)} articles using selector '{selector['name']}'")
                break
        
        if not articles:
            debug_print("No articles found with standard selectors, trying fallback")
            articles = soup.find_all(['article', 'div'], class_=lambda x: x and any(c in x.lower() for c in ['post', 'article', 'blog', 'entry']))
            debug_print(f"Found {len(articles)} articles with fallback selector")
        
        new_count = 0
        for i, article in enumerate(articles):  
            debug_print(f"\nProcessing article {i+1}/{len(articles)}")
            
            # Extract link
            sources = article.find('a', href=True)
            if not sources:
                debug_print("No link found in article, skipping")
                continue
                
            article_url = urljoin(url, sources['href'])
            debug_print(f"Article URL: {article_url}")
            
            # Check if already exists
            if collection.find_one({'sources': article_url}):
                debug_print("Article already in database, skipping")
                continue
            
            # Fetch article content
            try:
                article_resp = requests.get(article_url, headers=headers, timeout=10)
                article_soup = BeautifulSoup(article_resp.text, 'html.parser')
                
                # Extract title
                title = article_soup.find('h1')
                if not title:
                    title = article_soup.find('title')
                title_text = title.get_text().strip() if title else "No Title Found"
                debug_print(f"Title: {title_text}")
                
                # Extract content
                paragraphs = article_soup.find_all('p')
                content = '\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
                
                # Save to database
                data = {
                    'title': title_text,
                    'sources': article_url,
                    'content': content,
                    'source': url,
                    'crawled_at': time.time()
                }
                collection.insert_one(data)
                new_count += 1
                debug_print("Successfully saved article")
                
            except Exception as e:
                debug_print(f"Error processing article: {str(e)}")
                continue
                
        return new_count
        
    except Exception as e:
        debug_print(f"Error crawling {url}: {str(e)}")
        return 0

def debug_crawl():
    total_new = 0
    for url in TARGET_URLS:
        debug_print(f"\n{'='*50}")
        debug_print(f"CRAWLING: {url}")
        debug_print(f"{'='*50}")
        new = crawl_single_url(url)
        total_new += new
        debug_print(f"Added {new} new articles from {url}")
    
    debug_print(f"\nTotal new articles added: {total_new}")
    debug_print(f"Total articles in DB: {collection.count_documents({})}")
    
    # Print latest 3 entries
    debug_print("\nLatest entries:")
    for doc in collection.find().sort('_id', -1).limit(3):
        debug_print(f"- {doc['title']} ({doc['sources']})")

def scheduled_crawl():
    """Function to be run on schedule with logging"""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting scheduled crawl...")
    try:
        for url in TARGET_URLS:
            new = crawl_single_url(url)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Crawl completed successfully")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error during crawl: {str(e)}")

if __name__ == "__main__":
    schedule.every(6).hours.do(scheduled_crawl)
    
    scheduled_crawl()
    
    print("Crawler scheduler started. Press Ctrl+C to exit.")
    while True:
        schedule.run_pending()
        time.sleep(60)  