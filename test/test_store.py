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
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NON INFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import unittest
import xarray as xr

from test_cmems import CmemsTest
from xcube_cmems.store import CmemsDataOpener
from xcube_cmems.store import CmemsDataStore


class CmemsDataOpenerTest(unittest.TestCase):

    def setUp(self) -> None:
        dataset_id = "dataset-bal-analysis-forecast-wav-hourly"
        cmems = CmemsTest._create_cmems_instance(dataset_id)
        self.opener = CmemsDataOpener(cmems, dataset_id)

    def test_open_data(self):
        dataset_id = "dataset-bal-analysis-forecast-wav-hourly"
        ds = self.opener.open_data(dataset_id,
                                   variable_names=['VHM0'],
                                   bbox=[9.0, 53.0, 30.0, 66.0],
                                   time_range=['2020-06-16', '2020-07-16']
                                   )
        self.assertIsInstance(ds, xr.Dataset)


class CmemsDataStoreTest(unittest.TestCase):

    def setUp(self) -> None:
        dataset_id = "dataset-bal-analysis-forecast-wav-hourly"
        cmems = CmemsTest._create_cmems_instance(dataset_id)
        self.datastore = CmemsDataStore(cmems, dataset_id)

    def test_get_all_data_ids(self):
        dataset_ids = self.datastore.get_data_ids()
        self.assertEqual(125840, len(dataset_ids))
        self.assertTrue('dataset-bal-analysis-forecast-wav-hourly' in
                        dataset_ids)
