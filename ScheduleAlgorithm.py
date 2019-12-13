import datetime
import pytz



'''
[
{'date':2019-12-12, 'start':[8,0], 'end':1400}, {'date':2019-12-13, 'start':0900, 'end':1300}
]
'''
class ScheduleAlgorithm:
	def __init__(self,service):
		self.service = service

	def FindBlankBlock(self,timeRange):#(self,timeRange,pref):
		d = datetime.datetime.now()
		#create Taipei timezone
		tw = pytz.timezone('Asia/Taipei')
		#set d timezone is 'Asia/Taipei'
		twdt = tw.localize(d)
		#change to utc time
		utc_dt = d.astimezone(pytz.utc).isoformat()+'Z'
		utc_dt = utc_dt[:-7] + 'Z'
		print(utc_dt)

		now = datetime.datetime.now().isoformat() + 'Z' # 'Z' indicates UTC time
		print(type(now),now)
		print('Getting the upcoming 10 events')
		events_result = self.service.events().list(calendarId='primary', timeMin=utc_dt,
		                                    maxResults=10, singleEvents=True,
		                                    orderBy='startTime').execute()
		events = events_result.get('items', [])
		if not events:
			print('No upcoming events found.')
		for event in events:
			start = event['start'].get('dateTime', event['start'].get('date'))
			print(start, event['summary'])
	#def AssignBlock(self,Event):