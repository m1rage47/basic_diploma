from typing import Dict

import requests

from config import API_KEY, BASE_URL

headers = {"accept": "application/json", "X-API-KEY": API_KEY}


def requester(by_title: bool, query: Dict):
    query["page"] = 1
    query["limit"] = 100
    if by_title:
        url = f"{BASE_URL}/movie/search"
    else:
        base = {
            "selectFields": [
                "budget",
                "name",
                "ageRating",
                "poster",
                "year",
                "enName",
                "rating",
                "description",
                "genres",
            ],
            "notNullFields": [
                "year",
                "name",
                "poster.url",
                "ageRating",
                "description",
                "enName",
                "rating.kp",
                "rating.imdb",
                "budget.value",
            ],
        }
        url = f"{BASE_URL}/movie"
        query.update(base)

    response = requests.get(url, headers=headers, params=query)

    return response.json()
