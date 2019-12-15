

class Preference:
	def __init__(self):
		self.workingHr = [[8,0],[20,0]]
		self.forbiddenHr = [[12,0],[13,0],[18,0],[19,0]]
		self.valuableHr = [[14,0],[18,0]]
		self.timeGap = 30 # minutes
		self.minimumDuration = 20 # minutes
		self.maxEvents = 5 # in a day

	def SetPreference(self,prefInfo):
		self.workingHr = prefInfo['workingHr']
		self.forbiddenHr = prefInfo['forbiddenHr']
		# and so on...