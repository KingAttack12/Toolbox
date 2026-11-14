import time
import unittest
from email.utils import formatdate
from unittest.mock import patch

from app import news


def feed(items):
    return ('<rss><channel>' + ''.join(
        '<item><title><![CDATA[' + title + ']]></title><link>' + url +
        '</link><pubDate>' + formatdate(date, usegmt=True) + '</pubDate></item>'
        for title, url, date in items) + '</channel></rss>').encode()


class NewsTests(unittest.TestCase):
    def setUp(self):
        self.state = patch.multiple(news, _items=[], _updated=None, _next_refresh=0)
        self.state.start()

    def tearDown(self):
        self.state.stop()

    def test_untrusted_links_markup_and_dates(self):
        now = time.time()
        data = feed([
            ('<b>Un titre</b>', 'https://www.lemonde.fr/article', now),
            ('Ancien', 'https://www.lemonde.fr/old', now - 90000),
            ('Futur', 'https://www.lemonde.fr/future', now + 1000),
            ('Autre domaine', 'https://www.lemonde.fr.evil.test/x', now),
            ('Script', 'javascript:alert(1)', now),
        ])
        items = news.parse_feed(data, 'Le Monde', 'www.lemonde.fr', now)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['title'], 'Un titre')
        with self.assertRaises(ValueError):
            news.parse_feed(b'<!DOCTYPE rss><rss/>', 'Le Monde', 'www.lemonde.fr', now)

    def test_shared_cache_limits_downloads(self):
        now = time.time()
        data = feed([('Titre', 'https://www.lemonde.fr/article', now)])
        with patch.object(news, 'urlopen') as fetch:
            fetch.return_value.__enter__.return_value.read.return_value = data
            first = news.headlines()
            self.assertEqual(len(first['items']), 1)
            self.assertEqual(news.headlines(), first)
            self.assertEqual(fetch.call_count, 2)

    def test_outage_keeps_only_recent_items_and_backs_off(self):
        now = time.time()
        news._items = [{'title': 'Récent', 'url': 'https://www.lemonde.fr/x', 'source': 'Le Monde', 'published_at': now},
                       {'title': 'Ancien', 'url': 'https://www.lemonde.fr/y', 'source': 'Le Monde', 'published_at': now-90000}]
        news._updated = now - 3600
        with patch.object(news, 'urlopen', side_effect=TimeoutError) as fetch:
            result = news.headlines()
            self.assertEqual(len(result['items']), 1)
            self.assertTrue(result['stale'])
            news.headlines()
            self.assertEqual(fetch.call_count, 2)

    def test_concurrent_request_does_not_wait_for_refresh(self):
        news._lock.acquire()
        try:
            with patch.object(news, 'urlopen') as fetch:
                self.assertEqual(news.headlines()['items'], [])
                fetch.assert_not_called()
        finally:
            news._lock.release()
