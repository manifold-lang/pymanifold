import sys

mappingFilePath = "manifoldToModelicaMapping.txt"
manifoldOutputFilePath = ""
mappedOutputFilePath = "result.txt"


def main():
	setupPaths()
	
	mappingDict = createMappingDict(mappingFilePath)

	mappedDict = createMappedDict(manifoldOutputFilePath, mappingDict)

	createNewFile(mappedDict)

def setupPaths():
	global manifoldOutputFilePath
	global mappingFilePath
	numberOfArgs = len(sys.argv)
	
	if numberOfArgs == 2:
		manifoldOutputFilePath = sys.argv[1]
		print("Output file path " + manifoldOutputFilePath)
		print("Mapping input file path " + mappingFilePath)
	if numberOfArgs == 3:
		manifoldOutputFilePath = sys.argv[1]
		mappingFilePath = sys.argv[2]
		print("Output file path " + manifoldOutputFilePath)
		print("Mapping input file path " + mappingFilePath)
	else:
		sys.stderr.write(
			"At least 1 Input required, <ManifoldOutputFilePath> <MappingFilePath = optional>,\nFor example : python parser.py manifold_output.txt mapping.txt"
		)
		exit()

def createMappingDict(mappingFile):
	# Create mapping dictionary using mapping file
	f = open(mappingFile, "r")
	mappingDict = {}
	for line in f:
		line = line.replace(" ","").split(":")
		mappedKey = line[0].strip()
		manifoldOutputKey = line[1].strip()
		mappingDict[mappedKey] = manifoldOutputKey
	f.close()
	return mappingDict


def createMappedDict(manifoldOutputFile, mappingDict):
	# create mapped dictionary with output values and labels
	f = open(manifoldOutputFile, "r")
	mappedDict = {}
	for line in f:
		line = line.strip().replace(" ","").split(":")
		key = line[0].strip()
		if key in mappingDict:
			values = line[1][1:-1].split(",")
			result = (float(values[0]) + float(values[1]))/2
			mappedKey = mappingDict[key]
			mappedDict[mappedKey] = result
	f.close()
	return mappedDict

def createNewFile(resultDict):
	# generate output file
	f = open(mappedOutputFilePath,"w+")
	for key in resultDict:
		f.write(key + " = " + str(resultDict[key]) + "\n")
	f.close()
	print("Generated output can be find at " + mappedOutputFilePath)

if __name__ == '__main__':
	main()
