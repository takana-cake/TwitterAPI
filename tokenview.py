import sys
import json
from requests_oauthlib import OAuth1Session
from urllib.parse import parse_qsl

def TwitterOAuth(consumer_key, consumer_secret, oauth_token = None, oauth_verifier = None):
	twitter = OAuth1Session(consumer_key, consumer_secret, oauth_token, oauth_verifier)
	return twitter

def request_token(twitter, oauth_callback = "https://knowledgestack.dip.jp/pages/tokenview.php"):
	request_token_url = "https://api.twitter.com/oauth/request_token"
	response = twitter.post(
			request_token_url,
			params={'oauth_callback': oauth_callback}
	)
	# responseからリクエストトークンを取り出す
	request_token = dict(parse_qsl(response.content.decode("utf-8")))
	# リクエストトークンから連携画面のURLを生成
	#authenticate_url = "https://api.twitter.com/oauth/authenticate"
	#authenticate_endpoint = '%s?oauth_token=%s' \
	#	  % (authenticate_url, request_token['oauth_token'])
	return request_token

def access_token(twitter, oauth_verifier):
	access_token_url = "https://api.twitter.com/oauth/access_token"
	try:
		response = twitter.post(
			access_token_url,
			params={'oauth_verifier': oauth_verifier}
		)
	except Exception as e:
		return e
	access_token = dict(parse_qsl(response.content.decode("utf-8")))
	return access_token


dir = "/var/www/cgi-bin/"
file = open(dir + "secret.json")
json_data = json.load(file)
consumer_key = json_data["CK"]
consumer_secret = json_data["CS"]

if len(sys.argv) == 1:
	twitter = TwitterOAuth(consumer_key, consumer_secret)
	token = request_token(twitter)
	authenticate_url = "https://api.twitter.com/oauth/authenticate"
	authenticate_endpoint = '%s?oauth_token=%s' % (authenticate_url, token['oauth_token'])
	print(authenticate_endpoint)
elif len(sys.argv) == 3:
	save = open(dir + "save.json","r+")
	with open(dir + "save.json", "r") as save:
		try:
			json_data = json.load(save)
		except ValueError:
			json_data = []
	oauth_token = sys.argv[1]
	oauth_verifier = sys.argv[2]
	twitter = TwitterOAuth(consumer_key, consumer_secret, oauth_token, oauth_verifier)
	access_token = access_token(twitter, oauth_verifier)
	# 良い手段が思いつかない
	flag = False
	for i in len(json_data):
		if json_data[i]["user_id"] == access_token["user_id"]:
			json_data[i]["screen_name"] = user["screen_name"]
			json_data[i]["oauth_token"] = access_token["oauth_token"]
			json_data[i]["oauth_token_secret"] = access_token["oauth_token_secret"]
			flag = True
	if flag is False:
		json_data.append(access_token)
	with open(dir + "save.json", "w") as save:
		json.dump(json_data,save)
	print(access_token)
else:
	print("err")
