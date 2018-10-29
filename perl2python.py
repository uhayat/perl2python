import os
import sys
import re
import argparse

class Perl2Python():

	def __init__(self,inFilePath, outFilePath=None):

		self.inFile = open(inFilePath)
		self.out = open(outFilePath,'w+')
		self.tabCounter = 0
		self.lineCounter = 0
		self.logger = None
		self.logFile = 'log.txt'
		self.importList = dict()
		self.DebugLog = False
		self.verbose = False

	def LOG(self, msg):
		if not self.DebugLog:
			return

		if self.logger == None:
			self.logger = open(self.logFile,'w+')
		self.logger.write(msg)

	def increamentTab(self):
		self.tabCounter += 1
	
	def write(self, data):
		print (data),
		self.out.write(data)

	def writeLine(self, data):
		self.out.write(data + '\n')

	def writeIndent(self):
		self.write('\t'* self.tabCounter)

	def checkSpecialVariable(self, varName):
		varName = varName.strip()
		self.LOG("checkSpecialVariable(): " +varName+'\n')
		
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
		self.LOG("replaceVarInString():" + line + '\n')

		mo = re.match('(.*)\$(#?[a-zA-Z1-9_!]+){(.*)}(.*)', line)
		if mo:
			self.LOG("Found with array \n")
			left = mo.group(1)
			varName = mo.group(2)
			index = mo.group(3)
			right = mo.group(4)
			self.LOG('FWA1: ' + left + '~~' + varName + '["' + index + '"]' + '~~' + right  + '\n')
			if left.startswith('"'): left = left +'"'
			left2 = self.parseExpression(left)
			middle = self.checkSpecialVariable(varName) + '["' + index + '"]'
			if right.endswith('"'): right = '"' + right
			right2 = self.parseExpression(right)
			self.LOG('FWA2: ' + left2 + '~~' + middle + '~~' + right2 + '\n')
			self.LOG('FWA3: ' + left2 + ' + ' + middle + ' + ' + right2 + '\n')

			left = left2
			right = right2

			if left != '': left = left + ' + '
			if right != '': right =  ' + ' + right

			if left == '"" + ': left = ''
			if right == ' + ""': right = ''
			
			newStr = left + middle + right
			self.LOG('final: ' + newStr + '\n')
			return newStr
		
		mo = re.match('(.*)\$(#?[a-zA-Z1-9_!]+)(.*)', line)
		if False:
			self.LOG("Found with array \n")
			left = mo.group(1)
			varName = mo.group(2)
			right = mo.group(3)
			if left.startswith('"'): left = left +'"'
			if right.startswith('"'): right = '"' + right

			newStr = self.replaceVarInString(left) + ' + ' + self.checkSpecialVariable(varName) + ' + ' + self.replaceVarInString(right)
			self.LOG('final:\n' + newStr + '\n')
			return newStr
			

		mo = re.match('(.*)\$(#?[a-zA-Z1-9_!\?]+)(.*)', line)
		if mo:
			self.LOG("Found \n")
			left = mo.group(1)
			middle = mo.group(2)
			right = mo.group(3)
			self.LOG('F1: ' + left + '~~' + middle + '~~' + right + '\n')
			newStr = ''
			if left != "":
				if left.startswith('"'): 
					left = left + '"'
				newStr = left + ' + '
			middle = self.checkSpecialVariable(middle)
			self.LOG('F2: ' + left + '~~' + middle + '~~' + right + '\n')
			postVar = ''
			if right != "":
				if right.endswith('"'):
					right = '"'+ right
				postVar = ' + ' + right
			m3 = re.match('{([a-zA-Z-!#]*)}(.*)', right)
			if m3:
				self.LOG("Found 0\n")
				dictIndex = m3.group(1)
				fourthVal = m3.group(2)
				if fourthVal == '"' : fourthVal = ""
				postVar = '["' + dictIndex +'"]'+ fourthVal

			newStr += middle  + postVar
			self.LOG(line+"\n")
			self.LOG(newStr+'\n')
			return newStr
		

		mo = re.match('(.*)\$\?(.*)', line)
		if mo:
			self.LOG('? found \n')
		return line

	def parseExpression(self, expression):
		self.LOG('parseExpression(): '+expression + '\n')
		expression = expression.strip()
		expression = expression.rstrip(';')
		expression = expression.strip()

		mo = re.match('(.*)"(.*)"(.*)', expression)
		if mo:
			left = mo.group(1)
			self.LOG('left: '+left + '\n')
			middle = mo.group(2)
			self.LOG('midle: '+middle + '\n')
			right = mo.group(3)
			self.LOG('right: '+right + '\n')

			middle = self.replaceVarInString('"' + middle + '"')
			self.LOG('midle2 handled: ' + left +'~' + middle + '~'+ right + '\n')
			right = self.parseExpression(right)
			self.LOG('midle3 handled: ' + left +'~' + middle + '~'+ right + '\n')

			return left + middle + right

		fixed = self.replaceVarInString(expression)

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
			#self.LOG('*** function detected...\n')
			#self.LOG(line)
			funcName = mo.group(1).strip()
			argList = mo.group(2).strip()
			self.writeIndent()
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
		

		mo = re.match('}*\s*(if|elsif)\s*\((.*)\)(.*)\s*$', line)
		if mo:
			self.LOG("handleIf(): " + line + '\n')
			#self.write("ifcount " +  self.tabCounter)
			statement = mo.group(1)
			if statement == 'elsif': statement = 'elif'
			ifCondition = mo.group(2).strip()
			self.writeIndent()
			self.write(statement + " " )
			m2 = re.match('(-e|-d)\s*"(.*)', ifCondition)
			if m2:
				self.LOG('FileExistCheck:\n')
				filePath = m2.group(2)
				filePath = self.parseExpression(filePath)
				ifCondition = 'os.path.exists('+filePath+')'
				self.write(ifCondition)
			else:
				self.arithmeticLines(ifCondition.strip())
			self.write(":\n")
			self.increamentTab()
			return True
		return False


	def handleElse(self, line):
		
		mo = re.match('\s*else\s*{*\s*$', line)
		if mo:
			#remember to remove } if present
			self.writeIndent()
			self.write("else:\n")
			self.increamentTab()
			return True
		return False

	def handleWhile(self, line):
		
		line = line.strip()
		self.LOG('handleWhile(): ')

		#looping through every line in a FILE 
		mo = re.match('while\s*(.*)\<\>(.*)\s*(.*)$', line)
		if mo:
			self.LOG('LoopLineInFile2:')
			self.writeIndent()
			self.write("import fileinput\n")
			self.importList['fileinput'] = 1
			self.writeIndent()
			self.write("for line in fileinput.input():\n")
			return True

		#looping through every line in a FILE 
		mo = re.match('while\s*\((.*)\s*=\s*\<(.*)\>(.*)\s*(.*)$', line)
		if mo:
			self.LOG('LoopLineInFile2: ')
			varName = mo.group(1).lstrip('$ ')
			fileObject = mo.group(2)
			self.writeIndent()
			self.write("for "+varName+" in "+fileObject+".readlines():\n")
			self.increamentTab()
			return True

		#looping through STDIN (while loop)
		mo = re.match('\s*while\s*(.*)\<STDIN\>(.*)\s*(.*)\s*$', line)
		if mo:
			self.LOG('SDTIN : ')
			self.writeIndent()
			self.write("import sys\n")
			self.writeIndent()
			self.write("for line in sys.stdin:\n")
			return True

		mo = re.match('(.*)\s*while\s*\((.*)\)(.*)\s*$', line)
		if mo:
			self.LOG('Simple While:')
			mb = re.match('(.*)\s*while\s*\((.*)\s*\<STDIN\>\s*\)(.*)\s*$', line) #stdin   
			if mb:
				self.writeIndent()
				self.write("for line in sys.stdin:")
			else:
				whileCondition = mo.group(2)
				self.writeIndent()
				self.write("while (")
				self.arithmeticLines(whileCondition)
				self.write("):\n")
				self.increamentTab()
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
		self.LOG('evaluateLogical(): '+ expression + '\n')
		expression = expression.strip()
		mo = re.match('^(.*)(&&|\|\|)(.*)$',expression)
		if mo and expression != "":
			self.LOG('&& || Group: \n')
			left = mo.group(1)
			operator = mo.group(2)
			right = mo.group(3)
			self.LOG("!! Logical [%s] %s [%s]\n"%(left, operator,right))
			return self.evaluateLogical(left) + ' ' + operator + ' ' + self.evaluateLogical(right)

		expression = self.replaceComparisonOperators(expression)
		m1 = re.match('(.*)\s*(=\~)\s*(.*)',expression)
		if m1:
			self.LOG('+++++ ' + expression + '\n')
			self.LOG('++++! ' + m1.group(2) + '\n')
			self.LOG('++++~' + self.checkSpecialVariable(m1.group(1).strip('$@')) + '\n')
			return self.checkSpecialVariable(m1.group(1).strip('$@')) + ' =~ "' + m1.group(3) + '"'

		m2 = re.match('(.*)\s*(==|!=|<=?|>=?)\s*(.*)',expression)
		if m2:
			self.LOG('~~~~ ' + expression + '\n')
			self.LOG('~~~! ' + m2.group(2) + '\n')
			return self.parseExpression(m2.group(1)) + ' ' + m2.group(2) + ' ' + self.parseExpression(m2.group(3))
		return  self.parseExpression (expression)

	def arithmeticLines(self, param1):
		self.LOG('arithmeticLines(): '+ param1 + '\n')

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
			self.writeIndent()
			self.write(line.strip() + "\n")
			return True
		return False

	def handleForEach(self, line):
		

		#self.write(self.tabCounter
		mo = re.match('\s*foreach\s*\((.*)\)\s*$', line)
		if mo:
			#self.LOG("foreach detected\n")
			#self.LOG(line)
			lst = mo.group(1)
			#self.LOG("["+lst+"]\n")
			#for loops (If in C style then no direct comparison)?
			#foreach (with ARGV) (super specific, could do with broadening in scope)
			m2 = re.match('\s*foreach\s*\$(.*)\s*\((.*)\)\s*{\s*$', line)
			if m2:
				#foreach $i (0..$#ARGV) becomes for i in xrange (len(sys.argv) - 1):
				variableName = m2.group(1)
				self.writeIndent()
				self.write("for " + variableName + " in xrange (len(sys.argv) - 1):\n")
				self.increamentTab()
				return True
			
			lstName = lst.lstrip('@')
			#self.LOG(lstName)
			if lstName == '_': lstName = 'param1'
			
			self.writeIndent()
			self.write("for param1 in "+lstName+":\n")
			self.increamentTab()
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
			self.writeIndent()
			if target != '':
				self.write(target + '.write("' + self.parseExpression(printInput) + '")\n')
			else:
				self.write('print "' + self.parseExpression(printInput) + '"\n')
			return True
		

		#print statment with no newline
		mo = re.match('\s*print\s*"(.*)"[\s;]*$', line)
		if mo:
			printInput = mo.group(1)
			self.writeIndent()
			self.write("print (\""+printInput+"\")\n")
			return True
		#print statment with no newline
		mo = re.match('\s*print\s*"(.*)"[\s;]*$', line)
		if mo:
			printInput = mo.group(1)
			self.writeIndent()
			self.write("print (\""+printInput+"\")\n")
			return True
		return False
		

	def handleSed(self, sedExp):
		self.LOG('handleSed(): '+ sedExp)
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
			self.writeIndent()
			self.write(varName + " = " + self.parseExpression(expression).strip() + "\n")
			return True

		# global variable declaration 
		mo = re.match('\s*[\$@](.*)\s*=\s*(.*)$', line)
		if mo:
			varName = mo.group(1)
			varName = self.checkSpecialVariable(varName)
			expression = mo.group(2)
			self.writeIndent()
			self.LOG("global variable: "+ expression + '\n')
			# check if it is a sed expression
			if len(expression) > 0 and expression[0] == '~':
				self.write(self.handleVarName(varName) + " = " + self.handleSed(expression[1:]) + "\n")
				return True

			self.write(self.handleVarName(varName) + " = " + self.parseExpression(expression) + "\n")
			return True
		return False

	def DoConversion(self):

		# File iterate
		for line in self.inFile.readlines():
			self.lineCounter += 1
			self.LOG("line "+str(self.lineCounter)+": " +  line)
			line = line.strip()

			#self.write( " self.tabCounter "+  self.tabCounter)

			#NOTE: Deal with semicolons on a line by line basis

			# translate #! line 
			if line.startswith('#!') and self.lineCounter == 1:
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
				self.writeIndent()
				self.write( "break\n")
				continue

			mo = re.match('next;$', line)
			if mo:
				self.writeIndent()
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
				self.writeIndent();	
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
				self.increamentTab()
				continue
			
			# sub routines without paranthesis
			mo = re.match('^\s*sub\s+(.*)\s*$', line)
			if mo:
				funcProto = mo.group(1)
				self.write( "def " + funcProto + "():\n")
				self.increamentTab()
				continue

			#push
			mo = re.match('^\s*push\s*\(\s*\@(.*)\,\s*(.*)\)\s*;$', line)
			if mo:
				self.writeIndent()
				self.write( mo.group(1) + ".push(" + mo.group(2).strip('$') + ")\n")
				continue

			#pop
			mo = re.match('^\s*pop\s*\@(.*);$', line)
			if mo:
				self.writeIndent()
				self.write( mo.group(1) + ".pop()\n")
				continue

			#unshift
			mo = re.match('^\s*unshift\s*\@(.*)\,\s*(.*)\s*;$', line)
			if mo:
				self.writeIndent()
				self.write( mo.group(1) + ".unshift(" + mo.group(2) + ")\n")
				continue

			#pop
			mo = re.match('^\s*shift\s*\@(.*);$', line)
			if mo:
				self.writeIndent()
				self.write( mo.group(1) + ".shift\n")
				continue

			if self.handleFunctionCall(line):
				self.write( '')
				continue
			#self.handleFunctionCall(line)

			#self.LOG('5\n')
			#print statement with newline
			if self.handlePrint(line):
				continue

			#split
			mo = re.match('(.*)\s*=\s*split\(\/(.*)\/,\s*\$(.*)\)\s*;', line)
			if mo:
				string = mo.group(3)
				delineator = mo.group(2)
				assignmentVariable = mo.group(1)
				self.writeIndent()
				self.write( assignmentVariable + " = " + string + '.split("' + delineator + '")\n')
				continue

			#join
			mo = re.match('(.*)\s*=\s*join\(\'(.*)\'\,\s*(.*)\)\s*;$', line)
			if mo:
				assignmentVariable = mo.group(1)
				string = mo.group(3)
				delineator = mo.group(2)
				self.writeIndent()
				self.write( assignmentVariable + '= ' + delineator + '.join(['+string+ '])')
				continue

			self.LOG("*********\n")
			self.LOG(line + '\n')
			#arithmetic operations
			mo = re.match('[^\s]*\s*=(.*);$', line)
			if mo:
				if mo == re.match('\@(.*)\s*=\s*(.*);$', line): #arrays are dealt with seperately
					next
				else:
					self.writeIndent()
					self.arithmeticLines(line)

			# ++ and --
			mo = re.match('(.*)\s*\+\+(.*);$', line) 
			if mo:
				# change ++ and -- to python equivalents
				self.writeIndent()
				plusPlus = mo.group(1)
				plusPlus = plusPlus.replace('$','')
				self.write( plusPlus +"+=1")
				continue

			mo = re.match('(.*)\s*\-\-(.*);$', line)
			if mo:
				self.writeIndent()
				minusMinus = mo.group(1)
				minusMinus = minusMinus.replace('$','')
				self.write( minusMinus +"-= 1")
				continue

			# return 
			mo = re.match('^\s*return\s*(.*)', line)
			if mo:
				self.writeIndent()
				self.write( 'return ' + self.parseExpression( mo.group(1) ) + '\n')
				continue

			#end curly brace needs removal
			mo = re.match('^\s*[}]\s*$', line)
			if mo:
				#line = line.replace('}','')
				self.tabCounter -= 1
				continue

			#end curly brace needs removal
			mo = re.match('\s*{\s*$', line)
			if mo:
				#line = line.replace('{}}','')
				#self.tabCounter -= 1
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
				self.writeIndent()
				self.write( line )
				continue

			# It is some thing else 
			self.write( "#"+ line + '\n')

def _createParser():
	parser = argparse.ArgumentParser(description='perl2python Commands help.')
	parser.add_argument("-i", "--inputfile",
						metavar=(('inputfile')),
						required=True,
						help="Perl file to be precessed.")
	parser.add_argument("-o", "--ouputfile",
						metavar=(('ouputfile')),
						required=True,
						help="Output python file name.")
	return parser

def main():
	parser = _createParser()
	args = parser.parse_args()

	inputFilePath = args.inputfile
	ouputFilePath = args.ouputfile
	if not os.path.exists(inputFilePath):
		print ("Error: input file [{}] does not exist".format(inputFilePath))
		exit(1)

	pe2py = Perl2Python(inputFilePath, ouputFilePath)
	pe2py.DoConversion()

if __name__ == '__main__':
	main()
