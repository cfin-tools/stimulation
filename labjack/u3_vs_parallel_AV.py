# -*- coding: utf-8 -*-
"""
Test trigger latency of LabJack U3-LV (USB) vs. parallel port
This will only work on a suitably ancient Win-machine (XP, 32-bit)
"""
from psychopy import core, logging, event, visual, sound
from psychopy import parallel, prefs
from labjack import u3
import sys
# This is ugly code, revise by making wavhelpers part of a module
sys.path.insert(0, '../')
import utilities

when = core.Clock()

parallel.setPortAddress(0x378)  # address for parallel port on many machines
# Figure out whether to flip pins or fake it
try:
    parallel.setData(1)
except RuntimeError:
    def setParallelData(code=1):
        if code > 0:
            print('{:.7f} sec, parallel TRIG {:d} (Fake)'.
                  format(when.getTime(), code))
        pass
else:
    def setParallelData(code=0):
        parallel.setData(code)
    setParallelData(0)

try:
    u3dev = u3.U3()
except Exception as e:  # NullHandleException not known to Flake8
    print(e)
    print('U3 not connected, faking it.')
    def setU3Data(code=0):
        if code > 0:
            print('{:.7f} sec, U3 TRIG {:d} (Fake)'.
                  format(when.getTime(), code))
else:
    def setU3Data(code=0):
        u3dev.getFeedback(u3.PortStateWrite([0x00, code, 0x00]))
    setU3Data(0)
    def trigger_U3(code=1, duration=0.010):
        cmd_list = [u3.PortStateWrite([0x00, code, 0x00]),
                   u3.WaitShort(Time=int(duration/128.e-6)),
                   u3.PortStateWrite([0x00, 0, 0x00])]
        u3dev.getFeedback(*cmd_list)
    
# Not needed:
#    core.wait(trigDuration,trigDuration/2.) # equivalent to time.sleep(0.005) plus a tight while-loop for another 0.005 secs!
#    core.wait(trigDuration)
#    u3dev.getFeedback(u3.PortStateWrite([0x00, 0x00, 0x00]))
#    u3dev.toggleLED()


if prefs.general['audioLib'][0] == 'pyo':
    #if pyo is the first lib in the list of preferred libs then we could use small buffer
    #pygame sound is very bad with a small buffer though
    sound.init(48000,buffer=128)
print 'Using %s(with %s) for sounds' %(sound.audioLib, sound.audioDriver)

audioSamplingRate = 48000
audStimDur_sec = 0.050
audStimTaper_sec = 0.005

# Using wavhelpers:
monoChanStr = \
    utilities.load_stimuli(200.0, audioSamplingRate,
                           audStimDur_sec, audStimTaper_sec, isStereo=False)

monoSound = sound.Sound(monoChanStr, autoLog=False)


# Window and stimulus definitions
bckColour = '#303030'
bckColour = '#000000'
monitor = 'testMonitor'
frameRate = 60.0
stimSize = 8.
stimCycPerDeg = 1.
angCycles = 0.
stimCycles = stimSize * stimCycPerDeg / 2.
stimBaseSpeed = 2.  # deg/s
radialPhaseAdvanceBaseline = stimBaseSpeed/frameRate


win = visual.Window(monitor=monitor, units='deg', fullscr=False,
                    color=bckColour)
rad_stim = visual.RadialStim(win, size=stimSize, units="deg", tex='sinXsin',
                             radialCycles=stimCycles, angularCycles=angCycles,
                             mask='radRamp', autoLog=False)

frameSyncSpot = visual.GratingStim(win, tex=None, mask=None,
                                   size=(1., 1.), color='white',
                                   units='deg', pos=(0, 0), autoLog=False)
#####################

spotOnTime = int(frameRate//20)  # trigger should be on for 3 frames, i.e., 50 ms
spotOffTime = int(frameRate - spotOnTime)

bContinue = True
curCode = 1
while bContinue:

#    rad_stim.setRadialPhase(radialPhaseAdvanceBaseline, operation='-')
#    rad_stim.draw()

    setParallelData(code=curCode)
    # setU3Data(code=curCode<<4)
    setU3Data(code=curCode)

    monoSound.play()

    for _ in xrange(spotOnTime):  
        frameSyncSpot.draw()
        win.flip()  # appear

    setParallelData(code=0)
    setU3Data(code=0)

    for _ in xrange(spotOffTime):
        win.flip()  # disappear

    if event.getKeys(keyList=['escape', 'q', 'space']):  # flush it!
        bContinue = False

try:
    u3dev.close()
except NameError:
    pass

core.quit()
