# TwitterAPI v.20221202.0
# -*- coding: utf-8 -*-

from logging import getLogger, handlers, Formatter, StreamHandler, DEBUG
from requests_oauthlib import OAuth1Session
import argparse
import json
import time, sys, os, re, csv
from datetime import datetime, timedelta, timezone
from requests.exceptions import ConnectionError
import urllib.request
from urllib.parse import unquote

class TwetterObj:
	def __init__(self, CK, CS, AT, AS):
		self.session = OAuth1Session(CK, CS, AT, AS)

	def searchTweets(self, keyword, fullText = False, total = -1, onlyText = False, includeRetweet = False):
		#----------------
		# URL、パラメータ
		#----------------
		url_search = 'https://api.twitter.com/1.1/search/tweets.json'
		if fullText is True:
			params = {'q':keyword, 'count':100,'result_type':'recent', "tweet_mode" : "extended"}
		else:
			params = {'q':keyword, 'count':100,'result_type':'recent'}
		params['include_rts'] = str(includeRetweet).lower()
		# include_rts は statuses/user_timeline のパラメータ。search/tweets には無効

		#----------------
		# 回数制限を確認
		#----------------
		self.checkLimit("search", "/search/tweets")

		#----------------
		# ツイート取得
		#----------------
		cnt = 0
		unavailableCnt = 0
		while True:
			try:
				res = self.session.get(url_search, params = params)
			except ConnectionError as e:
				logger.debug("ConnectionError:" + str(e))
				time.sleep(60)
				continue
			if res.status_code == 503:
				# 503 : Service Unavailable
				if unavailableCnt > 10:
					raise Exception('Twitter API error %d' % res.status_code)

				unavailableCnt += 1
				logger.debug('Service Unavailable 503')
				self.waitUntilReset(time.mktime(datetime.now().timetuple()) + 30)
				continue

			unavailableCnt = 0

			if res.status_code != 200:
				raise Exception('Twitter API error %d' % res.status_code)

			tweets = self.pickupTweet(json.loads(res.text))
			if len(tweets) == 0:
				# len(tweets) != params['count'] としたいが
				# count は最大値らしいので判定に使えない。
				# ⇒  "== 0" にする
				# https://dev.twitter.com/discussions/7513
				break

			for tweet in tweets:
				if (('retweeted_status' in tweet) and (includeRetweet is False)):
					pass
				else:
					if onlyText is True:
						# メッセージ本文だけ取得するか
						yield tweet['text']
					else:
						yield tweet

					cnt += 1
					if total > 0 and cnt >= total:
						return

			params['max_id'] = tweet['id'] - 1

			# ヘッダ確認 （回数制限）
			# X-Rate-Limit-Remaining が入ってないことが稀にあるのでチェック
			if ('X-Rate-Limit-Remaining' in res.headers and 'X-Rate-Limit-Reset' in res.headers):
				if (int(res.headers['X-Rate-Limit-Remaining']) == 0):
					self.waitUntilReset(int(res.headers['X-Rate-Limit-Reset']))
					self.checkLimit("search", "/search/tweets")
			else:
				logger.debug('not found  -  X-Rate-Limit-Remaining" OR "X-Rate-Limit-Reset')
				self.checkLimit("search", "/search/tweets")

	def checkLimit(self, arg1, arg2):
		'''
		回数制限を問合せ、アクセス可能になるまで wait する
		'''
		unavailableCnt = 0
		while True:
			url = "https://api.twitter.com/1.1/application/rate_limit_status.json"
			try:
				res = self.session.get(url)
			except ConnectionError as e:
				logger.debug("ConnectionError:" + str(e))
				time.sleep(60)
				continue
			if res.status_code == 503:
				# 503 : Service Unavailable
				if unavailableCnt > 10:
					raise Exception('Twitter API error %d' % res.status_code)
				unavailableCnt += 1
				logger.debug('Service Unavailable 503')
				self.waitUntilReset(time.mktime(datetime.now().timetuple()) + 30)
				continue
			if res.status_code != 200:
				raise Exception('Twitter API error %d' % res.status_code)
			res_text = json.loads(res.text)
			remaining = int(res_text['resources'][arg1][arg2]['remaining'])
			reset = int(res_text['resources'][arg1][arg2]['reset'])
			if (remaining == 0):
				self.waitUntilReset(reset)
			else:
				break

	def waitUntilReset(self, reset):
		seconds = reset - time.mktime(datetime.now().timetuple())
		seconds = max(seconds, 0)
		logger.debug("waiting" + str(seconds) + "sec")
		sys.stdout.flush()
		time.sleep(seconds + 10)  # 念のため + 10 秒
	
	def showList(self, user_id = "", screen_name = ""):
		url_showlist = "https://api.twitter.com/1.1/lists/list.json"
		if user_id:
			params = {'user_id' : user_id}
		elif screen_name:
			params = {'screen_name' : screen_name}
		unavailableCnt = 0
		while True:
			try:
				res = self.session.get(url_showlist, params = params)
			except ConnectionError as e:
				logger.debug("ConnectionError:" + str(e))
				time.sleep(60)
				continue
			if res.status_code == 503:
				if unavailableCnt > 10:
					logger.debug(str(tweetId) + str(res.status_code) + res.text)
					break
				unavailableCnt += 1
				self.waitUntilReset(time.mktime(datetime.datetime.now().timetuple()) + 30)
				continue
			if res.status_code != 200:
				logger.debug(res.text)
			break
		res_text = json.loads(res.text)
		return res_text
	
	def getList(self, list_id):
		url_getList = "https://api.twitter.com/1.1/lists/show.json"
		params = {'list_id' : list_id}
		unavailableCnt = 0
		while True:
			try:
				res = self.session.get(url_getList, params = params)
			except ConnectionError as e:
				logger.debug("ConnectionError:" + str(e))
				time.sleep(60)
				continue
			if res.status_code == 503:
				if unavailableCnt > 10:
					logger.debug(str(tweetId) + str(res.status_code) + res.text)
					break
				unavailableCnt += 1
				self.waitUntilReset(time.mktime(datetime.datetime.now().timetuple()) + 30)
				continue
			if res.status_code != 200:
				logger.debug(res.text)
			break
		res_text = json.loads(res.text)
		return res_text
	
	def addList(self, list_id, adduser_id):
		url_addlist = "https://api.twitter.com/1.1/lists/members/create.json"
		params = {'list_id' : list_id, 'user_id' : adduser_id}
		unavailableCnt = 0
		while True:
			try:
				res = self.session.post(url_addlist, params = params)
			except ConnectionError as e:
				logger.debug("ConnectionError:" + str(e))
				time.sleep(60)
				continue
			if res.status_code == 503:
				if unavailableCnt > 10:
					logger.debug(str(tweetId) + str(res.status_code) + res.text)
					break
				unavailableCnt += 1
				self.waitUntilReset(time.mktime(datetime.datetime.now().timetuple()) + 30)
				continue
			if res.status_code != 200:
				logger.debug(res.text)
				self.checkLimit("lists", "/lists/members")
			break

	def favorites(self, tweetId):
		url_fav = "https://api.twitter.com/1.1/favorites/create.json"
		params = {'id' : tweetId}
		unavailableCnt = 0
		while True:
			try:
				res = self.session.post(url_fav, params = params)
			except ConnectionError as e:
				logger.debug("ConnectionError:" + str(e))
				time.sleep(60)
				continue
			if res.status_code == 503:
				if unavailableCnt > 10:
					logger.debug(str(tweetId) + str(res.status_code) + res.text)
					break
				unavailableCnt += 1
				self.waitUntilReset(time.mktime(datetime.datetime.now().timetuple()) + 30)
				continue
			if res.status_code != 200:
				logger.debug(str(tweetId) + str(res.status_code) + res.text)
			break

	def retweet(self, tweetId):
		url_rt = "https://api.twitter.com/1.1/statuses/retweet/%d.json"%tweetId
		unavailableCnt = 0
		while True:
			try:
				res = self.session.post(url_rt) # retweet実行
			except ConnectionError as e:
				logger.debug("ConnectionError:" + str(e))
				time.sleep(60)
				continue
			if res.status_code == 503:
				# 503 : Service Unavailable
				if unavailableCnt > 10:
					logger.debug(str(tweetId) + str(res.status_code) + res.text)
					break
				unavailableCnt += 1
				self.waitUntilReset(time.mktime(datetime.datetime.now().timetuple()) + 30)
				continue
			if res.status_code != 200:
				logger.debug(str(tweetId) + str(res.status_code) + res.text)
			break

	def showStatus(self, repid):
		url_show = "https://api.twitter.com/1.1/statuses/show.json"
		params = {"id":repid}
		unavailableCnt = 0
		while True:
			try:
				res = self.session.get(url_show, params = params)
			except ConnectionError as e:
				logger.debug("ConnectionError:" + str(e))
				time.sleep(60)
				continue
			if res.status_code == 503:
				if unavailableCnt > 10:
					logger.debug(str(tweetId) + str(res.status_code) + res.text)
					break
				unavailableCnt += 1
				self.waitUntilReset(time.mktime(datetime.datetime.now().timetuple()) + 30)
				continue
			if res.status_code != 200:
				logger.debug(str(tweetId) + str(res.status_code) + res.text)
			break
		res_text = json.loads(res.text)
		return res_text

	def pickupTweet(self, res_text):
		'''
		res_text からツイートを取り出し、配列にセットして返却
		'''
		results = []
		for tweet in res_text['statuses']:
			results.append(tweet)
		return results

	def getFollowList(self, screen_name):
		ids = []
		url_flist = 'https://api.twitter.com/1.1/friends/list.json'
		self.screen = screen_name
		params = {'screen_name':self.screen,'count':200}
		unavailableCnt = 0
		while True:
			try:
				res = self.session.get(url_flist, params = params)
			except ConnectionError as e:
				logger.debug("[getFollowList]" + "ConnectionError:" + str(e))
				time.sleep(60)
				continue
			if res.status_code == 503:
				# 503 : Service Unavailable
				if unavailableCnt > 10:
					logger.debug("[getFollowList]" + self.screen + str(res.status_code) + res.text)
					break
				unavailableCnt += 1
				self.waitUntilReset(time.mktime(datetime.now().timetuple()) + 30)
				continue
			if res.status_code != 200:
				logger.debug("[getFollowList]" + self.screen + str(res.status_code) + res.text)
				self.checkLimit("friends", "/friends/list")
				if unavailableCnt > 10:
					break
				unavailableCnt += 1
				continue
			res_loads = json.loads(res.text)
			for i in res_loads['users']:
				ids.append({"id":i['id'], "screen_name":i['screen_name']})
			if res_loads['next_cursor'] == 0:
				break
			else:
				params['cursor'] = res_loads['next_cursor']
		return ids

	def showUser(self, screen_name = "", user_id = ""):
		ids = []
		url_show = 'https://api.twitter.com/1.1/users/show.json'
		if screen_name:
			params = {'screen_name':screen_name}
		elif user_id:
			params = {'user_id':user_id}
		else:
			return None
		unavailableCnt = 0
		while True:
			try:
				res = self.session.get(url_show, params = params)
			except ConnectionError as e:
				logger.debug("ConnectionError:" + str(e))
				time.sleep(60)
				continue
			if res.status_code == 503:
				# 503 : Service Unavailable
				if unavailableCnt > 10:
					logger.debug(self.screen + str(res.status_code) + res.text)
					break
				unavailableCnt += 1
				self.waitUntilReset(time.mktime(datetime.now().timetuple()) + 30)
				continue
			if res.status_code != 200:
				logger.debug(self.screen + str(res.status_code) + res.text)
				self.checkLimit("users", "/users/show")
				if unavailableCnt > 10:
					break
				unavailableCnt += 1
				continue
			user = json.loads(res.text)
			return user

	def searchKeyword(self, keyword, total = 1000, onlyText = False, includeRetweet = False):
		self.keyword = keyword
		for tweet in self.searchTweets(keyword, total, onlyText, includeRetweet):
			yield tweet

	def messageSent(self, send2id, text_msg):
		self.send2id = send2id
		url_msg = 'https://api.twitter.com/1.1/direct_messages/events/new.json'
		headers = {'content-type': 'application/json'}
		payload = {"event":
			{"type": "message_create",
			"message_create": {
				"target": {"recipient_id": self.send2id},
				"message_data": {"text": text_msg,}
			}}}
		payload = json.dumps(payload)
		unavailableCnt = 0
		while True:
			try:
				res = self.session.post(url_msg, headers=headers, data=payload)
			except ConnectionError as e:
				logger.debug("ConnectionError:" + str(e))
				time.sleep(60)
				continue
			if res.status_code == 503:
				# 503 : Service Unavailable
				if unavailableCnt > 10:
					logger.debug(str(res.status_code) + res.text)
					break
				unavailableCnt += 1
				self.waitUntilReset(time.mktime(datetime.now().timetuple()) + 30)
				continue
			if res.status_code != 200:
				logger.debug(str(res.status_code) + res.text)
			break

	def checkTL(self, user_id, include_rts = False, since_id = "", max_id = ""):
		url_tl = "https://api.twitter.com/1.1/statuses/user_timeline.json"
		if max_id and since_id:
			raise Exception('Do not put both sin and max.')
		if max_id:
			params = {"user_id":user_id, "include_rts":include_rts, "count":100, "max_id":max_id}
		elif since_id:
			params = {"user_id":user_id, "include_rts":include_rts, "count":100, "since_id":since_id}
		else:
			params = {"user_id":user_id, "include_rts":include_rts, "count":100}

		#----------------
		# 回数制限を確認
		#----------------
		self.checkLimit("statuses", "/statuses/user_timeline")

		#----------------
		# TimeLine取得
		#----------------
		cnt = 0
		unavailableCnt = 0
		while True:
			try:
				res = self.session.get(url_tl, params = params)
			except ConnectionError as e:
				logger.debug("ConnectionError:" + str(e))
				time.sleep(60)
				continue
			if res.status_code == 503:
				# 503 : Service Unavailable
				if unavailableCnt > 10:
					raise Exception('Twitter API error %d' % res.status_code)
				unavailableCnt += 1
				logger.debug("Service Unavailable 503")
				self.waitUntilReset(time.mktime(datetime.now().timetuple()) + 30)
				continue
			unavailableCnt = 0

			if res.status_code != 200:
				if "Not authorized." in res.text:
					break
				raise Exception('Twitter API error ',res.status_code,res.text)

			for tweet_tl in json.loads(res.text):
				yield tweet_tl
			if "since_id" in params:
				params['since_id'] = tweet_tl['id'] + 1
			else:
				try:
					params['max_id'] = tweet_tl['id'] - 1
				except Exception as e:
					print(e)
					print(params)
					# tweet_tlが宣言されてないてでる

			# ヘッダ確認 （回数制限）
			# X-Rate-Limit-Remaining が入ってないことが稀にあるのでチェック
			if ('X-Rate-Limit-Remaining' in res.headers and 'X-Rate-Limit-Reset' in res.headers):
				if (int(res.headers['X-Rate-Limit-Remaining']) == 0):
					self.waitUntilReset(int(res.headers['X-Rate-Limit-Reset']))
					self.checkLimit("search", "/search/tweets")
			else:
				logger.debug('not found  -  X-Rate-Limit-Remaining" OR "X-Rate-Limit-Reset')
				self.checkLimit("search", "/search/tweets")
			cnt += 1
			if cnt >= 100:
				break

	def pickUrls(self, SCREEN, FILEPATH):
		def splitUrls(TXT):
			DESCURLS = []
			SHORTURLS = []
			URL_PATTERN = re.compile("http[!-~]+")
			SHORTURLS = re.findall(URL_PATTERN, TXT)
			for j in SHORTURLS:
				if j[-1] in ["]", ")"]:
					j = j[:-1]
				try:
					DESCURL = (urllib.request.urlopen(j,timeout=3).geturl())
					DESCURLS.append(DESCURL)
				except Exception as err:
					logger.debug(err)
					logger.debug(j)
					DESCURLS.append(j)
			return DESCURLS
		USER_OBJECT = self.showUser(SCREEN)
		URLS = []
		USER_URL = USER_OBJECT["entities"]
		USER_DESCRIPTION = USER_OBJECT["description"]
		if "url" in USER_URL:
			URLS.append(USER_URL["url"]["urls"][0]["expanded_url"])
		URLS.extend(splitUrls(USER_DESCRIPTION))
		return URLS
	
	def getTrends(self):
		url_getTrends = "https://api.twitter.com/1.1/trends/place.json"
		params = {'id' : '23424856'}
		unavailableCnt = 0
		while True:
			try:
				res = self.session.get(url_getTrends, params = params)
			except ConnectionError as e:
				logger.debug("ConnectionError:" + str(e))
				time.sleep(60)
				continue
			if res.status_code == 503:
				if unavailableCnt > 10:
					logger.debug(str(res.status_code) + res.text)
					break
				unavailableCnt += 1
				self.waitUntilReset(time.mktime(datetime.datetime.now().timetuple()) + 30)
				continue
			if res.status_code != 200:
				logger.debug(res.text)
			break
		res_text = json.loads(res.text)
		return res_text
	


### download ###

def pickupMedia(tweet):
	ary = []
	if not 'extended_entities' in tweet:
		return None
	if 'media' in tweet["extended_entities"]:
		for media in tweet["extended_entities"]["media"]:
			if media["type"] == 'photo':
				DL_URL = media["media_url"]
				FILENAME = os.path.basename(DL_URL)
				MTYPE = "img"
				DL_URL = DL_URL + ":orig"
				ary.append({"fn":FILENAME,"mtype":MTYPE,"url":DL_URL})
			if media["type"] == 'animated_gif':
				DL_URL = media["video_info"]["variants"][0]["url"]
				FILENAME = os.path.basename(DL_URL)
				MTYPE = "gif"
				ary.append({"fn":FILENAME,"mtype":MTYPE,"url":DL_URL})
			if media["type"] == 'video':
				for i, var in enumerate(media["video_info"]["variants"]):
					if not "bitrate" in media["video_info"]["variants"][i]:
						media["video_info"]["variants"].pop(i)
				DL_URL = max(media["video_info"]["variants"], key=lambda d: d["bitrate"])["url"]
				if '?tag=' in DL_URL:
					DL_URL = DL_URL.rsplit("?", 1)[0]
				FILENAME = os.path.basename(DL_URL)
				MTYPE = "video"
				ary.append({"fn":FILENAME,"mtype":MTYPE,"url":DL_URL})
	return ary

def downloadMedia(DL_URL, FILEPATH, FILENAME):
	errcount = 0
	if FILEPATH[-1] is not "/":
		FILEPATH = FILEPATH + "/"
	while True:
		if os.path.exists(FILEPATH + FILENAME) == True:
			break
		try:
			with open(FILEPATH + FILENAME, 'wb') as f:
				dl_file = urllib.request.urlopen(DL_URL).read()
				f.write(dl_file)
		except Exception as e:
			if errcount < 3:
				logger.debug(e)
				time.sleep(60)
				continue
		break

def _logger():
	logger = getLogger(__name__)
	logger.setLevel(DEBUG)
	formatter = Formatter("[%(asctime)s] [%(process)d] [%(name)s] [%(levelname)s] %(message)s")
	handler_console = StreamHandler()
	handler_console.setLevel(DEBUG)
	handler_console.setFormatter(formatter)
	logger.addHandler(handler_console)
	handler_file = handlers.RotatingFileHandler(filename='./twiutil.log',maxBytes=1048576,backupCount=3)
	handler_file.setFormatter(formatter)
	logger.addHandler(handler_file)
	logger.propagate = False
	return logger

def _parser():
	parser = argparse.ArgumentParser(
		usage="""python3 twiutil.py [mode] <--option>
	
	Mandatory auth_screen.
	python3 twiutil.py getMediaOnFollow --auth_screen <auth_screen_name>
	python3 twiutil.py searchMediaFavRt --auth_screen <auth_screen_name> --keyword '<search_word>'
	python3 twiutil.py addListFollowUser --auth_screen <auth_screen_name> --list_id <list_id>
	python3 twiutil.py searchWordOnTL --auth_screen <auth_screen_name> --user_id <send message> --keyword '<search_word>'
	
	python3 twiutil.py searchWord2Json --auth_screen <auth_screen_name> --keyword '<search_word>' --output <output_file>
	python3 twiutil.py searchWordGetMedia --auth_screen <auth_screen_name> --keyword '<search_word>'
	python3 twiutil.py getMediaOnScreen --auth_screen <auth_screen_name> --screen_name <screen_name>
	python3 twiutil.py showUsrList --auth_screen <auth_screen_name> --screen_name <screen_name>
	python3 twiutil.py getTrends --auth_screen <auth_screen_name>""",
		add_help=True,
		formatter_class=argparse.RawTextHelpFormatter
	)
	parser.add_argument("mode", help="", type=str, metavar="[mode]")
	parser.add_argument("--auth_screen", help="", type=str, metavar="<auth_screen>")
	parser.add_argument("--screen_name", help="", type=str, metavar="<screen_name>")
	parser.add_argument("--user_id", help="", type=int, metavar="<user_id>")
	parser.add_argument("--keyword", help="", type=str, nargs='*', metavar="'<keyword>'")
	parser.add_argument("--output", help="", type=str, metavar="'<output_file>'")
	parser.add_argument("--list_id", help="", type=str, metavar="'<list_id>'")
	return parser.parse_args()

def _help():
	print("""class
	TwetterObj(CK, CS, AT, AS)
method
	searchTweets(keyword, fullText = False, total = -1, onlyText = False, includeRetweet = False)
	checkLimit(arg1, arg2)  Get rate limits and usage applied to each Rest API endpoint
	waitUntilReset(reset)
	showUsrList(user_id = "", screen_name = "")
	getList(list_id)
	addList(list_id, adduser_id)
	favorites(tweetId)
	retweet(tweetId)
	showStatus(tweetId)	     Return statuses-show response.
	getFollowList(screen_name)      Get follow "id" and "screen_name".
	showUser(screen_name = "", user_id = "")	Return user-show response.
	searchKeyword(keyword, total = 1000, onlyText = False, includeRetweet = False)
		yield tweet.
	messageSent(user_id, send_text)
	checkTL(user_id, include_rts = False, since_id = "", max_id = "")
	getTrends()
function
	pickupMedia(tweet)	      Return ary, {"fn":FILENAME,"url":DL_URL}
	downloadMedia(DL_URL, FILEPATH, FILENAME)""")

def _main():
	if os.path.dirname(sys.argv[0]):
		dir = os.path.dirname(sys.argv[0]) + "/"
	else:
		dir = os.getcwd() +"/"
	cmd_args = _parser()
	mode = cmd_args.mode
	auth_screen = ""
	if cmd_args.auth_screen:
		auth_screen = cmd_args.auth_screen
	logger.debug("mode:" + mode)
	JST = timezone(timedelta(hours=+9), 'JST')
	
	# OAuth
	secret = "secret.json"
	if os.path.exists(dir + secret) == False:
		with open(dir + secret,"w") as f:
			pass
	with open(dir + secret) as f:
		try:
			secret = json.load(f)
			CK = secret["CK"]
			CS = secret["CS"]
		except ValueError:
			logger.debug("secret.json is not set. Please input key.")
			while True:
				print("Consumer api Key: ")
				CK = input()
				print("Consumer api Secret: ")
				CS = input()
				if CK and CS:
					break
				else:
					print("please input keys")
	save_data = []
	if os.path.exists(dir + "save.json"):
		with open(dir + "save.json") as save:
			try:
				save_data = json.load(save)
			except ValueError:
				pass
	if not save_data:
		logger.debug("save.json is not set. Please check tokenview.")
		sys.exit()
	if auth_screen:
		for usr in save_data:
			if usr["screen_name"] == auth_screen:
				AT = usr["oauth_token"]
				AS = usr["oauth_token_secret"]
	else:
		AT = save_data[0]["oauth_token"]
		AS = save_data[0]["oauth_token_secret"]
	
	if cmd_args.screen_name:
		screen_name = cmd_args.screen_name
	if cmd_args.user_id:
		user_id = cmd_args.user_id
	if cmd_args.keyword:
		keyword = cmd_args.keyword[0]
	if cmd_args.list_id:
		list_id = cmd_args.list_id
	if cmd_args.output:
		output = cmd_args.output
		if not os.path.dirname(output):
			raise Exception('Filedir not exists.')
	
	# インスタンス作成
	getter = TwetterObj(CK, CS, AT, AS)
	
	# フォローしている人のMediaをDownload
	if mode == "getMediaOnFollow" or mode == "getMediaOnFollowEachUser":
		if not cmd_args.auth_screen:
			raise Exception('Not set auth_screen')
		user_id = getter.showUser(auth_screen)["id"]
		download_dir = dir + auth_screen + "/"
		if os.path.exists(download_dir) == False:
			os.makedirs(download_dir)
		if os.path.exists(download_dir + "db.json") == False:
			with open(download_dir + "db.json", "w") as save:
				pass
		with open(download_dir + "db.json", "r") as db:
			try:
				json_data = json.load(db)
			except ValueError:
				json_data = {}
		flist_res = getter.getFollowList(auth_screen)
		chknum = 0
		fnum = str(len(flist_res))
		for f in flist_res:
			chknum+=1
			logger.debug(str(chknum) + " / " + fnum)
			if mode == "getMediaOnFollowEachUser":
				FILEPATH = download_dir + f["screen_name"] + "/"
			else:
				FILEPATH = download_dir
			if os.path.exists(FILEPATH) == False:
				os.makedirs(FILEPATH)
				os.makedirs(FILEPATH + "img")
				os.makedirs(FILEPATH + "video")
				os.makedirs(FILEPATH + "gif")
			last_id = max_id = ""
			if f["id"] in json_data:
				last_id = json_data[f["id"]]
			for twi in getter.checkTL(user_id = f["id"]):
				if not max_id:
					max_id = twi["id"]
				if last_id == twi["id"]:
					break
				ARY = pickupMedia(twi)
				if ARY is None:
					continue
				for content in ARY:
					downloadMedia(content["url"], FILEPATH + content["mtype"] + "/", content["fn"])
			json_data[f["id"]] = max_id
		with open(download_dir + "db.json", "w") as save:
			json.dump(json_data,save)
	
	# keyword検索に対しフォローしているユーザがツイートしているか確認
	if mode == "searchWordOnTL":
		if not (auth_screen or keyword or user_id):
			raise Exception('Not set auth_screen or keyword or user_id')
		flist_res = getter.getFollowList(auth_screen)
		flist = []
		for f in flist_res:
			flist.append(f["id"])
		text_msg = ""
		cnt = 0
		timer = datetime.now() + timedelta(minutes=55)
		timer_sin = datetime.now().replace(minute=0,second=0) - timedelta(hours=6) # 6時間以内
		for tweet in getter.searchTweets(keyword, total = 1000):
			cnt += 1
			unix_time = ((tweet['id'] >> 22) + 1288834974657) / 1000.0
			ts = datetime.fromtimestamp(unix_time)
			if timer_sin > ts:
			       break
			if tweet['user']['id'] in flist:
				text_msg = "https://twitter.com/" + tweet['user']['screen_name'] + "/status/" + str(tweet['id'])
				getter.messageSent(user_id, text_msg)
			timer_now = datetime.now()
			if timer > timer_now and 95 < cnt:
				slt = timer - timer_now
				time.sleep(slt.total_seconds())
			elif timer < timer_now:
				timer = timer_now + timedelta(minutes=55)
				cnt = 0
			else:
				time.sleep(30)
	
	# キーワード画像検索してFAVRT/day
	if mode == "searchMediaFavRt":
		if not (auth_screen or keyword):
			raise Exception('Not set auth_screen or keyword')
		cnt = 0
		timer = datetime.now() + timedelta(minutes=55)
		timer_sin = datetime.now().replace(hour=0,minute=0,second=0) - timedelta(days=1)
		for tweet in getter.searchTweets(keyword, total = 1000):
			cnt += 1
			unix_time = ((tweet['id'] >> 22) + 1288834974657) / 1000.0
			ts = datetime.fromtimestamp(unix_time)
			if timer_sin > ts:
			       break
			if "media" in tweet["entities"]:
				getter.retweet(tweet['id'])
				getter.favorites(tweet['id'])
			if tweet["in_reply_to_status_id_str"]:
				reptweet = getter.showStatus(tweet["in_reply_to_status_id_str"])
				if "media" in reptweet["entities"]:
					getter.retweet(reptweet['id'])
					getter.favorites(reptweet['id'])
			timer_now = datetime.now()
			if timer > timer_now and 95 < cnt:
				slt = timer - timer_now
				time.sleep(slt.total_seconds())
			elif timer < timer_now:
				timer = timer_now + timedelta(minutes=55)
				cnt = 0
			else:
				time.sleep(30)

	# キーワード検索してjsonへ保存
	if mode == "searchWord2Json":
		if not (keyword or output):
			raise Exception('Not set keyword or output_file')
		json_sw = []
		cnt = 0
		timer = datetime.now() + timedelta(minutes=55)
		for tweet in getter.searchTweets(keyword, fullText = True, total = 1000):
			cnt += 1
			json_sw.append({"name":tweet['user']['name'], "text":tweet["full_text"], "id":tweet['id']})
			timer_now = datetime.now()
			if timer > timer_now and 95 < cnt:
				slt = timer - timer_now
				time.sleep(slt.total_seconds())
			elif timer < timer_now:
				timer = timer_now + timedelta(minutes=55)
				cnt = 0
			else:
				time.sleep(30)
		#filename = dir + re.sub(re.compile("[!-/:-@[-`{-~]"), '', keyword) + ".json"
		with open(output, "w") as save:
			json.dump(json_sw,save)
	
	# キーワード検索してMediaをDownload
	if mode == "searchWordGetMedia":
		if not (keyword):
			raise Exception('Not set keyword')
		FILEPATH = dir + re.sub(re.compile("[!-/:-@[-`{-~]"), '', keyword) + "/"
		keyword = keyword + " filter:media"
		if os.path.exists(FILEPATH) == False:
			os.makedirs(FILEPATH)
			os.makedirs(FILEPATH + "img")
			os.makedirs(FILEPATH + "video")
			os.makedirs(FILEPATH + "gif")
		for i in getter.searchKeyword(keyword):
			ARY = pickupMedia(i)
			if ARY is None:
				continue
			for content in ARY:
				if content:
					downloadMedia(content["url"], FILEPATH + content["mtype"] + "/", content["fn"])
	
	# screen_nameのMediaをDownload
	if mode == "getMediaOnScreen":
		if not cmd_args.screen_name:
			raise Exception('Not set screen_name')
		FILEPATH = dir + screen_name + "/"
		if os.path.exists(FILEPATH) == False:
			os.makedirs(FILEPATH)
			os.makedirs(FILEPATH + "img")
			os.makedirs(FILEPATH + "video")
			os.makedirs(FILEPATH + "gif")
		if os.path.exists(FILEPATH + "db.json") == False:
			with open(FILEPATH + "db.json", "w") as save:
				pass
		with open(FILEPATH + "db.json", "r") as db:
			try:
				json_data = json.load(db)
			except ValueError:
				json_data = {}
		last_id = max_id = ""
		if "last_id" in json_data:
			last_id = json_data["last_id"]
		user_id = getter.showUser(screen_name)["id"]
		for twi in getter.checkTL(user_id = user_id):
			if not max_id:
				max_id = twi["id"]
			if last_id == twi["id"]:
				break
			ARY = pickupMedia(twi)
			if ARY is None:
				continue
			for content in ARY:
				downloadMedia(content["url"], FILEPATH + content["mtype"] + "/", content["fn"])
		json_data["last_id"] = max_id
		with open(download_dir + "db.json", "w") as save:
			json.dump(json_data,save)
	
	# ユーザーの作成したリストを一覧表示する
	if mode == "showUsrList":
		if not cmd_args.screen_name:
			raise Exception('Not set screen_name')
		user_id = getter.showUser(screen_name = screen_name)["id"]
		lists = getter.showUsrList(user_id = user_id)
		for l in lists:
			logger.debug("id:" + str(l["id"]) + ", name:" + l["full_name"])
	# Followユーザーをリストへ追加する
	if mode == "addListFollowUser":
		if not (auth_screen or list_id):
			raise Exception('Not set auth_screen or list_id')
		flist_res = getter.getFollowList(auth_screen)
		for f in flist_res:
			getter.addList(list_id, f["id"])
	
	# 日本のトレンド取得
	if mode == "getTrends":
		res = getter.getTrends()
		print(res)
	
	# test
	if mode == "test":
		res = getter.getTrends()
		for i in res[0]["trends"]:
			print(str(i["tweet_volume"]) + "	:" + unquote(i["query"]))

if __name__ == '__main__':
	logger = _logger()
	_main()
	logger.debug("finish.")
else:
	logger = _logger()
	_help()
