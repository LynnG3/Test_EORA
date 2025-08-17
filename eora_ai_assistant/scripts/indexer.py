import sys
from pathlib import Path

# Корневая директория проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.scrapper import EoraScraper


def main():
    """Основная функция для создания индекса."""
    project_root = Path(__file__).parent.parent

    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)

    # Путь к файлу с данными
    data_file = data_dir / "scraped_data.json"

    # URLs для парсинга (будут автоматически обновляться)
    urls = [
        # URLs будут автоматически обновляться скриптом url_extractor.py
        "https://eora.ru"  # Базовый URL как fallback
    ]

    # Парсит сайт
    scraper = EoraScraper()
    scraper.scrape_specific_urls(urls)
    scraper.save_to_json(str(data_file))

    print("Scraping completed successfully!")


if __name__ == "__main__":
    main()
