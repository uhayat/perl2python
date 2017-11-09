import os
import sys
import re

tabCounter = 0
DebugLog = False

logger = None
counter = 0

importList = dict()

def LOG(msg):
	global logger
	if logger == None:
		logger = open('log.txt','w+')
	logger.write(msg)

class Perl2Python():

	def __init__(self,inFilePath, outFilePath=None):
		# check in exist
		self.inFile = open(inFilePath)
		self.out = open(outFilePath,'w+')
	
	def write(self, data):
		print (data),
		self.out.write(data)

	def writeLine(self, data):
		self.out.write(data + '\n')

	def addIndent(self, count):
		self.write('\t'*count)

	def checkSpecialVariable(self, varName):
		varName = varName.strip()
		LOG("checkSpecialVariable(): " +varName+'\n')
		
		lenOp = False
		if varName.startswith('#'):
			lenOp = True
			varName = varName.lstrip('#')

		if varName == '_':
			varName = 'param1'
		elif varName == '!':
			varName = 'returnStatus'
		elif varName == '?':
			varName = 'rCode'
		elif varName.startswith('ARGV'):
			varName = 'sys.argv' + varName[4:]

		if lenOp:
			return "len(" + varName + ")"
		return varName

	def replaceVarInString(self, line):
		LOG("replaceVarInString():" + line + '\n')

		mo = re.match('(.*)\$(#?[a-zA-Z1-9_!]+){(.*)}(.*)', line)
		if mo:
			LOG("Found with array \n")
			left = mo.group(1)
			varName = mo.group(2)
			index = mo.group(3)
			right = mo.group(4)
			LOG('FWA1: ' + left + '~~' + varName + '["' + index + '"]' + '~~' + right  + '\n')
			if left.startswith('"'): left = left +'"'
			left2 = self.parseExpression(left)
			middle = self.checkSpecialVariable(varName) + '["' + index + '"]'
			if right.endswith('"'): right = '"' + right
			right2 = self.parseExpression(right)
			LOG('FWA2: ' + left2 + '~~' + middle + '~~' + right2 + '\n')
			LOG('FWA3: ' + left2 + ' + ' + middle + ' + ' + right2 + '\n')

			left = left2
			right = right2

			if left != '': left = left + ' + '
			if right != '': right =  ' + ' + right

			if left == '"" + ': left = ''
			if right == ' + ""': right = ''
			
			newStr = left + middle + right
			LOG('final: ' + newStr + '\n')
			return newStr
		
		mo = re.match('(.*)\$(#?[a-zA-Z1-9_!]+)(.*)', line)
		if False:
			LOG("Found with array \n")
			left = mo.group(1)
			varName = mo.group(2)
			right = mo.group(3)
			if left.startswith('"'): left = left +'"'
			if right.startswith('"'): right = '"' + right

			newStr = self.replaceVarInString(left) + ' + ' + self.checkSpecialVariable(varName) + ' + ' + self.replaceVarInString(right)
			LOG('final:\n' + newStr + '\n')
			return newStr
			

		mo = re.match('(.*)\$(#?[a-zA-Z1-9_!\?]+)(.*)', line)
		if mo:
			LOG("Found \n")
			left = mo.group(1)
			middle = mo.group(2)
			right = mo.group(3)
			LOG('F1: ' + left + '~~' + middle + '~~' + right + '\n')
			newStr = ''
			if left != "":
				if left.startswith('"'): 
					left = left + '"'
				newStr = left + ' + '
			middle = self.checkSpecialVariable(middle)
			LOG('F2: ' + left + '~~' + middle + '~~' + right + '\n')
			postVar = ''
			if right != "":
				if right.endswith('"'):
					right = '"'+ right
				postVar = ' + ' + right
			m3 = re.match('{([a-zA-Z-!#]*)}(.*)', right)
			if m3:
				LOG("Found 0\n")
				dictIndex = m3.group(1)
				fourthVal = m3.group(2)
				if fourthVal == '"' : fourthVal = ""
				postVar = '["' + dictIndex +'"]'+ fourthVal

			newStr += middle  + postVar
			LOG(line+"\n")
			LOG(newStr+'\n')
			return newStr
		

		mo = re.match('(.*)\$\?(.*)', line)
		if mo:
			LOG('? found \n')
		return line

	def parseExpression(self, expression):
		LOG('parseExpression(): '+expression + '\n')
		expression = expression.strip()
		expression = expression.rstrip(';')
		expression = expression.strip()

		mo = re.match('(.*)"(.*)"(.*)', expression)
		if mo:
			left = mo.group(1)
			LOG('left: '+left + '\n')
			middle = mo.group(2)
			LOG('midle: '+middle + '\n')
			right = mo.group(3)
			LOG('right: '+right + '\n')

			middle = self.replaceVarInString('"' + middle + '"')
			LOG('midle2 handled: ' + left +'~' + middle + '~'+ right + '\n')
			right = self.parseExpression(right)
			LOG('midle3 handled: ' + left +'~' + middle + '~'+ right + '\n')

			return left + middle + right




		fixed = self.replaceVarInString(expression)
		#qout = False
		#if expression.startswith('"') and expression.endswith('"'):
		#	qout = True
			#expression = expression.strip('"')
		#expression = expression.replace('$','')
		#expression = expression.replace('{','[')
		#expression = expression.replace('}',']')
		
		#LOG('parseExpression(): fixed: '+fixed + '\n')
		#fixed = re.sub('""\s\+|\+\s""','',fixed)
		#LOG('parseExpression(): fixed2: '+fixed + '\n')
		#fixed = re.sub('\+\s"\s\+','+',fixed)

		return fixed

	def handleOpenFunction(self, argList):
		lst = argList.split(',')
		fileName = lst[1].strip()
		openMode = ''
		if fileName.find('>>') > 0:
			openMode = ", 'w+'"
			fileName = fileName.replace('>>','')
		fileName = self.parseExpression(fileName)
		self.write(lst[0].strip() + " = open(" + fileName + openMode + ")\n")

	def handleFunctionCall(self, line):
		
		mo = re.match('^\s*([a-zA-Z]*)\((.*)\)', line)
		if mo:
			#LOG('*** function detected...\n')
			#LOG(line)
			funcName = mo.group(1).strip()
			argList = mo.group(2).strip()
			self.addIndent(tabCounter)
			if funcName == 'system':
				funcName = 'rCode = system'
			elif funcName == 'open':
				self.handleOpenFunction(argList)
				return True
			
			# correct argList
			argList = self.parseExpression(argList)
			self.write(funcName + '(' + argList + ')\n')
			return True
		return False

	def handleIf(self, line):
		global tabCounter

		mo = re.match('}*\s*(if|elsif)\s*\((.*)\)(.*)\s*$', line)
		if mo:
			LOG("handleIf(): " + line + '\n')
			#self.write("ifcount " +  tabCounter)
			statement = mo.group(1)
			if statement == 'elsif': statement = 'elif'
			ifCondition = mo.group(2).strip()
			self.addIndent(tabCounter)
			self.write(statement + " " )
			m2 = re.match('(-e|-d)\s*"(.*)', ifCondition)
			if m2:
				LOG('FileExistCheck:\n')
				filePath = m2.group(2)
				filePath = self.parseExpression(filePath)
				ifCondition = 'os.path.exists('+filePath+')'
				self.write(ifCondition)
			else:
				self.arithmeticLines(ifCondition.strip())
			self.write(":\n")
			tabCounter += 1
			return True
		return False


	def handleElse(self, line):
		global tabCounter
		mo = re.match('\s*else\s*{*\s*$', line)
		if mo:
			#remember to remove } if present
			self.addIndent(tabCounter)
			self.write("else:\n")
			tabCounter += 1
			return True
		return False

	def handleWhile(self, line):
		global tabCounter
		line = line.strip()
		LOG('handleWhile(): ')

		#looping through every line in a FILE 
		mo = re.match('while\s*(.*)\<\>(.*)\s*(.*)$', line)
		if mo:
			LOG('LoopLineInFile2:')
			self.addIndent(tabCounter)
			self.write("import fileinput\n")
			importList['fileinput'] = 1
			self.addIndent(tabCounter)
			self.write("for line in fileinput.input():\n")
			return True

		#looping through every line in a FILE 
		mo = re.match('while\s*\((.*)\s*=\s*\<(.*)\>(.*)\s*(.*)$', line)
		if mo:
			LOG('LoopLineInFile2: ')
			varName = mo.group(1).lstrip('$ ')
			fileObject = mo.group(2)
			self.addIndent(tabCounter)
			self.write("for "+varName+" in "+fileObject+".readlines():\n")
			tabCounter += 1
			return True

		#looping through STDIN (while loop)
		mo = re.match('\s*while\s*(.*)\<STDIN\>(.*)\s*(.*)\s*$', line)
		if mo:
			LOG('SDTIN : ')
			self.addIndent(tabCounter)
			self.write("import sys\n")
			self.addIndent(tabCounter)
			self.write("for line in sys.stdin:\n")
			return True

		mo = re.match('(.*)\s*while\s*\((.*)\)(.*)\s*$', line)
		if mo:
			LOG('Simple While:')
			mb = re.match('(.*)\s*while\s*\((.*)\s*\<STDIN\>\s*\)(.*)\s*$', line) #stdin   
			if mb:
				self.addIndent(tabCounter)
				self.write("for line in sys.stdin:")
			else:
				whileCondition = mo.group(2)
				self.addIndent(tabCounter)
				self.write("while (")
				self.arithmeticLines(whileCondition)
				self.write("):\n")
				tabCounter += 1
			return True

		return False

	def replaceComparisonOperators(self, param1):
		
		#comparison operators that dont exist in Python replaced with those that do
		param1 = param1.replace( 'eq','==')
		param1 = param1.replace( 'ne','!=')
		param1 = param1.replace( 'gt','>')
		param1 = param1.replace( 'lt','<')
		param1 = param1.replace( 'ge','>=')
		param1 = param1.replace( 'le','<=')
		return param1

	def evaluateLogical(self, expression):
		LOG('evaluateLogical(): '+ expression + '\n')
		expression = expression.strip()
		mo = re.match('^(.*)(&&|\|\|)(.*)$',expression)
		if mo and expression != "":
			LOG('&& || Group: \n')
			left = mo.group(1)
			operator = mo.group(2)
			right = mo.group(3)
			LOG("!! Logical [%s] %s [%s]\n"%(left, operator,right))
			return self.evaluateLogical(left) + ' ' + operator + ' ' + self.evaluateLogical(right)

		expression = self.replaceComparisonOperators(expression)
		m1 = re.match('(.*)\s*(=\~)\s*(.*)',expression)
		if m1:
			LOG('+++++ ' + expression + '\n')
			LOG('++++! ' + m1.group(2) + '\n')
			LOG('++++~' + self.checkSpecialVariable(m1.group(1).strip('$@')) + '\n')
			return self.checkSpecialVariable(m1.group(1).strip('$@')) + ' =~ "' + m1.group(3) + '"'

		m2 = re.match('(.*)\s*(==|!=|<=?|>=?)\s*(.*)',expression)
		if m2:
			LOG('~~~~ ' + expression + '\n')
			LOG('~~~! ' + m2.group(2) + '\n')
			return self.parseExpression(m2.group(1)) + ' ' + m2.group(2) + ' ' + self.parseExpression(m2.group(3))
		return  self.parseExpression (expression)

	def arithmeticLines(self, param1):
		LOG('arithmeticLines(): '+ param1 + '\n')

		#param1 = replaceComparisonOperators(param1)

		param1 = self.evaluateLogical(param1)

		#stdin
		param1 = param1.replace('<STDIN>','float(sys.stdin.readline())')

		#and/or/not
		param1 = param1.replace('&&', ' and ') 
		param1 = param1.replace('||', ' or ')
		param1 = param1.replace('!', ' not ')


		#division
		param1 = param1.replace('/','//')

		#remove that semicolon
		param1 = param1.rstrip(';')
		self.write(param1)

	def handleVarName(self, varName):
		matchObj = re.match('(.*){(.*)}', varName.strip())
		if matchObj:
			dictVar = matchObj.group(1)
			dictIndex = matchObj.group(2)
			if dictVar == 'ENV':
				dictVar = 'os.environ'
			return dictVar + '["' + dictIndex + '"]'
		return varName

	def handleComments(self, line):
		mo = re.match('\s*#', line) or line.strip() == ''
		if mo:
			self.addIndent(tabCounter)
			self.write(line.strip() + "\n")
			return True
		return False

	def handleForEach(self, line):
		global tabCounter

		#self.write(tabCounter
		mo = re.match('\s*foreach\s*\((.*)\)\s*$', line)
		if mo:
			#LOG("foreach detected\n")
			#LOG(line)
			lst = mo.group(1)
			#LOG("["+lst+"]\n")
			#for loops (If in C style then no direct comparison)?
			#foreach (with ARGV) (super specific, could do with broadening in scope)
			m2 = re.match('\s*foreach\s*\$(.*)\s*\((.*)\)\s*{\s*$', line)
			if m2:
				#foreach $i (0..$#ARGV) becomes for i in xrange (len(sys.argv) - 1):
				variableName = m2.group(1)
				self.addIndent(tabCounter)
				self.write("for " + variableName + " in xrange (len(sys.argv) - 1):\n")
				tabCounter += 1
				return True
			
			lstName = lst.lstrip('@')
			#LOG(lstName)
			if lstName == '_': lstName = 'param1'
			
			self.addIndent(tabCounter)
			self.write("for param1 in "+lstName+":\n")
			tabCounter += 1
			return True

		return False

	def handlePrint(self, line):
		line = line.strip('; ')

		#print statement with newline
		mo = re.match('^print\s*(.*)"(.*)"$', line)
		if mo:
			target = mo.group(1).strip()
			#printInput = '"' + mo.group(2) + '"'
			printInput =  mo.group(2)
			self.addIndent(tabCounter)
			if target != '':
				self.write(target + '.write("' + self.parseExpression(printInput) + '")\n')
			else:
				self.write('print "' + self.parseExpression(printInput) + '"\n')
			return True
		

		#print statment with no newline
		mo = re.match('\s*print\s*"(.*)"[\s;]*$', line)
		if mo:
			printInput = mo.group(1)
			self.addIndent(tabCounter)
			self.write("print (\""+printInput+"\")\n")
			return True
		#print statment with no newline
		mo = re.match('\s*print\s*"(.*)"[\s;]*$', line)
		if mo:
			printInput = mo.group(1)
			self.addIndent(tabCounter)
			self.write("print (\""+printInput+"\")\n")
			return True
		return False
		

	def handleSed(self, sedExp):
		LOG('handleSed(): '+ sedExp)
		sedExp = sedExp.strip(' ;')
		return "evalSed('" + sedExp + "')"

	#
	def handleVarAssignment(self, line):
		line = line.strip()
		# local variable declaration 
		mo = re.match('my\s+(.*)\s*=\s*(.*)[\s;]*$', line)
		if mo:
			varName = mo.group(1)
			varName = varName.strip('$')
			varName = self.checkSpecialVariable(varName)
			expression = mo.group(2)
			self.addIndent(tabCounter)
			self.write(varName + " = " + self.parseExpression(expression).strip() + "\n")
			return True

		# global variable declaration 
		mo = re.match('\s*[\$@](.*)\s*=\s*(.*)$', line)
		if mo:
			varName = mo.group(1)
			varName = self.checkSpecialVariable(varName)
			expression = mo.group(2)
			self.addIndent(tabCounter)
			LOG("global variable: "+ expression + '\n')
			# check if it is a sed expression
			if len(expression) > 0 and expression[0] == '~':
				self.write(self.handleVarName(varName) + " = " + self.handleSed(expression[1:]) + "\n")
				return True

			self.write(self.handleVarName(varName) + " = " + self.parseExpression(expression) + "\n")
			return True
		return False

	def DoConversion(self):
		global counter
		global tabCounter

		# File iterate
		for line in self.inFile.readlines():
			counter += 1
			LOG("line "+str(counter)+": " +  line)
			line = line.strip()

			#self.write( " tabCounter "+  tabCounter)

			#NOTE: Deal with semicolons on a line by line basis

			# translate #! line 
			if line.startswith('#!') and counter == 1:
				self.write( "#!/usr/bin/python2.7 -u\n")
				continue

			# Blank & comment lines (unchanged)
			if self.handleComments(line):
				continue

			# variable initialization 
			if self.handleVarAssignment(line):
				continue

			#break/continue	
			mo = re.match('last;$', line)
			if mo:
				self.addIndent(tabCounter)
				self.write( "break\n")
				continue

			mo = re.match('next;$', line)
			if mo:
				self.addIndent(tabCounter)
				self.write( "continue\n")
				continue

			# if and elif
			if self.handleIf(line):
				continue

			# else
			if self.handleElse(line):
				continue

			# while loops
			if self.handleWhile(line):
				continue

			if self.handleForEach(line):
				continue

			#chomp from STDIN
			mo = re.match('chomp\s*\$(.*)\s*;$', line)
			if mo:
				self.addIndent(tabCounter);	
				self.write( mo.group(1) + " = sys.stdin.readlines()\n")
				continue


			# sub routines
			mo = re.match('^\s*sub\s+(.*)\s*\((.*)\)$', line)
			if mo:
				funcProto = mo.group(1)
				paramName = mo.group(2)
				if paramName == '$':
					paramName = 'param1'
				self.write( "def " + funcProto + "("+paramName+"):\n")
				tabCounter += 1
				continue
			
			# sub routines without paranthesis
			mo = re.match('^\s*sub\s+(.*)\s*$', line)
			if mo:
				funcProto = mo.group(1)
				self.write( "def " + funcProto + "():\n")
				tabCounter += 1
				continue

			#push
			mo = re.match('^\s*push\s*\(\s*\@(.*)\,\s*(.*)\)\s*;$', line)
			if mo:
				self.addIndent(tabCounter)
				self.write( mo.group(1) + ".push(" + mo.group(2).strip('$') + ")\n")
				continue

			#pop
			mo = re.match('^\s*pop\s*\@(.*);$', line)
			if mo:
				self.addIndent(tabCounter)
				self.write( mo.group(1) + ".pop()\n")
				continue

			#unshift
			mo = re.match('^\s*unshift\s*\@(.*)\,\s*(.*)\s*;$', line)
			if mo:
				self.addIndent(tabCounter)
				self.write( mo.group(1) + ".unshift(" + mo.group(2) + ")\n")
				continue

			#pop
			mo = re.match('^\s*shift\s*\@(.*);$', line)
			if mo:
				self.addIndent(tabCounter)
				self.write( mo.group(1) + ".shift\n")
				continue

			if self.handleFunctionCall(line):
				self.write( '')
				continue
			#self.handleFunctionCall(line)

			#LOG('5\n')
			#print statement with newline
			if self.handlePrint(line):
				continue

			#split
			mo = re.match('(.*)\s*=\s*split\(\/(.*)\/,\s*\$(.*)\)\s*;', line)
			if mo:
				string = mo.group(3)
				delineator = mo.group(2)
				assignmentVariable = mo.group(1)
				self.addIndent(tabCounter)
				self.write( assignmentVariable + " = " + string + '.split("' + delineator + '")\n')
				continue

			#join
			mo = re.match('(.*)\s*=\s*join\(\'(.*)\'\,\s*(.*)\)\s*;$', line)
			if mo:
				assignmentVariable = mo.group(1)
				string = mo.group(3)
				delineator = mo.group(2)
				self.addIndent(tabCounter)
				self.write( assignmentVariable + '= ' + delineator + '.join(['+string+ '])')
				continue

			LOG("*********\n")
			LOG(line + '\n')
			#arithmetic operations
			mo = re.match('[^\s]*\s*=(.*);$', line)
			if mo:
				if mo == re.match('\@(.*)\s*=\s*(.*);$', line): #arrays are dealt with seperately
					next
				else:
					self.addIndent(tabCounter)
					self.arithmeticLines(line)

			# ++ and --
			mo = re.match('(.*)\s*\+\+(.*);$', line) 
			if mo:
				# change ++ and -- to python equivalents
				self.addIndent(tabCounter)
				plusPlus = mo.group(1)
				plusPlus = plusPlus.replace('$','')
				self.write( plusPlus +"+=1")
				continue

			mo = re.match('(.*)\s*\-\-(.*);$', line)
			if mo:
				self.addIndent(tabCounter)
				minusMinus = mo.group(1)
				minusMinus = minusMinus.replace('$','')
				self.write( minusMinus +"-= 1")
				continue

			# return 
			mo = re.match('^\s*return\s*(.*)', line)
			if mo:
				self.addIndent(tabCounter)
				self.write( 'return ' + self.parseExpression( mo.group(1) ) + '\n')
				continue

			#end curly brace needs removal
			mo = re.match('^\s*[}]\s*$', line)
			if mo:
				#line = line.replace('}','')
				tabCounter -= 1
				continue

			#end curly brace needs removal
			mo = re.match('\s*{\s*$', line)
			if mo:
				#line = line.replace('{}}','')
				#tabCounter -= 1
				continue

			#ARRAY HANDLING
			#array conversion
			mo = re.match('(.*)\s*\@(.*)\s*(.*)\s*;$', line) #array in the line	
			if mo:
				arrayName = mo.group(2)
				if '/^\s*(.*)\s*\@(.*)\s*=\s*((.*))\s*;$' == 1: #declaring the array
					line = line.replace('@','')
					line = line.replace('(','[')
					line = line.replace(')',']')
					line = line.replace('"',"'")
					line = line.replace(';','')
					self.write( line )
				else: #accessing the array
					#  $arrayName[0 or whatever];
					line = line.replace('@','')
					line = line.replace(';','')
					self.write( line )

			# simple string
			mo = re.match('^"(.*)', line)
			if mo:
				self.addIndent(tabCounter)
				self.write( line )
				continue

			# It is some thing else 
			self.write( "#"+ line + '\n')

def main():

	inputFilePath = sys.argv[1]
	if not os.path.exists(inputFilePath):
		print ("Error: input file ["+ inputFilePath + "] does not exist")
		exit(1)

	#inputFile = open(inputFilePath)
	#out = open('out.py','w+')
	p2p = Perl2Python(inputFilePath,'out.py')
	p2p.DoConversion()

if __name__ == '__main__':
	if len(sys.argv) <2:
		print ("Error: Please provide input file")
		exit(1) 
	main()
