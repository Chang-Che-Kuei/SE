from __future__ import print_function
import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from ScheduleAlgorithm import ScheduleAlgorithm
from Preference import Preference

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
		'PreparingHours' : 15
	},
	'FinalEvent' : {
		'Start' : [2019,12,26,13,0],
		'End'   : [2019,12,26,15,0],
		'Location' : '德田館'
	}
}


def main():
	user = User()
	if user.service:
		timeRange = {'start':[2019,12,19,8,0], 'end':[2019,12,26,18,0]}
		blank = user.algo.FindBlankBlock(timeRange, user.pref)
		print(user.algo.AssignBlock(eventForAssignBlock,blank,user.pref,user.service))
		#eventID = '12345zxczxc678cx9'
		#user.CreateEvent({'summary':'test API'})
		#user.UpdateEvent(eventID, {'summary':'update event'})
		#user.DeleteEvent(eventID)

	


if __name__ == '__main__':
    main()