# -*- coding: UTF-8 -*-

# If you change or add any strings in this file please contact the translators listed below
# Everything must be in UTF-8
# Look for language codes here - http://www.w3.org/WAI/ER/IG/ert/iso639.htm

class en: # English - James Bunton <mailto:james@delx.cjb.net>/Daniel Henninger <mailto:jadestorm@nc.rr.com>
	# Text that may get sent to the user. Useful for translations. Keep any %s symbols you see or you will have troubles later
	sessiongreeting = u"This is an experimental gateway, PyICQ-t. If you experience problems please contact Daniel Henninger <jadestorm@nc.rr.com>"
	authenticatetext = u"WARNING: Registration is a two-step process.  First, please enter your local username and your local password.  If you enter a valid username and password, you will get a 'Registration Successful' message.  Then, click Register again, and you will be prompted for your AIM username and password."
	registertext = u"Please type your ICQ user id number into the username field and your password."
	notloggedin = u"Error. You must log into the transport before sending messages."
	notregistered = u"Sorry. You do not appear to be registered with this transport. Please register and try again. If you are having trouble registering please contact your Jabber administrator."
	waitforlogin = u"Sorry, this message cannot be delivered yet. Please try again when the transport has finished logging in."
	usernotonline = u"The user you specified is not currently online."
	gatewaytranslator = u"Enter the user's ICQ user id number."
	sessionnotactive = u"Your session with ICQ is not active at this time."
	aimemailnotification = u"You have %d new message(s) at %s!\nCheck your mail at %s."
	searchnodataform = u"Use the enclosed form to search.  If your Jabber client does not support Data Forms, you will not be able to use this functionality."
	searchtitle = u"ICQ Directory Search"
	searchinstructions = u"Fill in either the e-mail address field or any number of the other fields to search the ICQ directory for matching users.  If the e-mail address is filled in, all other fields are ignored."
	command_CommandList = u"PyICQt Commands"
	command_Statistics = u"Statistics for PyICQt"
	command_RosterRetrieval = u"Retrieve Roster Contents"
	command_ConnectUsers = u"Connect all registered users"
	command_Done = u"Command completed"
	command_NoSession = u"You must be logged in to use this command."
	command_ChangePassword = u"Change ICQ password"
	command_ChangePassword_Instructions = u"Enter your current and new ICQ passwords below."
	command_ChangePassword_NewPassword = u"New password"
	command_ChangePassword_NewPasswordAgain = u"New password (again)"
	command_ChangePassword_OldPassword = u"Current password"
	command_ChangePassword_Mismatch = u"New passwords entered do not match."
	command_ChangePassword_Failed = u"Password change failed.  Most likely this is due to the wrong current password being entered."
	command_EmailLookup = u"Look up ICQ users via email"
	command_EmailLookup_Instructions = u"Enter an email address below to locate screen names associated with it."
	command_EmailLookup_Email = u"E-Mail address"
	command_EmailLookup_Results = u"These screen names matched the address provided:"
	command_ChangeEmail = u"Change registered e-mail address"
	command_ChangeEmail_Instructions = u"Enter your new e-mail address below.\nA confirmation message will be sent to your current address and,\nunless you cancel, your new address will take effect in 72 hours."
	command_ChangeEmail_Email = u"E-Mail address"
	command_SetXStatus = u"Set x-status" #TODO: make translation for other languages
	command_Settings = u"Settings" #TODO: make translation for other languages
	command_FormatScreenName = u"Change format of screen name"
	command_FormatScreenName_Instructions = u"Enter format of screen name below.\nPlease be aware that only capitalization and spacing may be changed."
	command_FormatScreenName_FMTScreenName = u"Formatted ScreenName"
	command_ConfirmAccount = u"Confirm ICQ account"
	command_ConfirmAccount_Complete = u"Account confirmation request completed.\nYou should receive email soon with instructions on how to proceed."
	command_ConfirmAccount_Failed = u"Unable to request confirmation at this time."
	command_ICQURITranslate = u"Translate an ICQ URI"
	command_ICQURITranslate_Instructions = u"Enter an ICQ URI and appropriate action will be taken based off the function of the URI."
	command_ICQURITranslate_URI = u"URI"
	command_ICQURITranslate_Failed = u"Unable to determine function of URI."
	command_UpdateMyVCard = u"Update my VCard"
	statistics_OnlineSessions = u"Online Users"
	statistics_Uptime = u"Uptime"
	statistics_IncomingMessages = u"Incoming Messages"
	statistics_OutgoingMessages = u"Outgoing Messages"
	statistics_TotalSessions = u"Total Sessions"
	statistics_MaxConcurrentSessions = u"Max Concurrent Sessions"
	statistics_MessageCount = u"Message Count"
	statistics_FailedMessageCount = u"Failed Message Count"
	statistics_AvatarCount = u"Avatar Count"
	statistics_FailedAvatarCount = u"Failed Avatar Count"
	statistics_OnlineSessions_Desc = u"The number of users currently connected to the service."
	statistics_Uptime_Desc = u"How long the service has been running, in seconds."
	statistics_IncomingMessages_Desc = u"How many messages have been transferred from the ICQ network."
	statistics_OutgoingMessages_Desc = u"How many messages have been transferred to the ICQ network."
	statistics_TotalSessions_Desc = u"The number of connections since the service started."
	statistics_MaxConcurrentSessions_Desc = u"The maximum number of users connected at any one time."
	statistics_MessageCount_Desc = u"How many messages have been transferred to and from the ICQ network."
	statistics_FailedMessageCount_Desc = u"The number of messages that didn't make it to the ICQ recipient and were bounced."
	statistics_AvatarCount_Desc = u"How many avatars have been transferred to and from the ICQ network."
	statistics_FailedAvatarCount_Desc = u"The number of avatar transfers that have failed."
	xstatus_set = u"Your x-status has been set"
	xstatus_support_disabled = u"X-status support disabled\n by your administrator"
	xstatus_sending_disabled = u"X-status sending support disabled.\n Check your settings for details"
	xstatus_set_xstatus_name = u"Set x-status name"
	xstatus_set_instructions = u"Select x-status from list below\nNote: official clients supports only 24 statuses\n(Angry - Typing), support for other could be\ndepends from ICQ client"
	xstatus_keep_current = u"Keep current x-status"
	xstatus_no_xstatus = u"No x-status"
	xstatus_set_details = u"Set x-status title and description"
	settings_xstatus_recv_support = u"Support for x-status receiving"
	settings_xstatus_send_support = u"Support for x-status sending"
	settings_xstatus_restore_after_disconnect = u"Restore latest x-status after disconnect"
	# additional "normal" statuses
	anormal_out_to_lunch = u"Out to lunch"
	anormal_on_the_phone = u"On the phone"
	anormal_at_home = u"At home"
	anormal_at_work = u"At work"
	anormal_evil = u"Evil"
	anormal_depression = u"Depression"
	# x-statuses
	xstatus_angry = u"Angry"
	xstatus_taking_a_bath = u"Taking a bath"
	xstatus_tired = u"Tired"
	xstatus_party = u"Party"
	xstatus_drinking_beer = u"Drinking beer"
	xstatus_thinking = u"Thinking"
	xstatus_eating = u"Eating"
	xstatus_wathing_tv = u"Watching TV"
	xstatus_meeting = u"Meeting"
	xstatus_coffee = u"Coffee"
	xstatus_listening_to_music = u"Listening to music"
	xstatus_business = u"Business"
	xstatus_shooting = u"Shooting"
	xstatus_having_fun = u"Having fun"
	xstatus_on_the_phone = u"On the phone"
	xstatus_gaming = u"Gaming"
	xstatus_studyng = u"Studying"
	xstatus_shopping = u"Shopping"
	xstatus_feeling_sick = u"Feeling sick"
	xstatus_sleeping = u"Sleeping"
	xstatus_surfing = u"Surfing"
	xstatus_browsing = u"Browsing"
	xstatus_working = u"Working"
	xstatus_typing = u"Typing"
	xstatus_cn1 = u"Eating/Picnic"
	xstatus_cn2 = u"Having fun/PDA/Cooking"
	xstatus_cn3 = u"Chit chatting/Mobile/Smoking"
	xstatus_cn4 = u"Sleeping/I\"m high"
	xstatus_cn5 = u"I\"m mooving/On WC"
	xstatus_de1 = u"To be or not to be"
	xstatus_de2 = u"Watching pro7 on TV"
	xstatus_de3 = u"Love"
	xstatus_ru1 = u"RuSearch"
	xstatus_ru2 = u"RuLove"
	xstatus_ru3 = u"RuJournal"
	xstatus_bombus1 = u"Smoking"
	xstatus_bombus2 = u"Sex" 
	# these lines for adding to user's status
	xstatus_append_status = u"Status"
	xstatus_append_xstatus = u"X-status"
	xstatus_append_xmessage = u"X-message"
	
en_US = en # en-US is the same as en, so are the others
en_AU = en
en_GB = en
