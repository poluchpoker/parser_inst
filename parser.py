import httpx
import json
import csv
import re
from typing import Dict, Any, List
from datetime import datetime
from urllib.parse import urlparse

class InstagramParser:
    def __init__(self, sessionid: str, ds_user_id: str, csrftoken: str):
        self.client = httpx.Client(
            headers={
                "x-ig-app-id": "936619743392459",
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        
        self.cookies={
            "sessionid": sessionid,
            "ds_user_id": ds_user_id,
            "csrftoken": csrftoken
        }

    def extract_username_from_url(self, url: str) -> str:
        cleaned_url = url.split('?')[0].rstrip('/')
        
        username = cleaned_url.split('/')[-1]
        
        if not re.match(r'^[a-zA-Z0-9._]{1,30}$', username):
            raise ValueError("Некорректный URL профиля Instagram")
            
        return username

    def get_user_info(self, profile_url: str) -> Dict[str, Any]:
        try:
            username = self.extract_username_from_url(profile_url)
            
            response = self.client.get(
                f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}",
                cookies=self.cookies
            )
            response.raise_for_status()
            
            data = response.json()
            if "data" not in data or "user" not in data["data"]:
                raise ValueError("Неверный формат ответа от Instagram")
            
            user_data = data["data"]["user"]
            user_id = user_data["id"]
            
            posts_response = self.client.get(
                f"https://i.instagram.com/api/v1/feed/user/{user_id}/",
                cookies=self.cookies
            )
            posts_response.raise_for_status()
            posts_data = posts_response.json()

            posts_for_csv = []
            for item in posts_data.get("items", []):
                post = {
                    "text": item.get("caption", {}).get("text", "") if item.get("caption") else "",
                    "likes": item.get("like_count", "N/A"),
                    "comments": item.get("comment_count", "N/A"),
                    "date": datetime.fromtimestamp(item["taken_at"]).strftime('%Y-%m-%d') if item.get("taken_at") else "N/A"
                }
                posts_for_csv.append(post)

            self._create_csv_file(posts_for_csv)

            return {
                "followers": user_data["edge_followed_by"]["count"],
                "posts": user_data["edge_owner_to_timeline_media"]["count"],
            }

        except httpx.HTTPStatusError as e:
            return self._handle_http_error(e)
        except Exception as e:
            return {"error": str(e)}
        
    def _create_csv_file(self, posts_data: List[Dict[str, Any]]):
        try:
            with open("info_instagram.csv", mode="w", encoding='utf-8', newline='') as w_file:
                file_writer = csv.writer(w_file, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)
                file_writer.writerow(["Описание поста", "Лайки", "Комментарии", "Дата публикации"])
                
                for post in posts_data:
                    file_writer.writerow([
                        post["text"],
                        post["likes"],
                        post["comments"],
                        post["date"],
                    ])
        except Exception as e:
            print(f"Ошибка при сохранении в CSV: {str(e)}")
    
    def _handle_http_error(self, error: httpx.HTTPStatusError) -> Dict[str, str]:
        if error.response.status_code == 404:
            return {"error": "Пользователь не найден"}
        elif error.response.status_code == 403:
            return {"error": "Требуется авторизация. Обновите cookies"}
        else:
            return {"error": f"HTTP ошибка: {error.response.status_code}"}
    
    def __del__(self):
        self.client.close()

if __name__ == "__main__":
    parser = InstagramParser(
        sessionid=input("Введите sessionid из Instagrama: "),
        ds_user_id=input("Введите ds_user_id из Instagrama: "),
        csrftoken=input("Введите csrftoken из Instagrama: ")
    )
    profile_url = input("Введите URL на профиль: ")
    result = parser.get_user_info(profile_url)
    print(json.dumps(result, indent=2, ensure_ascii=False))