'''
from calendar_api.calendar_api import google_calendar_api

m=google_calendar_api()
m.create_event(calendar_id='184873625967-88hs5qi94u21c1n2t4tvrkhkn2jpctm4.apps.googleusercontent.com',
start='2019,12,12,8,00,00',
end='2017,12,12,9,15,00',
description='foo'
)
'''

from __future__ import print_function
import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from ScheduleAlgorithm import ScheduleAlgorithm

class User:
	def __init__(self):
		# The file token.pickle stores the user's access and refresh tokens, and is
		# created automatically when the authorization flow completes for the first
		# time.
		self.creds = None
		# If modifying these scopes, delete the file token.pickle.
		self.SCOPES = ['https://www.googleapis.com/auth/calendar']

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


def main():
	user = User()
	if user.service:
		timeRange = {'start':[2019,12,12,8,0], 'end':[2019.12,19,17,0]}
		user.algo.FindBlankBlock(timeRange)
		#eventID = '12345zxczxc678cx9'
		#user.CreateEvent({'summary':'test API'})
		#user.UpdateEvent(eventID, {'summary':'update event'})
		#user.DeleteEvent(eventID)

	'''
	# Call the Calendar API
	now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
	print(datetime.datetime.now())
	print('Getting the upcoming 10 events')
	events_result = service.events().list(calendarId='primary', timeMin=now,
	                                    maxResults=10, singleEvents=True,
	                                    orderBy='startTime').execute()
	events = events_result.get('items', [])

	if not events:
	    print('No upcoming events found.')
	for event in events:
	    start = event['start'].get('dateTime', event['start'].get('date'))
	    print(start, event['summary'])
'''




if __name__ == '__main__':
    main()