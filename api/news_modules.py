import requests
from bot.side_utils import *
from pymongo import MongoClient
from os import getenv
from gtts import gTTS, lang


class NewsModules:

    client = MongoClient('localhost', 27017)
    news_db = client.news_db

    def get_news_details(self, url):
        response = requests.get(url, params={'apiKey': getenv('NEWS_API_KEY')})
        return response.json()

    # One time call for effective caching
    def create_news_sources(self, source_list):
        for source in source_list:
            source_info = {
                "search_id": source['id'],
                "name": source['name'],
                "description": source['description'],
                "lang": source['language'],
                "site_url": source['url'],
                "api_url": "https://newsapi.org/v2/top-headlines?sources=" + str(source['id'])
            }
            self.news_db.news_sources.insert_one(source_info)

    def get_news_summary(self, news_source_list):
        for source in news_source_list:
            article_list_response = self.get_news_details(source['api_url'])
            if article_list_response['status'] == 'error':
                return article_list_response
            article_list = article_list_response['articles']
            news_articles = {
                'name': source['name'],
                'search_id': source['search_id'],
                'lang': source['lang'],
                'articles': article_list,
            }
            self.news_db.news_articles.insert(news_articles, check_keys=False)

    def prepare_news_audio(self, name, lang_value, summary_desc):
        news_audio = gTTS(text=summary_desc, lang=lang_value)
        news_audio.save("audio_summary/" + str(name) + "-summary.mp3")

    def get_agency_id(self, agency_name):
        query = {"name": str(agency_name)}
        news_source = self.news_db.news_sources.find_one(query)
        return news_source['search_id']

    def get_agency_obj(self, search_id):
        return self.news_db.news_sources.find_one({"search_id": str(search_id)})

    def get_text_summary(self, agency_id):
        news_article_list = self.news_db.news_articles.find({'search_id': str(agency_id)})
        summary_report = '\t* Breaking Headlines are :*\n\n'
        for articles in news_article_list:
            for article in articles['articles']:
                summary_report += '[' + article['title'] + '](' + (article['url']) + ')\n\n'
        return summary_report

    def prepare_news_summary(self):
        news_articles = self.news_db.news_articles.find({})
        for article in news_articles:
            try:
                if article['lang'] not in lang.tts_langs():
                    continue
                summary_desc = '\n Recent headlines in ' + str(article['name']) + ' today are\n'
                for desc in article['articles']:
                    if (desc['description'] == None):
                        summary_desc += desc['title'] + "\n In other news \n"
                    else:
                        summary_desc += desc['title'] + "\n" + desc['description'] + "\n In other news \n"
                summary_desc += "\n Check back later for updates."
                self.prepare_news_audio(article['name'], article['lang'], summary_desc)
            except Exception as e:
                with open(LOGFILE, 'a') as filePointer:
                    filePointer.write(str(traceback.format_exc()) + CONTENT_SAPERATOR)
                continue
