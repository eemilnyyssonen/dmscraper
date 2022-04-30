import os
import json
import re
from typing import Any

from dotenv import load_dotenv
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.mail import MailSender
from scrapy import signals


# Get envs from .env
load_dotenv(verbose = True)
# Get envs needed
EMAIL = os.getenv('EMAIL')
PASSWORD = os.getenv('PASSWORD')
TARGET = 'origin'

class DiscSpider(scrapy.Spider):
    name = 'discspoder'
    start_urls = [
        'https://europe.discmania.net/'
        ]

    def parse(self, response):
        cats = response.css('li.nav__sub-t__item a::attr(href)').getall()[0:4]
        yield from response.follow_all(cats, self.parse_cats)

    def parse_cats(self, response):
        links = response.css('div.main div.o-layout div.o-layout__item a.product-link::attr(href)')
        yield from response.follow_all(links, self.parse_prodpage)

        pg = response.css('span.next a')
        yield from response.follow_all(pg, self.parse_cats)


    def parse_prodpage(self, response):
        yield {
            'name': response.css('h1.section__title-text::text').get(),
            'description': ''.join(response.css('div.product-single__content-text p::text').getall()),
            'color(s)-weight(size)/qtu': dict(zip([ii.strip() for ii in response.css('option::text').getall()], response.css('option::attr(data-stock-quantity)').getall())),
            'price': response.css('span.money::text').get(),
            'link': response.url
        }

    @classmethod
    def from_crawler(cls, crawler) -> scrapy.Spider:
        spider = cls()
        crawler.signals.connect(spider.spider_closed, signals.spider_closed)
        return spider

    def spider_closed(self, spider) -> Any:
        result = check_json()
        first_sentence = f"Here are the ({len(result)}) results I found using the search term(s) {TARGET}:\n\n"
        body_ = ""
        if result: 
            for r in result:
                body_ += f"""Click here to get yours!\n\n{r['link']}\n\nName: {r['name']}\nPrice: {r['price']}\nAvailable weights and quantity: {r['color(s)-weight(size)/qtu']}\n\nDescription:\n\n{r['description']}
                \n\n"""
            mailer = MailSender(mailfrom=EMAIL,
                                smtphost="smtp.gmail.com", smtpport=465, smtpuser=EMAIL,  smtppass=PASSWORD, smtpssl=True, smtptls=True)
            return mailer.send(to=['eemil41@gmail.com'], subject='Spider found the target!', body=first_sentence + body_)
        self.logger.info('Found no targets.')

def check_json() -> bool:
    f = open('/home/eemilnyyssonen/Documents/DmScraper/items.json')
    data = json.load(f)
    #Check if target in discs, example term 'enigma'
    filtered_discs = list(filter(lambda x: re.search(TARGET, x['name'].lower()), data))
    return filtered_discs#[0]

if __name__ == "__main__":
    process = CrawlerProcess(settings={
        "FEEDS": {
            "/home/eemilnyyssonen/Documents/DmScraper/items.json": {
                "format": "json",
                "overwrite": True}
        },
    })
    process.crawl(DiscSpider)
    process.start()
