import os
from dotenv import load_dotenv

from scrapper import DocketScraper
from analysis import analyze


# Load environment variables from the .env file
load_dotenv()


if __name__ == "__main__":
    url = "https://www.regulations.gov/docket/FCIC-21-0007"
    output_file = "docket.json"

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    scraper = DocketScraper(url)
    scraper.run(output_file)

    analyze(output_file, OPENAI_API_KEY)
