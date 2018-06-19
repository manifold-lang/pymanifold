
class FluidProperties():

	PROPERTIES = {"water":[999.87, 18200, 0.001],
				 "mineraloil": [800, 10000000000,0.0003051],
				 "polyacrylamide":[1100, 14.28,0.003]}

	def getDesnity(self, fluid_name):
		return self.PROPERTIES[fluid_name][0]

	def getResistivity(self, fluid_name):
		return self.PROPERTIES[fluid_name][1]
	
	def getViscosity(self, fluid_name):
		return self.PROPERTIES[fluid_name][2]
