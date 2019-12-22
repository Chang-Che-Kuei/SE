from __future__ import print_function
import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from ScheduleAlgorithm import ScheduleAlgorithm
from Preference import Preference
import dateutil.parser
class User:
	def __init__(self):
		# The file token.pickle stores the user's access and refresh tokens, and is
		# created automatically when the authorization flow completes for the first
		# time.
		self.creds = None
		# If modifying these scopes, delete the file token.pickle.
		self.SCOPES = ['https://www.googleapis.com/auth/calendar']

		# open token.pickle
		if os.path.exists('token.pickle'):
			with open('token.pickle', 'rb') as token:
				self.creds = pickle.load(token)
		# If there are no (valid) credentials available, let the user log in.
		if not self.creds or not self.creds.valid:
			if self.creds and self.creds.expired and self.creds.refresh_token:
				self.creds.refresh(Request())
			else:
				flow = InstalledAppFlow.from_client_secrets_file(
					'credentials.json', self.SCOPES)
				self.creds = flow.run_local_server(port=0)
			# Save the credentials for the next run
			with open('token.pickle', 'wb') as token:
				pickle.dump(self.creds, token)

		self.service = build('calendar', 'v3', credentials=self.creds)
		self.algo = ScheduleAlgorithm(self.service)
		self.pref = Preference()
		
	def CreateEvent(self,Info):
		event = {
		  'summary': '測試',
		  'id': '1234gsfhdf567sss',
		  'start': {
		    'dateTime': '2019-12-12T2:00:00-00:00',
		    #'timeZone': 'Asia/Taipei',
		  },
		  'end': {
		    'dateTime': '2019-12-12T5:00:00-00:00',
		    #'timeZone': 'Asia/Taipei',
		  },
		  #'colorId' : 3,
		}
		event = self.service.events().insert(calendarId='primary', body=event).execute()

	def UpdateEvent(self,eventID,Info):
		event = self.service.events().get(calendarId='primary', eventId=eventID).execute()
		event['summary'] = Info['summary']
		self.service.events().update(calendarId='primary', eventId=eventID, body=event).execute()

	
	def DeleteEvent(self,eventID):
		self.service.events().delete(calendarId='primary', eventId=eventID).execute()

eventForAssignBlock = {
	'EventName' : '資工之夜',
	'Description' : '資工系表演',
	'Priority' : 20,
	'PreparingTime' : {
		'Start' : [2019,12,19,8,0],
		'End'   : [2019,12,26,17,0],
		'PreparingHours' :30
	},
	'FinalEvent' : {
		'Start' : [2019,12,26,13,0],
		'End'   : [2019,12,26,15,0],
		'Location' : '德田館'
	}
}

def GetBigEventEdit():
	editEvent = {}
	editEvent['OriginName'] = "editBig"
	editEvent['NewName'] = "NewNammmm"
	editEvent['Description'] = "bbb"
	editEvent['Priority'] = int('2')

	DRange = "12/26/2019 - 12/26/2019"
	prepStartFrom = [int(DRange[6:10]),int(DRange[0:2]),int(DRange[3:5])]
	import os
	os.environ['TZ']='Asia/Taipei'
	now = datetime.datetime.now()
	#print(now)
	if now.year == prepStartFrom[0] and now.month == prepStartFrom[1] and now.day == prepStartFrom[2]: # Start from today
		prepStartFrom.extend([now.hour,now.minute]) # the starting hr and minutes begin from tnow
	else: # start after today
		prepStartFrom.extend([0,0])
	prepStartTo   = [int(DRange[19:23]),int(DRange[13:15]),int(DRange[16:18]),23,59]
	prepHr = int(0)
	editEvent['PreparingTime'] = {
	    'Start': prepStartFrom, 'End': prepStartTo, 'PreparingHours': prepHr}

	GetFinalStart = "2019-12-28T08:00"
	GetFinalEnd = "2019-12-28T10:00"
	if GetFinalStart != '':
		FinalEventStart = [int(GetFinalStart[0:4]),int(GetFinalStart[5:7]),int(GetFinalStart[8:10]),int(GetFinalStart[11:13]),int(GetFinalStart[14:16])]
		FinalEventEnd = [int(GetFinalEnd[0:4]),int(GetFinalEnd[5:7]),int(GetFinalEnd[8:10]),int(GetFinalEnd[11:13]),int(GetFinalEnd[14:16])]
		if prepStartTo[:3] == FinalEventStart[:3] : # the last day of preparation equals to the first day of final event
			prepStartTo[3:5] = FinalEventStart[3:5] # the preparation can not be latter than final event
		location = "NewPlace"
		editEvent['FinalEvent'] = {
		    'Start': FinalEventStart, 'End': FinalEventEnd, 'Location': location}
	#print('eventForAssignBlock ',eventForAssignBlock)
	return editEvent

def DeleteInvalidPrepEvent(user, From, To, editEvent,needMoreMin, deleteId):
	From = user.algo.GetUTCtimezone(From)
	To = user.algo.GetUTCtimezone(To)
	#print(From,'  ',To)
	
	if To > From: 
		preEvent = user.service.events().list(calendarId='primary',
		 timeMin=From, timeMax=To, singleEvents=True).execute()
		
		preEvent = preEvent.get('items', [])
		for e in preEvent:
			if e['summary'] == 'Big_' + editEvent['OriginName'] + "_Preparation":
				st, et = e['start']['dateTime'], e['end']['dateTime']
				start =  dateutil.parser.parse(st)
				end = dateutil.parser.parse(et)
				ts = (end - start).total_seconds() / 60; 
				needMoreMin += ts
				deleteId.append(e['id'])
				
	return needMoreMin

def EditBigEvent(user):
	#input
	editEvent = GetBigEventEdit()

	# Get origin data. Brute force search.   
	# Wish eventId is available.
	lastYear = (datetime.datetime.utcnow() - datetime.timedelta(days=8)).isoformat() + 'Z'
	nextYear = (datetime.datetime.utcnow() + datetime.timedelta(days=8)).isoformat() + 'Z'
	events = user.service.events().list(
	    calendarId='primary', timeMin=lastYear, timeMax=nextYear,
	    singleEvents=True, orderBy='startTime').execute()
	events = events.get('items', [])
	gooFinalEvent = None
	for e in events:
		if "Big_" + editEvent['OriginName'] + "_Preparation" == e['summary']:
			findEvent = e
		if "Big_" + editEvent['OriginName'] == e['summary']:
			gooFinalEvent = e

	# preapration hr需要更多或更少小時
	gooPrepHr = int(findEvent['description'].split('\n')[2])
	needMoreHr = editEvent['PreparingTime']['PreparingHours'] - gooPrepHr 
	needMoreMin = needMoreHr*60
	print("prepHr",needMoreMin)
	
	# 移除不在timeRange的未來prep事件(start延後、end提前)
	strPrepRange = findEvent['description'].split('\n')[1] 
	oriPrepRange = [int(i) for i in strPrepRange.split()] # [2019, 12, 24, 0, 0, 2019, 12, 27, 23, 59]

	# Delete prep event before new preparation start time (start 延後)
	deleteId = []
	newPrepStart = editEvent['PreparingTime']['Start']
	needMoreMin = DeleteInvalidPrepEvent(
		user, oriPrepRange[0:5], newPrepStart, editEvent, needMoreMin, deleteId)
	print("start 延後",needMoreMin)
	# Delete prep event adter new preparation end time (end 提前)
	newPrepEnd =  editEvent['PreparingTime']['End']
	needMoreMin = DeleteInvalidPrepEvent(
		user, newPrepEnd, oriPrepRange[5:10], editEvent, needMoreMin, deleteId)
	print("end 提前",needMoreMin)

	#其他非時間的改動: eventName, description
	editEvent['Description'] += '\n' + findEvent['description'].split('\n')[1]
	editEvent['Description'] += '\n' + str(editEvent['PreparingTime']['PreparingHours'])
	editEvent['EventName'] = "Big_" + editEvent['NewName']

	# Check final event
	if gooFinalEvent!= None and editEvent['FinalEvent']['Start'] != "": 
		user.service.events().delete(calendarId='primary', eventId=gooFinalEvent['id']).execute()
		finalStart = gooFinalEvent['start']['dateTime'] 
		finalEnd = gooFinalEvent['end']['dateTime'] # 2019-12-28T08:00:00+08:00
		print(finalStart,finalEnd)
		listFinStart = [int(finalStart[0:4]), int(finalStart[5:7]), int(finalStart[8:10]), int(finalStart[11:13]), int(finalStart[14:16])]
		listFinEnd = [int(finalEnd[0:4]), int(finalEnd[5:7]), int(finalEnd[8:10]), int(finalEnd[11:13]), int(finalEnd[14:16])]
		if user.algo.DetectConflict(listFinStart,listFinEnd) : 
			print("Cannot modify final event")
			user.service.events().insert(calendarId='primary', body=gooFinalEvent).execute()
			return "Cannot modify final event"
	elif gooFinalEvent!= None and editEvent['FinalEvent']['Start'] == "": # 原本有final event，後來使用者不要
		user.service.events().delete(calendarId='primary', eventId=gooFinalEvent['id']).execute()

	# 根據start 延後,end 提前 ，看總共要新增或減少多少prepration event，
	# 再用findBlankBlock然後AssignBlock
	tRange = {'start':editEvent['PreparingTime']['Start'],
				  'end':editEvent['PreparingTime']['End'] }
	utcNewPrepStart = user.algo.GetUTCtimezone(newPrepStart)
	utcNewPrepEnd   = user.algo.GetUTCtimezone(newPrepEnd)
	blankAndEvent = user.algo.FindBlankBlock(tRange, user.pref)
	if needMoreMin > 0:	 # Add prep events
		#print('blank ',blankAndEvent)
		result = user.algo.AssignBlock(editEvent,blankAndEvent,tRange,user.pref,user.service,needMoreMin/60)
		print("In editing big event, ",result)
		if result != "Add big event Successfully.": # restore the deleted final event
			user.service.events().insert(calendarId='primary', body=gooFinalEvent).execute()
			return "Failed. " + result

	elif needMoreMin < 0: # Delete prep events
		#print('blank ',blankAndEvent)
		result = user.algo.AssignBlock(editEvent,blankAndEvent,tRange,user.pref,user.service,-1)
		print("In editing big event, ",result)
		if result != "Add big event Successfully.": # restore the deleted final event
			user.service.events().insert(calendarId='primary', body=gooFinalEvent).execute()
			return "Failed. " + result

		deleteE = user.service.events().list(calendarId='primary', 
			timeMin=utcNewPrepStart, timeMax=utcNewPrepEnd, singleEvents=True).execute()
		deleteE = deleteE.get('items', [])
		for e in deleteE:
			if e['summary'] == 'Big_' + editEvent['OriginName'] + "_Preparation":
				st, et = e['start']['dateTime'], e['end']['dateTime']
				start =  dateutil.parser.parse(st)
				end = dateutil.parser.parse(et)
				ts = (end - start).total_seconds() / 60; 
				if ts <= needMoreMin:
					needMoreMin -= needMoreMin
					user.service.events().delete(calendarId='primary', eventId=e['id']).execute()
				else:
					newEndTime = start + datetime.timedelta(needMoreMin)
					listEndTime = [newEndTime.years,newEndTime.month,newEndTime.day,newEndTime.hour,newEndTime.minute]
					newUTCEndTime = user.algo.GetUTCtimezone(listEndTime) 
					e['end']['dateTime'] = newUTCEndTime
					user.service.events().update(calendarId='primary', eventId=e['id'], body=e).execute()
					needMoreMin = 0

				if needMoreMin == 0:
					break

	# update original prep events between the new prep start and prep end
	updateE = user.service.events().list(calendarId='primary', 
		timeMin=utcNewPrepStart, timeMax=utcNewPrepEnd, singleEvents=True).execute()
	updateE = updateE.get('items', [])
	for e in updateE:
		if e['summary'] == "Big_" + editEvent['OriginName'] + "_Preparation":
			e['summary'] = "Big_" + editEvent['OriginName'] + "_Preparation"
			e['description'] = editEvent['Description']
			user.service.events().update(calendarId='primary', eventId=e['id'], body=e).execute()


	# Delete original event outside of the new prep start and prep end
	for Id in deleteId:
		user.service.events().delete(calendarId='primary', eventId=Id).execute()
	return "Edit big event successfully."

def main():
	user = User()
	if user.service:
		EditBigEvent(user)
		#eventList(user,[0],['4adlrr2dc2lj4vo2lm9anl796s'],[2])
		#timeRange = {'start':[2019,12,19,8,0], 'end':[2019,12,26,18,0]}
		#blankAndEvent = user.algo.FindBlankBlock(timeRange, user.pref)
		#print(user.algo.AssignBlock(eventForAssignBlock,blankAndEvent,user.pref,user.service))
		
		#eventID = '12345zxczxc678cx9'
		#user.CreateEvent({'summary':'test API'})
		#user.UpdateEvent(eventID, {'summary':'update event'})
		#user.DeleteEvent(eventID)

	


if __name__ == '__main__':
    main()



# Feasibility study，開發時遇到沒想到的細節
# WBS團體討論時要乘5

'''
1. API show big event info (Id)
2. edit big and small event
3. delete big event
# Priority 

bug:

'''