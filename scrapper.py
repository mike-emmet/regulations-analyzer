import time
import json
import random
import re
import html
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils import download_pdf


class DocketScraper:
    def __init__(self, url):
        self.url = url
        self.driver = self._initialize_driver()
        self.docket_data = {}
        self.documents_data = []

    @staticmethod
    def _initialize_driver():
        """Initialize the Chrome WebDriver with custom settings."""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/536.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/536.36",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/90.0"
        ]
        chrome_options = Options()
        chrome_options.add_argument(f'user-agent={random.choice(user_agents)}')
        return webdriver.Chrome(options=chrome_options)

    def _wait_for_element(self, by, value, timeout=30):
        """Wait for an element to be present on the page."""
        return WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((by, value)))

    def _extract_agency(self):
        try:
            agenda_tab = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Unified Agenda')]")
            agenda_tab.click()
            self._wait_for_element(By.CSS_SELECTOR, 'div.ua-abstract', 3000)
            agenda_text = self._safe_find_element(By.XPATH, '//div[contains(@class, "ua-abstract")]//p')
            self.docket_data['Agenda'] = agenda_text

        except Exception as e:
            print(f"Error navigating to Docket Agenda tab: {e}")
        time.sleep(10)

    def extract_docket_details(self):
        """Extract basic docket details."""
        try:
            self._wait_for_element(By.XPATH, '//main[@class="main-content"]', 30000)
            self.docket_data['Title'] = self._safe_find_element(By.XPATH, '//h1[@class="h3 mt-0 mb-1 font-weight-bold js-title"]')
            self.docket_data['Docket ID'] = self._safe_find_element(By.XPATH, '//label[contains(text(), "Docket ID")]/following-sibling::p')
            self.docket_data['Agency'] = self._safe_find_element(By.XPATH, "//div[@class='col-md-12 mt-2 mb-4']//p[@class='lead text-muted mb-3 js-created-text']//strong")
            self.docket_data['Summary'] = self._safe_find_element(By.XPATH, "//div[@class='px-2']//div[@class='PREAMB']//p")
            self.docket_data['Docket Type'] = self._safe_find_element(By.XPATH, "//span[@class='text-uppercase text-muted d-inline-block ml-xs mb-0 align-bottom small font-weight-bold js-doctype']")
            self._wait_for_element(By.XPATH, "//a[contains(text(), 'All Comments on Docket')]", 30000)
            self.docket_data['Number of Comments'] = self._safe_find_element(By.XPATH, "//p[@class='mb-0 js-comments-posted']")
        except Exception as e:
            print(f"Error extracting docket details: {e}")

        self._extract_agency()

    def navigate_to_tab(self, tab_name):
        """Navigate to a specific tab."""
        try:
            tab = self.driver.find_element(By.XPATH, f"//a[contains(text(), '{tab_name}')]")
            tab.click()
            time.sleep(5)
        except Exception as e:
            print(f"Error navigating to {tab_name} tab: {e}")

    def extract_documents(self):
        """Extract document details from the 'Docket Documents' tab."""
        try:
            document_cards = self.driver.find_elements(By.CSS_SELECTOR, "div.card.card-type-proposed-rule.ember-view")
            document_links = [card.find_element(By.XPATH, ".//h3[@class='h4 card-title']//a[@class='ember-view']").get_attribute("href")
                              for card in document_cards]
            for link in document_links:
                self.driver.get(link)
                time.sleep(5)
                self._extract_single_document()
        except Exception as e:
            print(f"Error extracting document information: {e}")

    def _extract_comments(self):
        current_document_url = self.driver.current_url
        current_document_comments_url = current_document_url + "/comment"
        page = 1
        comment_list = []

        while page <= 2:
            if page > 1:
                current_document_comments_url += f"?pageNumber={page}"
            try:
                self.driver.get(current_document_comments_url)
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.results-container'))
                )
            except:
                break

            comment_cards = self.driver.find_elements(By.XPATH, '//div[contains(@class, "card-type-comment")]')

            for comment_card in comment_cards:
                comment_url = comment_card.find_element(By.XPATH,
                                                        ".//h3[contains(@class, 'card-title')]/a").get_attribute("href")
                comment_list.append(comment_url)

            time.sleep(10)
            page += 1

        comments = []
        print("Total Comments: ", len(comment_list))
        com_count = 1
        for comment_url in comment_list:
            print("Comment Number ", com_count)
            com_count += 1
            time.sleep(10)
            try:
                self.driver.get(comment_url)
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'main.main-content'))
                )
                comment_content = self.driver.find_element(By.XPATH,
                                                      '//h2[contains(@class, "section-heading")]/following-sibling::div[1]').text
                commenter_info = dict()
                try:
                    commenter_info_tab = self.driver.find_element(By.XPATH, '//div[@id="tab-submitter-info"]/ul')
                    commenter_info_list = commenter_info_tab.find_elements(By.TAG_NAME, "li")

                    for info in commenter_info_list:
                        key = info.find_element(By.TAG_NAME, "label").get_attribute("innerHTML").strip().split('\n')[0]
                        value = info.find_element(By.TAG_NAME, "p").get_attribute("innerHTML").strip()
                        commenter_info[key] = value
                except:
                    pass
                attachments = 0
                attachment_types = []
                try:
                    attachments = self.driver.find_element(By.XPATH, '//span[contains(@class, "badge-pill")]').text
                    attachment_urls = self.driver.find_elements(By.XPATH, '//a[contains(@class, "btn-block")]')
                    for attachment_url in attachment_urls:
                        att_url = attachment_url.get_attribute("href")
                        file_type = urlparse(att_url).path.split('.')[-1]
                        attachment_types.append(file_type)
                except:
                    pass

                try:
                    posted_on = self.driver.find_element(By.XPATH,
                                                    '//div[@class="col-md-12 mt-2 mb-4"]//p[@class="lead text-muted mb-3 js-posted-text"]'
                                ).text.split("on")[-1].lstrip()
                    commenter_info["Posted On"] = posted_on
                except:
                    pass

                commenter_info["Attachments"] = int(attachments)
                commenter_info["Attachment Types"] = attachment_types

                cleaned_comment = html.unescape(comment_content)
                cleaned_comment = re.sub(r"\s+", " ", cleaned_comment).strip()
                cleaned_comment = re.sub(r"•", "-", cleaned_comment)
                commenter_info["Comment"] = cleaned_comment

                comments.append(commenter_info)
            except:
                continue

        return comments

    def _extract_single_document(self):
        """Extract details of a single document."""
        doc = {}
        try:
            self._wait_for_element(By.XPATH, '//h1[@class="h3 mt-0 mb-1 font-weight-bold js-title"]')
            try:
                doc['Proposed Rule Title'] = self._wait_for_element(By.XPATH, '//h1[@class="h3 mt-0 mb-1 font-weight-bold js-title"]').text
            except:
                pass
            try:
                doc['Posted By'] = self._safe_find_element(By.XPATH, '//div[@class="col-md-12 mt-2 mb-4"]//p[@class="lead text-muted mb-3 js-posted-text"]//strong')
            except:
                pass
            try:
                doc['Posted Date'] = self._safe_find_element(By.XPATH, '//div[@class="col-md-12 mt-2 mb-4"]//p[@class="lead text-muted mb-3 js-posted-text"]').split("on")[-1].lstrip()
            except:
                pass
            try:
                doc['Document ID'] = self._safe_find_element(By.XPATH, '//div[@class="card-block py-0 pl-2 small text-muted"]//p[@class="mb-0"]')
            except:
                pass
            try:
                doc['Comments Received'] = self._safe_find_element(By.XPATH, '//div[@class="card-block py-0 pl-2 small text-muted"]//p[@class="mb-0 js-comments-received"]')
            except:
                pass

            extracted_data = {}

            try:
                # Get document content
                class_list = ["AGY", "ACT", "SUM", "ADD", "FURINF", "SUPLINF"]
                content_element = self.driver.find_element(By.XPATH,
                                                      '//main[@class="main-content"]//div[@class="row mb-6"]//div[@class="col-md-12"]//div[@class="px-2"]')
                for class_name in class_list:
                    item = content_element.find_element(By.XPATH, f".//div[@class='{class_name}']")
                    heading = item.find_element(By.TAG_NAME, "h2").text.strip()
                    content = ""
                    content_section = item.find_elements(By.TAG_NAME, "p")
                    for item_content in content_section:
                        content += item_content.text.strip()
                    if heading:
                        extracted_data[heading] = content

                doc["Document"] = {**extracted_data}
            except:
                pass

            document_url = self.driver.find_element(By.XPATH, "//ul[@class='dropdown-menu']/li[2]/a").get_attribute("href")
            file_name = download_pdf(document_url)
            doc["Document Path"] = file_name
            comments = self._extract_comments()
            doc["Comments"] = comments
            self.documents_data.append(doc)
        except Exception as e:
            print(f"Error extracting single document: {e}")

    def _safe_find_element(self, by, value):
        """Safely find an element and return its text or None."""
        try:
            return self.driver.find_element(by, value).text
        except:
            return None

    def save_data(self, file_name="docket.json"):
        """Save extracted data to a JSON file."""
        try:
            with open(file_name, "w", encoding="utf-8") as json_file:
                data = {**self.docket_data, "Documents": self.documents_data}
                json.dump(data, json_file, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving data: {e}")

    def run(self, output_file):
        """Main execution workflow."""
        try:
            self.driver.get(self.url)
            time.sleep(5)
            self.extract_docket_details()
            self.navigate_to_tab("Docket Documents")
            self.extract_documents()
            self.save_data(output_file)
        finally:
            self.driver.quit()
        print("Docket Data Scrape Completed")
