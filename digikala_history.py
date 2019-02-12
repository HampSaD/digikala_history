# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'digikalaextractor.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

import os
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QThread, QFile
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.uic import loadUi
import re
import requests
from bs4 import BeautifulSoup


class ProcessThread(QThread):
    def __init__(self, UI):
        QThread.__init__(self)
        self.UI = UI

    def __del__(self):
        self.wait()

    def stop(self):
        self.terminate()

    def run(self):
        if self.UI.username.text() == '':
            self.UI.log.append('لطفا ایمیل خود را وارد کنید')
            return
        if self.UI.password.text() == '':
            self.UI.log.append('لطفا پسورد خود را وارد کنید')
            return

        self.UI.log.append('شروع')

        def dkprice_to_numbers(dkprice):
            '''gets something like ۱۱۷،۰۰۰ تومان and returns 117000'''
            convert_dict = {u'۱': '1', u'۲': '2', u'۳': '3', u'۴': '4', u'۵': '5',
                            u'۶': '6', u'۷': '7', u'۸': '8', u'۹': '9', u'۰': '0', }
            price = u'۰' + dkprice
            for k in convert_dict.keys():
                price = re.sub(k, convert_dict[k], price)

            price = re.sub('[^0-9]', '', price)
            return int(price)

        def extract_data(one_page, all_orders, all_post_prices):
            soup = BeautifulSoup(one_page.text, 'html.parser')
            # there might be more than one table
            for this_table in soup.find_all('div', class_='c-table-order__body'):
                for this_item in this_table.find_all('div', class_='c-table-order__row'):
                    name = this_item.find('span').get_text()
                    dknum = this_item.find(
                        'div', class_='c-table-order__cell--value').get_text()
                    num = dkprice_to_numbers(dknum)
                    dkprice = this_item.find(
                        'div', class_='c-table-order__cell--price-value').get_text()
                    price = dkprice_to_numbers(dkprice)
                    dkdiscount = this_item.find(
                        'div', class_='c-table-order__cell c-table-order__cell--discount').get_text()
                    discount = dkprice_to_numbers(dkdiscount)
                    date = soup.find('h4').span.get_text()
                    date = re.sub(u'ثبت شده در تاریخ ', '', date)
                    all_orders.append((date, name, num, price, discount))

            dkpost_price = soup.find_all(
                'div', class_='c-table-draught__col')[3].get_text()
            post_price = dkprice_to_numbers(dkpost_price)
            all_post_prices.append(post_price)

        self.UI.log.append('تلاش برای ورود')
        url = 'https://www.digikala.com/users/login/'
        payload = {'login[email_phone]': self.UI.username.text(),
                   'login[password]': self.UI.password.text(), 'remember': 1}
        session = requests.session()
        r = session.post(url, data=payload)
        if r.status_code != 200:
            self.UI.log.append('مشکل در اتصال. کد خطا: %s' % r.status_code)
            return

        successful_login_text = 'سفارش‌های من'
        if re.search(successful_login_text, r.text):
            self.UI.log.append('لاگین موفق')
        else:
            self.UI.log.append('کلمه عبور یا نام کاربری اشتباه است')
            return

        page_number = 1
        orders = session.get(
            'https://www.digikala.com/profile/orders/?page=%i' % page_number)
        soup = BeautifulSoup(orders.text, 'html.parser')

        all_orders = []  # (list of (date, name, number, item_price))
        all_post_prices = []  # list of post prices

        while not soup.find('div', class_='c-profile-empty'):
            for this_order in soup.find_all('a', class_='btn-order-more'):
                this_order_link = this_order.get('href')
                print('going to fetch: http://digikala.com' + this_order_link)
                one_page = session.get('http://digikala.com' + this_order_link)
                extract_data(one_page, all_orders, all_post_prices)
            self.UI.log.append('بررسی صفحه %i' % page_number)
            page_number += 1
            orders = session.get(
                'https://www.digikala.com/profile/orders/?page=%i' % page_number)
            soup = BeautifulSoup(orders.text, 'html.parser')

        self.UI.log.append('پایان')

        total_price = 0
        total_purchase = 0
        full_purchase_list = ''
        n = 0
        total_post_price = 0
        total_discount = 0
        self.UI.output_general.setRowCount(len(all_orders))

        for date, name, num, price, discount in all_orders:
            this_purchase_str = "تاریخ %s:‌ %s عدد %s, به قیمت هر واحد %s\n" % (
                date, num, name, price)
            full_purchase_list = this_purchase_str + full_purchase_list
            this_product_total_price = (price * num) - discount
            total_price += this_product_total_price
            total_purchase += 1
            total_discount += discount

            self.UI.output_general.setItem(n, 0, QTableWidgetItem(str(date)))
            self.UI.output_general.setItem(n, 1, QTableWidgetItem(str(num)))
            self.UI.output_general.setItem(
                n, 2, QTableWidgetItem(str(this_product_total_price)))
            self.UI.output_general.setItem(
                n, 3, QTableWidgetItem(str(discount)))
            self.UI.output_general.setItem(n, 4, QTableWidgetItem(str(name)))
            n = n + 1
        purchase_count = len(all_post_prices)
        for post_price in all_post_prices:
            total_post_price += post_price

        self.UI.output_result.clear()
        price_item = [
            'کل خرید شما از دیجی کالا:    {} تومان'.format(total_price)]
        total_post_price_item = [
            'مجموع هزینه ی پست:          {} تومان'.format(total_post_price)]
        total_discount_item = [
            'مجموع تخفیفات دریافتی:     {} تومان'.format(total_discount)]
        purchase_item = ['تعداد خرید:    {} قطعه'.format(total_purchase)]
        purchase_count_item = ['دفعات خرید:    {} بار'.format(purchase_count)]

        self.UI.output_result.addItems(price_item)
        self.UI.output_result.addItems(total_post_price_item)
        self.UI.output_result.addItems(total_discount_item)
        self.UI.output_result.addItems(purchase_item)
        self.UI.output_result.addItems(purchase_count_item)


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def get_data():
    window.PT = ProcessThread(window)
    window.PT.start()
    window.run.setText("توقف")
    window.PT.finished.connect(done)
    window.run.clicked.disconnect(get_data)
    window.run.clicked.connect(window.PT.stop)


def done():
    window.run.setText("اجرا")
    window.run.clicked.disconnect(window.PT.stop)
    window.run.clicked.connect(get_data)


def setupWindow(window):
    # connect signals and slots in here
    window.run.clicked.connect(get_data)
    window.username.returnPressed.connect(window.run.click)
    window.password.returnPressed.connect(window.run.click)

    app_icon = QIcon(resource_path("icon.svg"))
    window.setWindowIcon(app_icon)


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    # app.setLayoutDirection(QtCore.Qt.RightToLeft)

    ui_file = QFile("digikala_history.ui")
    ui_file.open(QFile.ReadOnly)
    window = loadUi(ui_file)
    ui_file.close()
    setupWindow(window)
    window.show()

    sys.exit(app.exec_())
