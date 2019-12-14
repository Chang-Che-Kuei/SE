import datetime
import pytz
import numpy as np
import dateutil.parser
import sys
np.set_printoptions(threshold=sys.maxsize)

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

	def FindBlankBlock(self,timeRange):
		#Init free time
		start,end = timeRange['start'], timeRange['end']
		dayNum = (datetime.date(end[0], end[1], end[2]) - 
				  datetime.date(start[0], start[1], start[2]) ).days +1
		freeTime = np.ones((dayNum,24*60+1)) # one day has 24*60 minutes. '1' indicates free time
		freeTime[0,0:start[3]*60+start[4]  ] = 0 # Invalid time
		freeTime[dayNum-1,end[3]*60+end[4] + 1 : ] = 0

		# Get events from google calendar
		startD = self.GetUTCtimezone(start)
		endD   = self.GetUTCtimezone(end)
		events = self.service.events().list(calendarId='primary', timeMin=startD,
		                                    timeMax=endD, singleEvents=True,
		                                    orderBy='startTime').execute()

		# Set the time which is been occupied by events to be invalid
		events = events.get('items', [])
		for event in events:
			startE = event['start']['dateTime'] # '2019-12-12T16:00:00+08:00'
			endE = event['end']['dateTime'] 
			#convert isoforamt to datetime object
			startE =  dateutil.parser.parse(startE) # '2019-12-12 16:00:00+08:00'
			endE = dateutil.parser.parse(endE)
			
			dayIndex = (datetime.date(startE.year, startE.month, startE.day) - 
				  datetime.date(start[0], start[1], start[2]) ).days 
			# set the time range of this event to be invalid '0'
			freeTime[dayIndex, startE.hour*60+startE.minute : endE.hour*60+endE.minute] = 0 
			#print(event['summary'],event['start'].get('dateTime'))
			#print(freeTime[dayIndex])


		# Find the blank block
		firstDay = datetime.datetime(start[0],start[1],start[2])
		blank = []
		for day in range(dayNum):
			today =  firstDay + datetime.timedelta(days=day)
			eachDay = {'date':[today.year, today.month, today.day],'block':[]}
			s, e = -1, -1
			for minute in range(24*60+1):
				if (freeTime[day,minute] == 1) and (s == -1): # new start
					s=minute
					#print(s,minute,freeTime[day,minute])
				elif (freeTime[day,minute] == 0 and s != -1) or minute==24*60: # found time block
					e = minute 
					#print("AAAAAAAAAAa")
					hrStart, minStart = int(s/60), s%60
					hrEnd, minEnd = int(e/60), e%60
					eachDay['block'].append([hrStart,minStart])
					eachDay['block'].append([hrEnd,minEnd])
					s=-1
			blank.append(eachDay)
		return blank



	#def AssignBlock(self,Event):



'''
Returned data from FindBlankBlock(self,timeRange)
# list contains several dict. Start from 2019/12/12 to 2019/12/16
[
	{'date': [2019, 12, 12], 'block': [[8, 0], [16, 0], [17, 0], [24, 0]]},
	{'date': [2019, 12, 13], 'block': [[0, 0], [22, 0], [23, 0], [24, 0]]},
	{'date': [2019, 12, 14], 'block': [[0, 0], [19, 0], [21, 0], [24, 0]]},
	{'date': [2019, 12, 15], 'block': [[0, 0], [24, 0]]}, 
	{'date': [2019, 12, 16], 'block': [[0, 0], [24, 0]]}
]

'''