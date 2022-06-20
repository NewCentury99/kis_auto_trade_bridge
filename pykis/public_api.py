# Copyright 2022 Jueon Park
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime, timedelta
from collections import namedtuple
from typing import NamedTuple, Optional
import json
import requests

# request 관련 유틸리티------------------


def to_namedtuple(name: str, json_data: dict) -> NamedTuple:
    _x = namedtuple(name, json_data.keys())
    return _x(**json_data)


def get_base_headers(p: Optional[dict] = None) -> dict:
    base_headers = {
        "Content-Type": "application/json",
        "Accept": "text/plain",
        "charset": "UTF-8",
    }

    if p is not None:
        for k, v in p.items():
            base_headers[k] = v

    return base_headers
# request 관련 유틸리티------------------


class DomainInfo:
    def __init__(self, kind: Optional[str] = None, url: Optional[str] = None) -> None:
        if kind == "real":
            self.base_url = "https://openapi.koreainvestment.com:9443"
        elif kind == "virtual":
            self.base_url = "https://openapivts.koreainvestment.com:29443"

        elif kind is None and url is not None:
            self.base_url = url
        else:
            raise Exception("invalid domain info")

    def get_url(self, url_path: str):
        return f"{self.base_url}{url_path}"


class AccessToken:
    def __init__(self, resp: dict) -> None:
        r = to_namedtuple("res", resp)
        time_margin = timedelta(minutes=1)

        self.value = f"Bearer {str(r.access_token)}"
        self.valid_until = datetime.now() + timedelta(seconds=int(r.expires_in)) - time_margin

    def is_valid(self) -> bool:
        return datetime.now() < self.valid_until


class Api:
    def __init__(self, key_info: dict, domain_info=DomainInfo(kind="real"), account_info: Optional[dict] = None) -> None:
        """
        key_info: API 사용을 위한 인증키 정보. appkey, appsecret
        domain_info: domain 정보 (실전/모의/etc)
        account_info: 사용할 계좌 정보. account_code, account_product_code 
        """
        self.key: dict = key_info
        self.domain: DomainInfo = domain_info
        self.token: Optional[AccessToken] = None
        self.account: Optional[dict] = account_info

    def set_account(self, account_info):
        """
        사용할 계좌 정보 설정.
        account_info: 
        """
        return

    # 인증-----------------

    def auth(self):
        """
        토큰 발급.
        """
        url_path = "/oauth2/tokenP"
        url = self.domain.get_url(url_path)

        p = {
            "grant_type": "client_credentials",
            "appkey": self.key["appkey"],
            "appsecret": self.key["appsecret"]
        }

        headers = get_base_headers()

        resp = requests.post(
            url,
            data=json.dumps(p),
            headers=headers
        )

        if resp.status_code != 200:
            raise Exception("Authentication failed")

        self.token = AccessToken(resp.json())

    def need_auth(self) -> bool:
        return self.token is None or not self.token.is_valid()

    def set_hash_key(self, header: dict, param: dict):
        """
        header에 hash key 설정.
        """
        hash_key = self.get_hash_key(param)
        header["hashkey"] = hash_key

    def get_hash_key(self, param: dict):
        """
        hash key 값 가져오기.
        """
        url_path = "/uapi/hashkey"
        url = self.domain.get_url(url_path)

        headers = get_base_headers({
            "appkey": self.key["appkey"],
            "appsecret": self.key["appsecret"]
        })

        resp = requests.post(url, data=json.dumps(param), headers=headers)
        if resp.status_code != 200:
            raise Exception(
                f"get_has_key failed. response code: {resp.status_code}")

        return to_namedtuple("res", resp.json()).HASH
    # 인증-----------------

    # 시세 조회------------
    def get_kr_stock_price(self, ticker: str):
        """
        국내 주식 현재가 조회
        ticker: 종목코드
        return: 해당 종목 현재가 (단위: 원)
        """
        info = self._get_kr_stock_current_price_info(ticker)
        price = info["stck_prpr"]

        return int(price)

    def _get_kr_stock_current_price_info(self, ticker: str):
        """
        국내 주식 현재가 조회
        ticker: 종목코드
        return: 해당 종목 현재 시세 정보
        """
        url_path = "/uapi/domestic-stock/v1/quotations/inquire-price"
        url = self.domain.get_url(url_path)

        tr_id = "FHKST01010100"

        params = {
            'FID_COND_MRKT_DIV_CODE': 'J',
            'FID_INPUT_ISCD': ticker
        }

        if self.need_auth():
            self.auth()

        headers = get_base_headers({
            "appkey": self.key["appkey"],
            "appsecret": self.key["appsecret"],
            "authorization": self.token.value,
            "tr_id": tr_id
        })

        resp = requests.get(url, headers=headers, params=params)

        if resp.status_code != 200:
            raise Exception(
                f"get_kr_stock_price failed. response code: {resp.status_code}")

        body = to_namedtuple("body", resp.json())

        if body.rt_cd != "0":
            raise Exception(
                f"get_kr_stock_price retunrn code error: {body.rt_cd}")

        return body.output
    # 시세 조회------------

    # 잔고 조회------------
    def get_kr_buyable_cash(self):
        """
        구매 가능 현금(원화) 조회
        return: 해당 계좌의 구매 가능한 현금(원화)
        """
        return

    def get_kr_stock_balance(self):
        """
        국내 주식 잔고 조회
        return: 국내 주식 잔고 정보를 DataFrame으로 반환
        """
        return
    # 잔고 조회------------

    # 매매-----------------
    def buy_kr_stock(self, ticker: str, order_amount: int, price: int):
        """
        국내 주식 매수(현금)
        ticker: 종목코드
        order_amount: 주문 수량
        price: 주문 가격
        """
        return

    def sell_kr_stock(self, ticker: str, order_amount: int, price: int):
        """
        국내 주식 매매(현금)
        ticker: 종목코드
        order_amount: 주문 수량
        price: 주문 가격
        """
        return
    # 매매-----------------
