# -*- coding: utf-8 -*-
#@+leo-ver=5-thin
#@+node:ekr.20170317181903.1: * @file misc.py
#@@first
#@+<< docstring >>
#@+node:ekr.20170317181913.1: ** << docstring >>
""" Module yoton.misc

Defines a few basic constants, classes and functions.

Most importantly, it defines a couple of specific buffer classes that
are used for the low-level messaging.

"""
#@-<< docstring >>
#@+<< imports >>
#@+node:ekr.20170317183337.1: ** << imports >> misc.py
import leo.core.leoGlobals as g
# import os
import sys
import struct
import socket
import threading
import time
import random
from collections import deque

# Version dependent defs
V2 = sys.version_info[0] == 2
if V2:
    pass
    ###
    # if sys.platform.startswith('java'):
        # import __builtin__ as D  # Jython
    # else:
        # D = __builtins__
    # if not isinstance(D, dict):
        # D = D.__dict__
    ### bytes = D['str']
    ### str = D['unicode']
    # xrange = D['xrange']
    # basestring = basestring
    # long = D['long'] ### EKR: was long
else:
    # basestring = str  # to check if instance is string
    # bytes, str = bytes, str
    long = int # for the port
    # xrange = range
#@-<< imports >>
#@+others
#@+node:ekr.20170317181913.2: ** Property
def Property(function):
    """ Property(function)
    
    A property decorator which allows to define fget, fset and fdel
    inside the function.
    
    Note that the class to which this is applied must inherit from object!
    Code based on an example posted by Walker Hale:
    http://code.activestate.com/recipes/410698/#c6
    
    """
    
    # Define known keys
    known_keys = 'fget', 'fset', 'fdel', 'doc'
    
    # Get elements for defining the property. This should return a dict
    func_locals = function()
    if not isinstance(func_locals, dict):
        raise RuntimeError('Property function should "return locals()".')
    
    # Create dict with kwargs for property(). Init doc with docstring.
    D = {'doc': function.__doc__}
    
    # Copy known keys. Check if there are invalid keys
    for key in func_locals.keys():
        if key in known_keys:
            D[key] = func_locals[key]
        else:
            raise RuntimeError('Invalid Property element: %s' % key)
    
    # Done
    return property(**D)


#@+node:ekr.20170317181913.3: ** getErrorMsg
def getErrorMsg():
    """ getErrorMsg()
    Return a string containing the error message. This is usefull, because
    there is no uniform way to catch exception objects in Python 2.x and
    Python 3.x.
    """
    
    # Get traceback info
    type, value, tb = sys.exc_info()
    
    # Store for debugging?
    if True:        
        sys.last_type = type
        sys.last_value = value
        sys.last_traceback = tb
    
    # Print
    err = ''
    try:
        if not isinstance(value, (OverflowError, SyntaxError, ValueError)):
            while tb:
                err = "line %i of %s." % (
                        tb.tb_frame.f_lineno, tb.tb_frame.f_code.co_filename)
                tb = tb.tb_next
    finally:
        del tb
    ### return str(value) + "\n" + err
    return g.u(value)  + "\n" + err


#@+node:ekr.20170317181913.4: ** slot_hash
def slot_hash(name):
    """ slot_hash(name)
    
    Given a string (the slot name) returns a number between 8 and 2**64-1
    (just small enough to fit in a 64 bit unsigned integer). The number
    is used as a slot id.
    
    Slots 0-7 are reseved slots.
    
    """
    fac = 0xd2d84a61
    val = 0
    offset = 8
    for c in name:
        val += ( val>>3 ) + ( ord(c)*fac )
    val += (val>>3) + (len(name)*fac)
    return offset + (val % (2**64-offset))


#@+node:ekr.20170317181913.5: ** port_hash
def port_hash(name):
    """ port_hash(name)
    
    Given a string, returns a port number between 49152 and 65535. 
    (2**14 (16384) different posibilities)
    This range is the range for dynamic and/or private ports 
    (ephemeral ports) specified by iana.org.
    The algorithm is deterministic, thus providing a way to map names
    to port numbers.
    
    """
    fac = 0xd2d84a61
    val = 0
    for c in name:
        val += ( val>>3 ) + ( ord(c)*fac )
    val += (val>>3) + (len(name)*fac)
    return 49152 + (val % 2**14)


#@+node:ekr.20170317181913.6: ** split_address
def split_address(address):
    """ split_address(address) -> (protocol, hostname, port)
    
    Split address in protocol, hostname and port. The address has the 
    following format: "protocol://hostname:port". If the protocol is
    omitted, TCP is assumed.
    
    The hostname is the name or ip-address of the computer to connect to. 
    One can use "localhost" for a connection that bypasses some
    network layers (and is not visible from the outside). One can use
    "publichost" for a connection at the current computers IP address
    that is visible from the outside.
    
    The port can be an integer, or a sting. In the latter case the integer
    port number is calculated using a hash. One can also use "portname+offset"
    to specify an integer offset for the port number.
    
    """
    
    # Check
    #if not isinstance(address, basestring):
    if not g.isString(address):
        raise ValueError("Address should be a string.")
    if not ":" in address:
        raise ValueError("Address should be in format 'host:port'.")
    
    # Is the protocol explicitly defined (zeromq compatibility)
    protocol = ''
    if '://' in address:
        # Get protocol and stripped address
        tmp = address.split('://',1)
        protocol = tmp[0].lower()
        address = tmp[1]
    if not protocol:
        protocol = 'tcp'
    
    # Split
    tmp = address.split(':',1)
    host, port = tuple(tmp)
    
    # Process host
    if host.lower() == 'localhost':
        host = '127.0.0.1'
    if host.lower() == 'publichost':
        host = 'publichost' + '0'
    if host.lower().startswith('publichost') and host[10:] in '0123456789':
        index = int(host[10:])
        hostname = socket.gethostname()
        tmp = socket.gethostbyname_ex(hostname)
        try:
            host = tmp[2][index]  # This resolves to 127.0.1.1 on some Linuxes
        except IndexError:
            raise ValueError('Invalid index (%i) in public host addresses.' % index)
    
    # Process port
    try:
        port = int(port)
    except ValueError:
        # Convert to int, using a hash
        
        # Is there an offset?
        offset = 0
        if "+" in port:
            tmp = port.split('+',1)
            port, offset = tuple(tmp)
            try:
                offset = int(offset)
            except ValueError:
                raise ValueError("Invalid offset in address")
        
        # Convert
        port = port_hash(port) + offset
    
    # Check port
    #if port < 1024 or port > 2**16:
    #    raise ValueError("The port must be in the range [1024, 2^16>.")
    if port > 2**16:
        raise ValueError("The port must be in the range [0, 2^16>.")
    
    # Done
    return protocol, host, port


#@+node:ekr.20170317181913.7: ** class UID
class UID:
    """ UID
    
    Represents an 8-byte (64 bit) Unique Identifier.
    
    """ 
    
    _last_timestamp = 0
    
    #@+others
    #@+node:ekr.20170317181913.8: *3* __init__
    def __init__(self, id=None):
        # Create nr consisting of two parts
        if id is None:
            self._nr = self._get_time_int() << 32
            self._nr += self._get_random_int()
        elif isinstance(id, (int, long)):
            self._nr = id
        else:
            raise ValueError('The id given to UID() should be an int.')

    #@+node:ekr.20170317181913.9: *3* __repr__
    def __repr__(self):
        h = self.get_hex()
        return "<UID %s-%s>" % (h[:8], h[8:])

    #@+node:ekr.20170317181913.10: *3* get_hex
    def get_hex(self):
        """ get_hex()
        
        Get the hexadecimal representation of this UID. The returned
        string is 16 characters long.
        
        """
        h = hex(self._nr)
        h = h[2:].rstrip('L')
        h = h.ljust(2*8, '0')
        return h

    #@+node:ekr.20170317181913.11: *3* get_bytes
    def get_bytes(self):
        """ get_bytes()
        
        Get the UID as bytes.
        
        """
        return struct.pack('<Q', self._nr)

    #@+node:ekr.20170317181913.12: *3* get_int
    def get_int(self):
        """ get_int()
        
        Get the UID as a 64 bit (long) integer.
        
        """
        return self._nr

    #@+node:ekr.20170317181913.13: *3* _get_random_int
    def _get_random_int(self):
        return random.randrange(0xffffffff)

    #@+node:ekr.20170317181913.14: *3* _get_time_int
    def _get_time_int(self):
        # Get time stamp in steps of miliseconds
        timestamp = int(time.time() * 1000)
        # Increase by one if the same as last time
        if timestamp <= UID._last_timestamp:
            timestamp = UID._last_timestamp + 1
        # Store for next time
        UID._last_timestamp = timestamp
        # Truncate to 4 bytes. If the time goes beyond the integer limit, we just
        # restart counting. With this setup, the cycle is almost 25 days
        timestamp  = timestamp & 0xffffffff
        # Don't allow 0
        if timestamp == 0:
            timestamp += 1
            UID._last_timestamp += 1
        return timestamp



    #@-others
#@+node:ekr.20170317181913.15: ** class PackageQueue
class PackageQueue(object):
    """ PackageQueue(N, discard_mode='old')
    
    A queue implementation that can be used in blocking and non-blocking 
    mode and allows peeking. The queue has a limited size. The user
    can specify whether old or new messages should be discarted.
    
    Uses a deque object for the queue and a threading.Condition for
    the blocking.
    
    """
    
    #@+others
    #@+node:ekr.20170317181913.16: *3* class Empty
    class Empty(Exception):

        def __init__(self):
            Exception.__init__(self, 'pop from an empty PackageQueue')
    #@+node:ekr.20170317181913.18: *3* __init__
    def __init__(self, N, discard_mode='old'):
        
        # Instantiate queue and condition
        self._q = deque()
        self._condition = threading.Condition()
        
        # Store max number of elements in queue
        self._maxlen = int(N)
        
        # Store discard mode as integer
        discard_mode = discard_mode.lower()
        if discard_mode == 'old':
            self._discard_mode = 1
        elif discard_mode == 'new':
            self._discard_mode = 2
        else:
            raise ValueError('Invalid discard mode.')


    #@+node:ekr.20170317181913.19: *3* full
    def full(self):
        """ full()
        
        Returns True if the number of elements is at its maximum right now.
        Note that in theory, another thread might pop an element right 
        after this function returns.
        
        """ 
        return len(self) >= self._maxlen


    #@+node:ekr.20170317181913.20: *3* empty
    def empty(self):
        """ empty()
        
        Returns True if the number of elements is zero right now. Note 
        that in theory, another thread might add an element right
        after this function returns.
        
        """
        return len(self) == 0


    #@+node:ekr.20170317181913.21: *3* push
    def push(self, x):
        """ push(item)
        
        Add an item to the queue. If the queue is full, the oldest
        item in the queue, or the given item is discarted.
        
        """
        
        condition = self._condition
        condition.acquire()
        try:
            q = self._q
        
            if len(q) < self._maxlen:
                # Add now and notify any waiting threads in get()
                q.append(x)
                condition.notify() # code at wait() procedes
            else:
                # Full, either discard or pop (no need to notify)
                if self._discard_mode == 1:
                    q.popleft() # pop old
                    q.append(x)
                elif self._discard_mode == 2:
                    pass # Simply do not add
        
        finally:
            condition.release()


    #@+node:ekr.20170317181913.22: *3* insert
    def insert(self, x):
        """ insert(x)
        
        Insert an item at the front of the queue. A call to pop() will
        get this item first. This should be used in rare circumstances
        to give an item priority. This method never causes items to
        be discarted.
        
        """
        
        condition = self._condition
        condition.acquire()
        try:
            self._q.appendleft(x)
            condition.notify() # code at wait() procedes
        finally:
            condition.release()


    #@+node:ekr.20170317181913.23: *3* pop
    def pop(self, block=True):
        """ pop(block=True)
        
        Pop the oldest item from the queue. If there are no items in the
        queue:
          * the calling thread is blocked until an item is available
            (if block=True, default);
          * an PackageQueue.Empty exception is raised (if block=False);
          * the calling thread is blocked for 'block' seconds (if block
            is a float).
        
        """
        
        condition = self._condition
        condition.acquire()
        try:
            q = self._q
            
            if not block:
                # Raise empty if no items in the queue
                if not len(q):
                    raise self.Empty()
            elif block is True:
                # Wait for notify (awakened does not guarantee len(q)>0)
                while not len(q):
                    condition.wait()
            elif isinstance(block, float):
                # Wait if no items, then raise error if still no items
                if not len(q):
                    condition.wait(block) 
                    if not len(q):
                        raise self.Empty()
            else:
                raise ValueError('Invalid value for block in PackageQueue.pop().')
            
            # Return item
            return q.popleft()
        
        finally:
            condition.release()


    #@+node:ekr.20170317181913.24: *3* peek
    def peek(self, index=0):
        """ peek(index=0)
        
        Get an item from the queue without popping it. index=0 gets the
        oldest item, index=-1 gets the newest item. Note that index access
        slows to O(n) time in the middle of the queue (due to the undelying
        deque object).
        
        Raises an IndexError if the index is out of range.
        
        """
        return self._q[index]


    #@+node:ekr.20170317181913.25: *3* __len__
    def __len__(self):
        return self._q.__len__()
    #@+node:ekr.20170317181913.26: *3* clear
    def clear(self):
        """ clear()
        
        Remove all items from the queue.
        
        """
        
        self._condition.acquire()
        try:
            self._q.clear()
        finally:
            self._condition.release()



    #@-others
#@+node:ekr.20170317181913.27: ** class TinyPackageQueue
class TinyPackageQueue(PackageQueue):
    """ TinyPackageQueue(N1, N2, discard_mode='old', timeout=1.0)
    
    A queue implementation that can be used in blocking and non-blocking 
    mode and allows peeking. The queue has a tiny-size (N1). When this size
    is reached, a call to push() blocks for up to timeout seconds. The
    real size (N2) is the same as in the PackageQueue class. 
    
    The tinysize mechanism can be used to semi-synchronize a consumer
    and a producer, while still having a small queue and without having
    the consumer fully block.
    
    Uses a deque object for the queue and a threading.Condition for
    the blocking.
    
    """
    
    #@+others
    #@+node:ekr.20170317181913.28: *3* __init__
    def __init__(self, N1, N2, discard_mode='old', timeout=1.0):
        PackageQueue.__init__(self, N2, discard_mode)
        
        # Store limit above which the push() method will block
        self._tinylen = int(N1)
        
        # Store timeout
        self._timeout = timeout


    #@+node:ekr.20170317181913.29: *3* push
    def push(self, x):
        """ push(item)
        
        Add an item to the queue. If the queue has >= n1 values, 
        this function will block timeout seconds, or until an item is
        popped from another thread.
        
        """
        
        condition = self._condition
        condition.acquire()
        try:
            q = self._q
            lq = len(q)
            
            if lq < self._tinylen:
                # We are on safe side. Wake up any waiting threads if queue was empty
                q.append(x)
                condition.notify() # pop() at wait() procedes
            elif lq < self._maxlen:
                # The queue is above its limit, but not full
                condition.wait(self._timeout)
                q.append(x)
            else:
                # Full, either discard or pop (no need to notify)
                if self._discard_mode == 1:
                    q.popleft() # pop old
                    q.append(x)
                elif self._discard_mode == 2:
                    pass # Simply do not add
            
        finally:
            condition.release()


    #@+node:ekr.20170317181913.30: *3* pop
    def pop(self, block=True):
        """ pop(block=True)
        
        Pop the oldest item from the queue. If there are no items in the
        queue:
          * the calling thread is blocked until an item is available
            (if block=True, default);
          * a PackageQueue.Empty exception is raised (if block=False);
          * the calling thread is blocked for 'block' seconds (if block
            is a float).
        
        """
        
        condition = self._condition
        condition.acquire()
        try:
            q = self._q
            
            if not block:
                # Raise empty if no items in the queue
                if not len(q):
                    raise self.Empty()
            elif block is True:
                # Wait for notify (awakened does not guarantee len(q)>0)
                while not len(q):
                    condition.wait()
            elif isinstance(block, float):
                # Wait if no items, then raise error if still no items
                if not len(q):
                    condition.wait(block) 
                    if not len(q):
                        raise self.Empty()
            else:
                raise ValueError('Invalid value for block in PackageQueue.pop().')
            
            
             # Notify if this pop would reduce the length below the threshold
            if len(q) <= self._tinylen:
                condition.notifyAll() # wait() procedes
            
            # Return item
            return q.popleft()
        
        finally:
            condition.release()


    #@+node:ekr.20170317181913.31: *3* clear
    def clear(self):
        """ clear()
        
        Remove all items from the queue.
        
        """
        
        self._condition.acquire()
        try:
            lq = len(self._q)
            self._q.clear()
            if lq >= self._tinylen:
                self._condition.notify()
        finally:
            self._condition.release()
    #@-others
#@-others
#@@language python
#@@tabwidth -4
#@-leo
