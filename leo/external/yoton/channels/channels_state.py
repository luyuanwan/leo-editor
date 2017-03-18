# -*- coding: utf-8 -*-
#@+leo-ver=5-thin
#@+node:ekr.20170318090242.1: * @file channels_state.py
#@@first
""" Module yoton.channels.channels_state

Defines the channel class for state.

"""
#@+<< channels_state imports >>
#@+node:ekr.20170318090253.1: ** << channels_state imports >>
# from yoton.misc import bytes # basestring, str, long
# from yoton.misc import Property
from yoton.channels import BaseChannel
#@-<< channels_state imports >>
#@+others
#@+node:ekr.20170318090253.2: ** class StateChannel (BaseChannel)
class StateChannel(BaseChannel):
    """ StateChannel(context, slot_base, message_type=yoton.TEXT)
    
    Channel class for the state messaging pattern. A state is synchronized
    over all state channels of the same slot. Each channel can 
    send (i.e. set) the state and recv (i.e. get) the current state.
    Note however, that if two StateChannel instances set the state
    around the same time, due to the network delay, it is undefined
    which one sets the state the last.
    
    The context will automatically call this channel's send_last()
    method when a new context enters the network.
    
    The recv() call is always non-blocking and always returns the last
    received message: i.e. the current state.
    
    There are no limitations for this channel if events are not 
    processed, except that the received signal is not emitted.
    
    Parameters
    ----------
    context : yoton.Context instance
        The context that this channel uses to send messages in a network.
    slot_base : string
        The base slot name. The channel appends an extension to indicate
        message type and messaging pattern to create the final slot name.
        The final slot is used to connect channels at different contexts
        in a network
    message_type : yoton.MessageType instance 
        (default is yoton.TEXT)
        Object to convert messages to bytes and bytes to messages. 
        Users can create their own message_type class to let channels
        any type of message they want.
    
    """
    
    #@+others
    #@+node:ekr.20170318090253.3: *3* __init__
    def __init__(self, *args, **kwargs):
        BaseChannel.__init__(self, *args, **kwargs)
        
        # Variables to hold the current state. We use only the message
        # as a reference, so we dont need a lock.
        # The package is used to make _recv() function more or less,
        # and to be able to determine if a state was set (because the 
        # message may be set to None)
        self._current_package = None
        self._current_message = self.message_from_bytes(b'') ### bytes())


    #@+node:ekr.20170318090253.4: *3* _messaging_patterns
    def _messaging_patterns(self):
        return 'state', 'state'


    #@+node:ekr.20170318090253.5: *3* send
    def send(self, message):
        """ send(message)
        
        Set the state of this channel.
        
        The state-message is queued and send over the socket by the IO-thread. 
        Zero-length messages are ignored.
        
        """
        # Send message only if it is different from the current state
        # set current_message by unpacking the send binary. This ensures
        # that if someone does this, things still go well:
        #    a = [1,2,3]
        #    status.send(a)
        #    a.append(4)
        #    status.send(a)
        if message != self._current_message:
            self._current_package = self._send( self.message_to_bytes(message) )
            self._current_message = self.message_from_bytes(self._current_package._data)


    #@+node:ekr.20170318090253.6: *3* send_last
    def send_last(self):
        """ send_last()
        
        Resend the last message.
        
        """
        if self._current_package is not None:
            self._send( self.message_to_bytes(self._current_message) )


    #@+node:ekr.20170318090253.7: *3* recv
    def recv(self, block=False):
        """ recv(block=False)
        
        Get the state of the channel. Always non-blocking. Returns the
        most up to date state.
        
        """
        return self._current_message


    #@+node:ekr.20170318090253.8: *3* _recv_package
    def _recv_package(self, package):
        """ _recv_package(package)
        
        Bypass queue and just store it in a variable.
        
        """
        self._current_message = self.message_from_bytes(package._data)
        self._current_package = package
        #
        self._maybe_emit_received()


    #@+node:ekr.20170318090253.9: *3* _inject_package
    def _inject_package(self, package):
        """ Non-blocking version of recv_package. Does the same.
        """
        self._current_message = self.message_from_bytes(package._data)
        self._current_package = package
        #
        self._maybe_emit_received()


    #@+node:ekr.20170318090253.10: *3* _recv
    def _recv(self, block=None):
        """ _recv(block=None)
        
        Returns the last received or send set package. The package
        may not reflect the current state.
        
        """
        return self._current_package
    #@-others
#@-others
#@@language python
#@@tabwidth -4
#@-leo
