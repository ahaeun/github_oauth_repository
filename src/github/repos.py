import requests

API_BASE = "https://api.github.com"

# GitHub Search API(/search/repositories)는 sort로 stars/forks/help-wanted-issues/updated만
# 지원하고 full_name·created·pushed는 지원하지 않으므로, 검색 결과는 클라이언트에서 정렬한다.
_SORT_KEYS = {
    "full_name": lambda repo: (repo.get("full_name") or "").lower(),
    "created": lambda repo: repo.get("created_at") or "",
    "updated": lambda repo: repo.get("updated_at") or "",
    "pushed": lambda repo: repo.get("pushed_at") or "",
}


def _sort_repos(repos, sort):
    key = _SORT_KEYS.get(sort, _SORT_KEYS["updated"])
    return sorted(repos, key=key, reverse=(sort != "full_name"))


def _auth_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }


def list_repos(token, sort="updated", per_page=100):
    """인증된 사용자의 리파지토리 목록을 페이지네이션을 따라가며 모두 조회한다."""
    repos = []
    url = f"{API_BASE}/user/repos"
    params = {"per_page": per_page, "affiliation": "owner,collaborator,organization_member"}
    if sort:
        params["sort"] = sort
    headers = _auth_headers(token)

    while url:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        repos.extend(response.json())

        url = response.links.get("next", {}).get("url")
        params = None  # next url already contains query params

    return repos


def search_repos(token, q, sort="pushed", per_page=100):
    """GitHub Search API(/search/repositories)로 인증된 사용자 소유 리파지토리를 검색한다."""
    headers = _auth_headers(token)

    user_response = requests.get(f"{API_BASE}/user", headers=headers, timeout=10)
    user_response.raise_for_status()
    username = user_response.json()["login"]

    repos = []
    url = f"{API_BASE}/search/repositories"
    params = {"q": f"{q} in:name,description user:{username}", "per_page": per_page}

    while url:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        repos.extend(response.json().get("items", []))

        url = response.links.get("next", {}).get("url")
        params = None  # next url already contains query params

    return _sort_repos(repos, sort)


def view_repo(token, owner, repo):
    """특정 리파지토리의 상세 정보를 조회한다."""
    url = f"{API_BASE}/repos/{owner}/{repo}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()


def list_commits(token, owner, repo, per_page=100):
    """특정 리파지토리의 커밋 목록을 페이지네이션을 따라가며 모두 조회한다."""
    commits = []
    url = f"{API_BASE}/repos/{owner}/{repo}/commits"
    params = {"per_page": per_page}
    headers = {
        "Authorization": f"Bearer {token}", 
        "Accept": "application/vnd.github+json",
    }

    while url:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        commits.extend(response.json())

        url = response.links.get("next", {}).get("url")
        params = None

    return commits