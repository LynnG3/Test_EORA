import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import json
from pathlib import Path
import sys

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from eora_ai_assistant.logger import logger

class SimpleURLExtractor:
    """Простой класс для извлечения ссылок на кейсы с eora.ru"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.base_url = "https://eora.ru"
    
    def extract_case_urls(self):
        """Извлекает все ссылки на кейсы"""
        case_urls = []
        
        try:
            # 1. Парсим главную страницу
            logger.info("Extracting URLs from main page...")
            response = self.session.get(self.base_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ищем все ссылки на кейсы
            case_links = soup.find_all('a', href=re.compile(r'/cases/'))
            for link in case_links:
                href = link.get('href')
                if href:
                    full_url = urljoin(self.base_url, href)
                    if full_url not in case_urls:
                        case_urls.append(full_url)
            
            # 2. Парсим страницу портфолио
            logger.info("Extracting URLs from portfolio page...")
            portfolio_url = f"{self.base_url}/cases/"
            try:
                response = self.session.get(portfolio_url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Ищем ссылки на кейсы
                    portfolio_links = soup.find_all('a', href=re.compile(r'/cases/'))
                    for link in portfolio_links:
                        href = link.get('href')
                        if href:
                            full_url = urljoin(self.base_url, href)
                            if full_url not in case_urls:
                                case_urls.append(full_url)
            except Exception as e:
                logger.warning(f"Could not parse portfolio page: {e}")
            
            # 3. Убираем дубликаты и сортируем
            unique_urls = sorted(list(set(case_urls)))
            
            logger.info(f"Found {len(unique_urls)} unique case URLs")
            
            return unique_urls
            
        except Exception as e:
            logger.error(f"Error extracting URLs: {e}")
            return []
    
    def save_urls_to_file(self, urls, filename="extracted_case_urls.json"):
        """Сохраняет найденные URLs в файл"""
        data = {
            "source": "auto_extracted_from_eora",
            "total_urls": len(urls),
            "urls": urls
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(urls)} URLs to {filename}")
    
    def update_indexer(self, urls):
        """Обновляет файл indexer.py с новыми URLs"""
        try:
            indexer_path = Path(__file__).parent / "indexer.py"
            
            with open(indexer_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Формируем новый список URLs
            urls_str = ',\n        '.join([f'"{url}"' for url in urls])
            
            # Заменяем существующий список
            new_content = re.sub(
                r'urls = \[.*?\]',
                f'urls = [\n        {urls_str}\n    ]',
                content,
                flags=re.DOTALL
            )
            
            with open(indexer_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            logger.info(f"Updated {indexer_path} with {len(urls)} URLs")
            
        except Exception as e:
            logger.error(f"Error updating indexer.py: {e}")


def main():
    """Основная функция"""
    logger.info("Starting URL extraction...")

    extractor = SimpleURLExtractor()

    # Извлекаем URLs
    case_urls = extractor.extract_case_urls()

    if case_urls:
        # Сохраняем в файл
        extractor.save_urls_to_file(case_urls)

        # Обновляем indexer.py
        extractor.update_indexer(case_urls)

        logger.info("URL extraction completed successfully!")
        logger.info(f"Found URLs: {case_urls}")
    else:
        logger.error("No URLs found!")


if __name__ == "__main__":
    main()
