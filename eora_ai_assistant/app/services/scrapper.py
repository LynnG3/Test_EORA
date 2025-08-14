import os
import re
import json
import time

import requests
from bs4 import BeautifulSoup
# Selenium если не получится BeautifulSoup


class EoraScraper:
    """
    Класс для парсинга данных с сайта EORA.
    
    Позволяет извлекать текстовое содержимое страниц и сохранять
    результаты в JSON-файл для дальнейшего использования.
    """

    def __init__(self, base_url="https://eora.ru"):
        self.base_url = base_url
        self.visited_urls = set()
        self.data = []

    def scrape_url(self, url):
        """
        Парсинг отдельной страницы по URL.
        
        Извлекает текстовое содержимое страницы, удаляя ненужные элементы
        (скрипты, стили, навигацию и т.д.).
        
        Args:
            url (str): URL страницы для парсинга.
        """
        print(f"Scraping URL: {url}")
        if url in self.visited_urls:
            return

        self.visited_urls.add(url)

        try:
            # Задержка для предотвращения блокировки
            time.sleep(2)  # Пауза 2 секунды
            # заголовки браузеров для обхода защиты от скрапинга
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            # Выполняет HTTP-запрос
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            print(response)
            if response.status_code != 200:
                print(f"Failed to fetch {url}: {response.status_code}")
                return
            # Парсит HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Извлекает основной текст страницы
            content = soup.find('main') or soup.find('body')
            if content:
                # Удаляет скрипты, стили и другие ненужные элементы
                for tag in content.select(
                    'script, style, nav, footer, header'
                ):
                    tag.extract()

                # Получает текст и нормализует пробелы
                text = content.get_text(separator=' ', strip=True)
                text = re.sub(r'\s+', ' ', text)

                if text:
                    self.data.append({
                        'url': url,
                        'text': text,
                        'title': soup.title.string if soup.title else url
                    })
                    print(f"Scraped: {url}")
        except requests.exceptions.Timeout:
            print("The request timed out.")
        except requests.exceptions.RequestException as e:
            print(f"Error scraping {url}: {e}")

    def scrape_specific_urls(self, urls):
        """
        Парсинг списка URL-адресов.
        
        Args:
            urls (list): Список URL-адресов для парсинга.
            
        Returns:
            list: Список извлеченных данных.
        """
        for url in urls:
            self.scrape_url(url)

        return self.data

    def save_to_json(self, filename="data/scraped_data.json"):
        """
        Сохранение извлеченных данных в JSON-файл.

        Args:
            filename (str): Путь к файлу для сохранения данных.
        """
        abs_path = os.path.abspath(filename)
        print(f"Saving data to: {abs_path}")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

        print(f"Data saved to {filename}")
