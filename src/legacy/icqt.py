# -*- coding: utf-8 -*-
# Copyright 2004-2006 Daniel Henninger <jadestorm@nc.rr.com>
# Licensed for distribution under the GPL version 2, check COPYING for details

from twisted.internet import protocol, reactor
from twisted.python import log
from tlib import oscar
from tlib import socks5
import config
import utils
from debug import LogEvent, INFO, WARN, ERROR
import lang
import re
import time
import datetime
import binascii
import md5
import locale
import struct



#############################################################################
# BOSConnection
#############################################################################
class B(oscar.BOSConnection):
	def __init__(self,username,cookie,oscarcon):
		self.chats = list()
		self.ssigroups = list()
		self.ssiiconsum = list()
		self.requesticon = {}
		self.awayResponses = {}
		self.oscarcon = oscarcon
		self.authorizationRequests = [] # buddies that need authorization
		self.oscarcon.bos = self
		self.session = oscarcon.session  # convenience
		self.capabilities = [oscar.CAP_ICON, oscar.CAP_UTF, oscar.CAP_ICQXTRAZ, oscar.CAP_SERV_REL, oscar.CAP_TYPING]
		if config.enableWebPresence:
			self.statusindicators = oscar.STATUS_WEBAWARE
		self.unreadmessages = 0
		if config.crossChat:
			self.capabilities.append(oscar.CAP_CROSS_CHAT)
		oscar.BOSConnection.__init__(self,username,cookie)
		if config.socksProxyServer and config.socksProxyPort:
			self.socksProxyServer = config.socksProxyServer
			self.socksProxyPort = config.socksProxyPort
		if config.icqPort:
			self.connectPort = config.icqPort

	def initDone(self):
		if not hasattr(self, "session") or not self.session:
			LogEvent(INFO, msg="No session!")
			return
		self.requestSelfInfo().addCallback(self.gotSelfInfo)
		#self.requestSelfInfo() # experimenting with no callback
		self.requestSSI().addCallback(self.gotBuddyList)
		if self.updateSelfXstatusOnStart:
			self.updateSelfXstatus()
		LogEvent(INFO, self.session.jabberID)

	def connectionLost(self, reason):
		message = "ICQ connection lost! Reason: %s" % reason
		if self.session:
			LogEvent(INFO, self.session.jabberID, message)
		try:
			self.oscarcon.alertUser(message)
		except:
			pass

		oscar.BOSConnection.connectionLost(self, reason)

		try:
			self.session.connectionLost()
		except:
			pass

	def gotUserInfo(self, id, type, userinfo):
		if userinfo:
			for i in xrange(len(userinfo)):
				try:
					userinfo[i] = userinfo[i].decode(self.userEncoding, 'strict')
				except (UnicodeError, LookupError):
					userinfo[i] = userinfo[i].decode('utf-8', 'replace')
		if self.oscarcon.userinfoCollection[id].gotUserInfo(id, type, userinfo):
			# True when all info packages has been received
			self.oscarcon.gotvCard(self.oscarcon.userinfoCollection[id])
			del self.oscarcon.userinfoCollection[id]

	def buddyAdded(self, uin):
		from glue import icq2jid
		for g in self.ssigroups:
			for u in g.users:
				if u.name == uin:
					if u.authorized:
						self.session.sendPresence(to=self.session.jabberID, fro=icq2jid(uin), show=None, ptype="subscribed")
						return

	def gotAuthorizationResponse(self, uin, success):
		from glue import icq2jid
		LogEvent(INFO, self.session.jabberID)
		if success:
			for g in self.ssigroups:
				for u in g.users:
					if u.name == uin:
						u.authorized = True
						u.authorizationRequestSent = False
						self.session.sendPresence(to=self.session.jabberID, fro=icq2jid(uin), show=None, ptype="subscribed")
						return
		else:
			for g in self.ssigroups:
				for u in g.users:
					if u.name == uin:
						u.authorizationRequestSent = False
			self.session.sendPresence(to=self.session.jabberID, fro=icq2jid(uin), show=None, status=None, ptype="unsubscribed")

	def gotAuthorizationRequest(self, uin):
		from glue import icq2jid
		LogEvent(INFO, self.session.jabberID)
		if self.settingsOptionEnabled('clist_deny_all_auth_requests'): # deny all auth requests
			self.sendAuthorizationResponse(uin, False, "Request denied")
		else:
			if not uin in self.authorizationRequests:
				self.authorizationRequests.append(uin)
				self.session.sendPresence(to=self.session.jabberID, fro=icq2jid(uin), ptype="subscribe")

	def youWereAdded(self, uin):
		from glue import icq2jid
		LogEvent(INFO, self.session.jabberID)
		self.session.sendPresence(to=self.session.jabberID, fro=icq2jid(uin), ptype="subscribe")

	def detectAdditionalNormalStatus(self, icqStatus):
		LogEvent(INFO, self.session.jabberID)

		anormal = None
		show = None
		if icqStatus in ('away', 'chat', 'dnd', 'xa'):
		  show = icqStatus
		elif icqStatus == 'busy':
		  show = 'dnd'
		elif icqStatus == 'depression':
		  anormal = 'anstatus_depression'
		elif icqStatus == 'evil':
		  anormal = 'anstatus_evil'
		elif icqStatus == 'home':
		  anormal = 'anstatus_at_home'
		elif icqStatus == 'work':
		  anormal = 'anstatus_at_work'
		elif icqStatus == 'lunch':
		  show = 'away'
		  anormal = 'anstatus_out_to_lunch'
		elif icqStatus == 'phone':
		  show = 'dnd'
		  anormal = 'anstatus_on_the_phone'

		return (show, anormal)
	
	def parseAndSearchForActivity(self, title):
		LogEvent(INFO, self.session.jabberID)
		for key in ACTIVITIES:
			subactivities = ACTIVITIES[key]
			for subkey in subactivities:
				if subkey != 'category':
					title_lo = title.lower().replace('_', ' ')
					native_lo = lang.get(subkey).lower().replace('_', ' ')
					intern_lo = ACTIVITIES[key][subkey].replace('_', ' ')
					if title_lo.find(intern_lo) != -1 or title_lo.find(native_lo) != -1:
						return [ACTIVITIES[key]['category'], ACTIVITIES[key][subkey]]
			if 'category' in subactivities:
				title_lo = title.lower().replace('_', ' ')
				native_lo = lang.get(key).lower().replace('_', ' ')
				intern_lo = key.replace('_', ' ')
				if title_lo.find(intern_lo) != -1 or title_lo.find(native_lo) != -1:
					return [ACTIVITIES[key]['category'], 'None']
		return [None, None]
	
	def parseAndSearchForMood(self, title):
		LogEvent(INFO, self.session.jabberID)
		for key in MOODS:
			title_lo = title.lower().replace('_', ' ')
			native_lo = lang.get(key).lower().replace('_', ' ')
			intern_lo = MOODS[key].replace('_', ' ')
			if title_lo.find(intern_lo) != -1 or title_lo.find(native_lo) != -1:
				return MOODS[key]
		return None
		
	def sendPersonalEvents(self, buddyjid, mood, s_mood, act, s_act, subact, s_subact, text, s_text, usetune, s_usetune):
		LogEvent(INFO, self.session.jabberID)
		a_mood = None 
		a_act = None
		a_subact = None
		a_usetune =None
		if buddyjid: # for user
			to = self.session.jabberID
			fro = buddyjid
		else: # for transport
			to = self.session.jabberID
			fro = config.jid	
		# sending mood
		if int(self.settingsOptionEnabled('user_mood_receiving')):
			if mood and (mood != s_mood or (s_mood and text != s_text)): # if need set other mood or other text
				self.session.pytrans.pubsub.sendMood(to=to, fro=fro, mood=mood, text=text) # send mood
				a_mood = mood
			elif s_mood and not mood: # mood was set and not set now
				self.session.pytrans.pubsub.sendMood(to=to, fro=fro, action='retract') # retract mood
		# sending activity
		if int(self.settingsOptionEnabled('user_activity_receiving')):
			if act and (not (act == s_act and subact == s_subact) or (s_act and text != s_text)): # if need set other act/subact or other text
				self.session.pytrans.pubsub.sendActivity(to=to, fro=fro, act=act, subact=subact, text=text) # send act
				a_act = act
				a_subact = subact
			elif s_act and not act or s_subact and not subact: # act or subact was set and not set now
				self.session.pytrans.pubsub.sendActivity(to=to, fro=fro, action='retract') # retract activity
		# sending tune
		if int(self.settingsOptionEnabled('user_tune_receiving')):
			musicinfo = utils.parseTune(text)
			if usetune and ((s_usetune and text != s_text) or not s_usetune):
				self.session.pytrans.pubsub.sendTune(to=to, fro=fro, musicinfo=musicinfo) # send tune
				a_usetune = usetune
			elif s_usetune and not usetune: # tune was set and not set now
				self.session.pytrans.pubsub.sendTune(to=to, fro=fro, stop=True) # stop tune
		# returns info about personal events, which were really sent
		return a_mood, a_act, a_subact, a_usetune
					
	def sendPersonalEventsStop(self, buddyjid, s_mood, s_act, s_subact, s_usetune):
		LogEvent(INFO, self.session.jabberID)
		if buddyjid: # for user
			to = self.session.jabberID
			fro = buddyjid
		else: # for transport
			to = self.session.jabberID
			fro = config.jid
		# send retract or stop
		if s_mood and int(self.settingsOptionEnabled('user_mood_receiving')):
			self.session.pytrans.pubsub.sendMood(to=to, fro=fro, action='retract') # retract mood
		if (s_act or s_subact) and int(self.settingsOptionEnabled('user_activity_receiving')):
			self.session.pytrans.pubsub.sendActivity(to=to, fro=fro, action='retract') # retract activity
		if s_usetune and int(self.settingsOptionEnabled('user_tune_receiving')):
			self.session.pytrans.pubsub.sendTune(to=to, fro=fro, stop=True) # stop tune

	def updateBuddy(self, user, selfcall = False):
		from glue import icq2jid
		LogEvent(INFO, self.session.jabberID)
		
		buddyjid = icq2jid(user.name)
                c = self.session.contactList.findContact(buddyjid)
                if not c: return

		ptype = None
		
		show, anstatus = self.detectAdditionalNormalStatus(user.icqStatus)
		status = user.status
		encoding = user.statusencoding
		url = user.url
		if encoding and status:
			if encoding == "utf-16be":
				status = status.decode("utf-16be", "replace")
			if encoding == "unicode":
				status = status.decode("utf-16be", "replace")
			elif encoding == "iso-8859-1":
				status = status.decode("iso-8859-1", "replace")
			elif encoding == self.userEncoding:
				status = status.decode(self.userEncoding, "replace")
			elif encoding == config.encoding:
				status = status.decode(config.encoding, "replace")
			elif encoding == "icq51pseudounicode":
				# XXX: stupid Unicode test
				# XXX: ICQ 5.1 CZ clients seem to wrap UTF-8 (assuming it's CP1250) into UTF-16
				#      while e.g. Miranda sends it as ascii
				##if len(status) != 0 and ord(status[0]) == 0:
				if len(status) != 0:
					status = str(status)
					try:
						status1 = status.decode('utf-16be', 'strict')
						status1 = status1.encode('cp1250', 'strict')
						status1 = status1.decode('utf-8', 'strict')
						status = status1
					except:
						try:
							status1 = status.decode('utf-8', 'strict')
							status = status1
						except:
							try:
								status1 = status.decode(config.encoding, "strict")
								status = status1
							except:
								#status = "Wrong encoding:" + repr(status)
								status = str(status).decode("iso-8859-1", "replace")
		elif status:
			# this is a fallback solution in case that the client status encoding has not been extracted, to avoid raising an exception
			status = status.decode('utf-8', 'replace')
			LogEvent(WARN, self.session.jabberID, "Unknown status message encoding for %s" % user.name)
		else: # no status text
		    pass
		status = oscar.dehtml(status) # Removes any HTML tags

		if user.iconmd5sum != None and not config.disableAvatars and not config.avatarsOnlyOnChat:
			if self.oscarcon.legacyList.diffAvatar(user.name, md5Hash=binascii.hexlify(user.iconmd5sum)):
				LogEvent(INFO, self.session.jabberID, "Retrieving buddy icon for %s" % user.name)
				self.retrieveBuddyIconFromServer(user.name, user.iconmd5sum, user.icontype).addCallback(self.gotBuddyIconFromServer)
			else:
				LogEvent(INFO, self.session.jabberID, "Buddy icon is the same, using what we have for %s" % user.name)
			
		if user.caps:
			self.oscarcon.legacyList.setCapabilities(user.name, user.caps)
		if (user.customStatus and len(user.customStatus) > 0) or anstatus:
			self.oscarcon.legacyList.setCustomStatus(user.name, user.customStatus)
		else:
			mask = ('mood', 'activity', 'subactivity', 'text', 'usetune') # keep values for mood/activity
			self.oscarcon.legacyList.delCustomStatus(user.name, savemask=mask)
			
		LogEvent(INFO, self.session.jabberID, "Status message: %s" % status)
		
		if config.xstatusessupport:		
			if int(self.settingsOptionValue('xstatus_receiving_mode')) != 0:
				status5 = '' # status for ICQ5.1 mode
				status6 = '' # status for ICQ6 mode
				x_status_name = None
				requestForXStatus = True # need request for x-status details
				# icon
				if int(self.settingsOptionValue('xstatus_receiving_mode')) == 1 and int(self.settingsOptionEnabled('xstatus_option_smooth')) == 0: # in ICQ5.1 strict mode
					if 'icqmood' in user.customStatus: # ICQ6 mood
						del user.customStatus['icqmood'] # don't needed
				if int(self.settingsOptionValue('xstatus_receiving_mode')) == 2 and int(self.settingsOptionEnabled('xstatus_option_smooth')) == 0: # in ICQ6 strict mode
					if 'x-status' in user.customStatus: # ICQ5.1 x-status icon
						del user.customStatus['x-status'] # don't needed
				# get x-status name
				if int(self.settingsOptionValue('xstatus_receiving_mode')) == 2: # in ICQ 6 mode
					x_status_name = self.oscarcon.getXStatus(user.name, True)
				else:
					x_status_name = self.oscarcon.getXStatus(user.name)
				# text	
				if int(self.settingsOptionValue('xstatus_receiving_mode')) == 2:
					status6 = status
				if int(self.settingsOptionValue('xstatus_receiving_mode')) == 3: # mixed
					if 'icqmood' in user.customStatus and status != '': # already have icon and text of a status
						requestForXStatus = False
						status6 = status
					if selfcall == True:
						status6 = ''
				if int(self.settingsOptionValue('xstatus_receiving_mode')) in (1,3):
					x_status_title, x_status_desc = self.oscarcon.getXStatusDetails(user.name)
					if x_status_title != '' and x_status_desc != '':
						if x_status_title == ' ':
							status5 = x_status_desc
						elif x_status_desc == ' ':
							status5 = x_status_title
						else:
							status5 = x_status_title + ' ' + x_status_desc
					elif x_status_title == '' and x_status_desc != '':
						status5 = x_status_desc
					elif x_status_title != '' and x_status_desc == '':
						status5 = x_status_title
				# need choose status now
				if int(self.settingsOptionValue('xstatus_receiving_mode')) == 1:
					status = status5
				if int(self.settingsOptionValue('xstatus_receiving_mode')) == 2:
					status = status6
				if int(self.settingsOptionValue('xstatus_receiving_mode')) == 3:
					if len(status5) > len (status6):
						status = status5
					else:
						status = status6
				# displaying status icon as mood/activity
				mood = None
				act = None
				subact = None
				text = None
				usetune = False
				
				s_mood, s_act, s_subact, s_text, s_usetune = self.oscarcon.getPersonalEvents(user.name) # get Personal Events
				# ok. displaying via PEP enabled
				if self.settingsOptionEnabled('xstatus_display_text_as_PEP') or self.settingsOptionEnabled('xstatus_display_icon_as_PEP'):
					# mapping x-status -> mood/activity
					if self.settingsOptionEnabled('xstatus_display_icon_as_PEP'):
						if x_status_name != '' or anstatus: # x-status or additional normal status presents 
							mood_a = None
							act_a = None
							subact_a = None
							if anstatus in AN_STATUS_MAP:
								mood_a, act_a, subact_a = AN_STATUS_MAP[anstatus]
							if x_status_name in X_STATUS_MAP and x_status_name != 'xstatus_listening_to_music':	
								mood, act, subact = X_STATUS_MAP[x_status_name]
							elif x_status_name == 'xstatus_listening_to_music':
								usetune = True
						
							if not mood and mood_a: # if no mood from x-status
								mood = mood_a # get mood from additional normal status
							if not act and act_a: # if no activity from x-status
								act = act_a # get activity
								subact = subact_a # get subactivity
					# status text parsing and displaying as mood/activity
					if self.settingsOptionEnabled('xstatus_display_text_as_PEP'):
						if status != '' and int(self.settingsOptionValue('xstatus_receiving_mode')) in (2,3):
							mood_p = None
							act_p = None
							subact_p = None
									
							mood_p = self.parseAndSearchForMood(status)
							act_p, subact_p = self.parseAndSearchForActivity(status)
							
							if mood_p: # mood found in status text
								mood = mood_p # use mood from text
							if act_p: # activity found in status text
								act = act_p # use activity from text
								subact = subact_p # and subactivity from text too
					# additional text for mood/activity
					if status6 != '':
						text = status6
					elif status5 != '':
						text = status5
					# send personal events	
					mood, act, subact, usetune = self.sendPersonalEvents(buddyjid, mood, s_mood, act, s_act, subact, s_subact, text, s_text, usetune, s_usetune)	
				else:  # displaying disabled
					self.sendPersonalEventsStop(buddyjid, s_mood, s_act, s_subact, s_usetune)
					
				# no icon in roster. Impossible recognize or displaying disabled 
				if not mood and not act and not subact and not usetune: 
					if int(self.settingsOptionValue('xstatus_receiving_mode')) in (1,2,3):
						if status == '' and x_status_name != '':
							status = lang.get(x_status_name) # write standart name
						elif status != '' and x_status_name != '':
							if status != lang.get(x_status_name):
								status = lang.get(x_status_name) + ': ' + status # or add it as prefix
						if anstatus and anstatus != '':
							if status != '':
								status = '\n' + status
							status = lang.get(anstatus) + status
				
				self.oscarcon.setPersonalEvents(user.name, mood, act, subact, text, usetune) # set personal events
				# need send request for x-status details	
				if selfcall == False and requestForXStatus == True:
					if int(self.settingsOptionValue('xstatus_receiving_mode')) in (1,3):
						self.sendXstatusMessageRequestWithDelay(user.name) # request Xstatus message
			else:
				# x-status support disabled
				status = ''
				
		requestForAwayMsg = False
		if user.flags.count("away"):
			if int(self.settingsOptionEnabled('away_messages_receiving')):
				requestForAwayMsg = True
				
		if requestForAwayMsg == True:
			self.getAway(user.name).addCallback(self.sendAwayPresence, user, show, status)	
		else:
			if user.idleTime:
				if user.idleTime>60*24:
					idle_time = "Idle %d days"%(user.idleTime/(60*24))
					if not show: show = "xa"
				elif user.idleTime>60:
					idle_time = "Idle %d hours"%(user.idleTime/(60))
					if not show: show = "away"
				else:
					idle_time = "Idle %d minutes"%(user.idleTime)
				if status and status != '' and status != ' ':
					status="%s\n%s"%(idle_time,status)
				else:
					status=idle_time
					
			c.updatePresence(show=show, status=status, ptype=ptype, url=url)
			self.oscarcon.legacyList.updateSSIContact(user.name, presence=ptype, show=show, status=status, ipaddr=user.icqIPaddy, lanipaddr=user.icqLANIPaddy, lanipport=user.icqLANIPport, icqprotocol=user.icqProtocolVersion, url=url)

	def gotBuddyIconFromServer(self, (contact, icontype, iconhash, iconlen, icondata)):
		if config.disableAvatars: return
		LogEvent(INFO, self.session.jabberID, "%s: hash: %s, len: %d" % (contact, binascii.hexlify(iconhash), iconlen))
		if iconlen > 0 and iconlen != 90: # Some ICQ clients send crap
			self.oscarcon.legacyList.updateAvatar(contact, icondata, md5Hash=iconhash)

	def offlineBuddy(self, user):
		from glue import icq2jid 
		LogEvent(INFO, self.session.jabberID, user.name)
		buddyjid = icq2jid(user.name)
                c = self.session.contactList.findContact(buddyjid)
                if not c: return
		show = None
		status = None
		ptype = "unavailable"
		c.updatePresence(show=show, status=status, ptype=ptype)
		self.oscarcon.legacyList.updateSSIContact(user.name, presence=ptype, show=show, status=status)
		
		s_mood, s_act, s_subact, s_text, s_usetune = self.oscarcon.getPersonalEvents(user.name) # get Personal Events
		self.sendPersonalEventsStop(buddyjid, s_mood, s_act, s_subact, s_usetune) # stop them
		self.oscarcon.legacyList.delCustomStatus(user.name) # del custom status struct for user
		self.oscarcon.setPersonalEvents(user.name, None, None, None) # reset personal events struct
		self.oscarcon.legacyList.delUserVars(user.name) # del custom user vars

	def receiveMessage(self, user, multiparts, flags, delay=None):
		from glue import icq2jid

		LogEvent(INFO, self.session.jabberID, "%s %s %s" % (user.name, multiparts, flags))
		sourcejid = icq2jid(user.name)
		if len(multiparts) == 0:
			return # no data, illegal formed message
		if len(multiparts[0]) >= 1:
			text = multiparts[0][0]
		if len(multiparts[0]) > 1:
			if multiparts[0][1] == 'unicode':
				encoding = 'utf-16be'
			elif multiparts[0][1] == 'utf8':
				encoding = 'utf-8'
			elif multiparts[0][1] == 'custom': # can be any
				encoding = utils.guess_encoding_by_decode(text, self.userEncoding, 'minimal')[1] # try guess
			else:
				encoding = config.encoding
		else:
			encoding = self.userEncoding
		LogEvent(INFO, self.session.jabberID, "Using encoding %s" % (encoding))
		text = text.decode(encoding, "replace")
		xhtml = utils.prepxhtml(text)
		if not user.name[0].isdigit():
			text = oscar.dehtml(text)
		text = text.strip()
		mtype = "chat"
		if "auto" in flags:
			mtype = "headline"
 
 		offlinemessage = False
	    	for flag in flags:	
			if flag == 'offline':
				offlinemessage = True
		if offlinemessage == False:
			delay = None # Send timestamp to user if offline message

		if not (self.settingsOptionEnabled('autoanswer_enable') and self.settingsOptionEnabled('autoanswer_hide_dialog')): # send incoming message to jabber client
			self.session.sendMessage(to=self.session.jabberID, fro=sourcejid, body=text, mtype=mtype, delay=delay, xhtml=xhtml)
		self.session.pytrans.serviceplugins['Statistics'].stats['IncomingMessages'] += 1
		self.session.pytrans.serviceplugins['Statistics'].sessionUpdate(self.session.jabberID, 'IncomingMessages', 1)
		if self.settingsOptionEnabled('autoanswer_enable'):
			if self.settingsOptionExists('autoanswer_text'): # custom text
				autoanswer_text = self.settingsOptionValue('autoanswer_text')
			else: # text by default
				autoanswer_text = lang.get('autoanswer_text_content')
			if not self.settingsOptionEnabled('autoanswer_hide_dialog'): # send autoanswer reply to user
				self.session.sendMessage(to=self.session.jabberID, fro=sourcejid, body='%s %s' % (lang.get('autoanswer_prefix'), autoanswer_text), mtype=mtype, delay=delay, xhtml=xhtml)
			self.sendMessage(user.name, autoanswer_text) # send auto-answer text to contact
		if not config.disableAwayMessage and self.awayMessage and not "auto" in flags:
			if not self.awayResponses.has_key(user.name) or self.awayResponses[user.name] < (time.time() - 900):
				#self.sendMessage(user.name, "Away message: "+self.awayMessage.encode("iso-8859-1", "replace"), autoResponse=1)
				self.sendMessage(user.name, "Away message: "+self.awayMessage, autoResponse=1)
				self.awayResponses[user.name] = time.time()

		if "icon" in flags and not config.disableAvatars:
			if self.oscarcon.legacyList.diffAvatar(user.name, numHash=user.iconcksum):
				LogEvent(INFO, self.session.jabberID, "User %s has a buddy icon we want, will ask for it next message." % user.name)
				self.requesticon[user.name] = 1
			else:
				LogEvent(INFO, self.session.jabberID, "User %s has a icon that we already have." % user.name)

		if "iconrequest" in flags and hasattr(self.oscarcon, "myavatar") and not config.disableAvatars:
			LogEvent(INFO, self.session.jabberID, "User %s wants our icon, so we're sending it." % user.name)
			icondata = self.oscarcon.myavatar
			self.sendIconDirect(user.name, icondata, wantAck=1)
			
	def receiveReceiptMsgReceived(self, user, cookie):
		LogEvent(INFO, self.session.jabberID) # legacy client received own message
		msg_query = self.oscarcon.getUserVarValue(user, 'wait_for_confirm_msg_query')
		if len(msg_query):
			if cookie in msg_query:
				jabber_mid, resource, s_time = msg_query[cookie] # message id, resource and time of sending
				from glue import icq2jid
				sourcejid = icq2jid(user)
				self.session.sendMessage(to=self.session.jabberID + '/' + resource, fro=sourcejid, receipt=True, mID=jabber_mid) # send confirmation to jabber client
				uvars = {}
				uvars['wait_for_confirm_msg_query'] = msg_query # update query
				del msg_query[cookie] # delete cookie - id from query
				self.oscarcon.legacyList.setUserVars(user, uvars) # update user's vars

	def receiveWarning(self, newLevel, user):
		LogEvent(INFO, self.session.jabberID)
		#debug.log("B: receiveWarning [%s] from %s" % (newLevel,hasattr(user,'name') and user.name or None))

	def receiveTypingNotify(self, type, user):
		from glue import icq2jid
		LogEvent(INFO, self.session.jabberID)
		#debug.log("B: receiveTypingNotify %s from %s" % (type,hasattr(user,'name') and user.name or None))
		sourcejid = icq2jid(user.name)
		if type == "begin":
			self.session.sendTypingNotification(to=self.session.jabberID, fro=sourcejid, typing=True)
			self.session.sendChatStateNotification(to=self.session.jabberID, fro=sourcejid, state="composing")
		elif type == "idle":
			self.session.sendTypingNotification(to=self.session.jabberID, fro=sourcejid, typing=False)
			self.session.sendChatStateNotification(to=self.session.jabberID, fro=sourcejid, state="paused")
		elif type == "finish":
			self.session.sendTypingNotification(to=self.session.jabberID, fro=sourcejid, typing=False)
			self.session.sendChatStateNotification(to=self.session.jabberID, fro=sourcejid, state="active")

	def errorMessage(self, message):
		tmpjid = config.jid
		if self.session.registeredmunge:
			tmpjid = tmpjid + "/registered"
		self.session.sendErrorMessage(to=self.session.jabberID, fro=tmpjid, etype="cancel", condition="recipient-unavailable",explanation=message)

	def receiveSendFileRequest(self, user, file, description, cookie):
		LogEvent(INFO, self.session.jabberID)

	def emailNotificationReceived(self, addr, url, unreadnum, hasunread):
		LogEvent(INFO, self.session.jabberID)
		#debug.log("B: emailNotificationReceived %s %s %d %d" % (addr, url, unreadnum, hasunread))
		if unreadnum > self.unreadmessages:
			diff = unreadnum - self.unreadmessages
			self.session.sendMessage(to=self.session.jabberID, fro=config.jid, body=lang.get("icqemailnotification", config.jid) % (diff, addr, url), mtype="headline")
		self.unreadmessages = unreadnum


	# Callbacks
	def sendAwayPresence(self, msg, user, show, pstatus):
		from glue import icq2jid
		buddyjid = icq2jid(user.name)
		LogEvent(INFO, self.session.jabberID)

		c = self.session.contactList.findContact(buddyjid)
		if not c: return
		
		ptype = None
		idleTime = 0
		status = None
		url = None
		
		if msg[0] and msg[1] and len(msg[0]) == 4 and len(msg[1]) == 2: # online since time and idle time
			onlineSince = datetime.datetime.utcfromtimestamp(struct.unpack('!I',msg[0])[0])
			log.msg('User %s online since %sZ' % (user.name, onlineSince.isoformat()))
			idleTime = struct.unpack('!H',msg[1])[0]
			log.msg('User %s idle %s minutes' % (user.name, idleTime))
		else:
			status = msg[1]
			url = user.url

			if status != None:
				charset = "iso-8859-1"
				m = None
				if msg[0]:
					m = re.search('charset="(.+)"', msg[0])
				if m != None:
					charset = m.group(1)
					if charset == 'unicode-2-0':
						charset = 'utf-16be'
					elif charset == 'utf-8': pass
					elif charset == "us-ascii":
						charset = "iso-8859-1"
					elif charset == "iso-8859-1": pass
					elif charset == self.userEncoding: pass
					else:
						LogEvent(INFO, self.session.jabberID, "Unknown charset (%s) of buddy's away message" % msg[0]);
						charset = config.encoding
						status = msg[0] + ": " + status
	
				try:
					status = status.decode(charset, 'strict')
				except:
					pass
				try:
					status1 = status.encode(config.encoding, 'strict')
					status = status1.decode('utf-8', 'strict')
				except:
					if ord(status[0]) == 0 and ord(status[len(status)-1]) == 0:
						status = str(status[1:len(status)-1])
					try :
						status = str(status).decode('utf-8', 'strict')
					except:
						try:
							status = str(status).decode(config.encoding, 'strict')
						except:
							status = "Status decoding failed: " + status
				try:
					utfmsg = unicode(msg[0], errors='replace')
				except:
					utfmsg = msg[0]
				status = oscar.dehtml(status)
				LogEvent(INFO, self.session.jabberID, "Away (%s, %s) message %s" % (charset, utfmsg, status))
	
			if status == "Away" or status=="I am currently away from the computer." or status=="I am away from my computer right now.":
				status = ""
				
			if user.idleTime:
				idleTime = user.idleTime
				
		if idleTime:
			if idleTime>60*24:
				idle_time = "Idle %d days"%(idleTime/(60*24))
			elif idleTime>60:
				idle_time = "Idle %d hours"%(idleTime/(60))
			else:
				idle_time = "Idle %d minutes"%(idleTime)
			if status and status != '' and status != ' ':
				status="%s\n%s"%(idle_time,status)
			else:
				status=idle_time

		if status:
			if pstatus:
				status = status + '\n' + pstatus
		else:
			status = pstatus

		c.updatePresence(show=show, status=status, ptype=ptype)
		self.oscarcon.legacyList.updateSSIContact(user.name, presence=ptype, show=show, status=status, ipaddr=user.icqIPaddy, lanipaddr=user.icqLANIPaddy, lanipport=user.icqLANIPport, icqprotocol=user.icqProtocolVersion, url=url)

	def gotSelfInfo(self, user):
		LogEvent(INFO, self.session.jabberID)
		self.name = user.name

	def receivedSelfInfo(self, user):
		LogEvent(INFO, self.session.jabberID)
		self.name = user.name

	def receivedIconUploadRequest(self, iconhash):
		if config.disableAvatars: return
		LogEvent(INFO, self.session.jabberID, "%s" % binascii.hexlify(iconhash))
		if hasattr(self.oscarcon, "myavatar"):
			LogEvent(INFO, self.session.jabberID, "I have an icon, sending it on, %d" % len(self.oscarcon.myavatar))
			self.uploadBuddyIconToServer(self.oscarcon.myavatar, len(self.oscarcon.myavatar)).addCallback(self.uploadedBuddyIconToServer)
			#del self.oscarcon.myavatar

	def receivedIconDirect(self, user, icondata):
		if config.disableAvatars: return
		LogEvent(INFO, self.session.jabberID, "%s [%d]" % (user.name, user.iconlen))
		if user.iconlen > 0 and user.iconlen != 90: # Some ICQ clients send crap
			self.oscarcon.legacyList.updateAvatar(user.name, icondata, numHash=user.iconcksum)

	def uploadedBuddyIconToServer(self, iconchecksum):
		LogEvent(INFO, self.session.jabberID, "%s" % (iconchecksum))

	def readGroup(self, memberlist, parent=None):
		for member in memberlist:
			if isinstance(member, oscar.SSIGroup):
				LogEvent(INFO, self.session.jabberID, "Found group %s" % (member.name))
				self.ssigroups.append(member)
				self.readGroup(member.users, parent=member)
			elif isinstance(member, oscar.SSIBuddy):
				if member.nick:
					try:
						unick, uenc = utils.guess_encoding(member.nick, self.userEncoding, 'minimal', mode=2) # attempt to decode
					except (UnicodeError, LookupError): # no, error occured
						unick = member.nick.encode('utf-8', 'replace') # convert to utf-8
				else:
					unick = None
				if parent:
					LogEvent(INFO, self.session.jabberID, "Found user %r (%r) from group %r" % (member.name, unick, parent.name))
				else:
					LogEvent(INFO, self.session.jabberID, "Found user %r (%r) from master group" % (member.name, unick))
				self.oscarcon.legacyList.updateSSIContact(member.name, nick=unick)
				if member.name[0].isdigit() and (not member.nick or member.name == member.nick):
					# Hrm, lets get that nick
					self.getnicknames.append(member.name)
			else:
				LogEvent(INFO, self.session.jabberID, "Found unknown SSI entity: %r" % member)
			
	def gotBuddyList(self, l):
		LogEvent(INFO, self.session.jabberID, "%s" % (str(l)))
		self.getnicknames = list()
		if l is not None and l[0] is not None:
			self.readGroup(l[0])
		if l is not None and l[5] is not None:
			for i in l[5]:
				LogEvent(INFO, self.session.jabberID, "Found icon %s" % (str(i)))
				self.ssiiconsum.append(i)
		self.activateSSI()
		if l is not None and l[8] is not None and l[3] != "denysome":
			LogEvent(INFO, self.session.jabberID, "Permissions not set in a compatible manner on SSI, switching to 'deny some'")
			l[8].permitMode = oscar.AIM_SSI_PERMDENY_DENY_SOME
			self.startModifySSI()
			self.modifyItemSSI(l[8])
			self.endModifySSI()
		self.setProfile(self.session.description)
		self.setIdleTime(0)
		self.clientReady()
		if not config.disableMailNotifications:
			self.activateEmailNotification()
		self.session.ready = True
		tmpjid=config.jid
		if self.session.registeredmunge:
			tmpjid=config.jid+"/registered"
		if self.session.pytrans:
			self.session.sendPresence(to=self.session.jabberID, fro=tmpjid, show=self.oscarcon.savedShow, status=self.oscarcon.savedFriendly, url=self.oscarcon.savedURL)
		if not self.oscarcon.savedShow:
			#self.oscarcon.setBack(self.oscarcon.savedFriendly)
			self.oscarcon.setAway() # reset away message
		else:
			self.oscarcon.setAway(self.oscarcon.savedFriendly) # set away message
		if int(self.settingsOptionValue('xstatus_sending_mode')) == 1: # in ICQ5.1 mode
			self.setExtendedStatusRequest(message='', setmsg=True) # reset ICQ6 status
		if hasattr(self.oscarcon, "myavatar") and not config.disableAvatars:
			self.oscarcon.changeAvatar(self.oscarcon.myavatar)
		self.oscarcon.setICQStatus(self.oscarcon.savedShow)
		self.requestOffline()
		# Ok, lets get those nicknames.
		for n in self.getnicknames:
			self.getShortInfo(n).addCallback(self.gotNickname, n)

	def gotNickname(self, (nick, first, last, email), uin):
		LogEvent(INFO, self.session.jabberID)
		if nick:
			try: # may be
				unick, uenc = utils.guess_encoding(nick, self.userEncoding, 'minimal', mode=2) # attempt to decode
			except (UnicodeError, LookupError): # no
				unick = nick.encode('utf-8', 'replace') # convert to utf-8
			LogEvent(INFO, self.session.jabberID, "Found a nickname, lets update.")
			self.oscarcon.legacyList.updateNickname(uin, unick)

	def warnedUser(self, oldLevel, newLevel, username):
		LogEvent(INFO, self.session.jabberID)
		
	def setStatusIconForTransport(self, reset=False):
		# it's undocumented feature of Gajim seems. In any case it's looks fine
		LogEvent(INFO, self.session.jabberID)
		
		mood = None
		act = None
		subact = None
		text = None
		usetune = False
		
		s_mood, s_act, s_subact, s_text, s_usetune = self.oscarcon.getSelfPersonalEvents() # get Personal Events
		
		if config.xstatusessupport and int(self.settingsOptionValue('xstatus_sending_mode')) != 0 and self.settingsOptionEnabled('xstatus_icon_for_transport'): # possible show it
			x_status_name = ''
			if 'x-status name' in self.selfCustomStatus:
				x_status_name = self.selfCustomStatus['x-status name']
			status = ''
			if int(self.settingsOptionValue('xstatus_sending_mode')) == 1:
				x_status_title = ''
				x_status_desc = ''
				if 'x-status title' in self.selfCustomStatus:
					x_status_title = self.selfCustomStatus['x-status title']
				if 'x-status desc' in self.selfCustomStatus:
					x_status_desc = self.selfCustomStatus['x-status desc']
				if x_status_title != '' and x_status_desc != '':
					if x_status_title == ' ':
						status = x_status_desc
					elif x_status_desc == ' ':
						status = x_status_title
					else:
						status = x_status_title + ' ' + x_status_desc
				elif x_status_title == '' and x_status_desc != '':
					status = x_status_desc
				elif x_status_title != '' and x_status_desc == '':
					status = x_status_title
			if int(self.settingsOptionValue('xstatus_sending_mode')) in (2,3):
				if 'avail.message' in self.selfCustomStatus:
					status = self.selfCustomStatus['avail.message']
	
			mood_p = None
			act_p = None
			subact_p = None
	
			if x_status_name in X_STATUS_MAP and x_status_name != 'xstatus_listening_to_music':	
				mood, act, subact = X_STATUS_MAP[x_status_name]
			elif x_status_name == 'xstatus_listening_to_music':
				usetune = True
			mood_p = self.parseAndSearchForMood(status)
			act_p, subact_p = self.parseAndSearchForActivity(status)
			if status != '':
				text = status
				
			if mood_p: # mood found in status text
				mood = mood_p # use mood from text
			if act_p: # activity found in status text
				act = act_p # use activity from text
				subact = subact_p # and subactivity from text too
				
			mood, act, subact, usetune = self.sendPersonalEvents(None, mood, s_mood, act, s_act, subact, s_subact, text, s_text, usetune, s_usetune)
		else:
			self.sendPersonalEventsStop(None, s_mood, s_act, s_subact, s_usetune)
			
		self.oscarcon.setSelfPersonalEvents(mood, act, subact, text, usetune) # set personal events



#############################################################################
# Oscar Authenticator
#############################################################################
class OA(oscar.OscarAuthenticator):
	def __init__(self,username,password,oscarcon,deferred=None,icq=1):
		self.oscarcon = oscarcon
		self.BOSClass = B
		oscar.OscarAuthenticator.__init__(self,username,password,deferred,icq)

	def connectToBOS(self, server, port):
		if config.socksProxyServer:
			c = socks5.ProxyClientCreator(reactor, self.BOSClass, self.username, self.cookie, self.oscarcon)
			return c.connectSocks5Proxy(server, port, config.socksProxyServer, config.socksProxyPort, "OABOS")
		else:
			c = protocol.ClientCreator(reactor, self.BOSClass, self.username, self.cookie, self.oscarcon)
			return c.connectTCP(server, port)

#	def connectionLost(self, reason):
#		message = "ICQ connection lost! Reason: %s" % reason
#		try:
#			LogEvent(INFO, self.session.jabberID, message)
#		except:
#			pass
#
#		try:
#			self.oscarcon.alertUser(message)
#		except:
#			pass
#
#		oscar.OscarConnection.connectionLost(self, reason)
#
#		try:
#			self.oscarcon.session.removeMe()
#		except:
#			pass

# mapping x-statuses on moods and activities
X_STATUS_MAP = dict([
	('xstatus_angry', ['angry', None, None]),
	('xstatus_taking_a_bath', [None, 'grooming', 'taking_a_bath']),
	('xstatus_tired', ['stressed', None, None]),
	('xstatus_party', [None, 'relaxing', 'partying']),
	('xstatus_drinking_beer', [None, 'drinking', 'having_a_beer']),
	('xstatus_thinking', ['serious', None, None]),
	('xstatus_eating', [None, 'eating', None]),
	('xstatus_watching_tv', [None, 'relaxing', 'watching_tv']),
	('xstatus_meeting', [None, 'relaxing', 'socializing']),
	('xstatus_coffee', [None, 'drinking', 'having_coffee']),
	('xstatus_listening_to_music', ['aroused', None, None]),
	('xstatus_business', [None, 'having_appointment', None]),
	('xstatus_shooting', [None, 'traveling', 'commuting']),
	('xstatus_having_fun', ['contented', None, None]),
	('xstatus_on_the_phone', [None, 'talking', 'on_the_phone']),
	('xstatus_gaming', [None, 'relaxing', 'gaming']),
	('xstatus_studying', [None, 'working', 'studying']),
	('xstatus_shopping', [None, 'relaxing', 'shopping']),
	('xstatus_feeling_sick', ['sick', None, None]),
	('xstatus_sleeping', [None, 'inactive', 'sleeping']),
	('xstatus_surfing', [None, 'exercising', 'swimming']),
	('xstatus_browsing', [None, 'relaxing', 'reading']),
	('xstatus_working', [None, 'working', None]),
	('xstatus_typing', [None, 'working', 'writing']),
	('xstatus_cn1', [None, 'relaxing', 'going_out']),
	('xstatus_cn2', ['happy', None, None]),
	('xstatus_cn3', [None, 'talking', 'in_real_life']),
	('xstatus_cn4', [None, 'inactive', 'hanging_out']),
	('xstatus_cn5', ['excited', None, None]),
	('xstatus_de1', ['amazed', None, None]),
	('xstatus_de2', [None, 'relaxing', 'watching_a_movie']),
	('xstatus_de3', ['in_love', None, None]),
	('xstatus_ru1', ['curious', None, None]),
	('xstatus_ru2', ['flirtatious', None, None]),
	('xstatus_ru3', ['impressed', None, None])
])

AN_STATUS_MAP = dict([
	('anstatus_evil', ['annoyed', None, None]),
	('anstatus_depression', ['depressed', None, None]),
	('anstatus_at_home', [None, 'inactive ', 'day_off']),
	('anstatus_at_work', [None, 'working', 'in_a_meeting']),
	('anstatus_out_to_lunch', [None, 'eating', 'having_lunch']),
	('anstatus_on_the_phone', [None, 'talking', None])
])

MOODS = dict([
	('mood_afraid', 'afraid'),
	('mood_amazed', 'amazed'),
	('mood_angry', 'angry'),
	('mood_annoyed', 'annoyed'),
	('mood_anxious', 'anxious'),
	('mood_aroused', 'aroused'),
	('mood_ashamed', 'ashamed'),
	('mood_bored', 'bored'),
	('mood_brave', 'brave'),
	('mood_calm', 'calm'),
	('mood_cold', 'cold'),
	('mood_confused', 'confused'),
	('mood_contented', 'contented'),
	('mood_cranky', 'cranky'),
	('mood_curious', 'curious'),
	('mood_depressed', 'depressed'),
	('mood_disappointed', 'disappointed'),
	('mood_disgusted', 'disgusted'),
	('mood_distracted', 'distracted'),
	('mood_embarrassed', 'embarrassed'),
	('mood_excited', 'excited'),
	('mood_flirtatious', 'flirtatious'),
	('mood_frustrated', 'frustrated'),
	('mood_grumpy', 'grumpy'),
	('mood_guilty', 'guilty'),
	('mood_happy', 'happy'),
	('mood_hot', 'hot'),
	('mood_humbled', 'humbled'),
	('mood_humiliated', 'humiliated'),
	('mood_hungry', 'hungry'),
	('mood_hurt', 'hurt'),
	('mood_impressed', 'impressed'),
	('mood_in_awe', 'in_awe'),
	('mood_in_love', 'in_love'),
	('mood_indignant', 'indignant'),
	('mood_interested', 'interested'),
	('mood_intoxicated', 'intoxicated'),
	('mood_invincible', 'invincible'),
	('mood_jealous', 'jealous'),
	('mood_lonely', 'lonely'),
	('mood_mean', 'mean'),
	('mood_moody', 'moody'),
	('mood_nervous', 'nervous'),
	('mood_neutral', 'neutral'),
	('mood_offended', 'offended'),
	('mood_playful', 'playful'),
	('mood_proud', 'proud'),
	('mood_relieved', 'relieved'),
	('mood_remorseful', 'remorseful'),
	('mood_restless', 'restless'),
	('mood_sad', 'sad'),
	('mood_sarcastic', 'sarcastic'),
	('mood_serious', 'serious'),
	('mood_shocked', 'shocked'),
	('mood_shy', 'shy'),
	('mood_sick', 'sick'),
	('mood_sleepy', 'sleepy'),
	('mood_stressed', 'stressed'),
	('mood_surprised', 'surprised'),
	('mood_thirsty', 'thirsty'),
	('mood_worried', 'worried')
])

ACTIVITIES = dict([
	('act_doing_chores', dict([
		('category', 'doing_chores'),
		('subact_buying_groceries', 'buying_groceries'),
		('subact_cleaning', 'cleaning'),
		('subact_cooking', 'cooking'),
		('subact_doing_maintenance', 'doing_maintenance'),
		('subact_doing_the_dishes', 'doing_the_dishes'),
		('subact_doing_the_laundry', 'doing_the_laundry'),
		('subact_gardening', 'gardening'),
		('subact_running_an_errand', 'running_an_errand'),
		('subact_walking_the_dog', 'walking_the_dog')
	])),
	('act_drinking', dict([
		('category', 'drinking'),
		('subact_having_a_beer', 'having_a_beer'),
		('subact_having_coffee', 'having_coffee'),
		('subact_having_tea', 'having_tea')
	])),
	('act_eating', dict([
		('category', 'eating'),
		('subact_having_a_snack', 'having_a_snack'),
		('subact_having_breakfast', 'having_breakfast'),
		('subact_having_dinner', 'having_dinner'),
		('subact_having_lunch', 'having_lunch')
	])),
	('act_exercising', dict([
		('category', 'exercising'),
		('subact_cycling', 'cycling'),
		('subact_hiking', 'hiking'),
		('subact_jogging', 'jogging'),
		('subact_playing_sports', 'playing_sports'),
		('subact_running', 'running'),
		('subact_skiing', 'skiing'),
		('subact_swimming', 'swimming'),
		('subact_working_out', 'working_out')
	])),
	('act_grooming', dict([
		('category', 'grooming'),
		('subact_at_the_spa', 'at_the_spa'),
		('subact_brushing_teeth', 'brushing_teeth'),
		('subact_getting_a_haircut', 'getting_a_haircut'),
		('subact_shaving', 'shaving'),
		('subact_taking_a_bath', 'taking_a_bath'),
		('subact_taking_a_shower', 'taking_a_shower')
	])),
	('act_having_appointment', dict([
		('category', 'having_appointment')
	])),
	('act_inactive', dict([
		('category', 'inactive'),
		('subact_day_off', 'day_off'),
		('subact_hanging_out', 'hanging_out'),
		('subact_on_vacation', 'on_vacation'),
		('subact_scheduled_holiday', 'scheduled_holiday'),
		('subact_sleeping', 'sleeping')
	])),
	('act_relaxing', dict([
		('category', 'relaxing'),
		('subact_gaming', 'gaming'),
		('subact_going_out', 'going_out'),
		('subact_partying', 'partying'),
		('subact_reading', 'reading'),
		('subact_rehearsing', 'rehearsing'),
		('subact_shopping', 'shopping'),
		('subact_socializing', 'socializing'),
		('subact_sunbathing', 'sunbathing'),
		('subact_watching_tv', 'watching_tv'),
		('watching_a_movie', 'watching_a_movie')
	])),
	('act_talking', dict([
		('category', 'talking'),
		('subact_in_real_life', 'in_real_life'),
		('subact_on_the_phone', 'on_the_phone'),
		('subact_on_video_phone', 'on_video_phone')
	])),
	('act_traveling', dict([
		('category', 'traveling'),
		('subact_commuting', 'commuting'),
		('subact_cycling', 'cycling'),
		('subact_driving', 'driving'),
		('subact_in_a_car', 'in_a_car'),
		('subact_on_a_bus', 'on_a_bus'),
		('subact_on_a_plane', 'on_a_plane'),
		('subact_on_a_train', 'on_a_train'),
		('subact_on_a_trip', 'on_a_trip'),
		('subact_walking', 'walking')
	])),
	('act_working', dict([
		('category', 'working'),
		('subact_coding', 'coding'),
		('subact_in_a_meeting', 'in_a_meeting'),
		('subact_studying', 'studying'),
		('subact_writing', 'writing')
	]))
])

