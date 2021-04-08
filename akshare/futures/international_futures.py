# -*- coding:utf-8 -*-
# /usr/bin/env python
"""
Date: 2021/4/8 17:22
Desc: 提供英为财情-国际大宗商品期货
https://cn.investing.com/commodities/brent-oil-historical-data
"""
import re

import pandas as pd
import requests
from bs4 import BeautifulSoup

from akshare.index.cons import short_headers, long_headers


def get_sector_symbol_name_url() -> dict:
    """
    期货所对应板块的 URL
    :return: dict
    {'能源': '/commodities/energy',
    '金属': '/commodities/metals',
    '农业': '/commodities/softs',
    '商品指数': '/indices/commodities-indices'}
    """
    url = "https://cn.investing.com/commodities/"
    res = requests.post(url, headers=short_headers)
    soup = BeautifulSoup(res.text, "lxml")
    name_url_option_list = soup.find_all(attrs={"class": "linkTitle"})  # 去掉-所有国家及地区
    url_list = [item.find("a")["href"] for item in name_url_option_list]
    name_list = [item.get_text() for item in name_url_option_list]
    name_code_map_dict = {}
    name_code_map_dict.update(zip(name_list, url_list))
    return name_code_map_dict


def futures_global_commodity_name_url_map(sector: str = "能源") -> pd.DataFrame:
    """
    参考网页: https://cn.investing.com/commodities/
    获取选择板块对应的: 具体期货品种的 url 地址
    :param sector: 板块, 对应 get_global_country_name_url 品种名称
    :type sector: str
    :return: dict of name-url
    :rtype: dict
    {'伦敦布伦特原油': '/commodities/brent-oil',
    'WTI原油': '/commodities/crude-oil',
    '伦敦汽油': '/commodities/london-gas-oil',
    '天然气': '/commodities/natural-gas?cid=49787',
    '燃料油': '/commodities/heating-oil',
    '碳排放': '/commodities/carbon-emissions',
    'RBOB汽油': '/commodities/gasoline-rbob',
    '布伦特原油': '/commodities/brent-oil?cid=49769',
    '原油': '/commodities/crude-oil?cid=49774'}
    """
    name_url_dict = get_sector_symbol_name_url()
    url = f"https://cn.investing.com{name_url_dict[sector]}"
    res = requests.post(url, headers=short_headers)
    soup = BeautifulSoup(res.text, "lxml")
    url_list = [
        item.find("a")["href"].split("?")[0]
        for item in soup.find_all(attrs={"class": "plusIconTd"})
    ]
    name_list = [
        item.find("a").get_text()
        for item in soup.find_all(attrs={"class": "plusIconTd"})
    ]
    name_code_map_dict = {}
    name_code_map_dict.update(zip(name_list, url_list))
    return name_code_map_dict


def get_sector_futures(
    sector="能源", symbol="伦敦布伦特原油", start_date="2000/01/01", end_date="2019/10/17"
):
    """
    具体国家的具体指数的从 start_date 到 end_date 期间的数据
    :param sector: str 对应函数中的国家名称
    :param symbol: str 对应函数中的指数名称
    :param start_date: str '2000/01/01', 注意格式
    :param end_date: str '2019/10/17', 注意格式
    :return: pandas.DataFrame
    """
    name_code_dict = futures_global_commodity_name_url_map(sector)
    temp_url = f"https://cn.investing.com/{name_code_dict[symbol]}-historical-data"
    res = requests.post(temp_url, headers=short_headers)
    soup = BeautifulSoup(res.text, "lxml")
    title = soup.find("h2", attrs={"class": "float_lang_base_1"}).get_text()
    res = requests.post(temp_url, headers=short_headers)
    soup = BeautifulSoup(res.text, "lxml")
    data = soup.find_all(text=re.compile("window.histDataExcessInfo"))[0].strip()
    para_data = re.findall(r"\d+", data)
    payload = {
        "curr_id": para_data[0],
        "smlID": para_data[1],
        "header": title,
        "st_date": start_date,
        "end_date": end_date,
        "interval_sec": "Daily",
        "sort_col": "date",
        "sort_ord": "DESC",
        "action": "historical_data",
    }
    url = "https://cn.investing.com/instruments/HistoricalDataAjax"
    r = requests.post(url, data=payload, headers=long_headers)
    temp_df = pd.read_html(r.text)[0]
    df_data = temp_df
    df_data = df_data.set_index(["日期"])
    df_data.index = pd.to_datetime(df_data.index, format="%Y年%m月%d日")
    df_data.index.name = "日期"
    if any(df_data["交易量"].astype(str).str.contains("-")):
        df_data["交易量"][df_data["交易量"].str.contains("-")] = df_data["交易量"][
            df_data["交易量"].str.contains("-")
        ].replace("-", 0)
    if any(df_data["交易量"].astype(str).str.contains("B")):
        df_data["交易量"][df_data["交易量"].str.contains("B").fillna(False)] = (
            df_data["交易量"][df_data["交易量"].str.contains("B").fillna(False)]
            .str.replace("B", "")
            .astype(float)
            * 1000000000
        )
    if any(df_data["交易量"].astype(str).str.contains("M")):
        df_data["交易量"][df_data["交易量"].str.contains("M").fillna(False)] = (
            df_data["交易量"][df_data["交易量"].str.contains("M").fillna(False)]
            .str.replace("M", "")
            .astype(float)
            * 1000000
        )
    if any(df_data["交易量"].astype(str).str.contains("K")):
        df_data["交易量"][df_data["交易量"].str.contains("K").fillna(False)] = (
            df_data["交易量"][df_data["交易量"].str.contains("K").fillna(False)]
            .str.replace("K", "")
            .astype(float)
            * 1000
        )
    df_data["交易量"] = df_data["交易量"].astype(float)
    df_data["涨跌幅"] = pd.DataFrame(
        round(df_data["涨跌幅"].str.replace("%", "").astype(float) / 100, 6)
    )
    df_data.name = title
    df_data.columns.name = None
    return df_data


if __name__ == "__main__":
    temp_dict = futures_global_commodity_name_url_map(sector="能源")
    print(temp_dict)
    index_df = get_sector_futures(
        sector="能源", symbol="伦敦布伦特原油", start_date="2012/01/01", end_date="2020/04/04"
    )
    print(index_df.name)
    print(index_df)
