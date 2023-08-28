# OPCUA connection object
import time
class OPCUAcon(object):
    """"Parameters
    ----------
    configuration_id: selects configuration from self.master_conf dictionary for Tuning:
    "5" = GB, "6" = GC, "7" = GX, "8" = GY, "99" = Teststand
    machine_id: Agathon machine id
    connection_id: Network id for OPC UA server
    server_port: Port of the OPC UA server
    """

    def __init__(self, machine_id=163, connection_id="192.168.1.3", server_port="4840"):
        self.master_conf = {"5": {'sercosIP': '192.168.143.3,0,0',
                                  'axis': 'GB',
                                  'osc_param_1': '53', # S-0-0053
                                  'osc_param_2' : '84', # S-0-0084
                                  'osc_param_3' : '189', # S-0-0189
                                  'osc_param_4' : '32816', # P-0-0048 (32768+48)
                                  'nb_of_values': '8192', # Number of measurement values
                                  },
                            "6": {'sercosIP': '192.168.143.1,1,0',
                                  'axis': 'GC',
                                  'osc_param_1': '51', # S-0-0051
                                  'osc_param_2' : '84', # S-0-0084
                                  'osc_param_3' : '189', # S-0-0189
                                  'osc_param_4' : '32816', # P-0-0048 (32768+48)
                                  'nb_of_values': '8192',
                                 },
                            "7": {'sercosIP': '192.168.143.1,0,0',
                                  'axis': 'GX',
                                  'osc_param_1': '51', # S-0-0051
                                  'osc_param_2' : '84', # S-0-0084
                                  'osc_param_3' : '189', # S-0-0189
                                  'osc_param_4' : '32816', # P-0-0048 (32768+48)
                                  },
                            "8": {'sercosIP': '192.168.143.9,1,0',
                                  'axis': 'GY',
                                  'osc_param_1': '51', # S-0-0051
                                  'osc_param_2' : '84', # S-0-0084
                                  'osc_param_3' : '189', # S-0-0189
                                  'osc_param_4' : '32816', # P-0-0048 (32768+48)
                                  },
                            "99": {'sercosIP': '192.168.143.4,0,0',
                                   'axis': 'GC',
                                   'osc_param_1': '51', # S-0-0051
                                   'osc_param_2' : '84', # S-0-0084
                                   'osc_param_3' : '189', # S-0-0189
                                   'osc_param_4' : '32816', # P-0-0048 (32768+48)
                                  },
                            }
        self.configuration_id = [5,6,7,8]
        self.machine_id = machine_id
        self.connection_id = connection_id
        self.server_port = server_port
        self.timestamp_initialization = time.time()
        self.connection = None # OPC UA connection
        self.config = None
        self.con_ready = False # Flag determines if connection works and conditions, that have to be set manually by the operator are ok
        self.set_ready = False # Flag determines if configuration parameters are set
        self.get_config() # sets the internal parameters w.r.t. the configuration id
        # Master configuration, if new configuration is added, make sure to define all parameters
    def ReadAxis(self):
        # Connection to OPC Server
        self.connection = Client('opc.tcp://' + self.connection_id + ':' + self.server_port)
        self.connection.connect()
        self.DriveTemp=self.connection.get_node('ns=7;s="SercosIP,' + self.config['sercosIP'] +'".ParameterSet."' + 'P-0-0028' + '"')
    def get_config(self):
        """Selects the configuration w.r.t the axis given to the object, if an addition configuration is created
        for autotuning (e.g. additional axis, different speed for tuning), it can be added here"""
        try:
            self.config = self.master_conf[self.configuration_id]
            self.d_min = self.config['d_min'].copy()
            self.d_max = self.config['d_max'].copy()
            self.opt_dim = self.d_min.shape[0]
            self.Ti = self.config['T_i']
            self.w = self.config['w'].copy()
            self.w_con = self.config['w_con'].copy()
            self.constrlim = self.config['constr_lim']
            self.critlim = self.config['crit_lim']
            self.faclim = self.config['fac_lim']
            self.iterinit = self.config['iter_init']
            self.iterlim = self.config['iter_lim']
            self.stop_eic_abs = self.config['stop_eic_abs']
            self.x_nom = self.config['x_nom'].copy()
            self.crit_step = self.config['crit_step'].copy()
        except:
            self.config = None
            print("No configuration ",self.configuration_id, " found or configuration incomplete")
    def init_connection(self):
        """Initializes the connection with the OPC UA server and sets the corresponding
        nodes w.r.t the parameter self.config, this has to be called first before auto-tuning can be started"""
        if self.config is None:
            print("No configuration selected")
        else:
            # Set the client url
            self.connection = Client('opc.tcp://' + self.connection_id + ':' + self.server_port)
            self.check_conditions()

            try:
                # initialize axis
                print("axis to be measured is ",self.config['axis'])
                self.set_ready = True

                # Trigger-Signal set
                trigger_sig = self.connection.get_node('ns=7;s="SercosIP,' + self.config['sercosIP'] +'".ParameterSet."P-0-0026"')
                trigger_sig.set_value(int(self.config['trigger_sig_set']))
                if trigger_sig.get_value() >= 32768:
                    print('Trigger signal is set to: P-' + str(trigger_sig.get_value()-32768))
                else:
                    print('Trigger signal is set to: S-' + str(trigger_sig.get_value()))
                if trigger_sig.get_value() != int(self.config['trigger_sig_set']):
                    self.set_ready = False

                # Trigger-Value set
                trigger_tresh = self.connection.get_node('ns=7;s="SercosIP,' + self.config['sercosIP'] +'".ParameterSet."P-0-0027"')
                trigger_tresh.set_value(int(int(self.config['trigger_tresh_set'])*1000)) # time 1000, since extension by 4 digits
                print('Trigger Treshold set to: ' + str(trigger_tresh.get_value()/1000))
                if trigger_tresh.get_value()/1000 != int(self.config['trigger_tresh_set']):
                    self.set_ready = False

                # Set the parameters for each of the 4 Oscilloscopes to be monitored.
                # Oscilloscope parameter sets are: P-0-0023, P-0-0024, P-0-0147, P-0-0148
                # Oscilloscope lists with the measured values are: P-0-0021, P-0-0022, P-0-0145, P-0-0146
                osc1 = self.connection.get_node('ns=7;s="SercosIP,' + self.config['sercosIP'] +'".ParameterSet."' + 'P-0-0023' + '"')
                osc2 = self.connection.get_node('ns=7;s="SercosIP,' + self.config['sercosIP'] +'".ParameterSet."' + 'P-0-0024' + '"')
                osc3 = self.connection.get_node('ns=7;s="SercosIP,' + self.config['sercosIP'] +'".ParameterSet."' + 'P-0-0147' + '"')
                osc4 = self.connection.get_node('ns=7;s="SercosIP,' + self.config['sercosIP'] +'".ParameterSet."' + 'P-0-0148' + '"')
                osc1parval = int(self.config['osc_param_1'])
                osc2parval = int(self.config['osc_param_2'])
                osc3parval = int(self.config['osc_param_3'])
                osc4parval = int(self.config['osc_param_4'])
                osc1.set_value(osc1parval, ua.VariantType.Int32)
                osc2.set_value(osc2parval, ua.VariantType.Int32)
                osc3.set_value(osc3parval, ua.VariantType.Int32)
                osc4.set_value(osc4parval, ua.VariantType.Int32)

            except:
                self.con_ready = False
                self.connection.disconnect()
                print('Could not set one or multiple params - no connection?')
