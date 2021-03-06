import sys,nose,collections
from nose.tools import ok_,eq_
from contextlib import nested
import psychopy.hardware as hw

try:
    import mock
except:
    def require_mock(fn):
        def _inner():
            raise nose.plugins.skip.SkipTest("Can't test without Mock")
        _inner.__name__ = fn.__name__
        return _inner
else:
    def require_mock(fn):
        return fn

def globMock(expr):
    if "?" in expr:
        return [expr.replace("?","1")]
    elif "*" in expr:
        return [expr.replace(r"*","MOCK1")]
    else:
        return [expr]

def assertPorts(expected,actual):
    actual = list(actual) # ensure list
    for port in expected:
        assert port in actual

@require_mock
def testGetWindowsSerialPorts():
    should_have = ["COM0","COM5","COM10"]
    with mock.patch("sys.platform","win32"):
        assertPorts(should_have,hw.getSerialPorts())

@require_mock
def testGetLinuxSerialPorts():
    should_have = ["/dev/ttyS1","/dev/ttyACM1","/dev/ttyUSB1"]
    with nested(mock.patch("sys.platform","linux2"),
                mock.patch("glob.iglob",globMock)):
       assertPorts(should_have,hw.getSerialPorts())

@require_mock
def testGetDarwinSerialPorts():
    should_have = ["/dev/tty.USAMOCK1","/dev/tty.KeyMOCK1","/dev/tty.modemMOCK1","/dev/cu.usbmodemMOCK1"]
    with nested(mock.patch("sys.platform","darwin"),
                mock.patch("glob.iglob",globMock)):
        assertPorts(should_have,hw.getSerialPorts())

@require_mock
def testGetCygwinSerialPorts():
    should_have = ["/dev/ttyS1"]
    with nested(mock.patch("sys.platform","cygwin"),
                mock.patch("glob.iglob",globMock)):
        assertPorts(should_have,hw.getSerialPorts())

@require_mock
def testGetCRSPhotometers():
    with mock.patch.dict("sys.modules",{"psychopy.hardware.crs": object()}):
        photoms = list(hw.getAllPhotometers())
        
        for p in photoms:
            assert p.longName != "CRS ColorCAL"

        assert isinstance(photoms,collections.Iterable)
        # missing crs shouldn't break it
        assert len(photoms) > 0

    
    # This allows us to test our logic even when pycrsltd is missing
    faked = type("MockColorCAL",(object,),{})
    with mock.patch("psychopy.hardware.crs.ColorCAL",faked):
        photoms = list(hw.getAllPhotometers())
        assert faked in photoms

def testGetPhotometers():
    photoms = hw.getAllPhotometers()
    
    # Always iterable
    assert isinstance(photoms,collections.Iterable)
    
    photoms = list(photoms)
    
    assert len(photoms) > 0


# I wish our PR650 would behave like this ;-)
_MockPhotometer = type("MockPhotometer",(object,),{"OK": True,"type": "MockPhotometer"})

_workingPhotometer = lambda port: _MockPhotometer
    
def _exceptionRaisingPhotometer(port):
    raise Exception("Exceptional quality they said...")

def testFindPhotometer():
    # findPhotometer with no ports should return None
    eq_(hw.findPhotometer(ports=[]),None)
    # likewise, if an empty device list is used return None
    eq_(hw.findPhotometer(device=[]),None)
    # even when both are empty
    eq_(hw.findPhotometer(device=[],ports=[]),None)
    
    # non-existant photometers return None, for now
    eq_(hw.findPhotometer(device="thisIsNotAPhotometer!"),None)
    
    # if the photometer raises an exception don't crash, return None
    eq_(hw.findPhotometer(device=[_exceptionRaisingPhotometer],ports="foobar"),None)
    
    # specifying a photometer should work
    assert hw.findPhotometer(device=[_workingPhotometer],ports="foobar") == _MockPhotometer
    
    
    # one broken, one working
    device = [_exceptionRaisingPhotometer,_workingPhotometer]
    assert hw.findPhotometer(device=device,ports="foobar") == _MockPhotometer