# The MIT License (MIT)
# Copyright (c) 2022 by the xcube development team and contributors
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NON INFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import aiohttp
import asyncio
from functools import cache
from io import BytesIO
from typing import List, Dict, Any, Optional
import lxml.etree as etree
import os
import logging
import time

import nest_asyncio
from pydap.cas.get_cookies import setup_session

from .constants import CAS_URL
from .constants import ODAP_SERVER
from .constants import DATABASE
from .constants import CSW_URL

_LOG = logging.getLogger('xcube')

CSW_NAMESPACES = {
    'dc': 'http://purl.org/dc/elements/1.1/',
    'csw': 'http://www.opengis.net/cat/csw/2.0.2'
}

_RECORDS_PER_REQUEST = 25
_GET_RECORDS_REQUEST = {
    'service': 'CSW',
    'request': 'GetRecords',
    'version': '2.0.2',
    'resultType': 'results',
    'ElementSetName': 'full',
    'maxRecords': _RECORDS_PER_REQUEST
}
# Ideally, we would read this from cmems
_TOTAL_NUM_OF_RECORDS = 300


class Cmems:
    """
        Represents the CMEMS opendap API
        :param cmems_username: CMEMS UserID
        :param cmems_password: CMEMS User Password
        :param cas_url: CMEMS cas url
        :param csw_url: CMEMS csw url
        :param databases: databases available - nrt (near real time)
        or my(multi-year)
        :param server: odap server

    """

    def __init__(self,
                 cmems_username: Optional[str] = None,
                 cmems_password: Optional[str] = None,
                 cas_url: str = CAS_URL,
                 csw_url: str = CSW_URL,
                 databases: List = DATABASE,
                 server: str = ODAP_SERVER):
        self.cmems_username = cmems_username if cmems_username is not None \
            else os.getenv('CMEMS_USERNAME')
        self.cmems_password = cmems_password if cmems_password is not None \
            else os.getenv('CMEMS_PASSWORD')
        self.valid_opendap_url = None
        self._csw_url = csw_url
        self.databases = databases
        self.odap_server = server
        self.metadata = {}
        self.opendap_dataset_ids = {}

        if not self.cmems_username or not self.cmems_password:
            raise ValueError('CmemsDataStore needs cmems credentials in '
                             'environment variables CMEMS_USERNAME and '
                             'CMEMS_PASSWORD or to be provided as '
                             'store params cmems_username and '
                             'cmems_password')

        self.session = setup_session(cas_url, self.cmems_username,
                                     self.cmems_password)

        cast_gc = self.session.cookies.get_dict().get('CASTGC')
        if cast_gc:
            # required by Central Authentication Service (CAS).
            # The setup_session function from pydap.cas.get_cookies is used to
            # establish a session with the CAS
            self.session.cookies.set("CASTGC", cast_gc)

    def get_opendap_urls(self, data_id) -> List[str]:
        """
        Constructs opendap urls given the dataset id
        :return: List of opendap urls
        """
        urls = []
        for i in range(len(self.databases)):
            urls.append(os.path.join("https://" + self.databases[i] + "." +
                                     self.odap_server + data_id))

        return urls

    @staticmethod
    async def get_response(session: aiohttp.ClientSession,
                           url: str,
                           params: Dict) -> \
            Optional[aiohttp.ClientResponse]:
        num_retries = 10
        for i in range(num_retries):
            resp = await session.request(method='GET',
                                         url=url,
                                         ssl=True,
                                         params=params)
            if resp.status == 200:
                return resp
            elif resp.status == 429:
                time.sleep(10)
            else:
                break
        return None

    async def read_data_ids_from_csw_records(self, start_record: int,
                                             session: aiohttp.ClientSession):
        params = {**_GET_RECORDS_REQUEST, 'startPosition': start_record + 1}
        resp = await self.get_response(
            session, self._csw_url, params
        )
        if not resp:
            return
        records_xml = etree.parse(BytesIO(await resp.content.read()))
        opendap_elements = records_xml.getroot().findall(
            './csw:SearchResults/csw:Record/dc:URI[@protocol="WWW:OPENDAP"]',
            namespaces=CSW_NAMESPACES
        )
        for opendap_element in opendap_elements:
            name = opendap_element.get('name')
            title = opendap_element.getparent().find(
                'dc:title',
                namespaces=CSW_NAMESPACES
            ).text
            self.opendap_dataset_ids[name] = title

    async def read_data_ids(self) -> None:
        """
        get csw records concurrently
        """
        tasks = []

        async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(limit=50, force_close=True)
        ) as session:
            for record in range(0, _TOTAL_NUM_OF_RECORDS, _RECORDS_PER_REQUEST):
                tasks.append(self.read_data_ids_from_csw_records(
                    record, session
                ))
            await asyncio.gather(*tasks)

    @cache
    def get_all_dataset_ids(self) -> Dict[str, Any]:
        """
        get all the opendap dataset ids by iterating through all CSW records
        currently by using asyncio
        :return: Dictionary of opendap dataset ids
        """
        # Workaround for RuntimeError: event loop is already running for JNB
        nest_asyncio.apply()
        asyncio.run(self.read_data_ids())
        return self.opendap_dataset_ids

    def dataset_names(self) -> List[str]:
        if self.opendap_dataset_ids:
            return self.opendap_dataset_ids.keys()
        else:
            return self.get_all_dataset_ids().keys()
