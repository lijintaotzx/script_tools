# coding=utf-8
from queue import Queue
from threading import Thread

import os
import requests
from fake_useragent import UserAgent
from lxml import etree


class ProxyPool:
    def __init__(self, ip_type, out_file_path='my_proxy_pool'):
        self.url = 'https://www.xicidaili.com/nn/{}'
        self.http_test_url = 'http://httpbin.org/get'
        self.https_test_url = 'https://www.baidu.com/'

        self.ip_type = ip_type
        self.out_file_path = out_file_path

        self.parse_html_queue = Queue()
        self.check_ip_queue = Queue()

        if not os.path.exists(self.out_file_path):
            os.makedirs(self.out_file_path)
        if not out_file_path.endswith('/'):
            self.out_file_path = self.out_file_path + '/'

    def get_headers(self):
        return {'User-Agent': UserAgent().random}

    def get_html(self, url):
        return requests.get(
            url=url,
            headers=self.get_headers()
        ).text

    def index_url_in(self):
        for page in range(1, 2):
            self.parse_html_queue.put(self.url.format(page))

    def get_xpath_value(self, xpath_value):
        return None if not len(xpath_value) else xpath_value[0]

    def parse_html(self, url):
        print("*" * 50)
        print(url)
        html = self.get_html(url)
        p = etree.HTML(html)
        ip_list = p.xpath('//table/tr')[1:]
        for info in ip_list:
            ip = self.get_xpath_value(info.xpath('./td[2]/text()'))
            port = self.get_xpath_value(info.xpath('./td[3]/text()'))
            address = self.get_xpath_value(info.xpath('./td[4]/a/text()'))
            ip_type = self.get_xpath_value(info.xpath('./td[6]/text()'))
            self.check_ip_queue.put({'ip': ip, 'port': port, 'ip_type': ip_type, 'address': address})

    def html_spider(self):
        self.index_url_in()

        task_list = []
        # 循环在消息队列中获取url，开启新线程，直到队列中url被取空
        while not self.parse_html_queue.empty():
            url = self.parse_html_queue.get()
            task = Thread(target=self.parse_html, args=(url,))
            task_list.append(task)
            task.start()

        [task.join() for task in task_list]

    def check_and_write_ip(self, ip_info):
        if self.ip_test(ip_info['ip'], ip_info['port'], ip_info['ip_type']):
            file_name = '{}{}.txt'.format(self.out_file_path, ip_info['ip_type'])
            content = '|'.join(list(ip_info.values())) + '\n'
            with open(file_name, 'a') as f:
                f.write(content)

    def ip_test(self, ip, port, ip_type):
        if ip_type == 'HTTP':
            url = self.http_test_url
            proxies = {
                'http': 'http://{}:{}'.format(ip, port),
                'https': ''
            }
        elif ip_type == 'HTTPS':
            url = self.http_test_url
            proxies = {
                'http': '',
                'https': 'https://{}:{}'.format(ip, port)
            }
        else:
            print('暂不支持：{}'.format(ip_type))
            return False

        try:
            requests.get(url=url, headers=self.get_headers(), proxies=proxies, timeout=3)
            print("{}|{}, \33[31m可用\033[0m".format(ip, port))
            return True
        except Exception as e:
            print("{}|{}, 不可用".format(ip, port))
            return False

    def get_proxy_task(self):
        import time
        time.sleep(10)
        task_list = []
        while not self.check_ip_queue.empty():
            ip_info = self.check_ip_queue.get()
            t = Thread(target=self.check_and_write_ip, args=(ip_info,))
            task_list.append(t)
            t.start()

        [t.join() for t in task_list]

    def run(self):
        tasks = [self.html_spider, self.get_proxy_task]
        t = []

        for task in tasks:
            task = Thread(target=task)
            t.append(task)
            task.start()
        [task.join() for task in t]


if __name__ == '__main__':
    proxy_pool = ProxyPool(ip_type='http')
    proxy_pool.run()
