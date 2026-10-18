import os
import sys
import re
from datetime import datetime, date
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "../custom_components/waste_collection_schedule",
        )
    ),
)

import waste_collection_schedule.source.portenf_sa_gov_au as portenf_sa_gov_au
from waste_collection_schedule.source.portenf_sa_gov_au import (
    ICON_MAP,
    TITLE,
    DESCRIPTION,
    URL,
    Source,
)


class MockResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP Error {self.status_code}")


HTML_PAGE_1 = """
<html>
<body>
  <form>
    <input type="hidden" name="__VIEWSTATE" value="viewstate_initial" />
    <input type="hidden" name="__EVENTVALIDATION" value="eventval_initial" />
  </form>
</body>
</html>
"""

HTML_PAGE_SELECT_SINGLE = """
<html>
<body>
  <form>
    <input type="hidden" name="__VIEWSTATE" value="viewstate_select" />
    <table>
      <tr>
        <td><a class="anchor-button small" href="javascript:__doPostBack('ctl00$MainContent$gvPropertyResults$ctl02$btnSelect','')">Select</a></td>
        <td><span>91 Addison Road Rosewater 2</span></td>
      </tr>
    </table>
  </form>
</body>
</html>
"""

HTML_PAGE_SELECT_MULTIPLE_MATCH = """
<html>
<body>
  <form>
    <input type="hidden" name="__VIEWSTATE" value="viewstate_select" />
    <table>
      <tr>
        <td><a class="anchor-button small" href="javascript:__doPostBack('ctl00$MainContent$gvPropertyResults$ctl02$btnSelect','')">Select</a></td>
        <td><span>93 Addison Road Rosewater</span></td>
      </tr>
      <tr>
        <td><a class="anchor-button small" href="javascript:__doPostBack('ctl00$MainContent$gvPropertyResults$ctl03$btnSelect','')">Select</a></td>
        <td><span>91 Addison Road Rosewater 2</span></td>
      </tr>
    </table>
  </form>
</body>
</html>
"""

HTML_PAGE_SELECT_MULTIPLE_MULTIPLE_MATCHES = """
<html>
<body>
  <form>
    <input type="hidden" name="__VIEWSTATE" value="viewstate_select" />
    <table>
      <tr>
        <td><a class="anchor-button small" href="javascript:__doPostBack('ctl00$MainContent$gvPropertyResults$ctl02$btnSelect','')">Select</a></td>
        <td><span>91 Addison Road Rosewater 2</span></td>
      </tr>
      <tr>
        <td><a class="anchor-button small" href="javascript:__doPostBack('ctl00$MainContent$gvPropertyResults$ctl03$btnSelect','')">Select</a></td>
        <td><span>91 Addison Road Rosewater 2 duplicate</span></td>
      </tr>
    </table>
  </form>
</body>
</html>
"""

HTML_PAGE_SELECT_MULTIPLE_NO_MATCH = """
<html>
<body>
  <form>
    <input type="hidden" name="__VIEWSTATE" value="viewstate_select" />
    <table>
      <tr>
        <td><a class="anchor-button small" href="javascript:__doPostBack('ctl00$MainContent$gvPropertyResults$ctl02$btnSelect','')">Select</a></td>
        <td><span>100 Main Street City</span></td>
      </tr>
      <tr>
        <td><a class="anchor-button small" href="javascript:__doPostBack('ctl00$MainContent$gvPropertyResults$ctl03$btnSelect','')">Select</a></td>
        <td><span>102 Main Street City</span></td>
      </tr>
    </table>
  </form>
</body>
</html>
"""

HTML_PAGE_NO_ADDRESS = """
<html>
<body>
  <form>
    <div>No records found</div>
  </form>
</body>
</html>
"""

HTML_PAGE_CALENDAR = """
<html>
<body>
  <form>
    <input type="hidden" name="__VIEWSTATE" value="viewstate_cal" />
  </form>
  <table id="cal">
    <tr>
      <th class="header-month"><span>March - April 2025</span></th>
    </tr>
    <tr>
      <td class="today main-month">15</td>
    </tr>
  </table>
  <table class="collection-day-calendar">
    <tr>
      <td class="main-month">
        <div class="daynumber">15</div>
        <div class="pickup">
          <div class="bin-container">
            <div class="general-waste bin"></div>
          </div>
          <div class="bin-container">
            <div class="organics bin"></div>
          </div>
        </div>
      </td>
      <td class="other-month">
        <div class="daynumber">02</div>
        <div class="next-pickup">
          <div class="bin-container">
            <div class="recycling bin"></div>
          </div>
        </div>
      </td>
    </tr>
  </table>
</body>
</html>
"""

HTML_PAGE_CALENDAR_SINGLE_MONTH = """
<html>
<body>
  <form>
    <input type="hidden" name="__VIEWSTATE" value="viewstate_cal" />
  </form>
  <table id="cal">
    <tr>
      <th class="header-month"><span>March 2025</span></th>
    </tr>
    <tr>
      <td class="today main-month">15</td>
    </tr>
  </table>
  <table class="collection-day-calendar">
    <tr>
      <td class="main-month">
        <div class="daynumber">15</div>
        <div class="pickup">
          <div class="bin-container">
            <div class="general-waste bin"></div>
          </div>
        </div>
      </td>
    </tr>
  </table>
</body>
</html>
"""

HTML_PAGE_CALENDAR_YEAR_SPANNING = """
<html>
<body>
  <form>
    <input type="hidden" name="__VIEWSTATE" value="viewstate_cal" />
  </form>
  <table id="cal">
    <tr>
      <th class="header-month"><span>December 2024 - January 2025</span></th>
    </tr>
    <tr>
      <td class="today other-month">05</td>
    </tr>
  </table>
  <table class="collection-day-calendar">
    <tr>
      <td class="main-month">
        <div class="daynumber">20</div>
        <div class="pickup">
          <div class="bin-container">
            <div class="organics bin"></div>
          </div>
        </div>
      </td>
      <td class="other-month">
        <div class="daynumber">05</div>
        <div class="pickup">
          <div class="bin-container">
            <div class="recycling bin"></div>
          </div>
        </div>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def test_source_init():
    source = Source(
        suburb="Rosewater",
        street="Addison Road",
        house_number=91,
        unit_number=2,
    )
    assert source._suburb == "Rosewater"
    assert source._street == "Addison Road"
    assert source._house_number == "91"
    assert source._unit_number == "2"


def test_fetch_single_address_success(monkeypatch):
    source = Source(
        suburb="Rosewater",
        street="Addison Road",
        house_number="91",
        unit_number="2",
    )

    responses = [
        MockResponse(HTML_PAGE_1),
        MockResponse(HTML_PAGE_SELECT_SINGLE),
        MockResponse(HTML_PAGE_CALENDAR),
    ]

    mock_session = MagicMock()
    mock_session.get.return_value = responses[0]
    mock_session.post.side_effect = responses[1:]

    monkeypatch.setattr(
        portenf_sa_gov_au.requests,
        "Session",
        lambda: mock_session,
    )

    class MockDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2025, 3, 15)

    monkeypatch.setattr(
        portenf_sa_gov_au,
        "datetime",
        MockDatetime,
    )

    entries = source.fetch()

    assert len(entries) == 3
    assert entries[0].date == date(2025, 3, 15)
    assert entries[0].type == "general-waste bin"
    assert entries[0].icon == "mdi:trash-can"

    assert entries[1].date == date(2025, 3, 15)
    assert entries[1].type == "organics bin"
    assert entries[1].icon == "mdi:leaf"

    assert entries[2].date == date(2025, 4, 2)
    assert entries[2].type == "recycling bin"
    assert entries[2].icon == "mdi:recycle"


def test_fetch_multiple_addresses_match(monkeypatch, caplog):
    source = Source(
        suburb="Rosewater",
        street="Addison Road",
        house_number="91",
        unit_number="2",
    )

    responses = [
        MockResponse(HTML_PAGE_1),
        MockResponse(HTML_PAGE_SELECT_MULTIPLE_MATCH),
        MockResponse(HTML_PAGE_CALENDAR),
    ]

    mock_session = MagicMock()
    mock_session.get.return_value = responses[0]
    mock_session.post.side_effect = responses[1:]

    monkeypatch.setattr(
        portenf_sa_gov_au.requests,
        "Session",
        lambda: mock_session,
    )

    class MockDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2025, 3, 15)

    monkeypatch.setattr(
        portenf_sa_gov_au,
        "datetime",
        MockDatetime,
    )

    entries = source.fetch()
    assert len(entries) == 3


def test_fetch_multiple_addresses_multiple_matches_warning(monkeypatch, caplog):
    source = Source(
        suburb="Rosewater",
        street="Addison Road",
        house_number="91",
        unit_number="2",
    )

    responses = [
        MockResponse(HTML_PAGE_1),
        MockResponse(HTML_PAGE_SELECT_MULTIPLE_MULTIPLE_MATCHES),
        MockResponse(HTML_PAGE_CALENDAR),
    ]

    mock_session = MagicMock()
    mock_session.get.return_value = responses[0]
    mock_session.post.side_effect = responses[1:]

    monkeypatch.setattr(
        portenf_sa_gov_au.requests,
        "Session",
        lambda: mock_session,
    )

    class MockDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2025, 3, 15)

    monkeypatch.setattr(
        portenf_sa_gov_au,
        "datetime",
        MockDatetime,
    )

    with caplog.at_level("WARNING"):
        entries = source.fetch()
        assert "Multiple addresses found, using first one" in caplog.text


def test_fetch_multiple_addresses_no_match_warning(monkeypatch, caplog):
    source = Source(
        suburb="Rosewater",
        street="Addison Road",
        house_number="91",
        unit_number="2",
    )

    responses = [
        MockResponse(HTML_PAGE_1),
        MockResponse(HTML_PAGE_SELECT_MULTIPLE_NO_MATCH),
        MockResponse(HTML_PAGE_CALENDAR),
    ]

    mock_session = MagicMock()
    mock_session.get.return_value = responses[0]
    mock_session.post.side_effect = responses[1:]

    monkeypatch.setattr(
        portenf_sa_gov_au.requests,
        "Session",
        lambda: mock_session,
    )

    class MockDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2025, 3, 15)

    monkeypatch.setattr(
        portenf_sa_gov_au,
        "datetime",
        MockDatetime,
    )

    with caplog.at_level("WARNING"):
        entries = source.fetch()
        assert "no perfect address match found" in caplog.text


def test_fetch_no_address_found(monkeypatch):
    source = Source(
        suburb="Nonexistent",
        street="Fake Road",
        house_number="0",
    )

    responses = [
        MockResponse(HTML_PAGE_1),
        MockResponse(HTML_PAGE_NO_ADDRESS),
    ]

    mock_session = MagicMock()
    mock_session.get.return_value = responses[0]
    mock_session.post.side_effect = responses[1:]

    monkeypatch.setattr(
        portenf_sa_gov_au.requests,
        "Session",
        lambda: mock_session,
    )

    with pytest.raises(ValueError, match="No address found"):
        source.fetch()


def test_fetch_single_month_header(monkeypatch):
    source = Source(
        suburb="Broadview",
        street="Regency Road",
        house_number=565,
    )

    responses = [
        MockResponse(HTML_PAGE_1),
        MockResponse(HTML_PAGE_SELECT_SINGLE),
        MockResponse(HTML_PAGE_CALENDAR_SINGLE_MONTH),
    ]

    mock_session = MagicMock()
    mock_session.get.return_value = responses[0]
    mock_session.post.side_effect = responses[1:]

    monkeypatch.setattr(
        portenf_sa_gov_au.requests,
        "Session",
        lambda: mock_session,
    )

    class MockDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2025, 3, 15)

    monkeypatch.setattr(
        portenf_sa_gov_au,
        "datetime",
        MockDatetime,
    )

    entries = source.fetch()
    assert len(entries) == 1
    assert entries[0].date == date(2025, 3, 15)


def test_fetch_year_spanning_header(monkeypatch):
    source = Source(
        suburb="Rosewater",
        street="Margaret Terrace",
        house_number="24",
    )

    responses = [
        MockResponse(HTML_PAGE_1),
        MockResponse(HTML_PAGE_SELECT_SINGLE),
        MockResponse(HTML_PAGE_CALENDAR_YEAR_SPANNING),
    ]

    mock_session = MagicMock()
    mock_session.get.return_value = responses[0]
    mock_session.post.side_effect = responses[1:]

    monkeypatch.setattr(
        portenf_sa_gov_au.requests,
        "Session",
        lambda: mock_session,
    )

    class MockDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2025, 1, 5)

    monkeypatch.setattr(
        portenf_sa_gov_au,
        "datetime",
        MockDatetime,
    )

    entries = source.fetch()
    assert len(entries) == 2
    # main_month is December (2024), other_month is January (2025)
    # today is January 5 (other_month)
    assert entries[0].date == date(2024, 12, 20)
    assert entries[1].date == date(2025, 1, 5)
