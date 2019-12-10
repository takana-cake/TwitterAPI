# -*- coding: utf-8 -*-

from requests_oauthlib import OAuth1Session
import json
import time, sys, os
from datetime import datetime, timedelta, timezone
from requests.exceptions import ConnectionError
import urllib.request

class TwetterObj:
	def __init__(self, CK, CS, AT, AS):
		self.session = OAuth1Session(CK, CS, AT, AS)

	def collect(self, total = -1, onlyText = False, includeRetweet = False):
		#----------------
		# URL、パラメータ
		#----------------
		url_search = 'https://api.twitter.com/1.1/search/tweets.json'
		params = {'q':self.keyword, 'count':100,'result_type':'mixed'}
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
				print("ConnectionError:",e)
				time.sleep(60)
				continue
			if res.status_code == 503:
				# 503 : Service Unavailable
				if unavailableCnt > 10:
					raise Exception('Twitter API error %d' % res.status_code)

				unavailableCnt += 1
				print ('Service Unavailable 503')
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
				print ('not found  -  X-Rate-Limit-Remaining" OR "X-Rate-Limit-Reset')
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
				print("ConnectionError:",e)
				time.sleep(60)
				continue
			if res.status_code == 503:
				# 503 : Service Unavailable
				if unavailableCnt > 10:
					raise Exception('Twitter API error %d' % res.status_code)
				unavailableCnt += 1
				print ('Service Unavailable 503')
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
		print ('\n       =====================')
		print ('	 == waiting %d sec ==' % seconds)
		print ('	 =====================')
		sys.stdout.flush()
		time.sleep(seconds + 10)  # 念のため + 10 秒

	def retweet(self, tweetId):
		unavailableCnt = 0
		url_fav = "https://api.twitter.com/1.1/favorites/create.json"
		params = {'id' : tweetId}
		while True:
			try:
				res = self.session.post(url_fav, params = params)
			except ConnectionError as e:
				print("ConnectionError:",e)
				time.sleep(60)
				continue
			if res.status_code == 503:
				if unavailableCnt > 10:
					#_log(tweetId,res.status_code)
					print(tweetId,res.status_code,res.text)
					break
				unavailableCnt += 1
				self.waitUntilReset(time.mktime(datetime.datetime.now().timetuple()) + 30)
				continue
			if res.status_code != 200:
				#_log(tweetId,res.status_code)
				print(tweetId,res.status_code,res.text)
			break
		url_rt = "https://api.twitter.com/1.1/statuses/retweet/%d.json"%tweetId
		unavailableCnt = 0
		while True:
			try:
				res = self.session.post(url_rt) # retweet実行
			except ConnectionError as e:
				print("ConnectionError:",e)
				time.sleep(60)
				continue
			if res.status_code == 503:
				# 503 : Service Unavailable
				if unavailableCnt > 10:
					#_log(tweetId,res.status_code)
					print(tweetId,res.status_code,res.text)
					break
				unavailableCnt += 1
				self.waitUntilReset(time.mktime(datetime.datetime.now().timetuple()) + 30)
				continue
			if res.status_code != 200:
				#_log(tweetId,res.status_code)
				print(tweetId,res.status_code,res.text)
			break

	def showStatus(self, repid):
		url_show = "https://api.twitter.com/1.1/statuses/show.json"
		params = {"id":repid}
		unavailableCnt = 0
		while True:
			try:
				res = self.session.get(url_show, params = params)
			except ConnectionError as e:
				print("ConnectionError:",e)
				time.sleep(60)
				continue
			if res.status_code == 503:
				if unavailableCnt > 10:
					#_log(tweetId,res.status_code)
					print("err05:",tweetId,res.status_code,res.text)
					break
				unavailableCnt += 1
				self.waitUntilReset(time.mktime(datetime.datetime.now().timetuple()) + 30)
				continue
			if res.status_code != 200:
				#_log(tweetId,res.status_code)
				print("err06:",tweetId,res.status_code,res.text)
			break
		return res

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
				print("ConnectionError:",e)
				time.sleep(60)
				continue
			if res.status_code == 503:
				# 503 : Service Unavailable
				if unavailableCnt > 10:
					#_log(self.screen,res.status_code)
					print(self.screen,res.status_code)
					break
				unavailableCnt += 1
				self.waitUntilReset(time.mktime(datetime.now().timetuple()) + 30)
				continue
			if res.status_code != 200:
				#_log(self.screen,res.status_code)
				print(self.screen,res.status_code)
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
				print("ConnectionError:",e)
				time.sleep(60)
				continue
			if res.status_code == 503:
				# 503 : Service Unavailable
				if unavailableCnt > 10:
					#_log(self.screen,res.status_code)
					print(self.screen,res.status_code)
					break
				unavailableCnt += 1
				self.waitUntilReset(time.mktime(datetime.now().timetuple()) + 30)
				continue
			if res.status_code != 200:
				#_log(self.screen,res.status_code)
				print(self.screen,res.status_code)
				self.checkLimit("users", "/users/show")
				if unavailableCnt > 10:
					break
				unavailableCnt += 1
				continue
			user = json.loads(res.text)
			return user
	
	def checkKeyword(self, keyword, timer, timer_sin):
		self.tl2json = []
		self.keyword = keyword
		self.timer = timer
		self.timer_sin = timer_sin
		for tweet in self.collect(total = 1000):
			unix_time = ((tweet['id'] >> 22) + 1288834974657) / 1000.0
			ts = datetime.fromtimestamp(unix_time)
			if self.timer_sin > ts:
				break
			if tweet['id'] in self.tl2json:
				continue
			if tweet['user']['id'] in self.flist_res:
				self.tl2json.append({'name':tweet['user']['name'][:10], 'screen':tweet['user']['screen_name'], 'id':tweet['id'], 'text':tweet['text'][:20],'fflag':True})
			else:
				self.tl2json.append({'name':tweet['user']['name'][:10], 'screen':tweet['user']['screen_name'], 'id':tweet['id'], 'text':tweet['text'][:20], 'fflag':False})

	def searchKeyword(self, keyword, total = 1000, onlyText = False, includeRetweet = False):
		self.tl2json = []
		self.keyword = keyword
		for tweet in self.collect(total , onlyText , includeRetweet):
			yield tweet

	def messageSent(self, send2id, send_text):
		self.send2id = send2id
		url_msg = 'https://api.twitter.com/1.1/direct_messages/events/new.json'
		headers = {'content-type': 'application/json'}
		payload = {"event":
			{"type": "message_create",
			"message_create": {
				"target": {"recipient_id": self.send2id},
				"message_data": {"text": send_text,}
			}}}
		payload = json.dumps(payload)
		unavailableCnt = 0
		while True:
			try:
				res = self.session.post(url_msg, headers=headers, data=payload)
			except ConnectionError as e:
				print("ConnectionError:",e)
				time.sleep(60)
				continue
			if res.status_code == 503:
				# 503 : Service Unavailable
				if unavailableCnt > 10:
					#_log(res.status_code)
					print(res.status_code,res.text)
					break
				unavailableCnt += 1
				self.waitUntilReset(time.mktime(datetime.now().timetuple()) + 30)
				continue
			if res.status_code != 200:
				#_log(res.status_code)
				print(res.status_code,res.text)
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
				print("ConnectionError:",e)
				time.sleep(60)
				continue
			if res.status_code == 503:
				# 503 : Service Unavailable
				if unavailableCnt > 10:
					raise Exception('Twitter API error %d' % res.status_code)
				unavailableCnt += 1
				print ('Service Unavailable 503')
				self.waitUntilReset(time.mktime(datetime.now().timetuple()) + 30)
				continue
			unavailableCnt = 0

			if res.status_code != 200:
				if "Not authorized." in res.text:
					break
				raise Exception('Twitter API error ',res.status_code,res.text)

			'''
			tweets = self.pickupTweet(json.loads(res.text))
			if len(tweets) == 0:
				# len(tweets) != params['count'] としたいが
				# count は最大値らしいので判定に使えない。
				# ⇒  "== 0" にする
				# https://dev.twitter.com/discussions/7513
				break
			'''

			for tweet_tl in json.loads(res.text):
				yield tweet_tl
			if "since_id" in params:
				params['since_id'] = tweet_tl['id'] + 1
			else:
				params['max_id'] = tweet_tl['id'] - 1
			

			# ヘッダ確認 （回数制限）
			# X-Rate-Limit-Remaining が入ってないことが稀にあるのでチェック
			if ('X-Rate-Limit-Remaining' in res.headers and 'X-Rate-Limit-Reset' in res.headers):
				if (int(res.headers['X-Rate-Limit-Remaining']) == 0):
					self.waitUntilReset(int(res.headers['X-Rate-Limit-Reset']))
					self.checkLimit("search", "/search/tweets")
			else:
				print ('not found  -  X-Rate-Limit-Remaining" OR "X-Rate-Limit-Reset')
				self.checkLimit("search", "/search/tweets")
			
			cnt += 1
			if cnt >= 100:
				break


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
				DL_URL = DL_URL + ":orig"
				ary.append({"fn":FILENAME,"url":DL_URL})
			if media["type"] == 'animated_gif':
				DL_URL = media["video_info"]["variants"][0]["url"]
				FILENAME = os.path.basename(DL_URL)
				ary.append({"fn":FILENAME,"url":DL_URL})
			if media["type"] == 'video':
				for i, var in enumerate(media["video_info"]["variants"]):
					if not "bitrate" in media["video_info"]["variants"][i]:
						media["video_info"]["variants"].pop(i)
				DL_URL = max(media["video_info"]["variants"], key=lambda d: d["bitrate"])["url"]
				if '?tag=' in DL_URL:
					DL_URL = DL_URL.rsplit("?", 1)[0]
				FILENAME = os.path.basename(DL_URL)
				ary.append({"fn":FILENAME,"url":DL_URL})
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
				print(e)
				time.sleep(60)
				continue
		break


def main():
	#dir = "/foo/var/"
	if os.path.dirname(sys.argv[0]):
		dir = os.path.dirname(sys.argv[0]) + "/"
	else:
		dir = os.getcwd() +"/"
	secret = "secret.json"
	
	if os.path.exists(dir + secret) == False:
		with open(dir + secret,"w") as f:
			pass
	with open(dir + secret) as f:
		try:
			secret = json.load(f)
		except ValueError:
			pass
	CK = secret["CK"]
	CS = secret["CS"]
	AT = secret["AT"]
	AS = secret["AS"]
	
	screen_name = ""
	user_id = ""
	keyword = ""
	JST = timezone(timedelta(hours=+9), 'JST')
	
	# インスタンス作成
	getter = TwetterObj(CK, CS, AT, AS)
	
	# フォローしている人のMediaをDownload
	if len(sys.argv) == 2:
		screen_name = sys.argv[1]
	else:
		print("please set screenname")
		sys.exit()
	user_id = getter.showUser(screen_name)["id"]
	## 鍵対策
	if os.path.exists(dir + "save.json"):
		with open(dir + "save.json") as save:
			try:
				save_data = json.load(save)	
			except ValueError:
				save_data = []
		for usr in save_data:
			if usr["user_id"] == user_id:
				AT = save_data["oauth_token"]
				AS = save_data["oauth_token_secret"]
	download_dir = dir + screen_name + "/"
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
	flist_res = getter.getFollowList(screen_name)
	for f in flist_res:
		FILEPATH = download_dir + f["screen_name"] + "/"
		if os.path.exists(FILEPATH) == False:
			os.makedirs(FILEPATH)
		last_id = max_id = ""
		if f["id"] in json_data:
			last_id = json_data[f["id"]]
		for twi in getter.checkTL(user_id = f["id"]):
			#def checkTL(self, user_id, include_rts = False, since_id = "", max_id = ""):
			if not max_id:
				max_id = twi["id"]
			if last_id == twi["id"]
				break
			ARY = pickupMedia(twi)
			if ARY is None:
				continue
			for content in ARY:
				downloadMedia(content["url"], FILEPATH, content["fn"])
		json_data[f["id"]] = max_id
	with open(download_dir + "db.json", "w") as save:
		json.dump(json_data,save)
	
	# キーワード検索してJSONに出力
	'''
	timer = datetime.now() + timedelta(minutes=55)
	timer_sin = datetime.now().replace(hour=0,minute=0,second=0) - timedelta(days=1)
	getter.checkKeyword(keyword, timer, timer_sin)
	if getter.tl2json:
		savefile = "/var/www/cgi-bin/log/" + datetime.now().strftime('%Y%m%d%H%M') + ".json"
		fileopen = open(savefile,"w+")
		json.dump(getter.tl2json,fileopen)
	'''
	
	# キーワード検索してMedia抽出
	'''
	for i in getter.searchKeyword(keyword):
		for j in pickupMedia(i):
			print(j)
	'''
	
	# キーワード画像検索してFAVRT/day
	'''
	cnt = 0
	for tweet in getter.collect(total = 1000):
		cnt += 1
		unix_time = ((tweet['id'] >> 22) + 1288834974657) / 1000.0
		ts = datetime.fromtimestamp(unix_time)
		if timer_sin > ts:
			break
		if "media" in tweet["entities"]:
			getter.retweet(tweet['id'])
		if tweet["in_reply_to_status_id_str"] is not None:
			reptweet = getter.showStatus(tweet["in_reply_to_status_id_str"])
			if "entities" in reptweet and "media" in reptweet["entities"]:
				getter.retweet(reptweet['id'])
		timer_now = datetime.now()
		if timer > timer_now and 95 < cnt:
			slt = timer - timer_now
			#slt = math.ceil(slt.total_seconds() / 60)
			time.sleep(slt.total_seconds())
		elif timer < timer_now:
			timer = timer_now + timedelta(minutes=55)
			cnt = 0
		else:
			time.sleep(30)
	'''
	
	# DM送る
	'''
	user_ids = []
	text_msg = ""
	for tl in getter.tl2json:
		if tl['fflag'] is True:
			text_msg = text_msg + "https://twitter.com/" + tl['screen'] + "/status/" + str(tl['id']) +"\n"
	if text_msg:
		for i in user_ids:
			getter.messageSent(i, send_text)
	'''
	

if __name__ == '__main__':
	main()
else:
	print("""class
	TwetterObj(CK, CS, AT, AS)

method
	collect(total = -1, onlyText = False, includeRetweet = False)
	checkLimit(arg1, arg2)	Get rate limits and usage applied to each Rest API endpoint
	waitUntilReset(reset)
	retweet(tweetId)
	showStatus(tweetId)		Return statuses-show response.
	getFollowList(screen_name)	Get follow "id" and "screen_name".
	checkKeyword(keyword, timer, timer_sin)		Append to self.tl2json list.
	searchKeyword(keyword, total = 1000, onlyText = False, includeRetweet = False)
		yield tweet.
	messageSent(user_id, send_text)
	checkTL(user_id, include_rts = False, since_id = "", max_id = "")

function
	pickupMedia(tweet)		yield DL_URL, FILENAME
	downloadMedia(DL_URL, FILEPATH, FILENAME)""")
