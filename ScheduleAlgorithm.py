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

	def GetUTCtimezone(self,date):
		d = datetime.datetime(date[0],date[1],date[2],date[3],date[4])
		#create Taipei timezone
		tw = pytz.timezone('Asia/Taipei')
		d = tw.localize(d)
		#change to utc time
		d = d.astimezone(pytz.utc).isoformat()
		d = d[:-6] + 'Z'
		return d

	def FindBlankBlock(self,timeRange):#(self,timeRange,pref):
		start,end = timeRange['start'], timeRange['end']
		startD = self.GetUTCtimezone(start)
		endD   = self.GetUTCtimezone(end)

		events_result = self.service.events().list(calendarId='primary', timeMin=startD,
		                                    timeMax=endD, singleEvents=True,
		                                    orderBy='startTime').execute()
		print(events_result['summary'])
		events = events_result.get('items', [])
		if not events:
			print('No upcoming events found.')
		for event in events:
			start = event['start'].get('dateTime', event['start'].get('date'))
			print(start, event['summary'])
	#def AssignBlock(self,Event):