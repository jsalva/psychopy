# Part of the PsychoPy library
# Copyright (C) 2009 Jonathan Peirce
# Distributed under the terms of the GNU General Public License (GPL).

import StringIO, sys
from components import *#getComponents('') and getAllComponents([])
import xml.dom.minidom #for saving files out
import xml.dom.ext#this come from installing pyxml (as well as the beasic xml included in python)

class IndentingBuffer(StringIO.StringIO):
    def __init__(self, *args, **kwargs):
        StringIO.StringIO.__init__(self, *args, **kwargs)
        self.oneIndent="    "
        self.indentLevel=0
    def writeIndented(self,text):
        """Write to the StringIO buffer, but add the current indent.
        Use write() if you don't want the indent.

        To test if the prev character was a newline use::
            self.getvalue()[-1]=='\n'

        """
        self.write(self.oneIndent*self.indentLevel + text)
    def setIndentLevel(self, newLevel, relative=False):
        """Change the indent level for the buffer to a new value.

        Set relative to True if you want to increment or decrement the current value.
        """
        if relative:
            self.indentLevel+=newLevel
        else:
            self.indentLevel=newLevel

class Experiment:
    """
    An experiment contains a single Flow and at least one
    Routine. The Flow controls how Routines are organised
    e.g. the nature of repeats and branching of an experiment.
    """
    def __init__(self):
        self.name=None
        self.flow = Flow(exp=self)#every exp has exactly one flow
        self.routines={}

        #this can be checked by the builder that this is an experiment and a compatible version
        self.psychopyVersion=psychopy.__version__ #imported from components
        self.psychopyLibs=['core','data', 'event']
        self.settings=getAllComponents()['SettingsComponent'](parentName='', exp=self)
        self._doc=None#this will be the xml.dom.minidom.doc object for saving
    def requirePsychopyLibs(self, libs=[]):
        """Add a list of top-level psychopy libs that the experiment will need.
        e.g. [visual, event]
        """
        if type(libs)!=list:
            libs=list(libs)
        for lib in libs:
            if lib not in self.psychopyLibs:
                self.psychopyLibs.append(lib)
    def addRoutine(self,routineName, routine=None):
        """Add a Routine to the current list of them.

        Can take a Routine object directly or will create
        an empty one if none is given.
        """
        if routine==None:
            self.routines[routineName]=Routine(routineName, exp=self)#create a deafult routine with this name
        else:
            self.routines[routineName]=routine

    def writeScript(self):
        """Write a PsychoPy script for the experiment
        """
        self.noKeyResponse=True#if keyboard is used (and data stored) this will be False
        s=IndentingBuffer(u'') #a string buffer object
        s.writeIndented('This experiment was created using PsychoPy2 Experiment Builder ')
        s.writeIndented("If you publish work using this script please cite the relevant papers (e.g. Peirce, 2007;2009)\n\n")

        #import psychopy libs
        libString=""; separator=""
        for lib in self.psychopyLibs:
            libString = libString+separator+lib
            separator=", "#for the second lib upwards we need a comma
        s.writeIndented("from numpy import * #many different maths functions\n")
        s.writeIndented("import os #handy system and path functions\n")
        s.writeIndented("from psychopy import %s\n" %libString)
        s.writeIndented("import psychopy.log #import like this so it doesn't interfere with numpy.log\n\n")

        self.settings.writeStartCode(s)#present info dlg, make logfile, Window
        #delegate rest of the code-writing to Flow
        self.flow.writeCode(s)
        self.settings.writeEndCode(s)#close log file

        return s
    def getUsedName(self, name):
        """Check the exp._usedNames dict and return None for unused or
        the type of object using it otherwise
        """
        #look for routines and loop names
        for flowElement in self.flow:
            if flowElement.getType()in ['LoopInitiator','LoopTerminator']:
                flowElement=flowElement.loop #we want the loop itself
            if flowElement.params['name']==name: return flowElement.getType()
        for routineName in self.routines.keys():
            for comp in self.routines[routineName]:
                if name==comp.params['name'].val: return comp.getType()
        return#we didn't find an existing name :-)
    def saveToXML(self, filename):
        #create the dom object
        doc = self._doc = xml.dom.minidom.Document()
        root=doc.createElement("PsychoPy2experiment")
        root.setAttribute('version', self.psychopyVersion)
        root.setAttribute('encoding', 'utf-8')
        doc.appendChild(root)
        ##in the following, anything beginning '
        #store settings
        settingsNode=doc.createElement('Settings')
        root.appendChild(settingsNode)
        for name, setting in self.settings.params.iteritems():
            settingNode=self._setXMLparam(parent=settingsNode,param=setting,name=name)
        #store routines
        routinesNode=doc.createElement('Routines')
        root.appendChild(routinesNode)
        for routineName, routine in self.routines.iteritems():#routines is a dict of routines
            routineNode = self._setXMLparam(parent=routinesNode,param=routine,name=routineName)
            for component in routine: #a routine is based on a list of components
                componentNode=self._setXMLparam(parent=routineNode,param=component,name=component.params['name'].val)
                for name, param in component.params.iteritems():
                    paramNode=self._setXMLparam(parent=componentNode,param=param,name=name)
        #implement flow
        flowNode=doc.createElement('Flow')
        root.appendChild(flowNode)
        for element in self.flow:#a list of elements(routines and loopInit/Terms)
            if element.getType() == 'LoopInitiator':
                loop=element.loop
                name = loop.params['name'].val      
                elementNode=doc.createElement(loop.getType())
                elementNode.setAttribute('name', name)
                for paramName, param in loop.params.iteritems():
                    paramNode = self._setXMLparam(parent=loopNode,param=param,name=paramName)
                    if paramName=='trialList': #override val with repr(val)
                        paramNode.setAttribute('val',repr(param.val))
            elif element.getType() == 'LoopTerminator':
                elementNode = doc.createElement('LoopTerminator')
                elementNode.setAttribute('loopTerminating', element.loop.params['name'].val)
            if element.getType() == 'Routine':
                elementNode = doc.createElement('Routine')
                elementNode.setAttribute('name', '%s' %element.params['name'])
            flowNode.appendChild(elementNode)
        #write to disk
        f=open(filename, 'wb')
        xml.dom.ext.PrettyPrint(doc, f)
        #f.write(self._doc.toxml())#simple printer doesn't work
        f.close()
    def _getShortName(self, longName):
        return longName.replace('(','').replace(')','').replace(' ','')
    def _setXMLparam(self,parent,param,name):
        """Add a new child to a given xml node.
        name can include spaces and parens, which will be removed to create child name
        """
        if hasattr(param,'getType'):
            thisType = param.getType()
        else: thisType='Param'
        thisChild = self._doc.createElement(thisType)
        thisChild.setAttribute('name',name)
        if hasattr(param,'val'): thisChild.setAttribute('val',str(param.val))
        if hasattr(param,'valType'): thisChild.setAttribute('valType',param.valType)
        if hasattr(param,'updates'): thisChild.setAttribute('updates',param.updates)
        parent.appendChild(thisChild)
        return thisChild
    def _getXMLparam(self,params,paramNode):
        """params is the dict of params of the builder component (e.g. stimulus) into which
        the parameters will be inserted (so the object to store the params should be created first)
        paramNode is the parameter node fetched from the xml file
        """
        name=paramNode.getAttribute('name')
        if hasattr(param,'val'): params[name].val = paramNode.getAttribute('val')
        if child.hasAttribute('valType'): params[name].valType = child.getAttribute('valType')
        if child.hasAttribute('updates'): params[name].updates = child.getAttribute('updates')
    def loadFromXML(self, filename):
        self._doc = doc = xml.dom.minidom.parse(filename)
        self.psychopyVersion = doc.getAttribute('version')
        #first make sure we're empty
        self.flow = Flow(exp=self)#every exp has exactly one flow
        self.routines={}
        #fetch exp settings
        ##NB the lines about someNode.hasattributes() are to avoid empty 'Text Attributes' inserted by pretty print
        settingsNode=doc.getElementsByTagName('settings')[0]
        for child in settingsNode.childNodes:
            if not child.hasAttributes(): continue#this is a junk text node
            self._getXMLparam(params=self.exp.settings.params, paramNode=child)
        #fetch routines
        routinesNode=doc.getElementsByTagName('routines')[0]
        for routineNode in routinesNode.childNodes:#get each routine node from the list of routines
            if not routineNode.hasAttributes(): continue#this is a junk text node
            routine = Routine(name=routineNode.getAttribute('name'), exp=self)
            self._getXMLparam(params=routine.params, paramNode=routineNode)
            #then create the 
            self.routines.append(routine)
            for componentNode in routineNode.childNodes:
                if not componentNode.hasAttributes(): continue#this is a junk text node
                compType=componentNode.getAttribute('type')
                component=self._getXMLparam(params=routine, paramNode=componentNode)
        #fetch flow settings
        flowXML=doc.getElementsByTagName('flow')[0]
    def setExpName(self, name):
        self.name=name
        self.settings.expName=name

class Param:
    """Defines parameters for Experiment Components
    A string representation of the parameter will depend on the valType:

    >>> sizeParam = Param(val=[3,4], valType='num')
    >>> print sizeParam
    numpy.asarray([3,4])

    >>> sizeParam = Param(val=[3,4], valType='str')
    >>> print sizeParam
    "[3,4]"

    >>> sizeParam = Param(val=[3,4], valType='code')
    >>> print sizeParam
    [3,4]

    """
    def __init__(self, val, valType, allowedVals=[],allowedTypes=[], hint="", updates=None, allowedUpdates=None):
        """
        @param val: the value for this parameter
        @type val: any
        @param valType: the type of this parameter ('num', 'str', 'code')
        @type valType: string
        @param allowedVals: possible vals for this param (e.g. units param can only be 'norm','pix',...)
        @type allowedVals: any
        @param allowedTypes: if other types are allowed then this is the possible types this parameter can have (e.g. rgb can be 'red' or [1,0,1])
        @type allowedTypes: list
        @param hint: describe this parameter for the user
        @type hint: string
        @param updates: how often does this parameter update ('experiment', 'routine', 'set every frame')
        @type updates: string
        @param allowedUpdates: conceivable updates for this param [None, 'routine', 'set every frame']
        @type allowedUpdates: list
        """
        self.val=val
        self.valType=valType
        self.allowedTypes=allowedTypes
        self.hint=hint
        self.updates=updates
        self.allowedUpdates=allowedUpdates
        self.allowedVals=allowedVals
    def __str__(self):
        if self.valType == 'num':
            try:
                return str(float(self.val))#will work if it can be represented as a float
            except:#might be an array
                return "asarray(%s)" %(self.val)
        elif self.valType == 'str':
            return repr(self.val)#this neatly handles like "it's" and 'He says "hello"'
        elif self.valType == 'code':
            return "%s" %(self.val)
        elif self.valType == 'bool':
            return "%s" %(self.val)
        else:
            raise TypeError, "Can't represent a Param of type %s" %self.valType

class TrialHandler():
    """A looping experimental control object
            (e.g. generating a psychopy TrialHandler or StairHandler).
            """
    def __init__(self, exp, name, loopType, nReps,
        trialList=[], trialListFile='',endPoints=[0,1]):
        """
        @param name: name of the loop e.g. trials
        @type name: string
        @param loopType:
        @type loopType: string ('rand', 'seq')
        @param nReps: number of reps (for all trial types)
        @type nReps:int
        @param trialList: list of different trial conditions to be used
        @type trialList: list (of dicts?)
        @param trialListFile: filename of the .csv file that contains trialList info
        @type trialList: string (filename)
        """
        self.type='TrialHandler'
        self.exp=exp
        self.order=['name']#make name come first (others don't matter)
        self.params={}
        self.params['name']=Param(name, valType='code', updates=None, allowedUpdates=None,
            hint="Name of this loop")
        self.params['nReps']=Param(nReps, valType='num', updates=None, allowedUpdates=None,
            hint="Number of repeats (for each type of trial)")
        self.params['trialList']=Param(trialList, valType='str', updates=None, allowedUpdates=None,
            hint="A list of dictionaries describing the differences between each trial type")
        self.params['trialListFile']=Param(trialListFile, valType='str', updates=None, allowedUpdates=None,
            hint="A comma-separated-value (.csv) file specifying the parameters for each trial")
        self.params['endPoints']=Param(endPoints, valType='num', updates=None, allowedUpdates=None,
            hint="The start and end of the loop (see flow timeline)")
        self.params['loopType']=Param(loopType, valType='str', allowedVals=['random','sequential','staircase'],
            hint="How should the next trial value(s) be chosen?")#NB staircase is added for the sake of the loop properties dialog
        #these two are really just for making the dialog easier (they won't be used to generate code)
        self.params['endPoints']=Param(endPoints,valType='num',
            hint='Where to loop from and to (see values currently shown in the flow view)')
    def writeInitCode(self,buff):
        #todo: write code to fetch trialList from file?
        #create nice line-separated list of trialTypes
        trialStr="[ \\\n"
        for line in self.params['trialList'].val:
            trialStr += "        %s,\n" %line
        trialStr += "        ]"
        #also a 'thisName' for use in "for thisTrial in trials:"
        self.thisName = ("this"+self.params['name'].val.capitalize()[:-1])
        #write the code
        buff.writeIndented("\n#set up handler to look after randomisation of trials etc\n")
        buff.writeIndented("%s=data.TrialHandler(nReps=%s, method=%s, extraInfo=expInfo, trialList=%s)\n" \
            %(self.params['name'], self.params['nReps'], self.params['loopType'], trialStr))
        buff.writeIndented("%s=trials.trialList[0]#so we can initialise stimuli with first trial values\n" %self.thisName)

    def writeLoopStartCode(self,buff):
        #work out a name for e.g. thisTrial in trials:
        buff.writeIndented("\n")
        buff.writeIndented("for %s in %s:\n" %(self.thisName, self.params['name']))
        buff.setIndentLevel(1, relative=True)
    def writeLoopEndCode(self,buff):
        buff.setIndentLevel(-1, relative=True)
        buff.writeIndented("\n")
        buff.writeIndented("#completed %s repeats of '%s' repeats\n" \
            %(self.params['nReps'], self.params['name']))
        buff.writeIndented("\n")

        #save data
        ##a string to show all the available variables
        stimOutStr="["
        for variable in self.params['trialList'].val[0].keys():#get the keys for the first trialType
            stimOutStr+= "'%s', " %variable
        stimOutStr+= "]"
        buff.writeIndented("%(name)s.saveAsPickle(filename+'.psydat')\n" %self.params)
        buff.writeIndented("%(name)s.saveAsText(filename+'.dlm',\n" %self.params)
        buff.writeIndented("    stimOut=%s,\n" %stimOutStr)
        buff.writeIndented("    dataOut=['n','all_mean','all_std', 'all_raw'])\n")
        buff.writeIndented("psychopy.log.info('saved data to '+filename+'.dlm')\n" %self.params)

    def getType(self):
        return 'TrialHandler'
class StairHandler():
    """A staircase experimental control object.
    """
    def __init__(self, exp, name, nReps, startVal, nReversals='None',
            nUp=1, nDown=3, minVal=0,maxVal=1,
            stepSizes='[4,4,2,2,1]', stepType='db', endPoints=[0,1]):
        """
        @param name: name of the loop e.g. trials
        @type name: string
        @param nReps: number of reps (for all trial types)
        @type nReps:int
        """
        self.type='StairHandler'
        self.exp=exp
        self.order=['name']#make name come first (others don't matter)
        self.params={}
        self.params['name']=Param(name, valType='code', hint="Name of this loop")
        self.params['nReps']=Param(nReps, valType='num',
            hint="(Minimum) number of trials in the staircase")
        self.params['start value']=Param(startVal, valType='num',
            hint="The initial value of the parameter")
        self.params['max value']=Param(maxVal, valType='num',
            hint="The maximum value the parameter can take")
        self.params['min value']=Param(minVal, valType='num',
            hint="The minimum value the parameter can take")
        self.params['step sizes']=Param(stepSizes, valType='num',
            hint="The size of the jump at each step (can change on each 'reversal')")
        self.params['step type']=Param(stepType, valType='str', allowedVals=['lin','log','db'],
            hint="The units of the step size (e.g. 'linear' will add/subtract that value each step, whereas 'log' will ad that many log units)")
        self.params['N up']=Param(nUp, valType='code',
            hint="The number of 'incorrect' answers before the value goes up")
        self.params['N down']=Param(nDown, valType='code',
            hint="The number of 'correct' answers before the value goes down")
        self.params['N reversals']=Param(nReversals, valType='code',
            hint="Minimum number of times the staircase must change direction before ending")
        #these two are really just for making the dialog easier (they won't be used to generate code)
        self.params['loopType']=Param('staircase', valType='str', allowedVals=['random','sequential','staircase'],
            hint="How should the next trial value(s) be chosen?")#NB this is added for the sake of the loop properties dialog
        self.params['endPoints']=Param(endPoints,valType='num',
            hint='Where to loop from and to (see values currently shown in the flow view)')

    def writeInitCode(self,buff):
        #todo: write code to fetch trialList from file?
        #create nice line-separated list of trialTypes
        trialStr="[ \\\n"
        for line in self.params['trialList'].val:
            trialStr += "        %s,\n" %line
        trialStr += "        ]"
        #also a 'thisName' for use in "for thisTrial in trials:"
        self.thisName = ("this"+self.params['name'].val.capitalize()[:-1])
        #write the code
        buff.writeIndented("\n#set up handler to look after randomisation of trials etc\n")
        buff.writeIndented("%s=data.StairHandler(nReps=%(name)s, extraInfo=expInfo,\n" %(self.params))
        buff.writeIndented("    startVal=%(start value)s, stepSizes=%(step sizes)i, stepType=%(step type)s,\n" %self.params)
        buff.writeIndented("    nReversals=%(nReversals)s, nTrials=%(nReps)i, \n" %self.params)
        buff.writeIndented("    nUp=%(N up)i, nDown=%(N down)i,\n" %self.params)
    def writeLoopStartCode(self,buff):
        #work out a name for e.g. thisTrial in trials:
        buff.writeIndented("\n")
        buff.writeIndented("for %s in %s:\n" %(self.thisName, self.params['name']))
        buff.setIndentLevel(1, relative=True)
    def writeLoopEndCode(self,buff):
        buff.setIndentLevel(-1, relative=True)
        buff.writeIndented("\n")
        buff.writeIndented("#staircase completed\n")
        buff.writeIndented("\n")
        #save data
        ##a string to show all the available variables
        stimOutStr="["
        for variable in self.params['trialList'].val[0].keys():#get the keys for the first trialType
            stimOutStr+= "'%s', " %variable
        stimOutStr+= "]"
        buff.writeIndented("%(name)s.saveAsText(filename+'.dlm')\n" %self.params)
        buff.writeIndented("%(name)s.saveAsPickle(filename+'.psydat')\n" %self.params)
        buff.writeIndented("psychopy.log.info('saved data to '+filename+'.dlm')\n" %self.params)
    def getType(self):
        return 'StairHandler'

class LoopInitiator:
    """A simple class for inserting into the flow.
    This is created automatically when the loop is created"""
    def __init__(self, loop):
        self.loop=loop
        self.exp=loop.exp
    def writeInitCode(self,buff):
        self.loop.writeInitCode(buff)
    def writeMainCode(self,buff):
        self.loop.writeLoopStartCode(buff)
        self.exp.flow._loopList.append(self.loop)#we are now the inner-most loop
    def getType(self):
        return 'LoopInitiator'
class LoopTerminator:
    """A simple class for inserting into the flow.
    This is created automatically when the loop is created"""
    def __init__(self, loop):
        self.loop=loop
        self.exp=loop.exp
    def writeInitCode(self,buff):
        pass
    def writeMainCode(self,buff):
        self.loop.writeLoopEndCode(buff)
        self.exp.flow._loopList.remove(self.loop)# _loopList[-1] will now be the inner-most loop
    def getType(self):
        return 'LoopTerminator'
class Flow(list):
    """The flow of the experiment is a list of L{Routine}s, L{LoopInitiator}s and
    L{LoopTerminator}s, that will define the order in which events occur
    """
    def __init__(self, exp):
        list.__init__(self)
        self.exp=exp
        self._currentRoutine=None
        self._loopList=[]#will be used while we write the code
    def addLoop(self, loop, startPos, endPos):
        """Adds initiator and terminator objects for the loop
        into the Flow list"""
        self.insert(int(endPos), LoopTerminator(loop))
        self.insert(int(startPos), LoopInitiator(loop))
        self.exp.requirePsychopyLibs(['data'])#needed for TrialHandlers etc
    def addRoutine(self, newRoutine, pos):
        """Adds the routine to the Flow list"""
        self.insert(int(pos), newRoutine)
    def removeComponent(self,component):
        """Removes a Loop, LoopTerminator or Routine from the flow
        """
        if component.getType() in ['LoopInitiator', 'LoopTerminator']:
            component=component.loop#and then continue to do the next
        if component.getType() in ['StairHandler', 'TrialHandler']:
            #we need to remove the termination points that correspond to the loop
            for comp in self:
                if comp.getType() in ['LoopInitiator','LoopTerminator']:
                    if comp.loop==component: self.remove(comp)
        elif component.getType()=='Routine':
            self.remove(component)#this one's easy!

    def writeCode(self, s):

        #initialise
        for entry in self: #NB each entry is a routine or LoopInitiator/Terminator
            self._currentRoutine=entry
            entry.writeInitCode(s)

        #run-time code
        for entry in self:
            self._currentRoutine=entry
            entry.writeMainCode(s)

class Routine(list):
    """
    A Routine determines a single sequence of events, such
    as the presentation of trial. Multiple Routines might be
    used to comprise an Experiment (e.g. one for presenting
    instructions, one for trials, one for debriefing subjects).

    In practice a Routine is simply a python list of Components,
    each of which knows when it starts and stops.
    """
    def __init__(self, name, exp):
        self.params={'name':name}
        self.name=name
        self.exp=exp
        self._continueName=''#this is used for script-writing e.g. "while continueTrial:"
        self._clockName=None#this is used for script-writing e.g. "t=trialClock.GetTime()"
        list.__init__(self)
    def addComponent(self,component):
        """Add a component to the end of the routine"""
        self.append(component)
    def removeComponent(self,component):
        """Remove a component from the end of the routine"""
        self.remove(component)
    def writeInitCode(self,buff):
        buff.writeIndented('\n')
        buff.writeIndented('#Initialise components for routine:%s\n' %(self.name))
        self._clockName = self.name+"Clock"
        self._continueName = "continue%s" %self.name.capitalize()
        buff.writeIndented('%s=core.Clock()\n' %(self._clockName))
        for thisEvt in self:
            thisEvt.writeInitCode(buff)

    def writeMainCode(self,buff):
        """This defines the code for the frames of a single routine
        """
        #This is the beginning of the routine, before the loop starts
        for event in self:
            event.writeRoutineStartCode(buff)

        #create the frame loop for this routine
        buff.writeIndented('\n')
        buff.writeIndented('#run the trial\n')
        buff.writeIndented('%s=True\n' %self._continueName)
        buff.writeIndented('t=0; %s.reset()\n' %(self._clockName))
        buff.writeIndented('while %s and (t<%.4f):\n' %(self._continueName, self.getMaxTime()))
        buff.setIndentLevel(1,True)

        #on each frame
        buff.writeIndented('#get current time\n')
        buff.writeIndented('t=%s.getTime()\n\n' %self._clockName)

        #write the code for each component during frame
        buff.writeIndented('#update each component (where necess)\n')
        for event in self:
            event.writeFrameCode(buff)

        #update screen
        buff.writeIndented('\n')
        buff.writeIndented('#check for quit (the [Esc] key)\n')
        buff.writeIndented('if event.getKeys("escape"): core.quit()\n')
        buff.writeIndented("event.clearEvents()#so that it doesn't get clogged with other events\n")
        buff.writeIndented('#refresh the screen\n')
        buff.writeIndented('win.flip()\n')

        #that's done decrement indent to end loop
        buff.setIndentLevel(-1,True)

        #write the code for each component for the end of the routine
        buff.writeIndented('\n')
        buff.writeIndented('#end of this routine (e.g. trial)\n')
        for event in self:
            event.writeRoutineEndCode(buff)

    def getType(self):
        return 'Routine'
    def getComponentFromName(self, name):
        for comp in self:
            if comp.params['name']==name:
                return comp
        return None
    def getMaxTime(self):
        maxTime=0;
        for event in self:
            exec("times=%s" %event.params['times'].val)#convert params['times'].val into numeric
            times.append(maxTime)
            maxTime=float(max(times))
        return maxTime