import requests
from bs4 import BeautifulSoup

def crawl_news_sources():
    # Example of scraping a news site
    url = "https://example-news-site.com/atrocity-news"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    articles = soup.find_all('article')  # Adjust based on the site's HTML structure
    atrocities = []
    
    for article in articles:
        title = article.find('h2').text
        description = article.find('p').text
        image_url = article.find('img')['src']
        region = article.find('span', class_='region').text
        
        # Scoring mechanism (this is a simple placeholder)
        score = len(description.split())  # Simplified: score based on description length
        
        atrocities.append({
            'title': title,
            'description': description,
            'image_url': image_url,
            'region': region,
            'score': score  # Ranking based on score
        })
        
    return sorted(atrocities, key=lambda x: x['score'], reverse=True)