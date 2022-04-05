#!/usr/bin/python

import argparse
from pywsman import *

class wsman_amt:
    """Class for handling Intel AMT configuration"""

    def __init__(self, ipaddress, username, password):
        self.ipaddress = ipaddress
        self.username = username
        self.password = password
        self.port = '16992'
        self.url = 'http://' + self.username + ':' + self.password + '@' + self.ipaddress + ':' + self.port + '/wsman'
        self.options = ClientOptions()
        assert self.options is not None

    def debug(self, debug):
        self.debug = debug
        if (self.debug):
            self.options.set_dump_request()

    def identify(self):
        self.client = Client( self.url )
        assert self.client is not None
        doc = self.client.identify( self.options )
        if doc is None:
            print("Connection failed")
            return
        if self.debug:
            print("%s" % doc)
        root = doc.root()
        prod_vendor = root.find( XML_NS_WSMAN_ID, "ProductVendor" )
        prod_version = root.find( XML_NS_WSMAN_ID, "ProductVersion" )
        print(f'{prod_vendor} {prod_version}')

    def get_redirection(self):
        XML_NS_AMT_CLASS = 'http://intel.com/wbem/wscim/1/amt-schema/1'
        method = 'AMT_RedirectionService'
        enabled_state_map = ['Unknown', 'Other',
                             'Enabled', 'Disabled',
                             'Shutting Down',
                             'Not Applicable',
                             'Enabled but Offline',
                             'In Test', 'Deferred',
                             'Quiesce', 'Starting']
        self.client = Client( self.url )
        assert self.client is not None
        ns = XML_NS_AMT_CLASS + '/' + method
        doc = self.client.get( self.options, ns )
        assert doc is not None
        if (self.debug):
            print("%s" % doc)
        if doc.is_fault():
            f = doc.fault()
            print(f'{method} failed: {f.reason()}')
            return
        root = doc.root()
        element = root.find( ns, "ElementName" )
        state = root.find( ns, "EnabledState" )
        if (int(state.__str__()) < 11):
            enabled_state = enabled_state_map[int(state.string())]
        elif (int(state.__str__()) < 32768):
            enabled_state = 'DMTF Reserved'
        elif (int(state.__str__()) == 32768):
            enabled_state = 'IDER and SOL are disabled'
        elif (int(state.__str__()) == 32769):
              enabled_state = 'IDER is enabled and SOL is disabled'
        elif (int(state.__str__()) == 32770):
            enabled_state = 'SOL is enabled and IDER is disabled'
        elif (int(state.__str__()) == 32771):
            enabled_state = 'IDER and SOL are enabled'
        else:
            enabled_state = 'Vendor Reserved'
        enabled = root.find( ns, "ListenerEnabled" )
        if (enabled.__str__() == 'true'):
            listener = 'enabled'
        else:
            listener = 'disabled'
        print(f'{element}: {enabled_state}, Listener is {listener}')

    def set_redirection_listener(self, action):
        XML_NS_AMT_CLASS = 'http://intel.com/wbem/wscim/1/amt-schema/1'
        method = 'AMT_RedirectionService'
        self.client = Client( self.url )
        assert self.client is not None
        ns = XML_NS_AMT_CLASS + '/' + method
        orig_doc = self.client.get( self.options, ns )
        if orig_doc is None:
            print(f'Could not retrieve {ns}')
            return
        if orig_doc.is_fault():
            f = orig_doc.fault()
            print(f'{method} failed: {f.reason()}')
            return
        if action == 'enable':
            state = 'true'
        elif action == 'disable':
            state = 'false'
        else:
            print(f'Invalid action {action}')
            return
        root = orig_doc.root()
        enabled = root.find( ns, "ListenerEnabled" )
        if enabled.__str__() == state:
            print(f'Listener already in state {action}')
            return
        enabled.set_text( state )
        # Slightly braindead interface; one really should allow
        # an XML Doc as argument here.
        doc = self.client.put( self.options, ns, orig_doc.__str__(),
                               len(orig_doc.__str__()), 'utf-8')
        assert doc is not None
        if (self.debug):
            print("%s" % doc)
        root = doc.root()
        enabled = root.find( ns, "ListenerEnabled" )
        if (enabled.__str__() == state):
            print(f'Listener changed to {state}')
        else:
            print(f'Failed to change listener to {action}')

    def set_redirection(self, serial, ider):
        XML_NS_AMT_CLASS = 'http://intel.com/wbem/wscim/1/amt-schema/1'
        method = 'AMT_RedirectionService'
        self.client = Client( self.url )
        assert self.client is not None
        ns = XML_NS_AMT_CLASS + '/' + method
        orig_doc = self.client.get( self.options, ns )
        if orig_doc is None:
            print(f'Could not retrieve {ns}')
            return
        if (self.debug):
            print("%s" % orig_doc)
        if orig_doc.is_fault():
            f = orig_doc.fault()
            print(f'{method} failed: {f.reason()}')
            return
        root = orig_doc.root()
        e = root.find( ns, "EnabledState" )
        state = e.__str__()
        if state < 32768:
            print(f'Invalid redirection state {state}')
            return
        if state > 32771:
            print(f'Invalid redirection state {state}')
            return
        new_state = 32768
        if serial == 'enabled':
            new_state = new_state + 2
        elif serial is None:
            if state > 32769:
                new_state = new_state + 2
        if ider == 'enabled':
            new_state = new_state + 1
        elif ider is None:
            if state % 1:
                new_state = new_state + 1

        if new_state == state:
            print(f'Nothing to do for {action}')
            return
        method = 'RequestStateChange'
        data = XmlDoc(method + '_INPUT', ns)
        input = data.root()
        input.add( ns, 'RequestedState', str(new_state) )
        doc = self.client.invoke( self.options, ns, method, data )
        assert doc is not None
        if (self.debug):
            print("%s" % doc)
        root = doc.root()
        value = root.find( ns, "ReturnValue" )
        if value is None:
            print(f'Error setting redirection state to {new_state}: {doc}')
            return
        if int(value.__str__()) == 0:
            print(f'serial redirection is {action}d')
            return
        if int(value.__str__()) < 7:
            status = return_value_map[int(value.__str__())]
        elif int(value.__str__()) < 4096:
            status = 'DMTF Reserved (' + value.__str__() + ')'
        elif int(value.__str__()) == 4096:
            status = 'Method Parameters Checked - Job Started'
        elif int(value.__str__()) == 4097:
            status = 'Invalid State Transition'
        elif int(value.__str__()) == 4098:
            status = 'Use of Timeout Parameter Not Supported'
        elif int(value.__str__()) == 4099:
            status = 'Busy'
        elif ( int(value.__str__()) < 32768 ):
            status = 'Method Reserved'
        else:
            status = 'Vendor Specific (' + value.__str() + ')'
        print(f'Setting serial redirection to {action} failed, {status}') 

    def kvm_redirection(self, action):
        XML_NS_IPS_CLASS = 'http://intel.com/wbem/wscim/1/ips-schema/1'
        method = 'IPS_KVMRedirectionSettingData'
        enabled_state_map = ['Unknown', 'Other',
                             'Enabled', 'Disabled',
                             'Shutting Down',
                             'Not Applicable',
                             'Enabled but Offline',
                             'In Test', 'Deferred',
                             'Quiesce', 'Starting']
        self.client = Client( self.url )
        assert self.client is not None
        ns = XML_NS_IPS_CLASS + '/' + method
        orig_doc = self.client.get( self.options, ns )
        assert orig_doc is not None
        if (self.debug):
            print("%s" % orig_doc)
        if orig_doc.is_fault():
            f = orig_doc.fault()
            print(f'{method} failed: {f.reason()}')
            return
        root = orig_doc.root()
        e = root.find( ns, "Is5900PortEnabled" )
        p = root.find( ns, "OptInPolicy" )
        t = root.find( ns, "SessionTimeout" )
        if action == 'status':
            print(f'Port 5900 Enabled: {e}, Opt-In Policy: {p}, session timeout {t}')
            return
        if action == 'disable':
            doc = self.client.invoke( self.options, ns, 'TerminateSession', None )
            assert doc is not None
            if doc.is_fault():
                f = doc.fault()
                print(f'{ns} method TerminateSession failed: {f.reason()}')
                return
            print(f'KVM redirection disabled')
            return
        if action != 'enable':
            print(f'Invalid KVM redirection action {action}')
            return

        if e.__str__() != 'true':
            e.set_text( 'true' )
        if p.__str__() != 'false':
            p.set_text( 'false' )
        if int(t.__str__()) != 0:
            t.set_text( '0' )
        p = root.find( ns, 'RFBPassword' )
        p.set_text( self.password )

        doc = self.client.put( self.options, ns, orig_doc.__str__(),
                               len(orig_doc.__str__()), 'utf-8')
        assert doc is not None
        if self.debug:
            print("%s" % doc)
        if doc.is_fault():
            f = doc.fault()
            print(f'{method} failed: {f.reason()}')
            return
        print(f'KVM Redirection enabled')

    def start_kvm_redirection(self):
        class_name = 'CIM_KVMRedirectionSAP'
        method = 'RequestStateChange'
        enabled_state_map = ['Unknown', 'Other',
                             'Enabled', 'Timeout',
                             'Shutting Down',
                             'Not Applicable',
                             'Enabled but Offline',
                             'In Test', 'Deferred',
                             'Quiesce', 'Starting']
        self.client = Client( self.url )
        assert self.client is not None
        ns = XML_NS_CIM_CLASS + '/' + class_name
        data = XmlDoc( method + '_INPUT', ns )
        input = data.root()
        input.add( ns, 'RequestedState', '2' )
        doc = self.client.invoke( self.options, ns, method, data )
        assert doc is not None
        if (self.debug):
            print("%s" % doc)
        if doc.is_fault():
            f = doc.fault()
            print(f'{method} failed: {f.reason()}')
            return
        root = doc.root()
        value = root.find( ns, 'ReturnValue' )
        if value is None:
            print(f'Failed to start KVM redirection: {doc}')
            return
        if int(value.__str__()) == 0:
            print(f'KVM redirection started')
            return
        if int(value.__str__()) == 3:
            print(f'KVM redirection could not be enabled before timeout')
            return
        if int(value.__str__()) == 5:
            print('KVM redirection could not be enabled, invalid requested state')
            return
        if int(value.__str()) == 4096:
            print(f'KVM redirection successfully initiated')
            return
        print(f'KVM redirection could not be started, error code {value.__str__()}')

    def get_powerstate(self):
        power_state_map = ['unknown', 'other', 'on', 'sleep', 'deep-sleep',
                           'soft-reset', 'off',  'hibernate',
                           'soft-off', 'reset', 'bus-reset', 'nmi',
                           'graceful-soft-off', 'graceful-off',
                           'graceful-bus-reset', 'graceful-soft-reset',
                           'graceful-reset', 'diag']
        requested_state_map = ['unknown', 'other', 'on', 'sleep', 'deep-sleep',
                               'soft-reset', 'off', 'hibernate', 'soft-off',
                               'reset', 'bus-reset', 'nmi', 'n/a',
                               'graceful-soft-off', 'graceful-off',
                               'graceful-bus-reset', 'graceful-soft-reset',
                               'graceful-reset', 'diag']
        available_state_map = ['unknown', 'other', 'on', 'sleep', 'deep-sleep',
                               'soft-reset', 'off', 'hibernate', 'soft-off',
                               'reset', 'bus-reset', 'nmi',
                               'graceful-soft-off', 'graceful-off',
                               'graceful-bus-reset', 'graceful-soft-reset',
                               'graceful-reset']
        method = 'CIM_AssociatedPowerManagementService'
        self.client = Client( self.url )
        assert self.client is not None
        ns = XML_NS_CIM_CLASS + '/' + method
        doc = self.client.get( self.options, ns )
        assert doc is not None
        if (self.debug):
            print("%s" % doc)
        if doc.is_fault():
            f = doc.fault()
            print(f'{method} failed: {f.reason()}')
            return
        root = doc.root()
        requested = root.find( ns, "RequestedPowerState" )
        if (requested.__str__() == "None"):
            requested_state = 'None'
        elif (int(requested.__str__()) < 18):
            requested_state = requested_state_map[int(requested.__str__())]
        elif (int(requested.__str__()) < 32768):
            requested_state = 'DMTF Reserved (' + requested.__str__() + ')'
        else:
            requested_state = 'Vendor Reserved (' + requested.__str__() + ')'
        power = root.find( ns, "PowerState" )
        if (int(power.__str__()) < 17):
            power_state = power_state_map[int(power.__str__())]
        elif (int(power.__str__()) < 32768):
            power_state = 'DMTF Reserved (' + power.__str__() + ')'
        else:
            power_state = 'Vendor Reserved (' + power.__str() + ')'
        available = root.find( ns, "AvailableRequestedPowerStates" )
        if (int(available.__str__()) < 17):
            available_state = available_state_map[int(available.__str__())]
        elif (int(available.__str__()) < 32768):
            available_state = 'DMTF Reserved (' + available.__str__() + ')'
        else:
            available_state = 'Vendor Reserved (' + available.__str__() + ')'
        power = root.find( ns, "PowerState" )
        if (int(power.__str__()) < 17):
            power_state = power_state_map[int(power.__str__())]
        elif (int(power.__str__()) < 32768):
            power_state = 'DMTF Reserved (' + power.__str__() + ')'
        else:
            power_state = 'Vendor Reserved (' + power.__str() + ')'
        print(f'Power: {power_state}, Last Requested: {requested_state}, Available: {available_state}')

    def set_powerstate(self, requested_state):
        power_state = { 'on': 2, 'sleep': 3, 'deep-sleep': 4, 'soft-reset':5,
                        'off': 6, 'hibernate': 7, 'soft-off': 8,
                        'reset': 9, 'bus-reset': 10, 'nmi': 11,
                        'graceful-soft-off': 12, 'graceful-off': 13,
                        'graceful-bus-reset': 14, 'graceful-soft-reset': 15,
                        'graceful-reset': 16 }
        return_value_map = [ 'Completed with No Error', 'Not Supported',
                             'Unknown or Unspecified Error',
                             'Cannot complete within Timeout Period',
                             'Failed', 'Invalid Parameter', 'In Use' ]
        try:
            state = power_state[requested_state]
        except KeyError:
            print(f'Invalid power state {requested_state}')
            return
        ns = XML_NS_CIM_CLASS + '/CIM_PowerManagementService'
        method = 'RequestPowerStateChange'
        selector = 'CIM_ComputerSystem'
        data = XmlDoc(method + '_INPUT', ns)
        input = data.root()
        input.add( ns, 'PowerState', str(state))
        elem = input.add(ns, 'ManagedElement', '')
        elem.add( XML_NS_ADDRESSING, 'Address', WSA_TO_ANONYMOUS )
        ref = elem.add( XML_NS_ADDRESSING, 'ReferenceParameters', '')
        ref.add( XML_NS_WS_MAN, 'ResourceURI', XML_NS_CIM_CLASS + '/' + selector)
        sel = ref.add( XML_NS_WS_MAN, 'SelectorSet', '')
        class_name = sel.add( XML_NS_WS_MAN, 'Selector', selector)
        class_name.attr_add( None, 'Name', 'CreationClassName')
        name = sel.add( XML_NS_WS_MAN, 'Selector', 'ManagedSystem')
        name.attr_add( None, 'Name', 'Name')
        if (self.debug):
            print("%s" % data)
        self.client = Client( self.url )
        assert self.client is not None
        doc = self.client.invoke( self.options, ns, method, data )
        assert doc is not None
        if (self.debug):
            print("%s" % doc)
        root = doc.root()
        value = root.find( ns, "ReturnValue" )
        if (value is None):
            print(f'Error setting powerstate to {requested_state}: {doc}')
            return
        if ( int(value.__str__()) < 7 ):
            status = return_value_map[int(value.__str__())]
        elif ( int(value.__str__()) < 4096 ):
            status = 'DMTF Reserved (' + value.__str__() + ')'
        elif ( int(value.__str__()) == 4096 ):
            status = 'Method Parameters Checked - Job Started'
        elif ( int(value.__str__()) == 4097 ):
            status = 'Invalid State Transition'
        elif ( int(value.__str__()) == 4098 ):
            status = 'Use of Timeout Parameter Not Supported'
        elif ( int(value.__str__()) == 4099 ):
            status = 'Busy'
        elif ( int(value.__str__()) < 32768 ):
            status = 'Method Reserved'
        else:
            status = 'Vendor Specific (' + value.__str() + ')'

        print(f'Set powerstate to {requested_state}: {status}')

def arg_identify(args):
    a = wsman_amt(args.host, args.username, args.password)
    a.debug(args.debug)
    a.identify()

def arg_power(args):
    a = wsman_amt(args.host, args.username, args.password)
    a.debug(args.debug)
    if args.action == 'status':
        a.get_powerstate()
    else:
        a.set_powerstate(args.action)

def arg_serial(args):
    a = wsman_amt(args.host, args.username, args.password)
    a.debug(args.debug)
    if args.action == 'status':
        a.get_redirection()
    else:
        a.set_redirection(args.action, None)

def arg_ider(args):
    a = wsman_amt(args.host, args.username, args.password)
    a.debug(args.debug)
    if args.action == 'status':
        a.get_redirection()
    else:
        a.set_redirection(None, args.action)

def arg_listener(args):
    a = wsman_amt(args.host, args.username, args.password)
    a.debug(args.debug)
    if args.action == 'status':
        a.get_redirection()
    else:
        a.set_redirection_listener(args.action)

def arg_kvm(args):
    a = wsman_amt(args.host, args.username, args.password)
    a.debug(args.debug)
    if args.action == 'start':
        a.start_kvm_redirection()
    else:
        a.kvm_redirection(args.action)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-H', '--host', help='AMT host address', required=True)
    parser.add_argument('-U', '--username', help='AMT username', required=True)
    parser.add_argument('-P', '--password', help='AMT password', required=True)
    parser.add_argument('-p', '--port', help='AMT port, default 16992',
                        type=int, default=16992)
    parser.add_argument('-d', '--debug', help='Enable debugging',
                        action='count', default=0)
    subparsers = parser.add_subparsers()
    parser_identify = subparsers.add_parser('identify',
                                            help='identify AMT firmware')
    parser_identify.add_argument('detail', help='Firmware details',
                                 action='store_true')
    parser_identify.set_defaults(func=arg_identify)
    parser_power = subparsers.add_parser('power',
                                         help='Commands for controlling power state')
    parser_power.add_argument('action', help='AMT Power action',
                              choices=['status','on', 'off', 'reset',
                                       'soft-off', 'soft-reset', 'nmi',
                                       'bus-reset', 'graceful-bus-reset',
                                       'graceful-off', 'graceful-reset',
                                       'graceful-soft-off',
                                       'graceful-soft-reset',
                                       'hibernate', 'sleep', 'deep-sleep'])
    parser_power.set_defaults(func=arg_power)
    parser_serial = subparsers.add_parser('serial',
                                          help='Commands for controlling serial redirection')
    parser_serial.add_argument('action', help='AMT serial redirection action',
                               choices=['status','enable','disable'])
    parser_serial.set_defaults(func=arg_serial)
    parser_listener = subparsers.add_parser('listener',
                                          help='Commands for controlling redirection listener')
    parser_listener.add_argument('action', help='AMT redirection listener action',
                               choices=['status','enable','disable'])
    parser_listener.set_defaults(func=arg_listener)
    parser_ider = subparsers.add_parser('ider',
                                          help='Commands for controlling IDE redirection')
    parser_ider.add_argument('action', help='AMT IDE redirection action',
                             choices=['status','enable','disable'])
    parser_ider.set_defaults(func=arg_ider)
    parser_kvm = subparsers.add_parser('kvm',
                                       help='Commands for controlling KVM redirection')
    parser_kvm.add_argument('action', help='AMT KVM redirection action',
                             choices=['status','enable','disable','start'])
    parser_kvm.set_defaults(func=arg_kvm)

    args = parser.parse_args()
    try:
        args.func(args)
    except AttributeError:
        print("No command specified, must be one of 'identify,power,serial,listener,ider,kvm'")

if __name__ == "__main__":
    main()
