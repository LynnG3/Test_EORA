import sys
from pathlib import Path

# Корневая директория проекта в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.scrapper import EoraScraper


def main():
    # Создает директорию для данных, если её нет
    project_root = Path(__file__).parent.parent

    # Создает директорию для данных в корне проекта
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)

    # Путь к файлу с данными
    data_file = data_dir / "scraped_data.json"

    # URLs для парсинга
    urls = [
        "https://eora.ru/cases/promyshlennaya-bezopasnost",
        "https://eora.ru/cases/lamoda-systema-segmentacii-i-poiska-po-pohozhey-odezhde",
        "https://eora.ru/cases/ifarm-nejroset-dlya-ferm",
        "https://eora.ru"
    ]

    # Парсит сайт
    scraper = EoraScraper()
    scraper.scrape_specific_urls(urls)
    scraper.save_to_json(str(data_file))

    print("Scraping completed successfully!")


if __name__ == "__main__":
    main()
