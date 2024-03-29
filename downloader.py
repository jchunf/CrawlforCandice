import re
import time
import json
import pandas as pd
import requests


'''
网页登陆ins——检查——储存空间——复制Cookie
option+command+i
'''


input_string = """
csrftoken	EYF96zqg9fqJKEH92aCCAW90EaCr34mC
ds_user_id	61001153455
rur	"CCO\05461001153455\0541735673907:01f786b38b678bc13a90c4d91db4b71f5e63f67eaf013f2c06e0da3629d1925c9561455d"
sessionid	61001153455%3AfgJBaOtxNAWchF%3A17%3AAYeo6KO9qNzKRlfEhA9S2Hi7aTBG88MewyDxNwsEag
shbid	"6417\05461001153455\0541735653428:01f72cf447a8483284d4f589c8f8fbe1a0f59c7a2f27105799043b8ce1c7f6623f84ac6b"
shbts	"1704117428\05461001153455\0541735653428:01f7906f9e9c825ca307f11bf442944cbb6d33cc021fa5b1b5b0a1bf09edc036e22ac901"
dpr	2
datr	MCK0ZOYsZRHi4UeOVXartbkD
mid	ZLQiMgAEAAFWvKZS-ZYDv9Niozgw
ig_did	115942BA-D9BA-4F8F-9495-83B80480DE41
ig_nrcb	1
"""

# Split the input string into lines and then into key-value pairs
key_value_pairs = [line.split(None, 1) for line in input_string.strip().split("\n")]

# Create a dictionary from the key-value pairs
cookie = {key: value for key, value in key_value_pairs}

# Print the resulting dictionary
#print(cookie)


PARAMS = r'("app_id":\s*"[^"]+")|("claim":\s*"[^"]+")|("csrf_token":\s*"[^"]+")'

URLS = [
    'https://www.instagram.com/',
    'https://www.instagram.com/api/v1/users/web_profile_info/',
    'https://www.instagram.com/api/v1/feed/user',
    'https://www.instagram.com/api/v1/media/'
]


class Ins:
    def __init__(self, cookies: dict):
        self.cookies = cookies
        self.session = requests.Session()
        self.headers = {
            'authority': 'www.instagram.com',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'zh-CN,zh;q=0.9',
            'sec-ch-ua-full-version-list': '"Google Chrome";v="113.0.5672.63", "Chromium";v="113.0.5672.63", "Not-A.Brand";v="24.0.0.0"',
            'sec-fetch-site': 'same-origin',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Instagram 76.0.0.15.395 Android (24/7.0; 640dpi; 1440x2560; samsung; SM-G930F; herolte; samsungexynos8890; en_US; 138226743)',
            'viewport-width': '1536',
        }
        self.get_Header_params()

    def ajax_request(self, url: str, /, params=None):
        """
        do requests, the engine of class
        :param url: api url
        :param params: api params
        :return: json object
        """
        for _ in range(5):
            try:
                resp = self.session.get(url, headers=self.headers, params=params, cookies=self.cookies)
                return resp.json()
            except requests.exceptions.RequestException:
                time.sleep(15)
        else:
            return None

    def get_Header_params(self):
        """
        every time visit ins will change header params, this is to get the header params
        :return: None
        """
        try:
            response = self.session.get(URLS[0], cookies=self.cookies, headers=self.headers)
            matches = re.findall(PARAMS, response.text)
            result = [match[i] for match in matches for i in range(3) if match[i]]
            # get app_id
            app_id = result[0].split(":")[1].strip().strip('"')
            # get claim
            claim = result[1].split(":")[1].strip().strip('"')
            # get csrf_token, if lose cookies, cannot get this param, also cannot access to other apis
            csrf_token = result[2].split(":")[1].strip().strip('"')
            # set values to headers
            self.headers.update({'x-asbd-id': '198387', 'x-csrftoken': csrf_token,
                                 'x-ig-app-id': app_id, 'x-ig-www-claim': claim,
                                 'x-requested-with': 'XMLHttpRequest', })
        except requests.exceptions.RequestException:
            raise 'Request error, please try again and check your Internet settings'

    def get_userInfo(self, userName: str):
        """
        get user info by username
        :param userName: name of user
        :return: dict of user info
        """
        params = {
            'username': userName,
        }
        resp = self.ajax_request(URLS[1], params=params)
        if resp:
            try:
                # to avoid exception? Internet went wrong may return wrong information
                data = resp['data']['user']
            except KeyError:
                raise 'Could not get user information...'
            return {
                'biography': data.get('biography'),
                'username': data.get('username'),
                'fbid': data.get('fbid'),
                'full_name': data.get('full_name'),
                'id': data.get('id'),
                'followed_by': data.get('edge_followed_by', {}).get('count'),
                'follow': data.get('edge_follow', {}).get('count'),
                'avatar': data.get('profile_pic_url_hd'),
                'noteCount': data.get('edge_owner_to_timeline_media', {}).get('count'),
                'is_private': data.get('is_private'),
                'is_verified': data.get('is_verified')
            } if data else 'unknown User'

    def get_userPosts(self, userName: str):
        """
        get all posts from the username
        :param userName:  name
        :return: generator
        """
        continuations = [{
            'count': '12',
        }]
        temp = userName + '/username/'
        while continuations:
            continuation = continuations.pop()
            # url will change when second request and later
            url = URLS[2] + f'/{temp}'
            resp = self.ajax_request(url, params=continuation)
            time.sleep(0.5)
            # no such user
            if not resp.get('user'):
                yield 'checking cookie or unknown/private User: {}'.format(userName)
            else:
                _items = resp.get('items')
                # simulate the mousedown
                if resp.get('more_available'):
                    continuations.append({'count': '12', 'max_id': resp.get('next_max_id')})
                    user = resp.get('user')
                    temp = user.get('pk_id') if user.get('pk_id') else user.get('pk')
                yield from self.extract_post(_items)

    def get_comments(self, id):
        """
        get comments by given post id
        :param id:
        :return: generator of comments
        """
        continuations = [{
            'can_support_threading': 'true',
            'permalink_enabled': 'false',
        }]
        # base url
        url = URLS[3] + f'{id}/comments/'
        while continuations:
            continuation = continuations.pop()
            resp = self.ajax_request(url, params=continuation)
            if resp.get('next_min_id'):
            #if resp['status'] == 'fail':
                continuations.append({
                    'can_support_threading': 'true',
                    'min_id': resp.get('next_min_id')
                })
            comments = resp.get('comments')
            if comments:
                for comment in comments:
                    yield {
                        'id': comment.get('pk'),
                        'user_name': comment.get('user', {}).get('username'),
                        'user_fullname': comment.get('user', {}).get('full_name'),
                        'text': comment.get('text'),
                        'created_at': comment.get('created_at'),
                        'comment_like_count': comment.get('comment_like_count'),
                        'reply_count': comment.get('child_comment_count')
                    }
                    if comment.get('child_comment_count') > 0:
                        yield from self.get_child_comment(id, comment.get('pk'))
            else:
                yield 'no comments or losing login cookies'

    def get_child_comment(self, main_id, id):
        """
        get child of the comment by comment_id, only used in function get_comments().
        :param main_id: post id
        :param id: comment_id
        :return: to comments generator
        """
        url = f'https://www.instagram.com/api/v1/media/{main_id}/comments/{id}/child_comments/'
        continuations = [{'max_id': ''}]
        while continuations:
            continuation = continuations.pop()
            resp = self.ajax_request(url, params=continuation)
            cursor = resp.get('next_max_child_cursor')
            if cursor:
                continuations.append({'max_id': cursor})
            comments = resp.get('child_comments')
            if comments:
                for comment in comments:
                    yield {
                        'id': comment.get('pk'),
                        'user_name': comment.get('user', {}).get('username'),
                        'user_fullname': comment.get('user', {}).get('full_name'),
                        'text': comment.get('text'),
                        'created_at': comment.get('created_at'),
                        'comment_like_count': comment.get('comment_like_count'),
                    }

    @staticmethod
    def extract_post(posts):
        """
        to extract a post from a list of posts
        :param posts: original instagram posts
        :return: dict of posts
        """
        for post in posts:
            caption = post.get('caption')
            item = {
                'code': post.get('code'),
                'id': post.get('pk'),
                'pk_id': post.get('id'),
                'comment_count': post.get('comment_count'),
                'like_count': post.get('like_count'),
                'text': caption.get('text') if caption else None,
                'created_at': caption.get('created_at') if caption else post.get('taken_at'),
            }
            # other type can be added by yourself
            types = post.get('media_type')
            item.update({
                'photo': [_.get('image_versions2', {}).get('candidates', [{}])[0].get('url') for _ in
                          post.get('carousel_media')]
            }) if types == 8 else None
            item.update({
                'video': post.get('video_versions', [{}])[0].get('url')
            }) if types == 2 else None
            item.update({
                'photo': post.get('image_versions2', {}).get('candidates', [{}])[0].get('url')
            }) if types == 1 else None
            yield item


if __name__ == '__main__':
    root_dir = '/Users/candice/Documents/研究/毕业论文/代码/crawler2.0/Instagram/'
    INS = Ins(cookie)
    posts_cnt = 50
    brand_file = root_dir + 'brand_list.csv'
    brands = pd.read_csv(brand_file)[['vertical', 'username']]
    brands_cnt = len(brands)
    vertical_f = brands['vertical'][0]
    vertical_json = {}
    for i in range(brands_cnt):
        vertical = brands['vertical'][i]
        if vertical != vertical_f:
            with open(root_dir + vertical_f+'.json', 'w') as file:
                json.dump(vertical_json, file, indent = 4)
            vertical_f = vertical
            vertical_json = {}
        user_name = brands['username'][i]
        if user_name not in vertical_json.keys():
            vertical_json[user_name] = {}
        try:
            vertical_json[user_name]['info'] = INS.get_userInfo(user_name)
            vertical_json[user_name]['posts'] = []
            posts = INS.get_userPosts(user_name)
            # items = INS.get_comments('3092771276598639274')
            post_cnt = 0
            for post in posts:
                try:
                    if type(post) is not dict:
                        continue
                    post_dict = {'post_id': post['id'], 'comment_count': post['comment_count'], 
                                'like_count': post['like_count'], 'text': post['text'], 'created_at': post['created_at']}
                    if 'photo' in post.keys():
                        post_dict['photo'] = post['photo']
                    comments = INS.get_comments(post['id'])
                    comments_cnt = max(50, post['comment_count'])
                    comment_cnt = 0
                    comments_list = []
                    for comment in comments:
                        try:
                            if type(comment) is not dict:
                                continue
                            comments_list.append(comment['text'])
                            comment_cnt += 1
                            if comment_cnt == comments_cnt:
                                break
                        except:
                            print(Exception)
                            continue
                    post_dict['comments'] = comments_list
                    vertical_json[user_name]['posts'].append(post_dict)
                    post_cnt += 1
                    if post_cnt == posts_cnt:
                        break
                except:
                    print(Exception)
                    continue
        except:
            print(Exception)
            continue
