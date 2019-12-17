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
		datetimeStart = datetime.date(start[0],start[1],start[2])
		dayNum = (datetime.date(end[0], end[1], end[2]) - 
				  datetime.date(start[0], start[1], start[2]) ).days +1
		freeTime = self.FilterByPref(dayNum,pref)
		
		# Set before start time and after end time to '0'
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
		numDayEvent = {}
		for event in events:
			startE = event['start']['dateTime'] # '2019-12-12T16:00:00+08:00'
			endE = event['end']['dateTime'] 
			#convert isoforamt to datetime object
			startE =  dateutil.parser.parse(startE) # '2019-12-12 16:00:00+08:00'
			endE = dateutil.parser.parse(endE)

			startDayIndex = (datetime.date(startE.year, startE.month, startE.day) - 
				  datetime.date(start[0], start[1], start[2]) ).days 

			endDayIndex = (datetime.date(endE.year, endE.month, endE.day) - 
				  datetime.date(start[0], start[1], start[2]) ).days 
			# set the duration of this event to be invalid '0'
			for day in range(startDayIndex,endDayIndex+1):
				date = datetimeStart + datetime.timedelta(days=day)
				strDate = str(date.year) + '-' + str(date.month) + '-' + str(date.day)
				if strDate in numDayEvent:
					numDayEvent[strDate] +=1
				else:
					numDayEvent[strDate] = 1

				if startDayIndex == endDayIndex: # one-day event
					freeTime[day, startE.hour*60+startE.minute: endE.hour*60+endE.minute] = 0
				elif startDayIndex == day: # first day 
					freeTime[day, startE.hour*60+startE.minute: 24*60] = 0
				elif endDayIndex == day: # last day 
					freeTime[day, 0:endE.hour*60+endE.minute] = 0
				else: #middle day
					freeTime[:,:] = 0

			# set the timeGap after this event to be invalid '0'
			freeTime[endDayIndex, endE.hour*60+endE.minute :
					endE.hour*60+endE.minute + pref.timeGap] = 0 
			#print(event['summary'],event['start'].get('dateTime'))
			#print(freeTime[dayIndex])


		# Find the blank block
		firstDay = datetime.datetime(start[0],start[1],start[2])
		blank = {}
		for day in range(dayNum):
			today =  firstDay + datetime.timedelta(days=day)

			date = str(today.year) + '-' + str(today.month) + '-' + str(today.day)
			block = []
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

						block.append([hrStart,minStart])
						block.append([hrEnd,minEnd])
					s=-1
			blank[date] = block
		print(blank,'\n',numDayEvent)

	def IsEventValid(self,event,blank,pref):
		# Determine there is a blank block for the final event
		finalEvent = event['FinalEvent']
		date = str(finalEvent['Start'][0])+str(finalEvent['Start'][1])+str(finalEvent['Start'][2])
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


		for blankDate in blank:
			block = blank[blankDate]
			for index in range(0,len(block),2):
				start = block[index][0]*60 + block[index][1]
				end   = block[index+1][0]*60 + block[index+1][1]
				blankDate = blankDate.replace('-','')
				if blankDate == date:
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
		date, start,end = timeInfo
		date = date.replace('-','')
		dateList = [int(date[0:4]),int(date[4:6]),int(date[6:8])]
		startTime = dateList+[int(start/60),start%60]
		endTime =  dateList+[int(end/60),end%60]

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

	def AssignBlock(self,event,blankAndEvent,pref,service):
		# Check conditions
		blank, numDayEvent = blankAndEvent
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
		for date, block in blank.items():
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
				prepEvent = self.MakePreparationEventFormat(event,[date,start,end])
				service.events().insert(calendarId='primary', body=prepEvent).execute()
				if prepMin == 0:
					break
			if prepMin == 0:
				break

		# Assign Final Event
		finEvent = self.MakeFinalEventFormat(event)
		service.events().insert(calendarId='primary', body=finEvent).execute()

		
		return 'Assign Successfully.'

	def DetectConflict(self, event):
		now = datetime.datetime.utcnow().isoformat() + 'Z'
		events_result = self.service.events().list(calendarId='primary', timeMin=now, maxResults=10, singleEvents=True, orderBy='startTime').execute()
		events = events_result.get('items', [])
		start = []
		end = []
		event_start = datetime.datetime.strptime(event['start']['dateTime'][:-6], '%Y-%m-%dT%H:%M:%S')
		event_end = datetime.datetime.strptime(event['end']['dateTime'][:-6], '%Y-%m-%dT%H:%M:%S')
		for i in range(len(events)):
			x = datetime.datetime.strptime(events[i]['start']['dateTime'][:-6], '%Y-%m-%dT%H:%M:%S')
			y = datetime.datetime.strptime(events[i]['end']['dateTime'][:-6], '%Y-%m-%dT%H:%M:%S')
			start.append(x)
			end.append(y)
		for i in range(len(start)):
			if events[i]['id'] == event['id']:
				print('same')
				continue
			if event_start < end[i] and event_end > start[i]:
				print(event_start, event_end, start[i], end[i])
				return True
		return False

	def NewEvent(self, event, start, end):
		new = {}
		exclude = ['id', 'kind', 'etag', 'status', 'htmlLink', 'created', 'updated', 'iCalUID', 'sequence']
		for key, value in event.items():
			if key not in exclude:
				new[key] = value
			else:
				pass
		new['start'] = {
			'dateTime': self.GetUTCtimezone(start)
			}
		new['end'] = {
			'dateTime': self.GetUTCtimezone(end)
			}
		return new

	def CheckFreeTotalBeforeEvent(self, blank_block, hrStart, minStart):
		free_total = 0
		for j in range(0, len(blank_block), 2):
			if blank_block[j][0] * 60 + blank_block[j][1] < hrStart*60 + minStart:  # early block
				free_total += blank_block[j+1][0] * 60+blank_block[j+1][1] - blank_block[j][0] * 60 - blank_block[j][1]
		return free_total

	def TimeShift(self, pref, day_of_deleted_event):
		year, month, day = [int(j) for j in day_of_deleted_event[:10].split('-')]
		timeMin = [year, month, day, pref.workingHr[0][0], pref.workingHr[0][1]]
		timeMax = [year, month, day, pref.workingHr[-1][0], pref.workingHr[-1][1]]
		timeRange={'start': timeMin, 'end': timeMax}
		blank = self.FindBlankBlock(timeRange, pref)
		#print(blank)
		# get all events on the day of the deleted event                
		events_result = self.service.events().list(calendarId='primary', timeMin=self.GetUTCtimezone(timeMin), timeMax=self.GetUTCtimezone(timeMax), singleEvents=True, orderBy='startTime').execute()
		events = events_result.get('items', [])
		

		for i in range(len(events)):
			if events[i]['summary'][-11:] == 'Preparation': # need to shift the preparation events only
			#	print(events[i]['summary'])
				event_date = events[i]['start']['dateTime'][:10]
				year, month, day = [int(j) for j in event_date.split('-')]
				hrStart, minStart = [int(j) for j in events[i]['start']['dateTime'][11:16].split(':')]
				hrEnd, minEnd = [int(j) for j in events[i]['end']['dateTime'][11:16].split(':')]
				duration = hrEnd*60 + minEnd - hrStart*60 - minStart
				#print(event_date, hrStart, minStart, hrEnd, minEnd, duration)
				blank_block = blank[event_date]
				# get the free total time before the event
				free_total = self.CheckFreeTotalBeforeEvent(blank_block, hrStart, minStart)
				print("free total = {}".format(free_total)) 
				for j in range(0, len(blank_block), 2):
					if blank_block[j][0] * 60 + blank_block[j][1] >= hrStart*60 + minStart:
						break
					block_duration = blank_block[j+1][0] * 60+blank_block[j+1][1] - blank_block[j][0] * 60 - blank_block[j][1]
					start = [year, month, day, blank_block[j][0], blank_block[j][1]]
					if block_duration >= duration:
						total = blank_block[j][0]*60+blank_block[j][1] + duration
						end = [year, month, day, int(total / 60), total % 60]
						duration = 0
					elif block_duration < duration and block_duration >= pref.minimumDuration:
						end = [year, month, day, blank_block[j+1][0], blank_block[j+1][1]]
						duration -= block_duration
					e = self.NewEvent(events[i], start, end)
					#print(start)
					#print(end)
					self.service.events().insert(calendarId='primary', body=e).execute()
					if duration <= 0:
						self.service.events().delete(calendarId='primary', eventId=events[i]['id']).execute()
						break
				if duration > 0:
					print(duration)
					NewEndTime = hrStart*60 + minStart + duration
					events[i]['end']['dateTime'] = self.GetUTCtimezone([year, month, day, int(NewEndTime / 60), int(NewEndTime % 60)])
					self.service.events().patch(calendarId='primary', eventId=events[i]['id'], body=events[i]).execute()                                        


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

<<<<<<< HEAD
2019.12.16 Fix Issues
1. Blank block format
{
	'2019-12-12': [[8, 0], [16, 0], [17, 0], [24, 0]]
}

2. Final event can cross multiple days.
3. MaxEvent and 重新判斷會不會因為MaxEvent而無法放Preparation
'''

'''
>>>>>>> 021dc20a79aeffee8d21520a2834bcd548f0262d
