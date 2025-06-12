import requests
from bs4 import BeautifulSoup
from transformers import pipeline
import re
import warnings
warnings.filterwarnings("ignore")

class WebScraperSummarizer:
    def __init__(self):
        """Initialize the web scraper with AI summarization capabilities"""
        print("Loading AI model for summarization...")
        self.summarizer = pipeline(
            "summarization", 
            model="facebook/bart-large-cnn",
            device=-1  # Use CPU
        )
        print("Model loaded successfully!")

    def scrape_content(self, url):
        """Scrape text content from the given URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()

            text_content = ""
            content_selectors = [
                'article', 'main', '.content', '#content', 
                '.post', '.entry', 'div.text', 'div.body'
            ]

            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    text_content = " ".join([elem.get_text() for elem in elements])
                    break

            if not text_content:
                paragraphs = soup.find_all(['p', 'div', 'span'])
                text_content = " ".join([p.get_text() for p in paragraphs])

            text_content = re.sub(r'\\s+', ' ', text_content).strip()
            return text_content

        except requests.exceptions.RequestException as e:
            return f"Error fetching URL: {str(e)}"
        except Exception as e:
            return f"Error parsing content: {str(e)}"

    def chunk_text(self, text, max_chunk_size=1000):
        """Split text into chunks for processing"""
        sentences = text.split('. ')
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk + sentence) < max_chunk_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def summarize_text(self, text, max_length=150, min_length=50):
        """Summarize text using AI model with professional prompt"""
        if not text or len(text.strip()) < 50:
            return "Text too short to summarize meaningfully."

        try:
            instruction = "Write a concise, professionally worded summary for a business news article: "
            prompt_text = instruction + text

            if len(prompt_text) > 1000:
                chunks = self.chunk_text(prompt_text)
                chunk_summaries = []

                for chunk in chunks[:5]:
                    summary = self.summarizer(
                        chunk,
                        max_length=max_length//len(chunks[:5]),
                        min_length=min_length//len(chunks[:5]),
                        do_sample=False
                    )
                    chunk_summaries.append(summary[0]['summary_text'])

                combined_summary = " ".join(chunk_summaries)
                if len(combined_summary) > max_length * 2:
                    final_summary = self.summarizer(
                        combined_summary,
                        max_length=max_length,
                        min_length=min_length,
                        do_sample=False
                    )
                    return final_summary[0]['summary_text']
                else:
                    return combined_summary
            else:
                summary = self.summarizer(
                    prompt_text,
                    max_length=max_length,
                    min_length=min_length,
                    do_sample=False
                )
                return summary[0]['summary_text']

        except Exception as e:
            return f"Error during summarization: {str(e)}"

    def process_url(self, url, summary_length="medium"):
        """Main method to scrape URL and return summary"""
        print(f"Scraping content from: {url}")
        content = self.scrape_content(url)

        if content.startswith("Error"):
            return {
                "url": url,
                "error": content,
                "summary": None,
                "original_length": 0
            }

        print(f"Scraped {len(content)} characters")

        length_params = {
            "short": {"max_length": 150, "min_length": 60},
            "medium": {"max_length": 1000, "min_length": 100},
            "long": {"max_length": 1000, "min_length": 150}
        }

        params = length_params.get(summary_length, length_params["medium"])

        print("Generating summary...")
        summary = self.summarize_text(content, **params)

        return {
            "url": url,
            "summary": summary,
            "original_length": len(content),
            "summary_length": len(summary),
            "compression_ratio": f"{len(summary)/len(content)*100:.1f}%"
        }

def main():
    """Example usage"""
    scraper = WebScraperSummarizer()
    test_urls = [
        "https://www.moneycontrol.com/news/business/startup/wellness-startup-biopeak-raises-3-5-million-in-seed-funding-from-ranjan-pai-office-accel-s-prashanth-prakash-others-13103236.html"
    ]

    for url in test_urls:
        print(f"\\n{'='*60}")
        result = scraper.process_url(url, summary_length="medium")

        if result.get("error"):
            print(f"Failed to process {url}")
            print(f"Error: {result['error']}")
        else:
            print(f"URL: {result['url']}")
            print(f"Original length: {result['original_length']} characters")
            print(f"Summary length: {result['summary_length']} characters")
            print(f"Compression: {result['compression_ratio']}")
            print(f"\\nSummary:\\n{result['summary']}")

if __name__ == "__main__":
    main()