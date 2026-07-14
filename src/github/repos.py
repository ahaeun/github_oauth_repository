import requests

API_BASE = "https://api.github.com"


def list_repos(token, per_page=100):
    """인증된 사용자의 리파지토리 목록을 페이지네이션을 따라가며 모두 조회한다."""
    repos = []
    url = f"{API_BASE}/user/repos"
    params = {"per_page": per_page, "affiliation": "owner,collaborator,organization_member"}
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    while url:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        repos.extend(response.json())

        url = response.links.get("next", {}).get("url")
        params = None  # next url already contains query params

    return repos
