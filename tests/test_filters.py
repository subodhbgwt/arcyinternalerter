"""Tests for the filter logic. No network, Telegram or .env needed.

Run with:  python -m pytest -q tests

A posting is kept only if it's (a) in one of my target regions, (b) recent
enough, (c) in one of the four tracks (quant, tech, finance, consulting),
(d) not HR / admin / sales / support, and (e) a student role.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from filters import (  # noqa: E402
    classify_track,
    is_amsterdam_location,
    is_internship,
    is_london_location,
    is_nordic_location,
    is_stockholm_location,
    is_target_location,
    is_zurich_location,
    label_for,
    passes,
    posted_within,
)

NOW = datetime.now(timezone.utc)


def job(title, location, dept="", **extra):
    return {"title": title, "location": location, "department": dept,
            "posted_at": NOW, **extra}


# --- the full gate --------------------------------------------------------
@pytest.mark.parametrize("title, location, dept, expected", [
    # kept: student role, right track, right place
    ("Software Engineer Intern", "Stockholm, Sweden", "Engineering", True),
    ("Quantitative Researcher Intern", "London, United Kingdom", "", True),
    ("Summer Analyst 2027 - Investment Banking", "Frankfurt, Germany", "", True),
    ("Trading Intern", "Amsterdam, Netherlands", "", True),
    ("Off-Cycle Internship - Global Markets", "London", "", True),
    ("Machine Learning Intern", "Zurich, Switzerland", "", True),
    ("Spring Insight Programme - Markets", "London, UK", "", True),
    # dropped: wrong place
    ("Software Engineer Intern", "San Francisco, CA", "Engineering", False),
    ("Quant Trader Intern", "London, Ontario, Canada", "", False),
    ("Software Engineer Intern", "Bengaluru, India", "", False),
    # dropped: not a student role
    ("Senior Software Engineer", "Stockholm, Sweden", "Engineering", False),
    ("Quantitative Researcher", "London, United Kingdom", "", False),
    # dropped: off-target function, even as an intern
    ("HR Intern", "Stockholm, Sweden", "People", False),
    ("Sales Intern", "Amsterdam, Netherlands", "Sales", False),
])
def test_passes(title, location, dept, expected):
    assert passes(job(title, location, dept)) is expected


def test_old_postings_are_dropped():
    old = job("Software Engineer Intern", "Stockholm, Sweden")
    old["posted_at"] = NOW - timedelta(days=10)
    assert passes(old, max_age_days=3) is False


def test_trusted_source_skips_role_checks():
    # Jane Street's events board: every posting is a student event,
    # so only location and age are checked.
    event = job("FTTP Program 2027", "London, United Kingdom", _trust=True)
    assert passes(event) is True
    event["location"] = "New York, NY"
    assert passes(event) is False


def test_extra_location_tokens():
    j = job("Software Engineer Intern", "Tbilisi, Georgia")
    assert passes(j) is False
    assert passes(j, extra_location_tokens=["Tbilisi"]) is True


# --- location -------------------------------------------------------------
@pytest.mark.parametrize("location, expected", [
    ("Stockholm, Sweden", True),
    ("Oslo, Norway", True),
    ("Amsterdam", True),
    ("London, United Kingdom", True),
    ("Zürich, Switzerland", True),
    ("Dublin, Ireland", True),
    ("Paris, France", True),
    ("London, Ontario, Canada", False),
    ("Paris, TX", False),
    ("New York, NY", False),
    ("Singapore", False),
    ("", False),
])
def test_is_target_location(location, expected):
    assert is_target_location(location) is expected


@pytest.mark.parametrize("fn, location, expected", [
    (is_stockholm_location, "Kista, Stockholm", True),
    (is_stockholm_location, "Oslo, Norway", False),
    (is_nordic_location, "Copenhagen, Denmark", True),
    (is_nordic_location, "Helsinki", True),
    (is_amsterdam_location, "Rotterdam, Netherlands", True),
    (is_london_location, "London", True),
    (is_london_location, "Amsterdam", False),
    (is_zurich_location, "Geneva, Switzerland", True),
    (is_zurich_location, "", False),
])
def test_city_buckets(fn, location, expected):
    assert fn(location) is expected


# --- role level -----------------------------------------------------------
@pytest.mark.parametrize("title, expected", [
    ("Software Engineer Intern", True),
    ("Summer Internship 2027", True),
    ("IMC Launchpad", True),
    ("SIG Discovery Day", True),
    ("Visiting Associate", True),
    ("Senior Software Engineer", False),
    ("Internal Auditor", False),
])
def test_is_internship(title, expected):
    assert is_internship(title) is expected


@pytest.mark.parametrize("title, track", [
    ("Quant Trader Intern", "Quant"),
    ("Investment Banking Summer Analyst", "Finance/IB"),
    ("Strategy Consultant Intern", "Consulting"),
    ("Backend Software Engineer Intern", "Tech/SWE"),
])
def test_classify_track(title, track):
    assert classify_track(title) == track


@pytest.mark.parametrize("title, label", [
    ("Off-Cycle Internship - Markets", "Off-cycle"),
    ("Spring Week 2027", "Spring/Insight"),
    ("Summer Analyst - Global Markets", "Summer analyst"),
    ("Software Engineer Intern", "Internship"),
    ("Graduate Programme 2027", "New grad"),
    ("Campus Quant Trader (Full-Time)", "Grad/FT"),
    ("Software Engineer", "Regular"),
])
def test_label_for(title, label):
    assert label_for({"title": title}) == label


def test_posted_within_keeps_postings_without_a_date():
    assert posted_within({"posted_at": None}, 2) is True
