# -*- coding: utf-8 -*-
"""measure your JNI in auditory amplitude using a (dual) staircase method"""

from psychopy import core, visual, gui, data, event
from psychopy.tools.filetools import fromFile, toFile
import time
import sys
import numpy as np
# This is ugly code, revise by making wavhelpers part of a module
sys.path.insert(0, '../')
import utilities

targetKeys = dict(left=['1', '2', 'left'], right=['3', '4', 'right'],
                  abort=['q', 'escape'])

audioSamplingRate = 44100
audStimDur_sec = 0.050
audStimTaper_sec = 0.005
minISI = 0.75
maxISI = 1.25
nReversalAverage = 2

curMonitor = 'testMonitor'
bckColour = '#303030'
fullScr = False

try:  # try to get a previous parameters file
    expInfo = fromFile('lastParams.pickle')
except:  # if not there then use a default set
    expInfo = {'subjID': 'test', 'sesNo': '10',
               'startIntAbv': -30.0, 'startIntBlw': -100.0,
               'stimLeft (Hz)': 1000, 'stimRight (Hz)': 1000,
               'relTargetVol': 50.}
dateStr = time.strftime("%b%d_%H%M", time.localtime())  # add the current time

# present a dialogue to change params
dlg = gui.DlgFromDict(expInfo, title='Auditory (dual) staircase',
                      order=['subjID', 'sesNo', 'stimLeft (Hz)',
                             'stimRight (Hz)'])
if dlg.OK:
    toFile('lastParams.pickle', expInfo)  # save params to file for next time
else:
    core.quit()  # the user hit cancel so exit

stimHz = [expInfo['stimLeft (Hz)'], expInfo['stimRight (Hz)']]

# Using wavhelpers:
leftChanStr, rightChanStr = \
    utilities.load_stimuli(stimHz, audioSamplingRate,
                           audStimDur_sec, audStimTaper_sec)

if sys.platform == 'win32':
    import winsound
    from psychopy import parallel as attenuatorPort

    attenuatorCtrl = utilities.AttenuatorController(attenuatorPort)

    def playSound(wavfile):
        winsound.PlaySound(wavfile,
                           winsound.SND_FILENAME | winsound.SND_NOWAIT)

else:
    attenuatorPort = utilities.FakeParallelPort()

    from psychopy import sound
    soundLeft = sound.Sound(leftChanStr, autoLog=False)
    soundRight = sound.Sound(rightChanStr, autoLog=False)

    attenuatorCtrl = \
        utilities.FakeAttenuatorController(attenuatorPort,
                                           soundLeft, soundRight)

    def playSound(wavfile):
        if wavfile == leftChanStr:
            soundLeft.play()
        elif wavfile == rightChanStr:
            soundRight.play()

# create window and stimuli
globalClock = core.Clock()  # to keep track of time
trialClock = core.CountdownTimer()

win = visual.Window(monitor=curMonitor,
                    units='deg', fullscr=fullScr, color=bckColour)
fixation = visual.PatchStim(win, color='white', tex=None,
                            mask='gauss', size=0.75)
message1 = visual.TextStim(win, pos=[0, +3], text='Ready...')
message2 = visual.TextStim(win, pos=[0, -3], text='')
message1.draw()
win.flip()
event.waitKeys(keyList=['space', 'enter'])

message1.setText('Hit a key when ready.')
message2.setText('Then press left button for left sound, '
                 'right button for right sound.')

# create the staircase handler
# with nUp=3, nDown=1, we are optimising for approaching the limit from ABOVE!
staircaseLeft = \
    data.StairHandler(startVal=expInfo['startIntAbv'],
                      stepType='lin',
                      stepSizes=[8., 4., 2., 1.],
                      minVal=-105., maxVal=0.0,
                      nUp=3, nDown=1,  # will home in on the 80% threshold
                      nTrials=5)
staircaseRight = \
    data.StairHandler(startVal=expInfo['startIntAbv'],
                      stepType='lin', stepSizes=[8., 4., 2., 1.],
                      minVal=-105., maxVal=0.0, nUp=3, nDown=1, nTrials=5)

# with nUp=3, nDown=1, we are optimising for approaching the limit from ABOVE!
staircaseLeft_below = \
    data.StairHandler(startVal=expInfo['startIntBlw'],
                      stepType='lin', stepSizes=[8., 4., 2., 1.],
                      minVal=-105., maxVal=0.0, nUp=1, nDown=3, nTrials=5)

staircaseRight_below = \
    data.StairHandler(startVal=expInfo['startIntBlw'],
                      stepType='lin', stepSizes=[8., 4., 2., 1.],
                      minVal=-105., maxVal=0.0, nUp=1, nDown=3, nTrials=5)

# display instructions and wait
message1.draw()
message2.draw()
fixation.draw()
win.flip()
# check for a keypress
event.waitKeys()

# draw all stimuli
fixation.draw()
win.flip()

leftDone = False
leftDone_below = False
rightDone = False
rightDone_below = False
runStaircases = True
globalClock.reset()

while runStaircases:
    # set side of sound
    targetSide = round(np.random.random())*2-1  # either +1(right) or -1(left)
    targetDir = round(np.random.random())*2-1  # either +1(above) or -1(below)

    if targetSide < 0:  # left
        curChanStr = leftChanStr
        curSide = 'left'
        if targetDir > 0:
            curStair = staircaseLeft
        elif targetDir < 0:
            curStair = staircaseLeft_below
    elif targetSide > 0:  # right
        curChanStr = rightChanStr
        curSide = 'right'
        if targetDir > 0:
            curStair = staircaseRight
        elif targetDir < 0:
            curStair = staircaseRight_below

    if not curStair.finished:
        thisVolume = curStair.next()
        if thisVolume:
            attenuatorCtrl.setVolume(thisVolume, side=curSide)
            playSound(curChanStr)

        # get response
        thisResp = None
        # max wait 0.75-1.25 secs!
        trialClock.reset(minISI + (maxISI - minISI)*np.random.random())
        allKeys = event.waitKeys(maxWait=1.)
        if not allKeys:  # no response given in 1 secs
            thisResp = 0
        else:
            for thisKey in allKeys[0]:
                if (thisKey in targetKeys['left'] and targetSide == -1) or \
                   (thisKey in targetKeys['right'] and targetSide == 1):
                    thisResp = 1  # correct
                elif (thisKey in targetKeys['right'] and targetSide == -1) or \
                     (thisKey in targetKeys['left'] and targetSide == 1):
                    thisResp = 0  # incorrect
                elif thisKey in targetKeys['abort']:
                    win.close()
                    core.quit()  # abort experiment

        # add the data to the staircase so it can calculate the next level
        curStair.addResponse(thisResp)
    else:
        if targetSide < 0:  # left
            if targetDir > 0 and not leftDone:
                leftDone = True
                print "Left above done", staircaseLeft.reversalIntensities
            elif targetDir < 0 and not leftDone_below:
                leftDone_below = True
                print "Left below done", staircaseLeft_below.reversalIntensities
        elif targetSide > 0:  # right
            if targetDir > 0 and not rightDone:
                rightDone = True
                print "Right above done", staircaseRight.reversalIntensities
            elif targetDir < 0 and not rightDone_below:
                rightDone_below = True
                print("Right below done",
                      staircaseRight_below.reversalIntensities)

    if leftDone and rightDone and leftDone_below and rightDone_below:
        break

    while trialClock.getTime() > 0.:
        core.wait(0.010)  # adds some uncertainty too...


print "Total time: %.2f seconds" % (globalClock.getTime())

avgThreshLeft = np.average(np.r_[(
    staircaseLeft.reversalIntensities[-nReversalAverage:],
    staircaseLeft_below.reversalIntensities[-nReversalAverage:])])

avgThreshRight = np.average(np.r_[(
    staircaseRight.reversalIntensities[-nReversalAverage:],
    staircaseRight_below.reversalIntensities[-nReversalAverage:])])


avgThreshLeft_rounded = avgThreshLeft - \
                        (np.remainder(10.0*avgThreshLeft, 5))/10.
avgThreshRight_rounded = avgThreshRight - \
                        (np.remainder(10.0*avgThreshRight, 5))/10.

print "Left threshold: %.1f" % (avgThreshLeft_rounded)
print "Right threshold: %.1f" % (avgThreshRight_rounded)

attenuatorCtrl.setVolume(avgThreshLeft_rounded, side='left')
attenuatorCtrl.setVolume(avgThreshRight_rounded, side='right')

# make a text file to save data
fileName = expInfo['subjID'] + '-' + str(expInfo['sesNo']) + '_' + dateStr
dataFile = open(fileName+'.txt', 'w')
# dataFile.write('targetSide	oriIncrement	correct\n')
dataFile.write('Reversal intensities')
dataFile.write('\nRevIntLeft_above: ')
for curInt in staircaseLeft.reversalIntensities:
    dataFile.write('%.1f ' % curInt)
dataFile.write('\nRevIntLeft_below: ')
for curInt in staircaseLeft_below.reversalIntensities:
    dataFile.write('%.1f ' % curInt)
dataFile.write('\nRevIntRight_above: ')
for curInt in staircaseRight.reversalIntensities:
    dataFile.write('%.1f ' % curInt)
dataFile.write('\nRevIntRight_below: ')
for curInt in staircaseRight_below.reversalIntensities:
    dataFile.write('%.1f ' % curInt)

dataFile.write('\nThresholds:')
dataFile.write('%.1f ' % avgThreshLeft_rounded)
dataFile.write('%.1f ' % avgThreshRight_rounded)
dataFile.close()

message1.setText('Thanks!')
message2.setText('Your thresholds are:\n%.1f / %.1f (L/R)' %
                 (avgThreshLeft_rounded, avgThreshRight_rounded))
message1.draw()
message2.draw()
win.flip()

# Here would be nice to be able to have a lock-command!
print("Hit the LOCK-button on the attenuator & Ramp (manual) "
      "up to +%.0f dB" % (expInfo['relTargetVol']))

# print "Ramping up to desired level..."
print("Then hit space or enter here...")

event.waitKeys(keyList=['space', 'enter'])

message1.setText('You will now hear 5 tones in each ear')
message2.setText('Please confirm that the volume is OK\n'
                 '(press any key to start)')
message1.draw()
message2.draw()
win.flip()

event.waitKeys()
for ii in range(5):
    playSound(leftChanStr)
    core.wait(1.)
    playSound(rightChanStr)
    core.wait(1.)


win.close()
core.quit()
