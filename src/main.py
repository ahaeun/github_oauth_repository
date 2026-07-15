from dotenv import load_dotenv

from src.auth import login
from src.github import list_repos, view_repo


def main():
    load_dotenv()
    token = login()
    repos = list_repos(token)

    print(f"\n조회된 리파지토리: {len(repos)}개")
    for repo in repos:
        print(f"- {repo['full_name']}")


if __name__ == "__main__":
    main()
