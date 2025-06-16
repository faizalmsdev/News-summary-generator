import requests
from bs4 import BeautifulSoup
import urllib.parse
import time
import json
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
from bs4 import BeautifulSoup
import os

# Import the news summary function
import nltk
from textblob import TextBlob
from newspaper import Article
from urllib.parse import urlparse

# Add the get_news_summary function
def setup_nltk():
    """Download required NLTK data"""
    try:
        nltk.data.find('tokenizers/punkt')
        nltk.data.find('corpora/stopwords')
    except LookupError:
        print("Downloading required NLTK data...")
        nltk.download('punkt')
        nltk.download('stopwords')

def resolve_redirected_url(url: str) -> str:
    """
    Given a Google News redirect URL, resolves and returns the final redirected URL.
    """
    # Setup Chrome options (headless)
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    # Start WebDriver
    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(url)
        time.sleep(5)  # Wait for the redirect to complete
        final_url = driver.current_url
    finally:
        driver.quit()

    return final_url


def get_news_summary(url, summary_sentences=3, return_json=False):
    """
    Generate a summary from a news article URL and return as dict
    
    Args:
        url (str): The news article URL
        summary_sentences (int): Number of sentences in the summary (default: 3)
        return_json (bool): If True, returns JSON string; if False, returns dict
    
    Returns:
        dict: Dictionary containing article summary and metadata
    """
    # Setup NLTK if needed
    setup_nltk()
    final_url = resolve_redirected_url(url)
    print(f"Resolved URL: {final_url}")
    try:
        # Validate URL
        parsed_url = urlparse(final_url)
        if not parsed_url.scheme or not parsed_url.netloc:
            error_result = {
                'success': False,
                'error': 'Invalid URL format',
                'url': final_url,
                'timestamp': datetime.now().isoformat()
            }
            return json.dumps(error_result, indent=2) if return_json else error_result
        
        # Initialize and download article
        article = Article(final_url)
        article.download()
        article.parse()
        
        # Check if article was successfully parsed
        if not article.text:
            error_result = {
                'success': False,
                'error': 'Could not extract text from the article',
                'url': final_url,
                'timestamp': datetime.now().isoformat()
            }
            return json.dumps(error_result, indent=2) if return_json else error_result
        
        # Use newspaper3k's built-in summarization
        article.nlp()
        newspaper_summary = article.summary
        
        # Alternative summary using TextBlob and NLTK
        blob = TextBlob(article.text)
        sentences = blob.sentences
        
        # Simple extractive summarization - get top sentences
        if len(sentences) <= summary_sentences:
            textblob_summary = str(blob)
        else:
            # Get sentences from different parts of the article
            step = len(sentences) // summary_sentences
            selected_sentences = []
            for i in range(0, len(sentences), step):
                if len(selected_sentences) < summary_sentences:
                    selected_sentences.append(str(sentences[i]))
            textblob_summary = ' '.join(selected_sentences)
        
        # Sentiment analysis using TextBlob
        sentiment = blob.sentiment
        
        # Determine sentiment label
        sentiment_label = "neutral"
        if sentiment.polarity > 0.1:
            sentiment_label = "positive"
        elif sentiment.polarity < -0.1:
            sentiment_label = "negative"
        
        # Determine objectivity label
        objectivity_label = "objective" if sentiment.subjectivity < 0.5 else "subjective"
        
        # Prepare successful result
        result = {
            'success': True,
            'url': final_url,
            'timestamp': datetime.now().isoformat(),
            'article': {
                'title': article.title or 'No title found',
                'authors': article.authors or [],
                'publish_date': article.publish_date.isoformat() if article.publish_date else None,
                'word_count': len(article.text.split()),
                'top_image': article.top_image or None
            },
            'summaries': {
                'newspaper3k': newspaper_summary or 'No summary generated',
                'textblob': textblob_summary or 'No summary generated'
            },
            'sentiment_analysis': {
                'polarity': round(sentiment.polarity, 3),
                'subjectivity': round(sentiment.subjectivity, 3),
                'sentiment_label': sentiment_label,
                'objectivity_label': objectivity_label
            },
            'keywords': article.keywords[:10] if hasattr(article, 'keywords') and article.keywords else []
        }
        
        return json.dumps(result, indent=2, default=str) if return_json else result
        
    except Exception as e:
        error_result = {
            'success': False,
            'error': str(e),
            'url': final_url,
            'timestamp': datetime.now().isoformat()
        }
        return json.dumps(error_result, indent=2) if return_json else error_result

class ComprehensiveNewsScraper:
    def __init__(self, headless=True):
        """Initialize the comprehensive news scraper"""
        self.chrome_options = Options()
        if headless:
            self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--disable-gpu")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        # Headers for requests
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    def scrape_google_news_articles(self, company_name, max_articles=5):
        """
        Scrapes Google News for articles about a specific company
        
        Args:
            company_name (str): Name of the company to search for
            max_articles (int): Maximum number of articles to scrape
        
        Returns:
            list: List of dictionaries containing basic article data
        """
        
        # Construct the Google News search URL
        base_url = "https://news.google.com/search"
        params = {
            'q': company_name,
            'hl': 'en-IN',
            'gl': 'IN',
            'ceid': 'IN:en'
        }
        
        search_url = f"{base_url}?{urllib.parse.urlencode(params)}"
        
        try:
            print(f"Searching for news articles about: {company_name}")
            print(f"URL: {search_url}")
            print("-" * 50)
            
            # Make the request
            response = requests.get(search_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # Parse the HTML content
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all article containers
            article_containers = soup.find_all('article') or soup.find_all(class_="xrnccd")
            
            if not article_containers:
                article_elements = soup.find_all(class_="WwrzSb")
                article_containers = []
                for element in article_elements:
                    container = element
                    for _ in range(10):
                        container = container.find_parent()
                        if container and (container.name == 'article' or 'article' in str(container.get('class', []))):
                            break
                    if container:
                        article_containers.append(container)
            
            if not article_containers:
                print("No article containers found. The page structure might have changed.")
                return []
            
            # Extract basic data from articles
            articles_data = []
            for i, container in enumerate(article_containers[:max_articles]):
                
                article_data = {
                    'google_news_url': 'URL not found',
                    'date': 'Date not found',
                    'author': 'Author not found',
                    'source_title': 'Source not found',
                    'source_image_url': 'Image not found',
                    'content_image_url': 'Content image not found',
                    'text_content': 'Content not found',
                    'article_title': 'Title not found'
                }
                
                # Extract URL
                url_element = container.find(class_="WwrzSb") or container.find(class_="JtKRv")
                if url_element:
                    href = url_element.get('href')
                    if href:
                        if href.startswith('./'):
                            article_data['google_news_url'] = f"https://news.google.com{href[1:]}"
                        elif href.startswith('/'):
                            article_data['google_news_url'] = f"https://news.google.com{href}"
                        else:
                            article_data['google_news_url'] = href
                
                # Extract source information
                source_container = container.find(class_="oovtQ")
                if source_container:
                    img_element = source_container.find('img')
                    if img_element:
                        img_src = img_element.get('src') or img_element.get('data-src')
                        if img_src:
                            article_data['source_image_url'] = img_src
                    
                    source_text = source_container.get_text(strip=True)
                    if source_text:
                        article_data['source_title'] = source_text
                
                # Extract content image
                content_image_element = container.find(class_="Quavad vwBmvb")
                if content_image_element:
                    img_tag = content_image_element.find('img')
                    if img_tag:
                        img_src = (img_tag.get('src') or 
                                  img_tag.get('data-src') or 
                                  img_tag.get('data-lazy-src') or
                                  img_tag.get('srcset', '').split(',')[0].strip().split(' ')[0])
                        
                        if img_src:
                            if img_src.startswith('http'):
                                article_data['content_image_url'] = img_src
                            elif img_src.startswith('//'):
                                article_data['content_image_url'] = f"https:{img_src}"
                            elif img_src.startswith('./'):
                                article_data['content_image_url'] = f"https://news.google.com{img_src[1:]}"
                            elif img_src.startswith('/'):
                                article_data['content_image_url'] = f"https://news.google.com{img_src}"
                
                # Extract date and author
                metadata_container = container.find(class_="UOVeFe")
                if metadata_container:
                    date_element = metadata_container.find(class_="hvbAAd")
                    if date_element:
                        article_data['date'] = date_element.get_text(strip=True)
                    
                    author_element = metadata_container.find(class_="bInasb")
                    if author_element:
                        article_data['author'] = author_element.get_text(strip=True)
                
                # Extract article title
                title_element = (container.find('h3') or 
                               container.find('h4') or 
                               container.find(class_="JtKRv") or
                               container.find(class_="mCBkyc"))
                if title_element:
                    article_data['article_title'] = title_element.get_text(strip=True)
                
                # Extract text content/summary
                content_selectors = [
                    'div[class*="snippet"]',
                    'div[class*="summary"]',
                    'div[class*="description"]',
                    '.st',
                    'span[class*="snippet"]'
                ]
                
                for selector in content_selectors:
                    content_element = container.select_one(selector)
                    if content_element:
                        article_data['text_content'] = content_element.get_text(strip=True)
                        break
                
                if article_data['text_content'] == 'Content not found':
                    all_text = container.get_text(separator=' ', strip=True)
                    content_parts = []
                    for part in all_text.split():
                        if len(' '.join(content_parts)) > 200:
                            break
                        content_parts.append(part)
                    
                    if content_parts:
                        article_data['text_content'] = ' '.join(content_parts)
                
                articles_data.append(article_data)
                
                print(f"Found Article {i+1}: {article_data['article_title']}")
            
            return articles_data
            
        except requests.RequestException as e:
            print(f"Error making request: {e}")
            return []
        except Exception as e:
            print(f"Error parsing content: {e}")
            return []

    def get_redirect_url(self, google_news_url):
        """Get the actual article URL from Google News redirect"""
        try:
            response = requests.get(google_news_url, headers=self.headers, allow_redirects=True, timeout=10)
            return response.url
        except:
            return google_news_url

    def get_news_summary_from_external(self, url):
        """
        Call the get_news_summary function and return the result
        """
        try:
            print(f"Calling get_news_summary for: {url}")
            
            # Call the actual get_news_summary function
            json_result = get_news_summary(url, return_json=False)
            
            return json_result
            
        except Exception as e:
            print(f"Error calling get_news_summary: {str(e)}")
            return None

    def extract_detailed_article_data(self, url, include_full_content=True):
        """Extract comprehensive article data from URL using external summary function"""
        try:
            print(f"Getting summary from external function for: {url}")
            
            # Call the external summary function
            summary_result = self.get_news_summary_from_external(url)
            
            if not summary_result or not summary_result.get('success'):
                print("✗ Failed to get summary from external function")
                print(summary_result)
                return None
            
            # Extract data from the external function result
            detailed_data = {
                'final_url': summary_result.get('url', url),
                'scraped_at': summary_result.get('timestamp', datetime.now().isoformat()),
                'detailed_title': summary_result.get('article', {}).get('title', 'Title not found'),
                'detailed_author': summary_result.get('article', {}).get('authors', ['Author not found']),
                'detailed_publish_date': summary_result.get('article', {}).get('publish_date', 'Date not found'),
                'word_count': summary_result.get('article', {}).get('word_count', 0),
                'main_image_url': summary_result.get('article', {}).get('top_image', 'Image not found'),
                'content_summary': summary_result.get('summaries', {}).get('newspaper3k', 'Summary not available'),
                'textblob_summary': summary_result.get('summaries', {}).get('textblob', 'TextBlob summary not available'),
                'sentiment_analysis': summary_result.get('sentiment_analysis', {}),
                'keywords': summary_result.get('keywords', []),
                'external_summary_success': True
            }
            
            # Add full content flag but don't include actual full content since we're using external summary
            if include_full_content:
                detailed_data['full_content_note'] = "Full content extraction skipped - using external summary function"
            
            return detailed_data
            
        except Exception as e:
            print(f"Error extracting detailed article data: {str(e)}")
            return None

    def scrape_comprehensive_news(self, company_name, max_articles=3, extract_full_content=True):
        """
        Main method to scrape comprehensive news data using external summary function
        
        Args:
            company_name (str): Company name to search for
            max_articles (int): Maximum number of articles to process
            extract_full_content (bool): Flag for compatibility (not used with external summary)
        
        Returns:
            dict: Comprehensive news data
        """
        print(f"Starting comprehensive news scraping for: {company_name}")
        print(f"Using external get_news_summary function")
        print("="*80)
        
        # Step 1: Get basic articles from Google News
        basic_articles = self.scrape_google_news_articles(company_name, max_articles)
        
        if not basic_articles:
            return {
                'search_query': company_name,
                'scraped_at': datetime.now().isoformat(),
                'total_articles_found': 0,
                'articles': []
            }
        
        # Step 2: Extract detailed content for each article using external function
        comprehensive_articles = []
        
        for i, basic_article in enumerate(basic_articles):
            print(f"\nProcessing article {i+1}/{len(basic_articles)}")
            print("-"*50)
            
            # Merge basic data
            comprehensive_article = {
                'article_id': i + 1,
                'google_news_data': basic_article,
                'detailed_data': None,
                'extraction_success': False
            }
            
            if basic_article['google_news_url'] != 'URL not found':
                # Get the actual article URL
                try:
                    actual_url = self.get_redirect_url(basic_article['google_news_url'])
                    print(f"Actual URL: {actual_url}")
                    
                    # Extract detailed content using external summary function
                    detailed_data = self.extract_detailed_article_data(actual_url, extract_full_content)
                    
                    if detailed_data:
                        comprehensive_article['detailed_data'] = detailed_data
                        comprehensive_article['extraction_success'] = True
                        print("✓ Successfully extracted summary using external function")
                        
                        # Print the newspaper3k summary
                        newspaper_summary = detailed_data.get('content_summary', 'No summary available')
                        print(f"✓ Newspaper3k Summary: {newspaper_summary[:100]}...")
                    else:
                        print("✗ Failed to extract content using external function")
                        
                except Exception as e:
                    print(f"✗ Error processing article: {str(e)}")
            
            comprehensive_articles.append(comprehensive_article)
            
            # Add delay between requests
            time.sleep(2)
        
        # Compile final result
        result = {
            'search_query': company_name,
            'scraped_at': datetime.now().isoformat(),
            'total_articles_found': len(comprehensive_articles),
            'successful_extractions': sum(1 for article in comprehensive_articles if article['extraction_success']),
            'summary_method': 'external_get_news_summary_function',
            'articles': comprehensive_articles
        }
        
        return result

    def save_comprehensive_data(self, data, filename=None):
        """Save comprehensive data to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"comprehensive_news_external_summary_{data['search_query'].replace(' ', '_')}_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\nComprehensive news data saved to: {filename}")
        return filename

    def print_summary(self, data):
        """Print a summary of the scraped data"""
        print("\n" + "="*100)
        print("COMPREHENSIVE NEWS SCRAPING SUMMARY (Using External Summary Function)")
        print("="*100)
        print(f"Search Query: {data['search_query']}")
        print(f"Scraped At: {data['scraped_at']}")
        print(f"Total Articles Found: {data['total_articles_found']}")
        print(f"Successful External Extractions: {data['successful_extractions']}")
        print(f"Summary Method: {data.get('summary_method', 'external_function')}")
        print("-"*100)
        
        for article in data['articles']:
            print(f"\nArticle {article['article_id']}:")
            print(f"  Title: {article['google_news_data']['article_title']}")
            print(f"  Source: {article['google_news_data']['source_title']}")
            print(f"  Date: {article['google_news_data']['date']}")
            print(f"  External Summary Extraction: {'✓' if article['extraction_success'] else '✗'}")
            
            if article['detailed_data']:
                # Print newspaper3k summary
                newspaper_summary = article['detailed_data'].get('content_summary', 'No summary available')
                if newspaper_summary != 'No summary available':
                    summary_preview = newspaper_summary[:150]
                    print(f"  Newspaper3k Summary: {summary_preview}...")
                
                # Print additional extracted data
                word_count = article['detailed_data'].get('word_count', 0)
                if word_count > 0:
                    print(f"  Word Count: {word_count}")
                
                keywords = article['detailed_data'].get('keywords', [])
                if keywords:
                    print(f"  Keywords: {', '.join(keywords[:5])}")
                
                sentiment = article['detailed_data'].get('sentiment_analysis', {})
                if sentiment:
                    sentiment_label = sentiment.get('sentiment_label', 'unknown')
                    polarity = sentiment.get('polarity', 0)
                    print(f"  Sentiment: {sentiment_label} (polarity: {polarity})")
        
        print("="*100)

def main():
    """Main function to run the comprehensive news scraper with external summary"""
    print("Enhanced Comprehensive News Scraper (Using External Summary Function)")
    print("="*70)
    
    # Get user input
    company_name = input("Enter the company name to search for: ").strip()
    
    if not company_name:
        print("Please enter a valid company name.")
        return
    
    try:
        max_articles = int(input("Enter max number of articles to process (default: 3): ").strip() or "3")
    except ValueError:
        max_articles = 3
    
    print("Note: Using external get_news_summary function for content extraction and summarization")
    
    # Initialize scraper
    scraper = ComprehensiveNewsScraper(headless=True)
    
    # Scrape comprehensive news data
    print(f"\nStarting comprehensive scraping...")
    comprehensive_data = scraper.scrape_comprehensive_news(
        company_name, 
        max_articles=max_articles,
        extract_full_content=True  # This flag is maintained for compatibility but not used
    )
    
    # Print summary
    scraper.print_summary(comprehensive_data)
    
    # Save to file
    save_choice = input("\nSave results to JSON file? (y/n): ").strip().lower()
    if save_choice == 'y':
        filename = input("Enter filename (press Enter for default): ").strip()
        if not filename:
            filename = None
        
        saved_file = scraper.save_comprehensive_data(comprehensive_data, filename)
        print(f"Data saved to: {saved_file}")
    
    print("\nScraping completed using external summary function!")

if __name__ == "__main__":
    main()