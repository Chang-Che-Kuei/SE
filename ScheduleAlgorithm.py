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

	def FilterByPref(self,dayNum,pref):
		# Preference setting
		# Yes: workingHr, forbiddenHr, timeGap ,minimumDuration 
    	# No: maxEvents, valuableHr 
		freeTime = np.zeros((dayNum,24*60+1)) # one day has 24*60 minutes. '1' indicates free time
		
		# Set workingHr
		work = pref.workingHr
		for i in range(0,len(work),2):
			workStart = work[i][0]*60 + work[i][1]
			workEnd   = work[i+1][0]*60 + work[i+1][1]
			freeTime[ :, workStart:workEnd] = 1

		# Set forbiddenHr
		fordidden = pref.forbiddenHr
		for i in range(0,len(fordidden),2):
			forbStart = fordidden[i][0]*60 + fordidden[i][1]
			forbEnd   = fordidden[i+1][0]*60 + fordidden[i+1][1]
			freeTime[ :, forbStart:forbEnd] = 0


		return freeTime

	def FindBlankBlock(self,timeRange,pref):

		#Init free time
		start,end = timeRange['start'], timeRange['end']
		dayNum = (datetime.date(end[0], end[1], end[2]) - 
				  datetime.date(start[0], start[1], start[2]) ).days +1
		freeTime = self.FilterByPref(dayNum,pref)
		
		# Set before start time and after send time to '0'
		freeTime[0,0:start[3]*60+start[4]  ] = 0 # Invalid time
		freeTime[dayNum-1,end[3]*60+end[4]  : ] = 0

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
			freeTime[dayIndex, startE.hour*60+startE.minute :
					 endE.hour*60+endE.minute + pref.timeGap] = 0 
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
				elif (freeTime[day,minute] == 0 and s != -1) or (freeTime[day,minute] == 1 and minute==24*60) : # found time block
					e = minute 
					if e-s >= pref.minimumDuration:
						hrStart, minStart = int(s/60), s%60
						hrEnd, minEnd = int(e/60), e%60
						eachDay['block'].append([hrStart,minStart])
						eachDay['block'].append([hrEnd,minEnd])
					s=-1
			blank.append(eachDay)
		return blank

	def IsEventValid(self,event,blank,pref):
		# Determine there is a blank block for the final event
		finalEvent = event['FinalEvent']
		date = finalEvent['Start'][0:3]
		finalStart = finalEvent['Start'][3]*60 + finalEvent['Start'][4]
		finalEnd   = finalEvent['End'][3]*60   + finalEvent['End'][4]
		validFinal = False
		# Determine there are sufficient blank block for the preparation event
		totalFreeTime = 0
		preparartionHr = event['PreparingTime']['PreparingHours']
		sufficentBlock = False
		# the 'end' of pref.workingHr and pref.forbiddenHr don't need pref.timeGap
		withoutGap = []
		withoutGap.append(pref.workingHr[1])
		withoutGap.extend(pref.forbiddenHr[0::2])
		sufficientTime = False

		for day in blank:
			block = day['block']
			for index in range(0,len(block),2):
				start = block[index][0]*60 + block[index][1]
				end   = block[index+1][0]*60 + block[index+1][1]
				if day['date'] == date:
					if start <= finalStart and end >= finalEnd:
						validFinal = True

				if block[index+1] not in withoutGap:
					end -= pref.timeGap
				if end - start < pref.minimumDuration:
					continue
				totalFreeTime = totalFreeTime + (end-start)
		if totalFreeTime/60 >= preparartionHr:
			sufficientTime = True
		return validFinal, sufficientTime, withoutGap

	def MakePreparationEventFormat(self,event,timeInfo):
		gooEvent = {}
		day, start,end = timeInfo
		startTime = day['date']+[int(start/60),start%60]
		endTime =  day['date']+[int(end/60),end%60]

		gooEvent['summary'] = event['EventName'] + '_Preparation'
		gooEvent['start'] = {'dateTime': self.GetUTCtimezone(startTime)}
		gooEvent['end'] = {'dateTime': self.GetUTCtimezone(endTime)}
		gooEvent['colorId'] = 11
		print(gooEvent)
		return gooEvent

	def MakeFinalEventFormat(self,event):
		gooEvent = {}
		gooEvent['summary'] = event['EventName']
		finE = event['FinalEvent']
		gooEvent['start'] = {'dateTime': self.GetUTCtimezone(finE['Start'])}
		gooEvent['end'] = {'dateTime': self.GetUTCtimezone(finE['End'])}
		gooEvent['location'] = finE['Location']
		gooEvent['colorId'] = 11
		print(gooEvent)
		return gooEvent

	def AssignBlock(self,event,blank,pref,service):
		for i in blank:
			print(i)
		# Check conditions
		bValidFinal, bSufficientTime, withoutGap = self.IsEventValid(event,blank,pref)
		# Return message
		if not bValidFinal and not bSufficientTime:
			return 'Final event is conflict and the preparation time is insufficient.'
		elif not bValidFinal:
			return 'Final event is conflict.'
		elif not bSufficientTime:
			return 'The preparation time is insufficient.'

		# Assign Preparation Event
		prepMin = event['PreparingTime']['PreparingHours']*60
		for day in blank:
			block = day['block']
			for index in range(0,len(block),2):
				start = block[index][0]*60 + block[index][1]
				end   = block[index+1][0]*60 + block[index+1][1]
				# if the following event is the end of forbiddenHr or workingHr,
				# don't need to substract with pref.minimumDuration
				if block[index+1] not in withoutGap: 
					end -= pref.timeGap
				if end-start < pref.minimumDuration:
					continue

				if prepMin < end-start: # It is the last preparation event
					end = start +prepMin
				prepMin -= (end-start)
				prepEvent = self.MakePreparationEventFormat(event,[day,start,end])
				service.events().insert(calendarId='primary', body=prepEvent).execute()
				if prepMin == 0:
					break
			if prepMin == 0:
				break

		# Assign Final Event
		finEvent = self.MakeFinalEventFormat(event)
		service.events().insert(calendarId='primary', body=finEvent).execute()

		
		return 'Assign Successfully.'



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